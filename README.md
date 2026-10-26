# Sistema Hospitalario de Gestión de Citas

Implementación del Sprint 2 para consultar disponibilidad, reservar citas de forma segura y cancelarlas. El proyecto separa la aplicación Flet de la API FastAPI; ambas se comunican por HTTP y la API es la única que accede a MySQL.

## Estado comprobado y versiones de la base

La ejecución guiada del 25 de octubre de 2026 utilizó la **base compacta de seis tablas**: `pacientes`, `doctores`, `servicios`, `horarios_doctor`, `ausencias_doctor` y `citas`. El backend detecta esa estructura y conserva también compatibilidad con el esquema anterior de trece tablas. No deben mezclarse sus instaladores ni sus migraciones.

El archivo `db/compacta/CHAT_estructura_exportada.sql` es una copia del DDL y procedimiento exportados de la base compacta. No contiene los datos de prueba. Es una referencia de estructura, no una migración para ejecutar sobre una base existente: contiene `DROP TABLE` y `DROP PROCEDURE`. La inicialización reproducible de datos de esa versión queda pendiente de documentar; no se afirma que los scripts de la base ampliada sirvan para ella.

Se observaron por API diez solicitudes coordinadas al mismo turno: un HTTP 201, nueve HTTP 409 y una sola cita confirmada en MySQL. También se comprobaron consulta desde Flet, cancelación, liberación del turno y nueva reserva conservando el ID histórico. Las pruebas automatizadas de médicos distintos y coordinación de cancelaciones utilizaron un repositorio en memoria. No se repitieron estas pruebas durante la preparación del primer commit.

Las guías anteriores y el documento Word de estudio son antecedentes: algunas descripciones del esquema ampliado no corresponden a la base compacta probada. La documentación universitaria de Fase 2 está en preparación. Grupo, equipo y fecha oficial de entrega están pendientes de confirmar.

## Estructura

```text
backend/app/       API, reglas de agenda y acceso a MySQL
frontend/          cliente de escritorio/móvil en Flet
db/                ajuste recomendado para el procedimiento almacenado
backend/tests/     pruebas sin una instancia de MySQL
```

## Antes de ejecutar

1. Cree y active un entorno virtual de Python 3.11 o superior.
2. Instale `pip install -r requirements.txt`.
3. Copie `.env.example` a `.env` y defina las credenciales de una cuenta MySQL con acceso limitado a `sistema_hospitalario`.
4. Si utiliza la **base compacta existente ya comprobada**, conserve sus tablas y procedimiento. No ejecute `003_mutex_concurrencia.sql` ni los instaladores de trece tablas. Si utiliza específicamente el **esquema ampliado anterior**, consulte las advertencias de esos scripts: `003` es su migración y `01` reconstruye la base, borrando datos. El antiguo `001` es legado y no debe reinstalarse.

## Ejecución

En una terminal, desde la raíz del proyecto:

```powershell
.\.venv-tests\Scripts\python.exe run_backend.py
```

En otra terminal:

```powershell
$env:HOSPITAL_API_BASE_URL = "http://127.0.0.1:8000"
.\.venv-tests\Scripts\python.exe frontend\app.py
```

La ejecución comprobada en esta PC usó `.venv-tests`. En una nueva instalación puede crear ese entorno con `python -m venv .venv-tests` e instalar dependencias con `.\.venv-tests\Scripts\python.exe -m pip install -r requirements.txt`. No copie entornos virtuales de otra computadora. Los `.bat` existentes usan `.venv`, por lo que deben ejecutarse solo si ese otro entorno está preparado.

Para ejecutar la API desde IDLE, abra `run_backend.py` con el intérprete que tiene
instaladas las dependencias y presione F5. Mantenga esa ventana abierta y ejecute
`frontend/app.py` con F5 desde una segunda ventana de IDLE.

En Windows, `Abrir_IDLE_del_proyecto.bat` abre una instancia de IDLE con el
intérprete `.venv` del proyecto. Ábralo dos veces para usar una ventana para la
API y otra para Flet.

La especificación interactiva queda disponible en `http://127.0.0.1:8000/docs`.

## Contrato de la API

| Operación | Método y ruta | Resultado relevante |
| --- | --- | --- |
| Consultar agenda | `GET /horarios/{id_doctor}?fecha=AAAA-MM-DD&id_servicio=ID` | Franjas disponibles u ocupadas para la duración del servicio. |
| Reservar | `POST /citas/reservar` | `201` si se confirma; `409` si otra transacción ganó el horario. |
| Cancelar | `PATCH /citas/cancelar/{id_cita}` | Marca la cita como cancelada de forma atómica. |

No se incluyó autenticación porque el Sprint 2 aún no define el mecanismo de login ni cómo se obtiene el paciente autenticado. Por ahora los identificadores se reciben explícitamente; al añadir JWT, `id_paciente` debe obtenerse del token y no del cuerpo de la petición.

## Concurrencia

`backend/app/services/doctor_mutex.py` mantiene un registro compartido por proceso de `threading.Lock`, uno por médico. `AgendaService.reserve` adquiere ese mutex antes de validar y llamar al procedimiento. `cancel` utiliza el mismo mutex. Dos peticiones del mismo médico se ordenan; las de médicos distintos tienen candados diferentes. La consulta de horarios no adquiere estos mutex.

El pequeño candado del diccionario solo protege la creación y el conteo de referencias: nunca cubre SQL ni espera otro mutex. Se cuentan propietarios y esperadores para poder retirar entradas sin crear dos candados simultáneos para el mismo médico. `finally` libera el mutex incluso cuando hay excepciones. Los registros `mutex espera`, `mutex adquirido` y `mutex liberado` muestran PID, identificador del hilo, médico y operación; la adquisición incluye milisegundos de espera. `espera` anuncia el intento de adquirir, aunque el candado esté libre.

El recurso compartido es la agenda de citas del médico. La condición de carrera es consultar un turno libre y confirmarlo mientras otra solicitud intenta hacer lo mismo. El mutex ordena las operaciones **solo dentro de un proceso**; no garantiza disponibilidad, no promete orden FIFO y no comparte memoria entre workers. Para demostrarlo use un worker. MySQL sigue decidiendo si el turno está libre y devuelve conflicto 409 a los intentos que pierden.

`sp_reservar_cita` mantiene START TRANSACTION, COMMIT, ROLLBACK y SELECT FOR UPDATE sobre el médico. El exportado compacto usa `SELECT COUNT(*) ... FROM doctores ... FOR UPDATE`; el SQL ampliado usa una lectura directa de su ID. No se ejecutó una prueba aislada del candado MySQL entre procesos durante la demostración guiada. Cancelación toma una transacción y bloquea primero doctor, después cita. Los timeouts, duplicados y deadlocks también se traducen a 409. Cualquier futuro flujo que cambie la agenda, jornadas o ausencias debe respetar el mismo protocolo de bloqueo del doctor.

**Solo el esquema ampliado** incorpora la llave única con columna generada `horario_ocupado`. La base compacta exportada no tiene esa restricción: sus estados son `confirmada` y `cancelada`, usa `cancelada_por`/`cancelada_en` y conserva la duración en cada cita. En ella la protección de reservas pasa por el procedimiento y los mutex del servicio. La nueva reserva INSERTA con un ID nuevo, conservando cancelaciones anteriores, tal como se comprobó con las citas 1, 2 y 3. El frontend y los contratos HTTP anteriores se conservan.

Consulte [GUIA_MUTEX.md](GUIA_MUTEX.md) para reproducir las pruebas y la demostración con diez hilos.

