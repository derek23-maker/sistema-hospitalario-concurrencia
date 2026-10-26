from dataclasses import dataclass
from enum import Enum


class ReservationOutcome(str, Enum):
    SUCCESS = "success"
    CONFLICT = "conflict"
    INVALID = "invalid"
    FAILURE = "failure"


@dataclass(frozen=True)
class ClassifiedResult:
    outcome: ReservationOutcome
    code: str
    message: str


def classify_procedure_result(raw_result: str | None) -> ClassifiedResult:
    """Convierte tanto el procedimiento actual como el endurecido a un contrato API."""
    raw = (raw_result or "").strip()
    normalized = raw.casefold()

    if raw.startswith("OK:") or "éxito:" in normalized:
        return ClassifiedResult(
            ReservationOutcome.SUCCESS,
            "CITA_CONFIRMADA",
            "La cita fue reservada correctamente.",
        )

    if normalized.startswith("validation:"):
        return ClassifiedResult(
            ReservationOutcome.INVALID,
            "SOLICITUD_INVALIDA",
            "El médico o servicio indicado no es válido.",
        )

    if "doctor_absent" in normalized or "médico se encuentra ausente" in normalized:
        return ClassifiedResult(
            ReservationOutcome.CONFLICT,
            "MEDICO_AUSENTE",
            "El médico está ausente en la fecha y hora seleccionadas.",
        )

    conflict_markers = ("conflict:", "condición de carrera", "horario ya fue apartado", "deadlock", "lock_timeout")
    if any(marker in normalized for marker in conflict_markers):
        return ClassifiedResult(
            ReservationOutcome.CONFLICT,
            "HORARIO_NO_DISPONIBLE",
            "El horario acaba de ser reservado o está siendo procesado por otra solicitud.",
        )

    return ClassifiedResult(
        ReservationOutcome.FAILURE,
        "RESERVA_NO_COMPLETADA",
        "No fue posible completar la reserva. Inténtelo de nuevo.",
    )

