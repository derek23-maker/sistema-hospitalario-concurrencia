from datetime import date

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.dependencies import get_agenda_service
from app.domain.contracts import (
    CancelarCitaRequest,
    CancelarCitaResponse,
    HorariosResponse,
    ReservaCitaRequest,
    ReservaCitaResponse,
)
from app.services.agenda import AgendaService


router = APIRouter(tags=["Citas"])


@router.get("/horarios/{id_doctor}", response_model=HorariosResponse)
def consultar_horarios(
    id_doctor: int = Path(gt=0),
    fecha: date = Query(description="Fecha a consultar en formato AAAA-MM-DD."),
    id_servicio: int = Query(gt=0, description="Servicio que determina la duración de cada franja."),
    service: AgendaService = Depends(get_agenda_service),
) -> HorariosResponse:
    return service.get_availability(id_doctor, id_servicio, fecha)


@router.post("/citas/reservar", response_model=ReservaCitaResponse, status_code=status.HTTP_201_CREATED)
def reservar_cita(
    request: ReservaCitaRequest,
    service: AgendaService = Depends(get_agenda_service),
) -> ReservaCitaResponse:
    return service.reserve(request)


@router.patch("/citas/cancelar/{id_cita}", response_model=CancelarCitaResponse)
def cancelar_cita(
    request: CancelarCitaRequest,
    id_cita: int = Path(gt=0),
    service: AgendaService = Depends(get_agenda_service),
) -> CancelarCitaResponse:
    return service.cancel(id_cita, request)

