-- =============================================================================
-- DATOS MINIMOS PARA LA DEMOSTRACION
-- Ejecutar despues de 01_INSTALAR_BASE_CORREGIDA.sql.
-- No borra datos existentes y se puede ejecutar mas de una vez.
-- =============================================================================

USE sistema_hospitalario;
START TRANSACTION;

INSERT INTO cuentas_usuario (email, password_hash, rol, estado_cuenta)
VALUES
    ('paciente.demo@hospital.local', 'solo_demo_sin_login', 'Paciente', 'Activo'),
    ('doctor.demo@hospital.local', 'solo_demo_sin_login', 'Doctor', 'Activo')
ON DUPLICATE KEY UPDATE email = VALUES(email);

INSERT INTO especialidades (nombre_especialidad, descripcion)
VALUES ('Medicina general', 'Especialidad de demostracion')
ON DUPLICATE KEY UPDATE descripcion = VALUES(descripcion);

INSERT INTO pacientes (
    id_usuario, nombre, apellido1, apellido2, codigo_postal,
    numero_telefono, fecha_nacimiento, tipo_sangre, sexo
)
SELECT
    u.id_usuario, 'Paola', 'Paciente', 'Demo', '06000',
    '5550000001', '1998-01-15', 'O+', 'F'
FROM cuentas_usuario AS u
WHERE u.email = 'paciente.demo@hospital.local'
ON DUPLICATE KEY UPDATE numero_telefono = VALUES(numero_telefono);

INSERT INTO doctores (
    id_usuario, id_especialidad, nombre, apellido1, apellido2,
    codigo_postal, num_telefono, fecha_nacimiento, sexo
)
SELECT
    u.id_usuario, e.id_especialidad, 'Daniel', 'Doctor', 'Demo',
    '06000', '5550000002', '1980-05-20', 'M'
FROM cuentas_usuario AS u
INNER JOIN especialidades AS e ON e.nombre_especialidad = 'Medicina general'
WHERE u.email = 'doctor.demo@hospital.local'
ON DUPLICATE KEY UPDATE
    id_especialidad = VALUES(id_especialidad),
    num_telefono = VALUES(num_telefono);

INSERT INTO servicios (nombre_servicio, costo, duracion_minutos)
SELECT 'Consulta general demo', 350.00, 30
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM servicios WHERE nombre_servicio = 'Consulta general demo'
);

-- Jueves, de 09:00 a 14:00. Para mañana use la fecha 2026-10-22.
INSERT INTO horarios_medicos (id_doctor, dia_semana, hora_inicio, hora_fin)
SELECT d.id_doctor, 'Jueves', '09:00:00', '14:00:00'
FROM doctores AS d
INNER JOIN cuentas_usuario AS u ON u.id_usuario = d.id_usuario
WHERE u.email = 'doctor.demo@hospital.local'
  AND NOT EXISTS (
      SELECT 1
      FROM horarios_medicos AS h
      WHERE h.id_doctor = d.id_doctor
        AND h.dia_semana = 'Jueves'
        AND h.hora_inicio = '09:00:00'
        AND h.hora_fin = '14:00:00'
  );

COMMIT;

-- Copie estos tres numeros en la interfaz Flet.
SELECT p.id_paciente AS id_paciente
FROM pacientes AS p
INNER JOIN cuentas_usuario AS u ON u.id_usuario = p.id_usuario
WHERE u.email = 'paciente.demo@hospital.local';

SELECT d.id_doctor AS id_doctor
FROM doctores AS d
INNER JOIN cuentas_usuario AS u ON u.id_usuario = d.id_usuario
WHERE u.email = 'doctor.demo@hospital.local';

SELECT id_servicio
FROM servicios
WHERE nombre_servicio = 'Consulta general demo';
