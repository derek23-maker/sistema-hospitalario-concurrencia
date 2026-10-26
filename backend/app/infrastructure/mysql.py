from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool

from app.core.config import Settings


class DatabaseUnavailableError(RuntimeError):
    """La API no puede adquirir o usar una conexión MySQL."""


class DatabaseConflictError(RuntimeError):
    """Otra transacción ocupa el recurso o se abortó por un deadlock."""


class Database:
    """Pool síncrono. FastAPI ejecuta sus rutas `def` en un pool de hilos."""

    def __init__(self, settings: Settings) -> None:
        self._pool = MySQLConnectionPool(
            pool_name=f"hospital_api_{uuid4().hex}",
            pool_size=settings.db_pool_size,
            pool_reset_session=settings.db_pool_reset_session,
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            charset="utf8mb4",
            use_unicode=True,
            autocommit=True,
        )
        # Solo lectura: reconoce la versión compacta exportada en CHAT.sql.
        with self.cursor() as (_, cursor):
            cursor.execute(
                "SELECT TABLE_NAME AS nombre FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN "
                "('horarios_doctor', 'ausencias_doctor', 'horarios_medicos', 'ausencias_medicos')"
            )
            tables = {row["nombre"] for row in cursor.fetchall()}
        self.compact_schema = {"horarios_doctor", "ausencias_doctor"}.issubset(tables)

    @contextmanager
    def cursor(self) -> Iterator[tuple[mysql.connector.MySQLConnection, mysql.connector.cursor.MySQLCursorDict]]:
        connection = None
        cursor = None
        try:
            connection = self._pool.get_connection()
            cursor = connection.cursor(dictionary=True)
            yield connection, cursor
        except mysql.connector.Error as exc:
            if connection is not None:
                connection.rollback()
            if exc.errno in (1062, 1205, 1213):
                raise DatabaseConflictError("La agenda está siendo modificada por otra transacción.") from exc
            raise DatabaseUnavailableError("No se pudo completar la operación en MySQL.") from exc
        finally:
            if connection is not None and connection.in_transaction:
                connection.rollback()
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

    def ping(self) -> None:
        with self.cursor() as (connection, _):
            connection.ping(reconnect=False, attempts=1, delay=0)
