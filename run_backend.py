"""Lanzador para ejecutar la API con F5 desde IDLE o con doble clic en un IDE."""

from pathlib import Path
import sys

import uvicorn


PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIRECTORY = PROJECT_ROOT / "backend"

if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
