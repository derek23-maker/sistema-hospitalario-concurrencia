# Pruebas y resultados técnicos

## Alcance de la suite

Se distinguen pruebas unitarias y ASGI con repositorio simulado, ejecución HTTP
con la base real e integración optativa sobre una base temporal. Un caso
programado no equivale a una prueba ejecutada contra la base de la demostración.

| Archivo en backend/tests/ | Alcance |
| --- | --- |
| test_slots.py | Intervalos y traslapes. |
| test_reservation_result.py | Clasificación de resultados del procedimiento. |
| test_agenda_service.py | Reglas de servicio y validación de jornada. |
| test_repository_cancellation.py | SQL y transacciones simuladas, compatibilidad compacta y retorno OUT. |
| test_mutex_api.py | Rutas ASGI y registro real de mutex con repositorio en memoria. |
| test_mysql_concurrency.py | Integración optativa con MySQL y esquema ampliado temporal. |

Los casos ASGI verifican diez intentos con un 201 y nueve 409, exclusión por médico,
avance concurrente de médicos distintos, consulta sin adquirir el mutex,
coordinación de reserva y cancelación, cancelación tardía de un ID antiguo,
liberación tras excepciones, limpieza del registro y trazas del candado. Las
conexiones simuladas verifican SQL, commit y rollback sin usar MySQL real.

## Ejecución sin modificar MySQL

Con dependencias instaladas, desde la raíz:

```powershell
# Retirar solo de esta terminal si estaba definida; omite las integraciones reales.
Remove-Item Env:HOSPITAL_TEST_DB_PASSWORD -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

Puede sustituir `.venv` por `.venv-tests` si ese es su entorno preparado.
Sin `HOSPITAL_TEST_DB_PASSWORD`, las tres integraciones MySQL se omiten
explícitamente. No necesita iniciar Flet ni el backend para los casos ASGI.

## Resultados funcionales documentados

Las evidencias del 25 de octubre de 2026 corresponden a Windows, Python 3.13.5 y
la base compacta de seis tablas. Se usaron médico 1, paciente 1, servicio 1 y una
jornada del lunes 26 de octubre de 09:00 a 14:00.

| ID | Escenario | Resultado observado | Evidencia |
| --- | --- | --- | --- |
| PF-01 | Consultar horarios | Diez turnos de treinta minutos; HTTP 200. | Flet y respuesta JSON. |
| PF-02 | Reservar las 09:00 | Cita 1 confirmada en MySQL; turno retirado de disponibilidad. El primer retorno tuvo la incidencia OUT indicada abajo. | Interfaz y tabla citas. |
| PF-03 | Diez solicitudes a las 09:30 | Una respuesta 201 y nueve 409; cliente índice 3 confirmado en esa ejecución. | Salida del script y logs del backend. |
| PF-04 | Verificar unicidad observada | reservas_confirmadas = 1; cita 2 confirmada. | SELECT COUNT(*) en MySQL. |
| PF-05 | Cancelar cita 1 | Mensaje de éxito, estado cancelada, origen paciente y fecha; cita 2 intacta. | Flet y consulta SQL. |
| PF-06 | Reservar otra vez las 09:00 | Turno disponible y nueva cita 3; cita 1 permanece cancelada. | Lista de horarios e historial SQL. |
| PF-07 | Cancelar de nuevo el ID 1 | Aviso de cita ya cancelada o completada; IDs 2 y 3 siguen confirmados. | Flet y consulta final. |

Las capturas originales con pies de figura se conservan en el paquete documental
de Fase 2, separado de los materiales personales de estudio. No se eliminan con
esta limpieza. La tabla registra la ejecución observada, no nuevas reservas.

Las trazas mostraron espera, adquisición y liberación con distintos hilos del
mismo PID para el médico 1. El conteo SQL complementa las respuestas HTTP:
un conflicto por sí solo no demuestra la integridad persistida.

## Incidencia del parámetro OUT

Se observó `KeyError: -1` al ejecutar `returned_args[-1]` después de `callproc`.
El cursor de diccionarios devolvía parámetros por nombre, no por posición. La cita
ya estaba confirmada, por lo que el fallo de respuesta no implicó rollback.
El código vigente distingue diccionario y tupla, extrae `sp_reservar_cita_arg8`
en el primer caso y consume los result sets. Los casos de regresión están en
`test_repository_cancellation.py`; las peticiones posteriores al reinicio
obtuvieron las respuestas esperadas. Esta limpieza no cambia dicha funcionalidad.

## Diez solicitudes contra una API activa

**Crea una cita real: no ejecutar como revisión documental sin autorización.**
Se necesitan entidades válidas, jornada registrada y un turno libre compatible
con la duración del servicio. Inicie un proceso con `run_backend.py`, sin
reinstalar ni reconstruir la base.

```powershell
# Definir primero los valores con datos válidos y una fecha futura.
.\.venv\Scripts\python.exe scripts\probar_api_concurrente.py --paciente $pacienteId --doctor $doctorId --servicio $servicioId --fecha $fecha --hora $hora
```

La fecha usa AAAA-MM-DD y la hora HH:MM:SS. El script exige exactamente un 201 y
nueve 409. Si el turno está ocupado no se espera una confirmación. El ganador
no es determinista; no tiene por qué volver a ser el cliente 3.

Consultas de lectura utilizadas para la evidencia histórica del modelo compacto:

```sql
SELECT id_cita, id_paciente, id_doctor, fecha_cita, hora_cita, estado
FROM sistema_hospitalario.citas
WHERE id_doctor = 1 AND fecha_cita = '2026-10-26' AND hora_cita = '09:30:00';

SELECT COUNT(*) AS reservas_confirmadas
FROM sistema_hospitalario.citas
WHERE id_doctor = 1 AND fecha_cita = '2026-10-26'
  AND hora_cita = '09:30:00' AND estado = 'confirmada';
```

Esos valores identifican la evidencia histórica, no un turno libre reutilizable.
Para otra ejecución deben sustituirse por los datos efectivamente usados.

## Integración optativa y límites de la evidencia

`test_mysql_concurrency.py` crea una base aleatoria `hospital_mutex_test_...`,
instala el modelo ampliado y elimina esa base al terminar. No usa la base
`sistema_hospitalario` existente. Necesita autorización y permisos para crear y
eliminar bases: no debe habilitarse durante una revisión documental sin ellos.
Las variables son `HOSPITAL_TEST_DB_HOST`, `HOSPITAL_TEST_DB_PORT`,
`HOSPITAL_TEST_DB_USER` y `HOSPITAL_TEST_DB_PASSWORD`.

Sus tres casos contemplan reserva HTTP con MySQL, diez llamadas directas al
procedimiento sin mutex Python y cancelación con nueva reserva. Se reportaron
omitidos en las revisiones sin credenciales; no se presentan como aprobados.
Tampoco hay evidencia equivalente de carga sostenida, varios procesos contra
la base compacta, fallos de red o demostración desde dos equipos. La rama de
reprogramación con cambio de médico requiere pruebas adicionales.

## Antecedentes automatizados

La documentación técnica anterior registró una suite preliminar de 25 casos:
22 aprobados y tres integraciones omitidas, junto con comprobaciones de sintaxis
y dependencias. Es un antecedente, no el conteo de la suite vigente. Las capturas
posteriores respaldan una prueba de médicos distintos y cuatro de coordinación
de cancelaciones con repositorio en memoria. La verificación de esta limpieza
se registra por separado a continuación.

## Verificación de la limpieza documental

La revisión utilizó el entorno existente `.venv-tests` y retiró la variable de
integración únicamente del proceso hijo de Python, sin cambiar `.env` ni la
configuración del sistema:

```powershell
.\.venv-tests\Scripts\python.exe -c "import os, unittest; os.environ.pop('HOSPITAL_TEST_DB_PASSWORD', None); suite=unittest.defaultTestLoader.discover('backend/tests'); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())"
.\.venv-tests\Scripts\python.exe -m pip check
git diff --check
```

Resultado: **29 casos descubiertos, 26 aprobados y 3 omitidos**, sin fallos.
Las omisiones corresponden exclusivamente a `MysqlConcurrencyTests`, por falta
del parámetro de habilitación en ese proceso. Entre los casos aprobados se
encuentran `test_ten_threads_one_created_nine_conflicts`, la concurrencia entre
médicos distintos, las cancelaciones coordinadas y la regresión de retorno OUT.
`pip check` informó `No broken requirements found` y `git diff --check` no
detectó errores de espacios. No se ejecutaron instaladores SQL, reservas reales,
reconstrucciones ni eliminaciones de bases. Esta comprobación valida la suite
sin MySQL; no se presenta como una nueva prueba funcional de la base real.
