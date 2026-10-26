from typing import Any

import httpx


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class HospitalApiClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def get_horarios(self, doctor_id: int, service_id: int, appointment_date: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/horarios/{doctor_id}",
            params={"fecha": appointment_date, "id_servicio": service_id},
        )

    async def reservar(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/citas/reservar", json=payload)

    async def cancelar(self, appointment_id: int, origin: str) -> dict[str, Any]:
        return await self._request("PATCH", f"/citas/cancelar/{appointment_id}", json={"origen": origin})

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=10.0) as client:
                response = await client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise ApiError(0, "API_NO_DISPONIBLE", "No se pudo conectar con la API.") from exc

        if response.is_success:
            return response.json()

        try:
            payload = response.json() if response.content else {}
        except ValueError:
            payload = {}
        detail = payload.get("detail", {}) if isinstance(payload, dict) else {}
        if not isinstance(detail, dict):
            detail = {}
        raise ApiError(
            response.status_code,
            detail.get("codigo", "ERROR_API"),
            detail.get("mensaje", "La API rechazó la solicitud."),
        )

