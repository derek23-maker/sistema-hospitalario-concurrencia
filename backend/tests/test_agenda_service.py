import sys
import unittest
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException

from app.domain.contracts import ReservaCitaRequest
from app.services.agenda import AgendaService


class FakeAgendaRepository:
    def __init__(self, procedure_result: str) -> None:
        self.procedure_result = procedure_result
        self.procedure_was_called = False

    def doctor_exists(self, _: int) -> bool:
        return True

    def patient_exists(self, _: int) -> bool:
        return True

    def service_duration(self, _: int) -> int:
        return 30

    def weekly_schedule(self, _: int, __: str) -> list[tuple[time, time]]:
        return [(time(9, 0), time(12, 0))]

    def call_reservation_procedure(self, _: ReservaCitaRequest) -> str:
        self.procedure_was_called = True
        return self.procedure_result


class AgendaServiceReservationTests(unittest.TestCase):
    def _request(self, appointment_time: time = time(9, 0)) -> ReservaCitaRequest:
        return ReservaCitaRequest(
            id_paciente=1,
            id_doctor=1,
            id_servicio=1,
            fecha_cita=date(2026, 10, 21),
            hora_cita=appointment_time,
        )

    def test_reservation_returns_confirmation_for_procedure_success(self) -> None:
        repository = FakeAgendaRepository("OK:APPOINTMENT_CONFIRMED")
        response = AgendaService(repository).reserve(self._request())
        self.assertEqual(response.estado.value, "confirmada")
        self.assertTrue(repository.procedure_was_called)

    def test_outside_schedule_does_not_call_stored_procedure(self) -> None:
        repository = FakeAgendaRepository("OK:APPOINTMENT_CONFIRMED")
        with self.assertRaises(HTTPException) as error:
            AgendaService(repository).reserve(self._request(time(12, 0)))
        self.assertEqual(error.exception.status_code, 422)
        self.assertFalse(repository.procedure_was_called)

    def test_concurrent_reservation_becomes_http_conflict(self) -> None:
        repository = FakeAgendaRepository("CONFLICT:SLOT_TAKEN")
        with self.assertRaises(HTTPException) as error:
            AgendaService(repository).reserve(self._request())
        self.assertEqual(error.exception.status_code, 409)
