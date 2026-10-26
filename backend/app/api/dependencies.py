from fastapi import Request

from app.infrastructure.mysql import Database
from app.repositories.agenda import AgendaRepository
from app.services.agenda import AgendaService


def get_agenda_service(request: Request) -> AgendaService:
    database: Database = request.app.state.database
    return AgendaService(AgendaRepository(database))

