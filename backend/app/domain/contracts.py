from datetime import date, datetime, time
from enum import Enum

from pydantic import BaseModel, Field, PositiveInt, field_validator


class ReservaCitaRequest(BaseModel):
    id_paciente: PositiveInt
    id_doctor: PositiveInt
    id_servicio: PositiveInt
    fecha_cita: date
    hora_cita: time
    motivo_consulta: str | None = Field(default=None, max_length=5000)
    id_cita_anterior: PositiveInt | None = None

    @field_validator("hora_cita")
    @classmethod
    def normalize_seconds(cls, value: time) -> time:
        return value.replace(microsecond=0)


class EstadoReserva(str, Enum):
    CONFIRMADA = "confirmada"
    CONFLICTO = "conflicto"


class ReservaCitaResponse(BaseModel):
    estado: EstadoReserva
    codigo: str
    mensaje: str


class CancelacionOrigen(str, Enum):
    PACIENTE = "paciente"
    MEDICO = "medico"


class CancelarCitaRequest(BaseModel):
    origen: CancelacionOrigen = CancelacionOrigen.PACIENTE


class CancelarCitaResponse(BaseModel):
    id_cita: PositiveInt
    estado: str
    fecha_cancelacion: datetime
    mensaje: str


class HorarioDisponible(BaseModel):
    hora_inicio: time
    hora_fin: time
    disponible: bool
    motivo_no_disponible: str | None = None


class HorariosResponse(BaseModel):
    id_doctor: PositiveInt
    id_servicio: PositiveInt
    fecha: date
    duracion_minutos: PositiveInt
    medico_ausente: bool
    horarios: list[HorarioDisponible]


class ErrorResponse(BaseModel):
    codigo: str
    mensaje: str

