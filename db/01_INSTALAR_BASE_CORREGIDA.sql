-- =============================================================================
-- SISTEMA HOSPITALARIO DE GESTION DE CITAS - SPRINT 2
-- MySQL 8 / InnoDB
--
-- EJECUTAR SOLO EN UNA INSTALACION DE DEMOSTRACION NUEVA.
-- Este archivo elimina la base "sistema_hospitalario" y la crea de nuevo.
-- Despues ejecute 02_CARGAR_DATOS_DEMO.sql.
-- =============================================================================

DROP DATABASE IF EXISTS sistema_hospitalario;
CREATE DATABASE sistema_hospitalario
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE sistema_hospitalario;

-- USUARIOS, PACIENTES Y DOCTORES
CREATE TABLE cuentas_usuario (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('Paciente', 'Doctor', 'Admin') NOT NULL DEFAULT 'Paciente',
    estado_cuenta ENUM('Activo', 'Inactivo', 'Pendiente') NOT NULL DEFAULT 'Activo',
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE pacientes (
    id_paciente INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL UNIQUE,
    nombre VARCHAR(50) NOT NULL,
    apellido1 VARCHAR(50) NOT NULL,
    apellido2 VARCHAR(50),
    codigo_postal VARCHAR(10),
    numero_telefono VARCHAR(15),
    fecha_nacimiento DATE NOT NULL,
    tipo_sangre VARCHAR(5),
    sexo ENUM('M', 'F', 'Otro') NOT NULL,
    CONSTRAINT fk_paciente_usuario FOREIGN KEY (id_usuario)
        REFERENCES cuentas_usuario(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE especialidades (
    id_especialidad INT AUTO_INCREMENT PRIMARY KEY,
    nombre_especialidad VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT
) ENGINE=InnoDB;

CREATE TABLE doctores (
    id_doctor INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL UNIQUE,
    id_especialidad INT NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    apellido1 VARCHAR(50) NOT NULL,
    apellido2 VARCHAR(50),
    codigo_postal VARCHAR(10),
    num_telefono VARCHAR(15),
    fecha_nacimiento DATE NOT NULL,
    sexo ENUM('M', 'F', 'Otro') NOT NULL,
    CONSTRAINT fk_doctor_usuario FOREIGN KEY (id_usuario)
        REFERENCES cuentas_usuario(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_doctor_especialidad FOREIGN KEY (id_especialidad)
        REFERENCES especialidades(id_especialidad) ON UPDATE CASCADE
) ENGINE=InnoDB;

-- AGENDA, DISPONIBILIDAD Y CITAS
CREATE TABLE servicios (
    id_servicio INT AUTO_INCREMENT PRIMARY KEY,
    nombre_servicio VARCHAR(100) NOT NULL,
    costo DECIMAL(10, 2) NOT NULL CHECK (costo >= 0),
    duracion_minutos INT NOT NULL DEFAULT 30 CHECK (duracion_minutos > 0)
) ENGINE=InnoDB;

CREATE TABLE horarios_medicos (
    id_horario INT AUTO_INCREMENT PRIMARY KEY,
    id_doctor INT NOT NULL,
    dia_semana ENUM('Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo') NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    CONSTRAINT fk_horario_doctor FOREIGN KEY (id_doctor)
        REFERENCES doctores(id_doctor) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_rango_horas CHECK (hora_fin > hora_inicio)
) ENGINE=InnoDB;

CREATE TABLE ausencias_medicos (
    id_ausencia INT AUTO_INCREMENT PRIMARY KEY,
    id_doctor INT NOT NULL,
    fecha_inicio DATETIME NOT NULL,
    fecha_fin DATETIME NOT NULL,
    motivo ENUM('Vacaciones', 'Incapacidad', 'Permiso', 'Personal') NOT NULL,
    estado ENUM('Pendiente', 'Aprobado', 'Cancelado') DEFAULT 'Aprobado',
    CONSTRAINT fk_ausencia_doctor FOREIGN KEY (id_doctor)
        REFERENCES doctores(id_doctor) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_rango_fechas_ausencia CHECK (fecha_fin >= fecha_inicio)
) ENGINE=InnoDB;

CREATE TABLE citas (
    id_cita INT AUTO_INCREMENT PRIMARY KEY,
    id_paciente INT NOT NULL,
    id_doctor INT NOT NULL,
    id_servicio INT NOT NULL,
    id_cita_anterior INT NULL,
    fecha_cita DATE NOT NULL,
    hora_cita TIME NOT NULL,
    estado ENUM('Pendiente', 'Confirmada', 'Completada', 'Cancelada_Paciente', 'Cancelada_Medico')
        NOT NULL DEFAULT 'Pendiente',
    motivo_consulta TEXT,
    fecha_cancelacion DATETIME NULL,
    CONSTRAINT fk_cita_paciente FOREIGN KEY (id_paciente)
        REFERENCES pacientes(id_paciente) ON UPDATE CASCADE,
    CONSTRAINT fk_cita_doctor FOREIGN KEY (id_doctor)
        REFERENCES doctores(id_doctor) ON UPDATE CASCADE,
    CONSTRAINT fk_cita_servicio FOREIGN KEY (id_servicio)
        REFERENCES servicios(id_servicio) ON UPDATE CASCADE,
    CONSTRAINT fk_cita_seguimiento FOREIGN KEY (id_cita_anterior)
        REFERENCES citas(id_cita) ON DELETE SET NULL ON UPDATE CASCADE,
    -- NULL permite conservar cancelaciones; las ocupadas siguen siendo únicas.
    horario_ocupado TINYINT GENERATED ALWAYS AS (
        CASE WHEN estado IN ('Pendiente', 'Confirmada', 'Completada') THEN 1 ELSE NULL END
    ) STORED,
    UNIQUE KEY uk_doctor_fecha_hora (id_doctor, fecha_cita, hora_cita, horario_ocupado)
) ENGINE=InnoDB;

-- EXPEDIENTE CLINICO, CONSULTAS Y RECETAS
CREATE TABLE expedientes_clinicos (
    id_expediente INT AUTO_INCREMENT PRIMARY KEY,
    id_paciente INT NOT NULL UNIQUE,
    fecha_creacion DATE NOT NULL DEFAULT (CURRENT_DATE),
    antecedentes_medicos TEXT,
    CONSTRAINT fk_expediente_paciente FOREIGN KEY (id_paciente)
        REFERENCES pacientes(id_paciente) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE consultas_medicas (
    id_consulta INT AUTO_INCREMENT PRIMARY KEY,
    id_cita INT NOT NULL UNIQUE,
    id_expediente INT NOT NULL,
    diagnostico TEXT NOT NULL,
    sintomas TEXT,
    notas_medicas TEXT,
    CONSTRAINT fk_consulta_cita FOREIGN KEY (id_cita)
        REFERENCES citas(id_cita) ON UPDATE CASCADE,
    CONSTRAINT fk_consulta_expediente FOREIGN KEY (id_expediente)
        REFERENCES expedientes_clinicos(id_expediente) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE recetas_medicas (
    id_receta INT AUTO_INCREMENT PRIMARY KEY,
    id_consulta INT NOT NULL,
    fecha_emision DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_receta_consulta FOREIGN KEY (id_consulta)
        REFERENCES consultas_medicas(id_consulta) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE medicamentos (
    id_medicamento INT AUTO_INCREMENT PRIMARY KEY,
    nombre_comercial VARCHAR(100) NOT NULL,
    formula VARCHAR(150) NOT NULL,
    presentacion VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE detalles_receta (
    id_detalle INT AUTO_INCREMENT PRIMARY KEY,
    id_receta INT NOT NULL,
    id_medicamento INT NOT NULL,
    dosis VARCHAR(100) NOT NULL,
    frecuencia_horas INT NOT NULL,
    duracion_dias INT NOT NULL,
    CONSTRAINT fk_detalle_receta FOREIGN KEY (id_receta)
        REFERENCES recetas_medicas(id_receta) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_detalle_medicamento FOREIGN KEY (id_medicamento)
        REFERENCES medicamentos(id_medicamento) ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_citas_busqueda ON citas(id_doctor, fecha_cita, hora_cita, estado);
CREATE INDEX idx_ausencias_fecha ON ausencias_medicos(id_doctor, fecha_inicio, fecha_fin);

-- Procedimiento actualizado. Orden: candado doctor antes de leer agenda.
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
