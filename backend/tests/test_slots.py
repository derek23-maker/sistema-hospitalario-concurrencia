import sys
import unittest
from datetime import datetime, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.slots import AbsenceInterval, AppointmentInterval, generate_slots


class SlotGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.day = datetime(2026, 10, 21)

    def test_slot_overlapping_a_longer_appointment_is_not_available(self) -> None:
        slots = generate_slots(
            day=self.day,
            schedule_start=time(9, 0),
            schedule_end=time(11, 0),
            duration_minutes=30,
            appointments=[AppointmentInterval(start=time(9, 0), duration_minutes=60)],
            absences=[],
        )
        self.assertEqual([slot.available for slot in slots], [False, False, True, True])

    def test_slots_do_not_run_past_the_end_of_the_schedule(self) -> None:
        slots = generate_slots(
            day=self.day,
            schedule_start=time(9, 0),
            schedule_end=time(10, 15),
            duration_minutes=30,
            appointments=[],
            absences=[],
        )
        self.assertEqual([(slot.start, slot.end) for slot in slots], [(time(9, 0), time(9, 30)), (time(9, 30), time(10, 0))])

    def test_partial_absence_only_blocks_the_affected_slot(self) -> None:
        slots = generate_slots(
            day=self.day,
            schedule_start=time(9, 0),
            schedule_end=time(11, 0),
            duration_minutes=30,
            appointments=[],
            absences=[
                AbsenceInterval(
                    start=datetime(2026, 10, 21, 9, 30),
                    end=datetime(2026, 10, 21, 9, 59),
                )
            ],
        )
        self.assertEqual([slot.available for slot in slots], [True, False, True, True])
