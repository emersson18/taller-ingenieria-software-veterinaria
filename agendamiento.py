"""Reglas de negocio para el módulo de agendamiento veterinario.

Este archivo implementa el núcleo del módulo; no es una aplicación web completa.
Los datos maestros (mascotas, servicios, profesionales y horarios) se inyectan al
crear el servicio. SQLite conserva las citas y serializa escrituras concurrentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from typing import Callable, Iterator
from zoneinfo import ZoneInfo


ZONA = ZoneInfo("America/Bogota")
ESTADOS_FINALES = {"Cancelada", "Inasistencia", "Completada"}
TRANSICIONES = {
    "Programada": {"Confirmada", "Cancelada"},
    "Confirmada": {"En atención", "Cancelada", "Inasistencia"},
    "En atención": {"Completada"},
    "Cancelada": set(),
    "Inasistencia": set(),
    "Completada": set(),
}
ROLES_RESERVA = {"administrador", "recepcion"}


class ErrorDeCita(ValueError):
    """Error de validación que puede mostrarse como mensaje seguro al usuario."""


@dataclass(frozen=True)
class Mascota:
    id: int
    propietario_id: int
    propietario_activo: bool


@dataclass(frozen=True)
class Servicio:
    id: int
    duracion_minutos: int
    activo: bool


@dataclass(frozen=True)
class Profesional:
    id: int
    activo: bool


HorarioValido = Callable[[int, datetime, datetime], bool]
Autorizar = Callable[[str, str], bool]


class Agendamiento:
    """Aplica las reglas de citas y persiste sus cambios de forma atómica.

    Los proveedores de datos maestros deben devolver None si el registro no
    existe. horario_valido recibe profesional_id, inicio y fin. autorizar recibe
    rol y operación; su implementación debe venir de la capa de servidor.
    """

    def __init__(
        self,
        ruta_bd: str | Path,
        obtener_mascota: Callable[[int], Mascota | None],
        obtener_servicio: Callable[[int], Servicio | None],
        obtener_profesional: Callable[[int], Profesional | None],
        horario_valido: HorarioValido,
        autorizar: Autorizar,
        reloj: Callable[[], datetime] | None = None,
    ) -> None:
        self.ruta_bd = str(ruta_bd)
        self.obtener_mascota = obtener_mascota
        self.obtener_servicio = obtener_servicio
        self.obtener_profesional = obtener_profesional
        self.horario_valido = horario_valido
        self.autorizar = autorizar
        self.reloj = reloj or (lambda: datetime.now(ZONA))
        self._crear_esquema()

    @contextmanager
    def _conexion(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.ruta_bd, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
        except BaseException:
            if db.in_transaction:
                db.rollback()
            raise
        else:
            if db.in_transaction:
                db.commit()
        finally:
            db.close()

    def _crear_esquema(self) -> None:
        with self._conexion() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS citas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mascota_id INTEGER NOT NULL,
                    propietario_id INTEGER NOT NULL,
                    servicio_id INTEGER NOT NULL,
                    profesional_id INTEGER NOT NULL,
                    inicio TEXT NOT NULL,
                    fin TEXT NOT NULL,
                    estado TEXT NOT NULL CHECK (estado IN
                      ('Programada','Confirmada','En atención','Cancelada',
                       'Inasistencia','Completada')),
                    creada_por TEXT NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS ix_citas_profesional_inicio ON citas(profesional_id, inicio)")
            db.execute("CREATE INDEX IF NOT EXISTS ix_citas_propietario_inicio ON citas(propietario_id, inicio)")

    @staticmethod
    def _fecha(valor: datetime) -> datetime:
        if not isinstance(valor, datetime) or valor.tzinfo is None:
            raise ErrorDeCita("La fecha y hora debe incluir zona horaria.")
        return valor.astimezone(ZONA)

    def _comprobar_permiso(self, rol: str, operacion: str) -> None:
        if not self.autorizar(rol, operacion):
            raise ErrorDeCita("No tienes permiso para realizar esta operación.")

    def reservar(
        self, *, rol: str, mascota_id: int, servicio_id: int,
        profesional_id: int, inicio: datetime,
    ) -> int:
        self._comprobar_permiso(rol, "reservar")
        if rol not in ROLES_RESERVA:
            raise ErrorDeCita("Este rol no puede reservar citas.")
        inicio = self._fecha(inicio)
        ahora = self._fecha(self.reloj())
        if inicio < ahora + timedelta(hours=2):
            raise ErrorDeCita("La cita debe reservarse con al menos dos horas de anticipación.")

        mascota = self.obtener_mascota(mascota_id)
        servicio = self.obtener_servicio(servicio_id)
        profesional = self.obtener_profesional(profesional_id)
        if mascota is None or not mascota.propietario_activo:
            raise ErrorDeCita("La mascota no existe o su propietario no está activo.")
        if servicio is None or not servicio.activo or servicio.duracion_minutos <= 0:
            raise ErrorDeCita("El servicio no está disponible.")
        if profesional is None or not profesional.activo:
            raise ErrorDeCita("El profesional no está disponible.")

        fin = inicio + timedelta(minutes=servicio.duracion_minutos)
        if not self.horario_valido(profesional_id, inicio, fin):
            raise ErrorDeCita("La cita queda fuera del horario de atención publicado.")

        # BEGIN IMMEDIATE serializa reservas que compiten por el mismo horario.
        # Todas las validaciones dependientes de citas ocurren dentro de la misma
        # transacción que inserta, evitando confirmar dos reservas simultáneas.
        with self._conexion() as db:
            db.execute("BEGIN IMMEDIATE")
            choque = db.execute("""
                SELECT 1 FROM citas
                WHERE profesional_id = ? AND estado NOT IN ('Cancelada','Inasistencia','Completada')
                  AND inicio < ? AND fin > ? LIMIT 1
            """, (profesional_id, fin.isoformat(), inicio.isoformat())).fetchone()
            if choque:
                raise ErrorDeCita("El profesional ya tiene una cita en ese horario.")

            cantidad = db.execute("""
                SELECT COUNT(*) FROM citas
                WHERE propietario_id = ? AND substr(inicio, 1, 10) = ?
                  AND estado NOT IN ('Cancelada','Inasistencia','Completada')
            """, (mascota.propietario_id, inicio.date().isoformat())).fetchone()[0]
            if cantidad >= 3:
                raise ErrorDeCita("El propietario ya tiene tres citas activas ese día.")

            cursor = db.execute("""
                INSERT INTO citas
                (mascota_id, propietario_id, servicio_id, profesional_id,
                 inicio, fin, estado, creada_por)
                VALUES (?, ?, ?, ?, ?, ?, 'Programada', ?)
            """, (mascota_id, mascota.propietario_id, servicio_id, profesional_id,
                  inicio.isoformat(), fin.isoformat(), rol))
            return int(cursor.lastrowid)

    def cancelar(self, *, rol: str, cita_id: int) -> None:
        self._comprobar_permiso(rol, "cancelar")
        ahora = self._fecha(self.reloj())
        with self._conexion() as db:
            db.execute("BEGIN IMMEDIATE")
            cita = db.execute("SELECT inicio, estado FROM citas WHERE id = ?", (cita_id,)).fetchone()
            if cita is None:
                raise ErrorDeCita("La cita no existe.")
            if cita["estado"] not in {"Programada", "Confirmada"}:
                raise ErrorDeCita("La cita no se puede cancelar en su estado actual.")
            inicio = self._fecha(datetime.fromisoformat(cita["inicio"]))
            if inicio - ahora < timedelta(hours=4):
                raise ErrorDeCita("La cancelación debe hacerse con al menos cuatro horas de anticipación.")
            db.execute("UPDATE citas SET estado = 'Cancelada' WHERE id = ?", (cita_id,))

    def reprogramar(self, *, rol: str, cita_id: int, nuevo_inicio: datetime) -> None:
        """Mueve una cita existente conservando su mascota, servicio y profesional."""
        self._comprobar_permiso(rol, "reprogramar")
        if rol not in ROLES_RESERVA:
            raise ErrorDeCita("Este rol no puede reprogramar citas.")
        nuevo_inicio = self._fecha(nuevo_inicio)
        ahora = self._fecha(self.reloj())
        if nuevo_inicio < ahora + timedelta(hours=2):
            raise ErrorDeCita("La nueva hora debe tener al menos dos horas de anticipación.")

        with self._conexion() as db:
            db.execute("BEGIN IMMEDIATE")
            cita = db.execute("SELECT * FROM citas WHERE id = ?", (cita_id,)).fetchone()
            if cita is None:
                raise ErrorDeCita("La cita no existe.")
            if cita["estado"] not in {"Programada", "Confirmada"}:
                raise ErrorDeCita("La cita no se puede reprogramar en su estado actual.")

            servicio = self.obtener_servicio(cita["servicio_id"])
            profesional = self.obtener_profesional(cita["profesional_id"])
            if servicio is None or not servicio.activo or profesional is None or not profesional.activo:
                raise ErrorDeCita("El servicio o el profesional ya no están disponibles.")
            nuevo_fin = nuevo_inicio + timedelta(minutes=servicio.duracion_minutos)
            if not self.horario_valido(cita["profesional_id"], nuevo_inicio, nuevo_fin):
                raise ErrorDeCita("La nueva hora queda fuera del horario publicado.")

            choque = db.execute("""
                SELECT 1 FROM citas
                WHERE id <> ? AND profesional_id = ?
                  AND estado NOT IN ('Cancelada','Inasistencia','Completada')
                  AND inicio < ? AND fin > ? LIMIT 1
            """, (cita_id, cita["profesional_id"], nuevo_fin.isoformat(),
                  nuevo_inicio.isoformat())).fetchone()
            if choque:
                raise ErrorDeCita("El profesional ya tiene una cita en ese horario.")

            cantidad = db.execute("""
                SELECT COUNT(*) FROM citas
                WHERE id <> ? AND propietario_id = ? AND substr(inicio, 1, 10) = ?
                  AND estado NOT IN ('Cancelada','Inasistencia','Completada')
            """, (cita_id, cita["propietario_id"], nuevo_inicio.date().isoformat())).fetchone()[0]
            if cantidad >= 3:
                raise ErrorDeCita("El propietario ya tiene tres citas activas ese día.")

            db.execute("UPDATE citas SET inicio = ?, fin = ? WHERE id = ?",
                       (nuevo_inicio.isoformat(), nuevo_fin.isoformat(), cita_id))

    def cambiar_estado(self, *, rol: str, cita_id: int, nuevo_estado: str) -> None:
        self._comprobar_permiso(rol, "cambiar_estado")
        with self._conexion() as db:
            db.execute("BEGIN IMMEDIATE")
            cita = db.execute("SELECT estado FROM citas WHERE id = ?", (cita_id,)).fetchone()
            if cita is None:
                raise ErrorDeCita("La cita no existe.")
            if nuevo_estado not in TRANSICIONES.get(cita["estado"], set()):
                raise ErrorDeCita("La transición de estado solicitada no está permitida.")
            db.execute("UPDATE citas SET estado = ? WHERE id = ?", (nuevo_estado, cita_id))

    def listar(self, *, rol: str, profesional_id: int | None = None,
               desde: datetime | None = None, hasta: datetime | None = None) -> list[dict]:
        self._comprobar_permiso(rol, "consultar")
        condiciones: list[str] = []
        parametros: list[object] = []
        if profesional_id is not None:
            condiciones.append("profesional_id = ?")
            parametros.append(profesional_id)
        if desde is not None:
            condiciones.append("inicio >= ?")
            parametros.append(self._fecha(desde).isoformat())
        if hasta is not None:
            condiciones.append("inicio < ?")
            parametros.append(self._fecha(hasta).isoformat())
        sql = "SELECT * FROM citas"
        if condiciones:
            sql += " WHERE " + " AND ".join(condiciones)
        sql += " ORDER BY inicio"
        with self._conexion() as db:
            return [dict(fila) for fila in db.execute(sql, parametros).fetchall()]
