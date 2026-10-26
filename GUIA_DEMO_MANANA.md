# Demostración de mañana: Sistema Hospitalario

Esta carpeta contiene todo el código del Sprint 2. La base y el programa son
dos cosas distintas: primero se instala MySQL, después se conecta el programa.

## Antes de salir de esta computadora

Copie la carpeta completa `Proyecto Concurrente` a una USB, Drive o la laptop
del compañero. No hace falta copiar la carpeta `.venv` si aparece: se crea de
nuevo en la otra laptop.

## En la laptop del compañero

Instalen una sola vez:

1. Python 3.11 o posterior. Durante la instalación marquen **Add Python to PATH**.
2. MySQL Server 8 y MySQL Workbench. Guarden la contraseña de `root`.

## Parte A: crear la base de datos

1. Abran **MySQL Workbench** y entren a la conexión local.
2. En `db`, abran `01_INSTALAR_BASE_CORREGIDA.sql`.
3. Presionen el icono del rayo para ejecutarlo una sola vez.
4. Abran `02_CARGAR_DATOS_DEMO.sql` y presionen el rayo.
5. Al final verán tres resultados: `id_paciente`, `id_doctor` e `id_servicio`.
   Anoten esos números. En una base nueva normalmente los tres serán `1`.

> `01_INSTALAR_BASE_CORREGIDA.sql` elimina y vuelve a crear solamente la base
> `sistema_hospitalario`. Úsenlo para una demo nueva; no lo ejecuten si desean
> conservar citas ya registradas.

## Parte B: preparar Python, sin escribir comandos

1. Den doble clic a `PREPARAR_PROYECTO.bat` y esperen el mensaje **Listo**.
2. Abran el archivo `.env` con Bloc de notas.
3. Cambien solamente esta línea con la contraseña de MySQL:

```env
DB_PASSWORD=ESCRIBE_AQUI_TU_CONTRASENA_MYSQL
```

4. Guarden el archivo.

## Parte C: ejecutar la demostración

1. Den doble clic a `INICIAR_BACKEND.bat`. Déjenlo abierto.
2. Esperen a leer `Uvicorn running on http://127.0.0.1:8000`.
3. Den doble clic a `INICIAR_FLET.bat`.
4. En Flet escriban los tres IDs obtenidos en MySQL, por ejemplo `1`, `1`, `1`.
5. Escriban una fecha que caiga en jueves, por ejemplo `2026-10-22`.
6. Presionen **Consultar horarios**, elijan una hora, escriban un motivo y
   presionen **Reservar cita**.

La cita queda guardada en la tabla `citas` de MySQL. Para comprobarlo, en
Workbench ejecuten:

```sql
USE sistema_hospitalario;
SELECT * FROM citas;
```

Para cancelar, copien el `id_cita` mostrado en Workbench, péguenlo en Flet y
presionen **Cancelar cita**. Con esta versión corregida, el horario cancelado
puede volver a reservarse.

## Si prefieren comandos

Desde PowerShell, dentro de esta carpeta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

En una ventana:

```powershell
.\.venv\Scripts\Activate.ps1
python run_backend.py
```

En una segunda ventana:

```powershell
.\.venv\Scripts\Activate.ps1
python -m flet run frontend\app.py
```

## Qué explicar al profesor

- Flet es la interfaz: el paciente consulta, reserva y cancela.
- FastAPI recibe la petición y nunca permite que Flet acceda directamente a MySQL.
- MySQL conserva doctores, pacientes, servicios, horarios y citas.
- `sp_reservar_cita` abre una transacción y bloquea la agenda del médico con
  `SELECT ... FOR UPDATE`. Si dos personas intentan apartar el mismo horario,
  solo una reserva y la otra recibe conflicto HTTP 409.
