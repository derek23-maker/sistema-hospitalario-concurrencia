# Implementación del control de concurrencia

## Recurso compartido y condición de carrera

El recurso protegido es la agenda de cada médico. Dos clientes pueden consultar
el mismo turno libre antes de que alguno confirme su reserva. Consultar y escribir
son operaciones distintas: la disponibilidad debe revalidarse al confirmar.

## Mutex por médico

[`DoctorMutexRegistry`](../backend/app/services/doctor_mutex.py) mantiene entradas
por `id_doctor`. Cada una contiene un `threading.Lock` y un contador de usuarios
que incluye propietario y esperadores. La instancia `doctor_mutexes` se comparte
entre servicios del mismo proceso; no se crea un candado por petición.

[`AgendaService.reserve`](../backend/app/services/agenda.py) entra en
`with self._mutexes.hold(request.id_doctor, "reserva")` antes de validar la jornada
y llamar al procedimiento. `cancel` identifica al médico y utiliza ese mismo
registro con la operación `cancelacion`. Las operaciones de un médico se excluyen;
las de médicos distintos pueden avanzar con candados diferentes. Consultar horarios
permanece fuera del mutex.

El candado auxiliar `_guard` solo protege el diccionario y el contador; no abarca
SQL ni la espera del candado del médico. `finally` libera el mutex incluso ante
excepciones. Cuando no quedan propietarios ni esperadores se retira la entrada.
El conteo impide eliminar un candado aún utilizado y crear dos para el mismo médico.

Los logs registran PID, hilo, médico y operación:

```text
mutex espera pid=... hilo=... medico=1 operacion=reserva
mutex adquirido pid=... hilo=... medico=1 operacion=reserva espera_ms=...
mutex liberado pid=... hilo=... medico=1 operacion=reserva
```

`espera` anuncia el intento, incluso si el candado está libre. `espera_ms` mide el
tiempo hasta adquirirlo, no la petición completa. Los identificadores son hilos
del servidor, no los índices de los clientes del script. Un hilo puede atender
distintas peticiones a lo largo del tiempo.

## Barrera e hilos

[`probar_api_concurrente.py`](../scripts/probar_api_concurrente.py) utiliza
`ThreadPoolExecutor(max_workers=10)`. Cada trabajador crea un cliente HTTP, espera
en `threading.Barrier(10)` y envía el mismo cuerpo de reserva. La barrera coordina
el inicio para aumentar la coincidencia temporal; no protege datos ni garantiza
llegada simultánea exacta. Pertenece al cliente; el mutex está en el backend.

Las rutas síncronas de FastAPI se atienden mediante hilos. El GIL de CPython no
convierte consultar-validar-insertar en una operación atómica ni reemplaza este
candado. El uso asíncrono de HTTPX en Flet permite esperar la respuesta de red;
asincronía y exclusión mutua resuelven problemas diferentes.

## Transacciones y modelos SQL

[`AgendaRepository`](../backend/app/repositories/agenda.py) obtiene conexiones del
pool y llama a `sp_reservar_cita`. La rutina valida entidades, jornada, ausencias
y traslapes e inserta una cita cuando corresponde. Mantiene `START TRANSACTION`,
`COMMIT`, `ROLLBACK` y una lectura con `FOR UPDATE` sobre la búsqueda del médico.
La cancelación inicia su transacción desde Python, bloquea primero médico y luego
cita, revalida el estado y actualiza el registro. Cancelar no elimina la cita;
reservar de nuevo crea otro ID y conserva el historial.

| Aspecto | Compacto usado en la demostración | Ampliado corregido |
| --- | --- | --- |
| Tablas | Seis; horarios_doctor y ausencias_doctor | Trece; horarios_medicos y ausencias_medicos |
| Lectura inicial del médico | SELECT COUNT(*) sobre doctores con FOR UPDATE | Lectura directa del ID con FOR UPDATE |
| Restricción de turno | Sin llave única de médico/fecha/hora | Columna generada horario_ocupado y llave única |
| Cancelación persistida | cancelada, cancelada_por y cancelada_en | Estados y campos del esquema ampliado |

La referencia compacta es
[`db/compacta/CHAT_estructura_exportada.sql`](../db/compacta/CHAT_estructura_exportada.sql).
Los instaladores y la migración de la raíz de `db/` son del modelo ampliado;
no deben aplicarse sobre la base compacta existente. Su presencia no demuestra
que ambos modelos se hayan probado de la misma manera.

## Límites

El mutex existe **por proceso**: no coordina otros workers, otras aplicaciones o
cambios directos desde Workbench. No promete orden FIFO. Para observarlo se usa
un único proceso del backend. MySQL conserva sus responsabilidades transaccionales;
no se atribuye al candado una garantía distribuida.

La prueba real de diez solicitudes comprobó el flujo integrado con el mutex
activo, no el bloqueo de MySQL aislado entre procesos. La reprogramación mediante
`id_cita_anterior`, especialmente con cambio de médico, requiere revisión y
pruebas específicas. Los futuros cambios de jornadas o ausencias deberán definir
un protocolo compatible de bloqueo.

Los casos y resultados se conservan en [Pruebas y resultados](pruebas.md).
