from datetime import date, datetime, time, timedelta

from app.domain.contracts import CancelacionOrigen, ReservaCitaRequest
from app.infrastructure.mysql import Database


ACTIVE_APPOINTMENT_STATES = ("Pendiente", "Confirmada")


def mysql_time(value: time | timedelta) -> time:
    """Connector/Python entrega columnas TIME como timedelta, no siempre time."""
    if isinstance(value, timedelta):
        return (datetime.min + value).time()
    return value


class AgendaRepository:
    def __init__(self, database: Database) -> None:
        self._database = database
        self._compact = getattr(database, "compact_schema", False)

    def doctor_exists(self, doctor_id: int) -> bool:
        with self._database.cursor() as (_, cursor):
            cursor.execute("SELECT 1 FROM doctores WHERE id_doctor = %s", (doctor_id,))
            return cursor.fetchone() is not None

    def patient_exists(self, patient_id: int) -> bool:
        with self._database.cursor() as (_, cursor):
            cursor.execute("SELECT 1 FROM pacientes WHERE id_paciente = %s", (patient_id,))
            return cursor.fetchone() is not None

    def service_duration(self, service_id: int) -> int | None:
        with self._database.cursor() as (_, cursor):
            cursor.execute("SELECT duracion_minutos FROM servicios WHERE id_servicio = %s", (service_id,))
            row = cursor.fetchone()
            return int(row["duracion_minutos"]) if row else None

    def weekly_schedule(self, doctor_id: int, day_name: str) -> list[tuple[time, time]]:
        table = "horarios_doctor" if self._compact else "horarios_medicos"
        with self._database.cursor() as (_, cursor):
            cursor.execute(
                f"""
                SELECT hora_inicio, hora_fin
                FROM {table}
                WHERE id_doctor = %s AND dia_semana = %s
                ORDER BY hora_inicio
                """,
                (doctor_id, day_name.lower() if self._compact else day_name),
            )
            return [(mysql_time(row["hora_inicio"]), mysql_time(row["hora_fin"])) for row in cursor.fetchall()]

    def approved_absences(self, doctor_id: int, on_date: date) -> list[tuple[datetime, datetime]]:
        starts_at = datetime.combine(on_date, time.min)
        ends_at = datetime.combine(on_date, time.max)
        with self._database.cursor() as (_, cursor):
            if self._compact:
                cursor.execute(
                    "SELECT inicio AS fecha_inicio, fin AS fecha_fin FROM ausencias_doctor "
                    "WHERE id_doctor = %s AND inicio <= %s AND fin >= %s",
                    (doctor_id, ends_at, starts_at),
                )
                return [(row["fecha_inicio"], row["fecha_fin"]) for row in cursor.fetchall()]
            cursor.execute(
                """
                SELECT fecha_inicio, fecha_fin
                FROM ausencias_medicos
                WHERE id_doctor = %s
                  AND estado = 'Aprobado'
                  AND fecha_inicio <= %s
                  AND fecha_fin >= %s
                """,
                (doctor_id, ends_at, starts_at),
            )
            return [(row["fecha_inicio"], row["fecha_fin"]) for row in cursor.fetchall()]

    def active_appointments(self, doctor_id: int, on_date: date) -> list[tuple[time, int]]:
        with self._database.cursor() as (_, cursor):
            if self._compact:
                # La duración se conserva en cada cita, aunque cambie el catálogo.
                cursor.execute(
                    "SELECT hora_cita, duracion_minutos FROM citas "
                    "WHERE id_doctor = %s AND fecha_cita = %s AND estado = 'confirmada' "
                    "ORDER BY hora_cita",
                    (doctor_id, on_date),
                )
                return [(mysql_time(row["hora_cita"]), int(row["duracion_minutos"]))
                        for row in cursor.fetchall()]
            cursor.execute(
                """
                SELECT c.hora_cita, s.duracion_minutos
                FROM citas AS c
                INNER JOIN servicios AS s ON s.id_servicio = c.id_servicio
                WHERE c.id_doctor = %s
                  AND c.fecha_cita = %s
                  AND c.estado IN (%s, %s, 'Completada')
                ORDER BY c.hora_cita
                """,
                (doctor_id, on_date, *ACTIVE_APPOINTMENT_STATES),
            )
            return [(mysql_time(row["hora_cita"]), int(row["duracion_minutos"])) for row in cursor.fetchall()]

    def call_reservation_procedure(self, request: ReservaCitaRequest) -> str | None:
        """El procedimiento controla su propia transacción; no abrir otra aquí."""
        args = (
            request.id_paciente,
            request.id_doctor,
            request.id_servicio,
            request.fecha_cita,
            request.hora_cita,
            request.motivo_consulta,
            request.id_cita_anterior,
            None,
        )
        with self._database.cursor() as (_, cursor):
            returned_args = cursor.callproc("sp_reservar_cita", args)
            # Se consumen result sets por si una implementación futura emite alguno.
            for result_set in cursor.stored_results():
                result_set.fetchall()
            if isinstance(returned_args, dict):
                # Con dictionary=True, Connector/Python nombra los parámetros
                # sp_reservar_cita_arg1 ... arg8. El OUT es el octavo.
                return returned_args["sp_reservar_cita_arg8"]
            return returned_args[-1]

    def appointment_doctor(self, appointment_id: int) -> int | None:
        with self._database.cursor() as (_, cursor):
            cursor.execute("SELECT id_doctor FROM citas WHERE id_cita = %s", (appointment_id,))
            row = cursor.fetchone()
            return int(row["id_doctor"]) if row else None

    def cancel_appointment(self, appointment_id: int, origin: CancelacionOrigen, doctor_id: int) -> datetime | None:
        state = "Cancelada_Paciente" if origin is CancelacionOrigen.PACIENTE else "Cancelada_Medico"
        active_states = ("confirmada",) if self._compact else ACTIVE_APPOINTMENT_STATES
        with self._database.cursor() as (connection, cursor):
            connection.start_transaction()
            cursor.execute("SELECT id_doctor FROM doctores WHERE id_doctor = %s FOR UPDATE", (doctor_id,))
            if cursor.fetchone() is None:
                connection.rollback()
                return None
            cursor.execute(
                "SELECT estado FROM citas WHERE id_cita = %s AND id_doctor = %s FOR UPDATE",
                (appointment_id, doctor_id),
            )
            row = cursor.fetchone()
            if row is None or row["estado"] not in active_states:
                connection.rollback()
                return None
            if self._compact:
                cursor.execute(
                    "UPDATE citas SET estado = 'cancelada', cancelada_por = %s, cancelada_en = CURRENT_TIMESTAMP "
                    "WHERE id_cita = %s AND id_doctor = %s AND estado = 'confirmada'",
                    (origin.value, appointment_id, doctor_id),
                )
                cursor.execute("SELECT cancelada_en AS fecha_cancelacion FROM citas WHERE id_cita = %s", (appointment_id,))
                cancelled_at = cursor.fetchone()["fecha_cancelacion"]
                connection.commit()
                return cancelled_at
            cursor.execute(
                """
                UPDATE citas
                SET estado = %s, fecha_cancelacion = CURRENT_TIMESTAMP
                WHERE id_cita = %s AND id_doctor = %s
                  AND estado IN (%s, %s)
                """,
                (state, appointment_id, doctor_id, *ACTIVE_APPOINTMENT_STATES),
            )
            if cursor.rowcount == 0:
                connection.rollback()
                return None
            cursor.execute("SELECT fecha_cancelacion FROM citas WHERE id_cita = %s", (appointment_id,))
            row = cursor.fetchone()
            connection.commit()
            return row["fecha_cancelacion"] if row else None

    def appointment_exists(self, appointment_id: int) -> bool:
        with self._database.cursor() as (_, cursor):
            cursor.execute("SELECT 1 FROM citas WHERE id_cita = %s", (appointment_id,))
            return cursor.fetchone() is not None

