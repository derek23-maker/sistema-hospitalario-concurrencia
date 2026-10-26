from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.agenda import router as agenda_router
from app.core.config import get_settings
from app.infrastructure.mysql import Database, DatabaseConflictError, DatabaseUnavailableError


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    database = Database(settings)
    database.ping()
    app.state.database = database
    yield


app = FastAPI(title=settings.api_title, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)
app.include_router(agenda_router)


@app.exception_handler(DatabaseUnavailableError)
def database_unavailable_handler(_: Request, __: DatabaseUnavailableError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": {"codigo": "BASE_DE_DATOS_NO_DISPONIBLE", "mensaje": "No hay conexión con la base de datos."}},
    )


@app.exception_handler(DatabaseConflictError)
def database_conflict_handler(_: Request, __: DatabaseConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": {
        "codigo": "AGENDA_EN_CONFLICTO",
        "mensaje": "Otra transacción está modificando la agenda. Actualiza e inténtalo de nuevo.",
    }})


@app.get("/health", tags=["Operación"])
def health_check() -> dict[str, str]:
    return {"estado": "ok"}
