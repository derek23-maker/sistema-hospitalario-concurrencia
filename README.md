# Sistema Hospitalario de Gestión de Citas con Control de Concurrencia

Proyecto universitario de **Programación Concurrente** para consultar disponibilidad,
reservar y cancelar citas médicas. Flet se comunica por HTTP con FastAPI;
únicamente el backend accede a MySQL.

Repositorio: [sistema-hospitalario-concurrencia](https://github.com/derek23-maker/sistema-hospitalario-concurrencia).

## Objetivo y alcance

Coordinar solicitudes concurrentes sobre la agenda de cada médico y conservar
resultados consistentes en una base relacional. Incluye consulta, reserva,
cancelación y conservación del historial. No incluye autenticación,
administración de catálogos desde la interfaz ni una demostración validada desde
dos computadoras. La interfaz ejecutada y comprobada es de escritorio.

## Tecnologías

| Tecnología | Función |
| --- | --- |
| Python | Lenguaje común de backend, interfaz y pruebas; ejecución comprobada con Python 3.13.5. |
| FastAPI y Pydantic | Rutas HTTP, contratos JSON, validación y documentación OpenAPI. |
| Flet | Formularios, consulta de horarios, reserva y cancelación. |
| HTTPX | Cliente asíncrono de Flet y solicitudes del ensayo concurrente. |
| MySQL 8 e InnoDB | Persistencia, relaciones, transacciones y procedimiento almacenado. |
| threading.Lock | Exclusión mutua por médico dentro del proceso del backend. |
| threading.Barrier y ThreadPoolExecutor | Coordinación de los clientes concurrentes de prueba. |
| unittest y TestClient | Pruebas de reglas, repositorio simulado y rutas ASGI. |

Los rangos de dependencias están en [requirements.txt](requirements.txt); no son
un bloqueo exacto de versiones.

## Arquitectura

```text
Flet --- HTTP / JSON (HTTPX) ---> Rutas FastAPI y contratos Pydantic
                                      |
                                 AgendaService
                             mutex por médico/proceso
                                      |
                               AgendaRepository
                               pool de conexiones
                                      |
                                MySQL InnoDB
                         procedimiento y transacciones
```

La consulta de disponibilidad no toma el mutex. Reserva y cancelación comparten
el candado del médico. Consultar un turno libre no garantiza que siga libre al
confirmarlo; la operación vuelve a validar el estado. El candado no se comparte
entre procesos y no sustituye las transacciones. Consulte
[Implementación de concurrencia](docs/concurrencia.md).

## Estructura del proyecto

```text
.env.example                    Plantilla sin contraseña real
.gitignore                      Exclusión de secretos y artefactos
README.md                       Presentación, instalación y ejecución
requirements.txt                Dependencias
run_backend.py                  Inicio de Uvicorn en 127.0.0.1:8000
PREPARAR_PROYECTO.bat            Preparación del entorno .venv
INICIAR_BACKEND.bat              Inicio del backend con .venv
INICIAR_FLET.bat                 Inicio de Flet con .venv
Abrir_IDLE_del_proyecto.bat      Apertura de IDLE con .venv
backend/
  app/
    api/                        Dependencias y rutas
    core/                       Configuración
    domain/                     Contratos, intervalos y resultados
    infrastructure/             Pool y conexiones MySQL
    repositories/               Consultas SQL y transacciones
    services/                   Reglas y mutex por médico
    main.py                     Construcción de FastAPI
  tests/                        Pruebas unitarias, ASGI e integración optativa
frontend/                       Interfaz Flet y cliente HTTP
db/
  compacta/                     Exportado del modelo de seis tablas
  *.sql                         Instaladores y migraciones del modelo ampliado
scripts/
  probar_api_concurrente.py      Diez solicitudes contra una API activa
docs/
  concurrencia.md               Mutex, barrera, transacciones y límites
  pruebas.md                    Verificación y resultados técnicos
```

## Base de datos: modelos que no deben mezclarse

La demostración comprobada utilizó **seis tablas** de sistema_hospitalario:
pacientes, doctores, servicios, horarios_doctor, ausencias_doctor y citas.
El backend detecta esa estructura y adapta las consultas. La referencia es
[el exportado compacto](db/compacta/CHAT_estructura_exportada.sql), que contiene
DDL y procedimiento, pero **no los datos de prueba**. Incluye DROP TABLE y
DROP PROCEDURE: no debe ejecutarse sobre una base existente para iniciar la API.
La inicialización reproducible de datos de una instalación compacta vacía queda
pendiente; esta ruta no se presenta como instalación completa desde cero.

Los SQL de la raíz de db/ corresponden al modelo **ampliado de trece tablas**:

- 01_INSTALAR_BASE_CORREGIDA.sql reconstruye la base y **borra sus datos**.
- 02_CARGAR_DATOS_DEMO.sql proporciona datos de ejemplo del modelo ampliado.
- 003_mutex_concurrencia.sql es una migración de ese modelo, no del compacto.
- 001_hardening_sp_reservar_cita.sql y 002_datos_demo.sql son antecedentes del
  esquema ampliado; 001 es legado y no debe reinstalarse después de 003.

Se conservan todos los SQL sin ejecutarlos durante esta limpieza. Antes de usarlos
se debe identificar el modelo, revisar su contenido y respaldar los datos.
La base compacta no contiene la llave única de turno con horario_ocupado
que sí incorpora la versión ampliada corregida.

## Instalación en Windows

Requisitos: Python 3.11 o superior, MySQL 8 activo y una base compatible preparada.
Utilice preferentemente una cuenta MySQL de privilegios limitados; no comparta
sus credenciales con los clientes de la interfaz.

Desde PowerShell, en la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Complete localmente DB_HOST, DB_PORT, DB_NAME, DB_USER y DB_PASSWORD. No publique
.env. Los demás parámetros están documentados en .env.example. No copie entornos
virtuales entre computadoras ni ejecute instaladores SQL para arrancar una base
ya preparada.

PREPARAR_PROYECTO.bat automatiza la creación de .venv, las dependencias y la copia
de la plantilla si .env no existe. No instala MySQL ni crea tablas.
La ejecución previamente comprobada utilizó .venv-tests; si conserva ese entorno,
sustituya .venv por .venv-tests en los comandos. Los .bat apuntan a .venv.

## Ejecución

Primera terminal desde la raíz:

```powershell
.\.venv\Scripts\python.exe run_backend.py
```

Segunda terminal, manteniendo el backend abierto:

```powershell
$env:HOSPITAL_API_BASE_URL = 'http://127.0.0.1:8000'
.\.venv\Scripts\python.exe frontend\app.py
```

Con .venv preparado, también pueden usarse INICIAR_BACKEND.bat e INICIAR_FLET.bat.
Abrir_IDLE_del_proyecto.bat abre IDLE con ese intérprete para ejecutar cada
programa por separado. Ningún lanzador reconstruye la base. run_backend.py
escucha solo en la interfaz local, con un proceso y sin recarga automática.

Documentación interactiva: [OpenAPI /docs](http://127.0.0.1:8000/docs).

| Operación | Método y ruta | Resultado |
| --- | --- | --- |
| Consultar | GET /horarios/{id_doctor}?fecha=AAAA-MM-DD&id_servicio=ID | 200 con franjas para la duración del servicio. |
| Reservar | POST /citas/reservar | 201 al confirmar; 409 ante conflicto. |
| Cancelar | PATCH /citas/cancelar/{id_cita} | 200 al cancelar; 409 si ya no es cancelable. |
| Estado | GET /health | Disponibilidad HTTP, no comprobación continua de MySQL. |

## Pruebas y resultados

Para comprobar lógica y coordinación sin MySQL, **no defina**
HOSPITAL_TEST_DB_PASSWORD en esa terminal. Las tres integraciones optativas se
omiten cuando esa variable no existe; habilitarlas crea y elimina una base temporal.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

Las pruebas ASGI sustituyen MySQL por un repositorio en memoria; no equivalen a
una ejecución distribuida. El procedimiento para diez clientes HTTP, sus
precondiciones y consultas de persistencia están en
[Pruebas y resultados](docs/pruebas.md).

La ejecución funcional documentada obtuvo una reserva HTTP 201 y nueve conflictos
409 al intentar el mismo turno, con una sola cita confirmada en MySQL. Se
comprobaron cancelación, liberación y nueva reserva con otro ID, conservando el
historial. No se presentan estos resultados como prueba de carga sostenida ni de
protección aislada entre procesos.

## Seguridad y limitaciones

.env, claves privadas, entornos virtuales, cachés y materiales personales de
preparación quedan excluidos. .env.example contiene valores de ejemplo.
Revise los cambios antes de cada commit.

Los identificadores se capturan manualmente y no existe autenticación. El mutex
es local a un proceso y no promete orden FIFO. Al refrescar disponibilidad, Flet
puede reemplazar el mensaje de confirmación; el límite del motivo también difiere
entre contrato y procedimiento compacto. Estos aspectos y la inicialización
compacta pendiente requieren revisión antes de un uso fuera del entorno académico.
Estas instrucciones no publican el servicio en internet.

