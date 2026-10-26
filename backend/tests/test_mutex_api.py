"""Pruebas HTTP reales en ASGI, con repositorio en memoria (sin MySQL)."""

import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time as clock_time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.agenda import router
from app.services.doctor_mutex import DoctorMutexRegistry, doctor_mutexes


PAYLOAD = {
    "id_paciente": 1, "id_doctor": 1, "id_servicio": 1,
    "fecha_cita": "2030-01-03", "hora_cita": "09:00:00",
}


def burst(count, operation):
    barrier = threading.Barrier(count)

    def worker(index):
        barrier.wait(timeout=10)
        return operation(index)

    with ThreadPoolExecutor(max_workers=count, thread_name_prefix="cliente") as executor:
        return list(executor.map(worker, range(count)))


class MemoryRepository:
    """Amplía la carrera a propósito. NO sincroniza la reserva por su cuenta."""

    def __init__(self):
        self.rows = {}
        self.next_id = 1
        self.guard = threading.Lock()  # Solo métricas/asignación de IDs entre doctores.
        self.active = 0
        self.max_active = 0
        self.inside = None
        self.entered = threading.Event()
        self.proceed = threading.Event()
        self.pause_cancel = False
        self.pause_reserve = False

    def patient_exists(self, _):
        return True

    def doctor_exists(self, _):
        return True

    def service_duration(self, _):
        return 30

    def weekly_schedule(self, *_):
        return [(clock_time(9), clock_time(12))]

    def approved_absences(self, *_):
        return []

    def active_appointments(self, doctor, _):
        return [(clock_time(9), 30) for row in self.rows.values()
                if row["doctor"] == doctor and row["active"]]

    def call_reservation_procedure(self, request):
        with self.guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.pause_reserve:
                self.entered.set()
                if not self.proceed.wait(5):
                    raise TimeoutError("Reserva no liberada por la prueba")
            if self.inside:
                self.inside.wait(timeout=5)  # Dos médicos deben llegar simultáneamente.
            occupied = any(row["doctor"] == request.id_doctor and row["active"]
                           for row in self.rows.values())
            time.sleep(0.015)  # Sin el mutex, diez lecturas verían libre el turno.
            if occupied:
                return "CONFLICT:SLOT_TAKEN"
            with self.guard:
                self.rows[self.next_id] = {"doctor": request.id_doctor, "active": True}
                self.next_id += 1
            return "OK:APPOINTMENT_CONFIRMED"
        finally:
            with self.guard:
                self.active -= 1

    def appointment_doctor(self, appointment_id):
        row = self.rows.get(appointment_id)
        return row["doctor"] if row else None

    def appointment_exists(self, appointment_id):
        return appointment_id in self.rows

    def cancel_appointment(self, appointment_id, origin, doctor_id):
        if self.pause_cancel:
            self.entered.set()
            if not self.proceed.wait(5):
                raise TimeoutError("Cancelación no liberada por la prueba")
        row = self.rows.get(appointment_id)
        if row and row["active"] and row["doctor"] == doctor_id:
            row["active"] = False
            return datetime(2030, 1, 3, 8)
        return None


class MutexApiTests(unittest.TestCase):
    def setUp(self):
        self.repository = MemoryRepository()
        app = FastAPI()
        app.include_router(router)
        app.state.database = object()
        # Se ejecuta la dependencia REAL: crea un servicio nuevo por petición.
        # Solo MySQL es sustituido. Así se comprueba que comparten el registro.
        self.repository_patch = patch("app.api.dependencies.AgendaRepository", return_value=self.repository)
        self.repository_patch.start()
        self.addCleanup(self.repository_patch.stop)
        self.client = self.enterContext(TestClient(app))

    def reserve(self, doctor=1):
        return self.client.post("/citas/reservar", json={**PAYLOAD, "id_doctor": doctor})

    def test_ten_threads_one_created_nine_conflicts(self):
        with self.assertLogs("uvicorn.error.agenda_mutex", level="INFO") as logs:
            responses = burst(10, lambda _: self.reserve())
        self.assertEqual(sorted(r.status_code for r in responses), [201] + [409] * 9)
        self.assertEqual(self.repository.max_active, 1)
        self.assertEqual(len(self.repository.rows), 1)
        for response in responses:
            if response.status_code == 409:
                self.assertEqual(response.json()["detail"]["codigo"], "HORARIO_NO_DISPONIBLE")
        for event in ("mutex espera", "mutex adquirido", "mutex liberado"):
            self.assertEqual(sum(event in line for line in logs.output), 10)

    def test_different_doctors_reach_critical_section_together(self):
        self.repository.inside = threading.Barrier(2)
        responses = burst(2, lambda index: self.reserve(index + 1))
        self.assertEqual([r.status_code for r in responses], [201, 201])
        self.assertEqual(self.repository.max_active, 2)

    def test_query_does_not_wait_for_doctor_mutex(self):
        with ThreadPoolExecutor(max_workers=1) as executor:
            with doctor_mutexes.hold(1, "prueba"):
                response = executor.submit(self.client.get, "/horarios/1", params={
                    "fecha": "2030-01-03", "id_servicio": 1,
                }).result(timeout=3)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["horarios"][0]["disponible"])

    def test_cancel_then_reserve_does_not_cancel_new_appointment(self):
        self.assertEqual(self.reserve().status_code, 201)
        self.repository.pause_cancel = True
        with ThreadPoolExecutor(max_workers=2) as executor:
            cancellation = executor.submit(self.client.patch, "/citas/cancelar/1", json={"origen": "paciente"})
            self.assertTrue(self.repository.entered.wait(3))
            with self.assertLogs("uvicorn.error.agenda_mutex", level="INFO"):
                reservation = executor.submit(self.reserve)
                try:
                    # El nuevo intento debe esperar la cancelación del mismo médico.
                    time.sleep(0.05)
                    self.assertFalse(reservation.done())
                finally:
                    self.repository.proceed.set()
                self.assertEqual(cancellation.result(timeout=5).status_code, 200)
                self.assertEqual(reservation.result(timeout=5).status_code, 201)
        self.assertFalse(self.repository.rows[1]["active"])
        self.assertTrue(self.repository.rows[2]["active"])
        self.assertEqual(self.client.patch("/citas/cancelar/1", json={}).status_code, 409)
        self.assertTrue(self.repository.rows[2]["active"])

    def test_reserve_before_cancel_returns_conflict_then_can_reserve(self):
        self.assertEqual(self.reserve().status_code, 201)
        self.assertEqual(self.reserve().status_code, 409)
        self.assertEqual(self.client.patch("/citas/cancelar/1", json={}).status_code, 200)
        self.assertEqual(self.reserve().status_code, 201)

    def test_cancel_waits_while_reservation_for_same_doctor_runs(self):
        self.assertEqual(self.reserve().status_code, 201)
        self.repository.pause_reserve = True
        with ThreadPoolExecutor(max_workers=2) as executor:
            reservation = executor.submit(self.reserve)
            self.assertTrue(self.repository.entered.wait(3))
            cancellation = executor.submit(self.client.patch, "/citas/cancelar/1", json={})
            try:
                time.sleep(0.05)
                self.assertFalse(cancellation.done())
            finally:
                self.repository.proceed.set()
            self.assertEqual(reservation.result(timeout=5).status_code, 409)
            self.assertEqual(cancellation.result(timeout=5).status_code, 200)
        self.assertFalse(self.repository.rows[1]["active"])

    def test_missing_cancellation_is_404(self):
        self.assertEqual(self.client.patch("/citas/cancelar/99", json={}).status_code, 404)

    def test_mutex_released_on_exception_and_registry_cleaned(self):
        registry = DoctorMutexRegistry()
        with self.assertRaisesRegex(RuntimeError, "simulado"):
            with registry.hold(1, "prueba"):
                raise RuntimeError("simulado")
        with ThreadPoolExecutor(max_workers=1) as executor:
            def acquire_again():
                with registry.hold(1, "prueba"):
                    return True
            self.assertTrue(executor.submit(acquire_again).result(timeout=3))
        self.assertEqual(registry._entries, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
