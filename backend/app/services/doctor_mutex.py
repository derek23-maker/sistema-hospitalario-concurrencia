"""Mutex por agenda, compartidos por todos los servicios de este proceso."""

import logging
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import monotonic


logger = logging.getLogger("uvicorn.error.agenda_mutex")


@dataclass
class _Entry:
    lock: threading.Lock = field(default_factory=threading.Lock)
    users: int = 0  # Incluye al propietario y a todos los hilos que esperan.


class DoctorMutexRegistry:
    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._entries: dict[int, _Entry] = {}

    @contextmanager
    def hold(self, doctor_id: int, operation: str):
        # El guard solo protege el diccionario; nunca cubre consultas ni esperas.
        with self._guard:
            entry = self._entries.setdefault(doctor_id, _Entry())
            entry.users += 1
        acquired = False
        started = monotonic()
        context = (os.getpid(), threading.get_ident(), doctor_id, operation)
        try:
            logger.info("mutex espera pid=%s hilo=%s medico=%s operacion=%s", *context)
            entry.lock.acquire()
            acquired = True
            logger.info("mutex adquirido pid=%s hilo=%s medico=%s operacion=%s espera_ms=%.2f",
                        *context, (monotonic() - started) * 1000)
            yield
        finally:
            if acquired:
                entry.lock.release()
                logger.info("mutex liberado pid=%s hilo=%s medico=%s operacion=%s", *context)
            with self._guard:
                entry.users -= 1
                if entry.users == 0:
                    del self._entries[doctor_id]


# Una instancia por proceso, NO una instancia por petición ni por servicio.
doctor_mutexes = DoctorMutexRegistry()
