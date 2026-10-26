import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.reservation_result import ReservationOutcome, classify_procedure_result


class ReservationResultTests(unittest.TestCase):
    def test_legacy_success_message_is_confirmed(self) -> None:
        result = classify_procedure_result("ÉXITO: Cita reservada correctamente de forma segura.")
        self.assertEqual(result.outcome, ReservationOutcome.SUCCESS)
        self.assertEqual(result.code, "CITA_CONFIRMADA")

    def test_legacy_concurrent_message_is_conflict(self) -> None:
        result = classify_procedure_result("ERROR: Condición de carrera detectada. El horario ya fue apartado por otro usuario.")
        self.assertEqual(result.outcome, ReservationOutcome.CONFLICT)

    def test_generic_procedure_failure_is_not_reported_as_success(self) -> None:
        result = classify_procedure_result("ERROR: Ocurrió un fallo en la transacción. Operación abortada.")
        self.assertEqual(result.outcome, ReservationOutcome.FAILURE)

    def test_hardened_procedure_validation_is_not_a_database_outage(self) -> None:
        result = classify_procedure_result("VALIDATION:SERVICE_NOT_FOUND")
        self.assertEqual(result.outcome, ReservationOutcome.INVALID)

