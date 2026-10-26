"""Diez hilos contra la API encendida. Crea UNA cita real si la prueba pasa."""

import argparse
import json
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--paciente", type=int, required=True)
    parser.add_argument("--doctor", type=int, required=True)
    parser.add_argument("--servicio", type=int, required=True)
    parser.add_argument("--fecha", required=True, help="AAAA-MM-DD, dentro de la jornada del médico")
    parser.add_argument("--hora", required=True, help="HH:MM:SS, turno libre")
    args = parser.parse_args()
    payload = {
        "id_paciente": args.paciente, "id_doctor": args.doctor,
        "id_servicio": args.servicio, "fecha_cita": args.fecha,
        "hora_cita": args.hora, "motivo_consulta": "Demostración de mutex con diez hilos",
    }
    barrier = threading.Barrier(10)

    def worker(index):
        with httpx.Client(timeout=60) as client:
            barrier.wait(timeout=30)
            response = client.post(args.url.rstrip("/") + "/citas/reservar", json=payload)
            return {"hilo": index, "status": response.status_code, "respuesta": response.json()}

    with ThreadPoolExecutor(max_workers=10, thread_name_prefix="demo") as executor:
        results = list(executor.map(worker, range(10)))
    for result in results:
        print(json.dumps(result, ensure_ascii=False))
    counts = Counter(row["status"] for row in results)
    print("Resultados HTTP:", dict(counts))
    if counts != {201: 1, 409: 9}:
        raise SystemExit("NO PASÓ: se esperaba exactamente un 201 y nueve 409. Verifica turno y datos.")
    print("PASÓ: una reserva confirmada y nueve conflictos. Consulta la tabla citas para ver su ID.")


if __name__ == "__main__":
    main()
