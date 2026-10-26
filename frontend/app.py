import os
from datetime import date

import flet as ft

try:
    # Funciona cuando Flet inicia este archivo directamente.
    from api_client import ApiError, HospitalApiClient
except ModuleNotFoundError:
    # También permite ejecutar pruebas o importar frontend.app desde la raíz.
    from frontend.api_client import ApiError, HospitalApiClient


class CitasView:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.client = HospitalApiClient(os.getenv("HOSPITAL_API_BASE_URL", "http://127.0.0.1:8000"))
        self.patient_id = ft.TextField(label="ID del paciente", keyboard_type=ft.KeyboardType.NUMBER)
        self.doctor_id = ft.TextField(label="ID del médico", keyboard_type=ft.KeyboardType.NUMBER)
        self.service_id = ft.TextField(label="ID del servicio", keyboard_type=ft.KeyboardType.NUMBER)
        self.appointment_date = ft.TextField(label="Fecha (AAAA-MM-DD)", value=date.today().isoformat())
        self.reason = ft.TextField(label="Motivo de consulta", multiline=True, min_lines=2, max_lines=4)
        self.slot = ft.Dropdown(label="Horario disponible", options=[], disabled=True)
        self.status = ft.Text(value="Consulta una fecha, médico y servicio para ver los horarios.")
        self.loading = ft.ProgressRing(visible=False, width=20, height=20, stroke_width=2)
        self.cancel_id = ft.TextField(label="ID de la cita a cancelar", keyboard_type=ft.KeyboardType.NUMBER)
        self.cancel_origin = ft.Dropdown(
            label="Cancelada por",
            value="paciente",
            options=[
                ft.DropdownOption(key="paciente", text="Paciente"),
                ft.DropdownOption(key="medico", text="Médico"),
            ],
        )

    def build(self) -> ft.Control:
        return ft.SafeArea(
            content=ft.Column(
                controls=[
                    ft.Text("Gestión de citas", size=28, weight=ft.FontWeight.W_600),
                    ft.Text("Consulta disponibilidad y reserva de forma segura."),
                    ft.Row(controls=[self.patient_id, self.doctor_id, self.service_id], wrap=True),
                    ft.Row(
                        controls=[
                            self.appointment_date,
                            ft.Button(content="Consultar horarios", on_click=self.consultar_horarios),
                        ],
                        wrap=True,
                    ),
                    self.slot,
                    self.reason,
                    ft.Row(
                        controls=[
                            ft.Button(content="Reservar cita", on_click=self.reservar_cita),
                            self.loading,
                        ]
                    ),
                    ft.Divider(),
                    ft.Text("Cancelar una cita", size=20, weight=ft.FontWeight.W_500),
                    ft.Row(
                        controls=[
                            self.cancel_id,
                            self.cancel_origin,
                            ft.Button(content="Cancelar cita", on_click=self.cancelar_cita),
                        ],
                        wrap=True,
                    ),
                    self.status,
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=14,
            )
        )

    def _ids_and_date(self) -> tuple[int, int, int, str]:
        try:
            patient_id = int(self.patient_id.value or "")
            doctor_id = int(self.doctor_id.value or "")
            service_id = int(self.service_id.value or "")
            date.fromisoformat(self.appointment_date.value or "")
        except ValueError as exc:
            raise ValueError("Captura identificadores numéricos y una fecha AAAA-MM-DD válida.") from exc
        if min(patient_id, doctor_id, service_id) <= 0:
            raise ValueError("Los identificadores deben ser mayores a cero.")
        return patient_id, doctor_id, service_id, self.appointment_date.value

    def _show_status(self, message: str, color: str) -> None:
        self.status.value = message
        self.status.color = color
        self.status.update()

    async def consultar_horarios(self, _: ft.Event | None) -> None:
        try:
            _, doctor_id, service_id, appointment_date = self._ids_and_date()
            self.loading.visible = True
            self.loading.update()
            response = await self.client.get_horarios(doctor_id, service_id, appointment_date)
            available = [item for item in response["horarios"] if item["disponible"]]
            self.slot.options = [
                ft.DropdownOption(key=item["hora_inicio"], text=f"{item['hora_inicio']} - {item['hora_fin']}")
                for item in available
            ]
            self.slot.value = None
            self.slot.disabled = not available
            self.slot.update()
            if response["medico_ausente"]:
                self._show_status("El médico está ausente en esa fecha.", ft.Colors.RED)
            elif available:
                self._show_status(f"Hay {len(available)} horarios disponibles. Selecciona uno para reservar.", ft.Colors.GREEN)
            else:
                self._show_status("No hay horarios disponibles para los datos consultados.", ft.Colors.ORANGE)
        except (ValueError, ApiError) as exc:
            message = exc.message if isinstance(exc, ApiError) else str(exc)
            self._show_status(message, ft.Colors.RED)
        finally:
            self.loading.visible = False
            self.loading.update()

    async def reservar_cita(self, _: ft.Event) -> None:
        try:
            patient_id, doctor_id, service_id, appointment_date = self._ids_and_date()
            if not self.slot.value:
                raise ValueError("Primero consulta y selecciona un horario disponible.")
            self.loading.visible = True
            self.loading.update()
            result = await self.client.reservar(
                {
                    "id_paciente": patient_id,
                    "id_doctor": doctor_id,
                    "id_servicio": service_id,
                    "fecha_cita": appointment_date,
                    "hora_cita": self.slot.value,
                    "motivo_consulta": self.reason.value or None,
                    "id_cita_anterior": None,
                }
            )
            self._show_status(result["mensaje"], ft.Colors.GREEN)
            await self.consultar_horarios(None)
        except ApiError as exc:
            color = ft.Colors.ORANGE if exc.status_code == 409 else ft.Colors.RED
            self._show_status(exc.message, color)
            if exc.status_code == 409:
                await self.consultar_horarios(None)
        except ValueError as exc:
            self._show_status(str(exc), ft.Colors.RED)
        finally:
            self.loading.visible = False
            self.loading.update()

    async def cancelar_cita(self, _: ft.Event) -> None:
        try:
            appointment_id = int(self.cancel_id.value or "")
            if appointment_id <= 0:
                raise ValueError
            self.loading.visible = True
            self.loading.update()
            result = await self.client.cancelar(appointment_id, self.cancel_origin.value or "paciente")
            self._show_status(result["mensaje"], ft.Colors.GREEN)
        except ValueError:
            self._show_status("Captura un ID de cita válido para cancelar.", ft.Colors.RED)
        except ApiError as exc:
            color = ft.Colors.ORANGE if exc.status_code == 409 else ft.Colors.RED
            self._show_status(exc.message, color)
        finally:
            self.loading.visible = False
            self.loading.update()


async def main(page: ft.Page) -> None:
    page.title = "Sistema Hospitalario"
    page.padding = 24
    page.theme_mode = ft.ThemeMode.LIGHT
    view = CitasView(page)
    page.add(view.build())


if __name__ == "__main__":
    ft.run(main)

