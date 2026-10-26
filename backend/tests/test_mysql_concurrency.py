"""Integración optativa con MySQL 8 real en una base temporal aislada.

HOSPITAL_TEST_DB_PASSWORD debe existir en el entorno (puede ser cadena vacía).
El usuario debe poder CREATE/DROP DATABASE. Nunca usa sistema_hospitalario.
"""

import os
import sys
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_mutex_api import PAYLOAD, burst

import mysql.connector
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.agenda import router
from app.core.config import Settings
from app.domain.contracts import ReservaCitaRequest
from app.infrastructure.mysql import Database
from app.repositories.agenda import AgendaRepository


def execute_script(connection, source):
    delimiter = ";"
    buffer = []
    with connection.cursor() as cursor:
        for line in source.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("--"):
                continue
            if stripped.upper().startswith("DELIMITER "):
                delimiter = stripped.split()[1]
                continue
            buffer.append(line)
            if stripped.endswith(delimiter):
                statement = "\n".join(buffer).rstrip()[:-len(delimiter)]
                cursor.execute(statement)
                if cursor.with_rows:
                    cursor.fetchall()
                buffer.clear()
        if buffer:
            raise AssertionError("SQL incompleto en la prueba")


@unittest.skipUnless("HOSPITAL_TEST_DB_PASSWORD" in os.environ,
                     "MySQL real omitido: falta HOSPITAL_TEST_DB_PASSWORD")
class MysqlConcurrencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = "hospital_mutex_test_" + uuid4().hex
        cls.admin = mysql.connector.connect(
            host=os.getenv("HOSPITAL_TEST_DB_HOST", "127.0.0.1"),
            port=int(os.getenv("HOSPITAL_TEST_DB_PORT", "3306")),
            user=os.getenv("HOSPITAL_TEST_DB_USER", "root"),
            password=os.environ["HOSPITAL_TEST_DB_PASSWORD"], autocommit=True,
        )
        root = Path(__file__).resolve().parents[2]
        source = (root / "db/01_INSTALAR_BASE_CORREGIDA.sql").read_text(encoding="utf-8")
        source = source.replace("DROP DATABASE IF EXISTS sistema_hospitalario;", "")
        source = source.replace("sistema_hospitalario", cls.schema)
        # Nombre aleatorio definido aquí. Nunca se elimina una base del usuario.
        cls.addClassCleanup(cls.drop_schema)
        execute_script(cls.admin, source)
        execute_script(cls.admin, (root / "db/02_CARGAR_DATOS_DEMO.sql")
                       .read_text(encoding="utf-8").replace("sistema_hospitalario", cls.schema))
        cls.database = Database(Settings(
            db_host=cls.admin.server_host, db_port=cls.admin.server_port,
            db_name=cls.schema, db_user=os.getenv("HOSPITAL_TEST_DB_USER", "root"),
            db_password=os.environ["HOSPITAL_TEST_DB_PASSWORD"], db_pool_size=20,
        ))

    @classmethod
    def drop_schema(cls):
        try:
            with cls.admin.cursor() as cursor:
                cursor.execute("DROP DATABASE IF EXISTS `" + cls.schema + "`")
        finally:
            cls.admin.close()

    def setUp(self):
        with self.database.cursor() as (_, cursor):
            cursor.execute("DELETE FROM citas")
        app = FastAPI()
        app.include_router(router)
        app.state.database = self.database
        self.client = self.enterContext(TestClient(app))

    def test_ten_threads_real_api_one_created_nine_conflicts(self):
        responses = burst(10, lambda _: self.client.post("/citas/reservar", json=PAYLOAD))
        self.assertEqual(sorted(r.status_code for r in responses), [201] + [409] * 9)
        with self.database.cursor() as (_, cursor):
            cursor.execute("SELECT COUNT(*) AS total FROM citas WHERE estado = 'Confirmada'")
            self.assertEqual(cursor.fetchone()["total"], 1)

    def test_database_alone_protects_ten_connections_without_python_mutex(self):
        # Se llama directamente al procedimiento para verificar protección entre
        # procesos/servidores que no comparten el registro Python.
        request = ReservaCitaRequest(**PAYLOAD)
        results = burst(10, lambda _: AgendaRepository(self.database).call_reservation_procedure(request))
        self.assertEqual(results.count("OK:APPOINTMENT_CONFIRMED"), 1)
        self.assertEqual(results.count("CONFLICT:SLOT_TAKEN"), 9)

    def test_cancel_rebook_and_late_cancel_preserves_new_id(self):
        self.assertEqual(self.client.post("/citas/reservar", json=PAYLOAD).status_code, 201)
        with self.database.cursor() as (_, cursor):
            cursor.execute("SELECT id_cita FROM citas")
            previous = cursor.fetchone()["id_cita"]
        self.assertEqual(self.client.patch(f"/citas/cancelar/{previous}", json={}).status_code, 200)
        self.assertEqual(self.client.post("/citas/reservar", json=PAYLOAD).status_code, 201)
        self.assertEqual(self.client.patch(f"/citas/cancelar/{previous}", json={}).status_code, 409)
        with self.database.cursor() as (_, cursor):
            cursor.execute("SELECT id_cita, estado FROM citas ORDER BY id_cita")
            rows = cursor.fetchall()
            self.assertEqual([r["estado"] for r in rows], ["Cancelada_Paciente", "Confirmada"])
            self.assertNotEqual(rows[0]["id_cita"], rows[1]["id_cita"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
