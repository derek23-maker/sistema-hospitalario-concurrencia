from dataclasses import dataclass
from datetime import datetime, time, timedelta


@dataclass(frozen=True)
class AppointmentInterval:
    start: time
    duration_minutes: int

    def overlaps(self, candidate_start: datetime, candidate_end: datetime) -> bool:
        existing_start = candidate_start.replace(
            hour=self.start.hour,
            minute=self.start.minute,
            second=self.start.second,
            microsecond=0,
        )
        existing_end = existing_start + timedelta(minutes=self.duration_minutes)
        return candidate_start < existing_end and existing_start < candidate_end


@dataclass(frozen=True)
class AbsenceInterval:
    start: datetime
    end: datetime

    def overlaps(self, candidate_start: datetime, candidate_end: datetime) -> bool:
        return candidate_start <= self.end and self.start < candidate_end


@dataclass(frozen=True)
class GeneratedSlot:
    start: time
    end: time
    available: bool
    reason: str | None = None


def generate_slots(
    *,
    day: datetime,
    schedule_start: time,
    schedule_end: time,
    duration_minutes: int,
    appointments: list[AppointmentInterval],
    absences: list[AbsenceInterval],
) -> list[GeneratedSlot]:
    """Genera franjas completas; nunca ofrece una que termine fuera de la jornada."""
    if duration_minutes <= 0:
        raise ValueError("La duración del servicio debe ser mayor a cero.")

    start = day.replace(
        hour=schedule_start.hour,
        minute=schedule_start.minute,
        second=schedule_start.second,
        microsecond=0,
    )
    end_of_schedule = day.replace(
        hour=schedule_end.hour,
        minute=schedule_end.minute,
        second=schedule_end.second,
        microsecond=0,
    )
    step = timedelta(minutes=duration_minutes)
    slots: list[GeneratedSlot] = []

    while start + step <= end_of_schedule:
        slot_end = start + step
        if any(item.overlaps(start, slot_end) for item in absences):
            slots.append(GeneratedSlot(start.time(), slot_end.time(), False, "Médico ausente"))
        elif any(item.overlaps(start, slot_end) for item in appointments):
            slots.append(GeneratedSlot(start.time(), slot_end.time(), False, "Horario ocupado"))
        else:
            slots.append(GeneratedSlot(start.time(), slot_end.time(), True))
        start = slot_end

    return slots

