-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: sistema_hospitalario
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `ausencias_doctor`
--

DROP TABLE IF EXISTS `ausencias_doctor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ausencias_doctor` (
  `id_ausencia` int unsigned NOT NULL AUTO_INCREMENT,
  `id_doctor` int unsigned NOT NULL,
  `inicio` datetime NOT NULL,
  `fin` datetime NOT NULL,
  `motivo` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_ausencia`),
  KEY `idx_ausencia_doctor` (`id_doctor`,`inicio`,`fin`),
  CONSTRAINT `fk_ausencia_doctor` FOREIGN KEY (`id_doctor`) REFERENCES `doctores` (`id_doctor`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `citas`
--

DROP TABLE IF EXISTS `citas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `citas` (
  `id_cita` int unsigned NOT NULL AUTO_INCREMENT,
  `id_paciente` int unsigned NOT NULL,
  `id_doctor` int unsigned NOT NULL,
  `id_servicio` int unsigned NOT NULL,
  `fecha_cita` date NOT NULL,
  `hora_cita` time NOT NULL,
  `duracion_minutos` int unsigned NOT NULL,
  `motivo_consulta` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` enum('confirmada','cancelada') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'confirmada',
  `cancelada_por` enum('paciente','medico') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cancelada_en` datetime DEFAULT NULL,
  `id_cita_anterior` int unsigned DEFAULT NULL,
  `creada_en` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_cita`),
  KEY `idx_cita_agenda` (`id_doctor`,`fecha_cita`,`estado`),
  KEY `fk_cita_paciente` (`id_paciente`),
  KEY `fk_cita_servicio` (`id_servicio`),
  CONSTRAINT `fk_cita_doctor` FOREIGN KEY (`id_doctor`) REFERENCES `doctores` (`id_doctor`),
  CONSTRAINT `fk_cita_paciente` FOREIGN KEY (`id_paciente`) REFERENCES `pacientes` (`id_paciente`),
  CONSTRAINT `fk_cita_servicio` FOREIGN KEY (`id_servicio`) REFERENCES `servicios` (`id_servicio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `doctores`
--

DROP TABLE IF EXISTS `doctores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `doctores` (
  `id_doctor` int unsigned NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `especialidad` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id_doctor`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `horarios_doctor`
--

DROP TABLE IF EXISTS `horarios_doctor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `horarios_doctor` (
  `id_horario` int unsigned NOT NULL AUTO_INCREMENT,
  `id_doctor` int unsigned NOT NULL,
  `dia_semana` enum('lunes','martes','miercoles','jueves','viernes','sabado','domingo') COLLATE utf8mb4_unicode_ci NOT NULL,
  `hora_inicio` time NOT NULL,
  `hora_fin` time NOT NULL,
  PRIMARY KEY (`id_horario`),
  KEY `idx_horario_doctor_dia` (`id_doctor`,`dia_semana`),
  CONSTRAINT `fk_horario_doctor` FOREIGN KEY (`id_doctor`) REFERENCES `doctores` (`id_doctor`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pacientes`
--

DROP TABLE IF EXISTS `pacientes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pacientes` (
  `id_paciente` int unsigned NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `apellidos` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `telefono` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id_paciente`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `servicios`
--

DROP TABLE IF EXISTS `servicios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servicios` (
  `id_servicio` int unsigned NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `duracion_minutos` int unsigned NOT NULL,
  PRIMARY KEY (`id_servicio`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'sistema_hospitalario'
--
/*!50003 DROP PROCEDURE IF EXISTS `sp_reservar_cita` */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_0900_ai_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
CREATE DEFINER=`root`@`localhost` PROCEDURE `sp_reservar_cita`(
    IN  p_id_paciente      INT,
    IN  p_id_doctor        INT,
    IN  p_id_servicio      INT,
    IN  p_fecha_cita       DATE,
    IN  p_hora_cita        TIME,
    IN  p_motivo_consulta  VARCHAR(500),
    IN  p_id_cita_anterior INT,
    OUT p_resultado        VARCHAR(100)
)
sp: BEGIN
    DECLARE v_duracion  INT;
    DECLARE v_conteo    INT;
    DECLARE v_inicio    DATETIME;
    DECLARE v_fin       DATETIME;
    DECLARE v_id_cita   INT;

    -- Deadlock (1213) o espera de bloqueo agotada (1205): conflicto estable.
    DECLARE EXIT HANDLER FOR 1213, 1205
    BEGIN
        ROLLBACK;
        SET p_resultado = 'CONFLICT:DEADLOCK';
    END;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_resultado = 'ERROR:SQL_EXCEPTION';
    END;

    -- Validaciones que no necesitan bloqueo.
    IF p_fecha_cita < CURDATE() THEN
        SET p_resultado = 'VALIDATION:PAST_DATE';
        LEAVE sp;
    END IF;

    SET v_conteo = (SELECT COUNT(*) FROM pacientes WHERE id_paciente = p_id_paciente);
    IF v_conteo = 0 THEN
        SET p_resultado = 'VALIDATION:PATIENT_NOT_FOUND';
        LEAVE sp;
    END IF;

    SET v_duracion = (SELECT duracion_minutos FROM servicios WHERE id_servicio = p_id_servicio);
    IF v_duracion IS NULL THEN
        SET p_resultado = 'VALIDATION:SERVICE_NOT_FOUND';
        LEAVE sp;
    END IF;

    SET v_inicio = TIMESTAMP(p_fecha_cita, p_hora_cita);
    SET v_fin    = DATE_ADD(v_inicio, INTERVAL v_duracion MINUTE);

    START TRANSACTION;

    -- Bloquea la agenda del medico: nadie mas reserva con este medico hasta el COMMIT.
    SELECT COUNT(*) INTO v_conteo FROM doctores WHERE id_doctor = p_id_doctor FOR UPDATE;
    IF v_conteo = 0 THEN
        ROLLBACK;
        SET p_resultado = 'VALIDATION:DOCTOR_NOT_FOUND';
        LEAVE sp;
    END IF;

    -- La franja debe caber completa dentro de un bloque de la jornada.
    SELECT COUNT(*) INTO v_conteo
      FROM horarios_doctor
     WHERE id_doctor  = p_id_doctor
       AND dia_semana = ELT(WEEKDAY(p_fecha_cita) + 1,
                            'lunes','martes','miercoles','jueves','viernes','sabado','domingo')
       AND hora_inicio <= p_hora_cita
       AND ADDTIME(p_hora_cita, SEC_TO_TIME(v_duracion * 60)) <= hora_fin;
    IF v_conteo = 0 THEN
        ROLLBACK;
        SET p_resultado = 'VALIDATION:OUTSIDE_SCHEDULE';
        LEAVE sp;
    END IF;

    -- Ausencias del medico que se traslapen con la franja.
    SELECT COUNT(*) INTO v_conteo
      FROM ausencias_doctor
     WHERE id_doctor = p_id_doctor AND inicio < v_fin AND fin > v_inicio;
    IF v_conteo > 0 THEN
        ROLLBACK;
        SET p_resultado = 'CONFLICT:DOCTOR_ABSENT';
        LEAVE sp;
    END IF;

    -- Citas confirmadas que se traslapen (las canceladas no cuentan).
    SELECT COUNT(*) INTO v_conteo
      FROM citas
     WHERE id_doctor = p_id_doctor
       AND estado = 'confirmada'
       AND TIMESTAMP(fecha_cita, hora_cita) < v_fin
       AND DATE_ADD(TIMESTAMP(fecha_cita, hora_cita), INTERVAL duracion_minutos MINUTE) > v_inicio;
    IF v_conteo > 0 THEN
        ROLLBACK;
        SET p_resultado = 'CONFLICT:SLOT_TAKEN';
        LEAVE sp;
    END IF;

    -- Reprogramacion: cancela la cita anterior del mismo paciente en la misma transaccion.
    IF p_id_cita_anterior IS NOT NULL THEN
        SELECT COUNT(*) INTO v_conteo
          FROM citas
         WHERE id_cita = p_id_cita_anterior
           AND id_paciente = p_id_paciente
           AND estado = 'confirmada';
        IF v_conteo = 0 THEN
            ROLLBACK;
            SET p_resultado = 'VALIDATION:PREVIOUS_APPOINTMENT_INVALID';
            LEAVE sp;
        END IF;
        UPDATE citas
           SET estado = 'cancelada', cancelada_por = 'paciente', cancelada_en = NOW()
         WHERE id_cita = p_id_cita_anterior;
    END IF;

    INSERT INTO citas (id_paciente, id_doctor, id_servicio, fecha_cita, hora_cita,
                       duracion_minutos, motivo_consulta, estado, id_cita_anterior)
    VALUES (p_id_paciente, p_id_doctor, p_id_servicio, p_fecha_cita, p_hora_cita,
            v_duracion, p_motivo_consulta, 'confirmada', p_id_cita_anterior);
    SET v_id_cita = LAST_INSERT_ID();

    COMMIT;
    SET p_resultado = CONCAT('OK:APPOINTMENT_CONFIRMED:', v_id_cita);
END ;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-25 21:22:02
