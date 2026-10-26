# Mutex por médico y pruebas concurrentes

## Código vigente

Use el backend de la raíz de este proyecto. La carpeta y el ZIP
`SISTEMA_HOSPITALARIO_SPRINT_2` son una fotografía de la entrega anterior y no
contienen esta actualización del mutex.

Se conservaron Flet, FastAPI, MySQL y las rutas de consulta, reserva y cancelación.
El mutex se aplica en el servicio real que usan las rutas, no en un ejemplo aparte.

## Preparar la base

Si ya tiene la base de la entrega anterior, detenga FastAPI, respalde los datos
y ejecute **una sola vez** `db/003_mutex_concurrencia.sql` en MySQL Workbench.
No borra citas. Cambia la llave única y reemplaza `sp_reservar_cita`.
No ejecute el antiguo `001_hardening_sp_reservar_cita.sql` después.

Para una base completamente nueva, ejecute `db/01_INSTALAR_BASE_CORREGIDA.sql`
y luego `db/02_CARGAR_DATOS_DEMO.sql`. En esa ruta ya no hace falta 003.
El archivo 01 sí elimina y reconstruye la base; úselo solo en una instalación nueva.

El procedimiento deja de sobrescribir citas canceladas. Cada reserva genera un
ID nuevo; una cancelación tardía no afecta a otra reserva. Las transacciones de
reserva y cancelación bloquean primero el médico y después operan sobre citas.
La restricción de unicidad sigue impidiendo dos turnos exactos ocupados.

## Ejecutar las pruebas sin MySQL

Desde PowerShell, dentro de la carpeta del proyecto:

```powershell
.\.venv-tests\Scripts\python.exe -m unittest discover -s backend\tests -v
```

En esta PC se creó `.venv-tests` porque `.venv` mezclaba un intérprete Python 3.13
con un binario de pydantic-core para Python 3.12 y no podía importar FastAPI.
No se borró ni se reemplazó ese entorno anterior. Para crear un entorno de prueba
en otra computadora:

```powershell
python -m venv .venv-tests
.\.venv-tests\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-tests\Scripts\python.exe -m unittest discover -s backend\tests -v
```

Las pruebas HTTP en `test_mutex_api.py` ejecutan las rutas y la dependencia real
que crea un servicio por petición. Solo sustituyen el repositorio MySQL por uno
en memoria que amplía deliberadamente la ventana de carrera. Verifican:

- Diez hilos, `threading.Barrier(10)`, exactamente un 201 y nueve 409.
- Un solo hilo dentro de la reserva por médico.
- Dos médicos dentro de sus secciones críticas al mismo tiempo, con otra barrera.
- Consulta de horarios mientras el mutex del médico está ocupado.
- Cancelación seguida de reserva y reserva seguida de cancelación.
- Cancelación tardía de un ID viejo sin afectar a la nueva cita.
- Liberación tras una excepción y limpieza del registro de mutex.
- Mensajes de espera, adquisición y liberación para los diez intentos.

Las pruebas del repositorio comprueban el orden de SQL de cancelación, commit,
rollback y rechazo de citas completadas/canceladas con conexiones simuladas.
Estas pruebas no sustituyen la ejecución del procedimiento en MySQL.

## Integración opcional con MySQL real

`test_mysql_concurrency.py` crea una base temporal con nombre aleatorio
`hospital_mutex_test_...`, instala tablas y datos, y la elimina al terminar.
No modifica `sistema_hospitalario`. Necesita una cuenta con permisos para crear
y eliminar esa base temporal. Proporcione la contraseña sin escribirla en un archivo:

```powershell
$clavePrueba = Read-Host 'Contraseña de MySQL' -AsSecureString
$env:HOSPITAL_TEST_DB_PASSWORD = [System.Net.NetworkCredential]::new('', $clavePrueba).Password
$env:HOSPITAL_TEST_DB_USER = 'root'
.\.venv-tests\Scripts\python.exe -m unittest discover -s backend\tests -p test_mysql_concurrency.py -v
Remove-Item Env:HOSPITAL_TEST_DB_PASSWORD
```

Opcionalmente configure `HOSPITAL_TEST_DB_HOST` y `HOSPITAL_TEST_DB_PORT`.
Las tres pruebas comprueban la reserva por HTTP con MySQL real, diez conexiones
llamando al procedimiento **sin mutex Python** y cancelación con nueva reserva.
Así se puede demostrar por separado la protección local y la de la base.
Si no existe `HOSPITAL_TEST_DB_PASSWORD`, se reportan explícitamente como omitidas.

## Demostrar diez solicitudes contra el servidor encendido

Configure `.env` con las credenciales de su base y aplique el SQL indicado arriba.
En una terminal, inicie un solo proceso sin recarga:

```powershell
.\.venv-tests\Scripts\python.exe run_backend.py
```

En otra terminal ejecute lo siguiente, cambiando IDs, fecha y hora por un turno
realmente libre que esté dentro de la jornada del médico:

```powershell
.\.venv-tests\Scripts\python.exe scripts\probar_api_concurrente.py --paciente 1 --doctor 1 --servicio 1 --fecha 2030-01-03 --hora 09:00:00
```

El ejemplo usa un jueves, que coincide con el horario de los datos demo.
Esta demostración crea una cita real. Se espera un 201 y nueve 409; el script
termina con error si obtiene otro resultado. Si se repite sobre el turno ya
ocupado, los diez intentos serán conflictos. Puede cancelar la cita usando su
ID desde Flet o `/docs`, o elegir otro turno libre para repetir.

En la consola del backend verá líneas parecidas a:

```text
mutex espera pid=... hilo=... medico=1 operacion=reserva
mutex adquirido pid=... hilo=... medico=1 operacion=reserva espera_ms=...
mutex liberado pid=... hilo=... medico=1 operacion=reserva
```

`espera` marca el intento; `espera_ms` mide cuánto tardó la adquisición.
Los ID de hilo son los hilos del backend, que pueden atender varias peticiones
en distintos momentos. El mutex es por médico y por proceso; si se usan varios
workers, cada uno tiene su registro y MySQL sigue dando protección entre ellos.

## Resultados verificados en esta modificación

Ejecución: `python -m unittest discover -s backend/tests -v` en `.venv-tests`.
Se ejecutaron 25 pruebas: **22 aprobadas y 3 omitidas**.
El escenario HTTP con repositorio en memoria verificó un 201 y nueve 409,
además de concurrencia entre médicos y coordinación de cancelaciones.
`compileall` finalizó sin errores y `pip check` no encontró dependencias rotas.

No se ejecutaron las tres integraciones con MySQL real ni la demostración sobre
el servidor con la base del usuario: no había `.env` ni contraseña de prueba
configurada. Los SQL fueron revisados, pero no se aplicaron a esa base.
