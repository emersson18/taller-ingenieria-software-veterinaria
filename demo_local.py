"""Demostración local: registra una cita y la consulta desde SQLite."""

from datetime import datetime, timedelta
from pathlib import Path

from agendamiento import Agendamiento, Mascota, Profesional, Servicio, ZONA


CARPETA = Path(__file__).parent
BASE_DATOS = CARPETA / "demostracion.sqlite"

# Datos maestros simulados: permiten probar Agendamiento sin implementar aquí
# los módulos de propietarios, mascotas, servicios ni profesionales.
mascotas = {1: Mascota(id=1, propietario_id=100, propietario_activo=True)}
servicios = {1: Servicio(id=1, duracion_minutos=60, activo=True)}
profesionales = {1: Profesional(id=1, activo=True)}


def horario_publicado(profesional_id: int, inicio: datetime, fin: datetime) -> bool:
    return profesional_id == 1 and inicio.hour >= 8 and fin.hour <= 18


def usuario_autorizado(rol: str, operacion: str) -> bool:
    return rol in {"administrador", "recepcion"}


app = Agendamiento(
    ruta_bd=BASE_DATOS,
    obtener_mascota=mascotas.get,
    obtener_servicio=servicios.get,
    obtener_profesional=profesionales.get,
    horario_valido=horario_publicado,
    autorizar=usuario_autorizado,
)

# Cada ejecución elige el próximo día libre para este propietario de prueba,
# así se puede volver a correr sin chocar con la cita demostrativa anterior.
reservadas = app.listar(rol="recepcion")
dias_usados = {
    datetime.fromisoformat(cita["inicio"]).date()
    for cita in reservadas
    if cita["propietario_id"] == 100
}
inicio = (datetime.now(ZONA) + timedelta(days=1)).replace(
    hour=10, minute=0, second=0, microsecond=0
)
while inicio.date() in dias_usados:
    inicio += timedelta(days=1)

cita_id = app.reservar(
    rol="recepcion",
    mascota_id=1,
    servicio_id=1,
    profesional_id=1,
    inicio=inicio,
)

print("Cita registrada correctamente")
print(f"Identificador: {cita_id}")
print(f"Inicio: {inicio.isoformat()}")
print(f"Fin: {(inicio + timedelta(minutes=60)).isoformat()}")
print(f"Base de datos: {BASE_DATOS}")
print("Citas guardadas:")
for cita in app.listar(rol="recepcion"):
    print(
        f"- #{cita['id']} | mascota {cita['mascota_id']} | "
        f"profesional {cita['profesional_id']} | {cita['inicio']} | {cita['estado']}"
    )
