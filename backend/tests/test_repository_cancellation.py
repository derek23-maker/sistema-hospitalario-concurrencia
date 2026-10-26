import sys
import unittest
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.contracts import CancelacionOrigen, ReservaCitaRequest
from app.repositories.agenda import AgendaRepository, mysql_time


class StubDatabase:
    def __init__(self, rows):
        self.connection = Mock()
        self.cursor_mock = Mock()
        self.cursor_mock.fetchone.side_effect = rows
        self.cursor_mock.rowcount = 1

    @contextmanager
    def cursor(self):
        yield self.connection, self.cursor_mock


class RepositoryCancellationTests(unittest.TestCase):
    def test_procedure_out_supports_dictionary_and_tuple_cursor_results(self):
        request = ReservaCitaRequest(
            id_paciente=1, id_doctor=1, id_servicio=1,
            fecha_cita="2030-01-03", hora_cita="09:00:00",
        )
        for outcome in ("OK:APPOINTMENT_CONFIRMED:1", "CONFLICT:SLOT_TAKEN"):
            for returned in ({"sp_reservar_cita_arg8": outcome}, (1, 1, 1, None, None, None, None, outcome)):
                with self.subTest(returned=returned):
                    database = StubDatabase([])
                    database.cursor_mock.callproc.return_value = returned
                    result_set = Mock()
                    database.cursor_mock.stored_results.return_value = [result_set]
                    self.assertEqual(AgendaRepository(database).call_reservation_procedure(request), outcome)
                    result_set.fetchall.assert_called_once()

    def test_compact_schema_cancel_uses_real_columns_and_keeps_transaction(self):
        timestamp = datetime(2030, 1, 3, 8)
        database = StubDatabase([{"id_doctor": 7}, {"estado": "confirmada"}, {"fecha_cancelacion": timestamp}])
        database.compact_schema = True
        result = AgendaRepository(database).cancel_appointment(11, CancelacionOrigen.MEDICO, 7)
        self.assertEqual(result, timestamp)
        queries = database.cursor_mock.execute.call_args_list
        self.assertIn("cancelada_por", queries[2].args[0])
        self.assertIn("cancelada_en", queries[2].args[0])
        self.assertEqual(queries[2].args[1], ("medico", 11, 7))
        database.connection.start_transaction.assert_called_once()
        database.connection.commit.assert_called_once()

    def test_compact_schedule_table_and_lowercase_day(self):
        database = StubDatabase([])
        database.compact_schema = True
        database.cursor_mock.fetchall.return_value = [{"hora_inicio": timedelta(hours=9), "hora_fin": timedelta(hours=14)}]
        self.assertEqual(AgendaRepository(database).weekly_schedule(1, "Lunes"), [(time(9), time(14))])
        query = database.cursor_mock.execute.call_args
        self.assertIn("FROM horarios_doctor", query.args[0])
        self.assertEqual(query.args[1], (1, "lunes"))

    def test_compact_absences_and_duration_use_exported_schema(self):
        database = StubDatabase([])
        database.compact_schema = True
        database.cursor_mock.fetchall.return_value = []
        repository = AgendaRepository(database)
        repository.approved_absences(1, datetime(2030, 1, 3).date())
        self.assertIn("FROM ausencias_doctor", database.cursor_mock.execute.call_args.args[0])
        repository.active_appointments(1, datetime(2030, 1, 3).date())
        query = database.cursor_mock.execute.call_args.args[0]
        self.assertIn("estado = 'confirmada'", query)
        self.assertNotIn("JOIN servicios", query)

    def test_transaction_locks_doctor_then_appointment_and_commits(self):
        timestamp = datetime(2030, 1, 3, 8)
        database = StubDatabase([{"id_doctor": 7}, {"estado": "Confirmada"}, {"fecha_cancelacion": timestamp}])
        result = AgendaRepository(database).cancel_appointment(11, CancelacionOrigen.PACIENTE, 7)
        self.assertEqual(result, timestamp)
        database.connection.start_transaction.assert_called_once()
        queries = database.cursor_mock.execute.call_args_list
        self.assertIn("FROM doctores", queries[0].args[0])
        self.assertIn("FOR UPDATE", queries[0].args[0])
        self.assertIn("FROM citas", queries[1].args[0])
        self.assertIn("FOR UPDATE", queries[1].args[0])
        self.assertEqual(queries[2].args[1], ("Cancelada_Paciente", 11, 7, "Pendiente", "Confirmada"))
        database.connection.commit.assert_called_once()
        database.connection.rollback.assert_not_called()

    def test_completed_or_cancelled_appointment_is_not_updated(self):
        for state in ("Completada", "Cancelada_Paciente", "Cancelada_Medico"):
            with self.subTest(state=state):
                database = StubDatabase([{"id_doctor": 7}, {"estado": state}])
                self.assertIsNone(AgendaRepository(database).cancel_appointment(11, CancelacionOrigen.MEDICO, 7))
                self.assertEqual(database.cursor_mock.execute.call_count, 2)
                database.connection.rollback.assert_called_once()
                database.connection.commit.assert_not_called()

    def test_doctor_changed_or_appointment_missing_rolls_back(self):
        database = StubDatabase([{"id_doctor": 7}, None])
        self.assertIsNone(AgendaRepository(database).cancel_appointment(11, CancelacionOrigen.PACIENTE, 7))
        database.connection.rollback.assert_called_once()

    def test_connector_time_conversion_preserves_time(self):
        self.assertEqual(mysql_time(timedelta(hours=9, minutes=30)), time(9, 30))
        self.assertEqual(mysql_time(time(14)), time(14))
