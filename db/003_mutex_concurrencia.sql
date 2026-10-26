-- MIGRACION NO DESTRUCTIVA de la versión anterior. Ejecutar UNA VEZ.
-- Detener el backend durante esta migración y respaldar antes con Workbench.
-- No ejecutar 01_INSTALAR_BASE_CORREGIDA.sql sobre datos que desea conservar.
-- DDL hace commit implícito en MySQL. Luego reemplazar el procedimiento.
USE sistema_hospitalario;
ALTER TABLE citas
    DROP INDEX uk_doctor_fecha_hora,
    ADD COLUMN horario_ocupado TINYINT
        GENERATED ALWAYS AS (
            CASE WHEN estado IN ('Pendiente', 'Confirmada', 'Completada')
                 THEN 1 ELSE NULL END
        ) STORED,
    ADD UNIQUE KEY uk_doctor_fecha_hora (id_doctor, fecha_cita, hora_cita, horario_ocupado);

-- El primer SELECT dentro de la transacción debe ser el candado del doctor.
-- Así la lectura consistente de citas comienza DESPUÉS de adquirirlo, incluso
-- en REPEATABLE READ. Cancelación respeta el mismo orden doctor -> cita.
USE sistema_hospitalario;

DELIMITER //

DROP PROCEDURE IF EXISTS sp_reservar_cita //

CREATE PROCEDURE sp_reservar_cita(
    IN p_id_paciente INT,
    IN p_id_doctor INT,
    IN p_id_servicio INT,
    IN p_fecha_cita DATE,
    IN p_hora_cita TIME,
    IN p_motivo_consulta TEXT,
    IN p_id_cita_anterior INT,
    OUT p_resultado VARCHAR(255)
)
proc_label: BEGIN
    DECLARE v_doctor_id INT DEFAULT NULL;
    DECLARE v_patient_id INT DEFAULT NULL;
    DECLARE v_absences INT DEFAULT 0;
    DECLARE v_service_duration INT DEFAULT NULL;
    DECLARE v_schedule_matches INT DEFAULT 0;
    DECLARE v_overlaps INT DEFAULT 0;
    DECLARE v_found BOOLEAN DEFAULT TRUE;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_found = FALSE;
    DECLARE EXIT HANDLER FOR 1062
    BEGIN
        ROLLBACK;
        SET p_resultado = 'CONFLICT:SLOT_TAKEN';
    END;
    DECLARE EXIT HANDLER FOR 1205
    BEGIN
        ROLLBACK;
        SET p_resultado = 'CONFLICT:LOCK_TIMEOUT';
    END;
    DECLARE EXIT HANDLER FOR 1213
    BEGIN
        ROLLBACK;
        SET p_resultado = 'CONFLICT:DEADLOCK_RETRY';
    END;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_resultado = 'ERROR:TRANSACTION_FAILED';
    END;

    START TRANSACTION;

    -- Candado pesimista que serializa reservas del mismo médico entre procesos.
    SET v_found = TRUE;
    SELECT id_doctor INTO v_doctor_id
    FROM doctores
    WHERE id_doctor = p_id_doctor
    FOR UPDATE;
    IF NOT v_found THEN
        ROLLBACK;
        SET p_resultado = 'VALIDATION:DOCTOR_NOT_FOUND';
        LEAVE proc_label;
    END IF;

    SET v_found = TRUE;
    SELECT id_paciente INTO v_patient_id
    FROM pacientes
    WHERE id_paciente = p_id_paciente;
    IF NOT v_found THEN
        ROLLBACK;
        SET p_resultado = 'VALIDATION:PATIENT_NOT_FOUND';
        LEAVE proc_label;
    END IF;

    SET v_found = TRUE;
    SELECT duracion_minutos INTO v_service_duration
    FROM servicios
    WHERE id_servicio = p_id_servicio;
    IF NOT v_found THEN
        ROLLBACK;
        SET p_resultado = 'VALIDATION:SERVICE_NOT_FOUND';
        LEAVE proc_label;
    END IF;

    SELECT COUNT(*) INTO v_schedule_matches
    FROM horarios_medicos
    WHERE id_doctor = p_id_doctor
      AND dia_semana = ELT(WEEKDAY(p_fecha_cita) + 1,
          'Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo')
      AND hora_inicio <= p_hora_cita
      AND hora_fin >= ADDTIME(p_hora_cita, SEC_TO_TIME(v_service_duration * 60));
    IF v_schedule_matches = 0 THEN
        ROLLBACK;
        SET p_resultado = 'VALIDATION:OUTSIDE_WORKING_HOURS';
        LEAVE proc_label;
    END IF;

    SELECT COUNT(*) INTO v_absences
    FROM ausencias_medicos
    WHERE id_doctor = p_id_doctor
      AND estado = 'Aprobado'
      AND fecha_inicio < DATE_ADD(TIMESTAMP(p_fecha_cita, p_hora_cita), INTERVAL v_service_duration MINUTE)
      AND fecha_fin >= TIMESTAMP(p_fecha_cita, p_hora_cita);
    IF v_absences > 0 THEN
        ROLLBACK;
        SET p_resultado = 'CONFLICT:DOCTOR_ABSENT';
        LEAVE proc_label;
    END IF;

    -- Con el candado del médico ya tomado, esta verificación no tiene ventana de carrera.
    SELECT COUNT(*) INTO v_overlaps
    FROM citas AS c
    INNER JOIN servicios AS s ON s.id_servicio = c.id_servicio
    WHERE c.id_doctor = p_id_doctor
      AND c.fecha_cita = p_fecha_cita
      AND c.estado IN ('Pendiente', 'Confirmada', 'Completada')
      AND c.hora_cita < ADDTIME(p_hora_cita, SEC_TO_TIME(v_service_duration * 60))
      AND ADDTIME(c.hora_cita, SEC_TO_TIME(s.duracion_minutos * 60)) > p_hora_cita;
    IF v_overlaps > 0 THEN
        ROLLBACK;
        SET p_resultado = 'CONFLICT:SLOT_TAKEN';
        LEAVE proc_label;
    END IF;

    -- Cada reserva recibe un ID nuevo; nunca sobrescribir una cita histórica.
    INSERT INTO citas (
        id_paciente, id_doctor, id_servicio, id_cita_anterior,
        fecha_cita, hora_cita, estado, motivo_consulta
    ) VALUES (
        p_id_paciente, p_id_doctor, p_id_servicio, p_id_cita_anterior,
        p_fecha_cita, p_hora_cita, 'Confirmada', p_motivo_consulta
    );

    COMMIT;
    SET p_resultado = 'OK:APPOINTMENT_CONFIRMED';
END //

DELIMITER ;
