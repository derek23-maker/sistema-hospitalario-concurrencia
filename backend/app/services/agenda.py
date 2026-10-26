from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status

from app.domain.contracts import (
    CancelarCitaRequest,
    CancelarCitaResponse,
    EstadoReserva,
    HorarioDisponible,
    HorariosResponse,
    ReservaCitaRequest,
    ReservaCitaResponse,
)
from app.domain.reservation_result import ReservationOutcome, classify_procedure_result
from app.domain.slots import AbsenceInterval, AppointmentInterval, generate_slots
from app.repositories.agenda import AgendaRepository
from app.services.doctor_mutex import DoctorMutexRegistry, doctor_mutexes


DAY_NAMES = ("Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo")


class AgendaService:
    def __init__(self, repository: AgendaRepository, mutexes: DoctorMutexRegistry = doctor_mutexes) -> None:
        self._repository = repository
        self._mutexes = mutexes

    def get_availability(self, doctor_id: int, service_id: int, appointment_date: date) -> HorariosResponse:
        if not self._repository.doctor_exists(doctor_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"codigo": "MEDICO_NO_ENCONTRADO", "mensaje": "El médico no existe."})

        duration = self._repository.service_duration(service_id)
        if duration is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"codigo": "SERVICIO_NO_ENCONTRADO", "mensaje": "El servicio no existe."})

        day_name = DAY_NAMES[appointment_date.weekday()]
        schedules = self._repository.weekly_schedule(doctor_id, day_name)
        reference_time = datetime.combine(appointment_date, time.min)
        absences = [
            AbsenceInterval(start=start, end=end)
            for start, end in self._repository.approved_absences(doctor_id, appointment_date)
        ]
        appointments = [
            AppointmentInterval(start=start, duration_minutes=appointment_duration)
            for start, appointment_duration in self._repository.active_appointments(doctor_id, appointment_date)
        ]
        all_slots = []
        for start, end in schedules:
            all_slots.extend(
                generate_slots(
                    day=reference_time,
                    schedule_start=start,
                    schedule_end=end,
                    duration_minutes=duration,
                    appointments=appointments,
                    absences=absences,
                )
            )
        doctor_absent_for_entire_schedule = bool(all_slots) and all(
            not slot.available and slot.reason == "Médico ausente" for slot in all_slots
        )

        return HorariosResponse(
            id_doctor=doctor_id,
            id_servicio=service_id,
            fecha=appointment_date,
            duracion_minutos=duration,
            medico_ausente=doctor_absent_for_entire_schedule,
            horarios=[
                HorarioDisponible(
                    hora_inicio=slot.start,
                    hora_fin=slot.end,
                    disponible=slot.available,
                    motivo_no_disponible=slot.reason,
                )
                for slot in all_slots
            ],
        )

    def reserve(self, request: ReservaCitaRequest) -> ReservaCitaResponse:
        with self._mutexes.hold(request.id_doctor, "reserva"):
            self._validate_reservation_window(request)
            result = classify_procedure_result(self._repository.call_reservation_procedure(request))
        if result.outcome is ReservationOutcome.SUCCESS:
            return ReservaCitaResponse(estado=EstadoReserva.CONFIRMADA, codigo=result.code, mensaje=result.message)
        if result.outcome is ReservationOutcome.CONFLICT:
            raise HTTPException(status.HTTP_409_CONFLICT, detail={"codigo": result.code, "mensaje": result.message})
        if result.outcome is ReservationOutcome.INVALID:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail={"codigo": result.code, "mensaje": result.message})
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail={"codigo": result.code, "mensaje": result.message})

    def _validate_reservation_window(self, request: ReservaCitaRequest) -> None:
        """Evita reservas fuera de jornada incluso si no provienen de la interfaz Flet."""
        if not self._repository.patient_exists(request.id_paciente):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail={"codigo": "PACIENTE_NO_ENCONTRADO", "mensaje": "El paciente no existe."},
            )
        if not self._repository.doctor_exists(request.id_doctor):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"codigo": "MEDICO_NO_ENCONTRADO", "mensaje": "El médico no existe."})
        duration = self._repository.service_duration(request.id_servicio)
        if duration is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"codigo": "SERVICIO_NO_ENCONTRADO", "mensaje": "El servicio no existe."})

        requested_start = datetime.combine(request.fecha_cita, request.hora_cita)
        requested_end = requested_start + timedelta(minutes=duration)
        weekday_name = DAY_NAMES[request.fecha_cita.weekday()]
        schedules = self._repository.weekly_schedule(request.id_doctor, weekday_name)
        fits_a_schedule = any(
            datetime.combine(request.fecha_cita, start) <= requested_start
            and requested_end <= datetime.combine(request.fecha_cita, end)
            for start, end in schedules
        )
        if not fits_a_schedule:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "codigo": "HORARIO_FUERA_DE_JORNADA",
                    "mensaje": "La duración del servicio no cabe en un horario de atención del médico.",
                },
            )

    def cancel(self, appointment_id: int, request: CancelarCitaRequest) -> CancelarCitaResponse:
        doctor_id = self._repository.appointment_doctor(appointment_id)
        if doctor_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"codigo": "CITA_NO_ENCONTRADA", "mensaje": "La cita no existe."})
        with self._mutexes.hold(doctor_id, "cancelacion"):
            # El repositorio vuelve a validar bajo bloqueo MySQL, en el mismo orden
            # que reserva: primero doctor y después cita.
            cancelled_at = self._repository.cancel_appointment(appointment_id, request.origen, doctor_id)
        if cancelled_at is not None:
            state = "Cancelada_Paciente" if request.origen.value == "paciente" else "Cancelada_Medico"
            return CancelarCitaResponse(
                id_cita=appointment_id,
                estado=state,
                fecha_cancelacion=cancelled_at,
                mensaje="La cita fue cancelada correctamente.",
            )
        if not self._repository.appointment_exists(appointment_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"codigo": "CITA_NO_ENCONTRADA", "mensaje": "La cita no existe."})
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"codigo": "CITA_NO_CANCELABLE", "mensaje": "La cita ya fue cancelada o completada."})

