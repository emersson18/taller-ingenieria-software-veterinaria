import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from agendamiento import Agendamiento, ErrorDeCita, Mascota, Profesional, Servicio


ZONA = ZoneInfo("America/Bogota")


class PruebasAgendamiento(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.ahora = datetime(2026, 10, 19, 8, 0, tzinfo=ZONA)
        self.mascotas = {1: Mascota(1, 10, True), 2: Mascota(2, 10, True),
                         3: Mascota(3, 10, True), 4: Mascota(4, 10, True),
                         5: Mascota(5, 20, False)}
        self.servicios = {1: Servicio(1, 60, True), 2: Servicio(2, 30, False)}
        self.profesionales = {1: Profesional(1, True), 2: Profesional(2, False)}
        self.app = Agendamiento(
            Path(self.temp.name) / "citas.sqlite",
            self.mascotas.get, self.servicios.get, self.profesionales.get,
            lambda profesional, inicio, fin: inicio.hour >= 8 and fin.hour <= 18,
            lambda rol, operacion: rol in {"administrador", "recepcion", "profesional"}
                and not (rol == "profesional" and operacion in {"reservar", "cancelar", "reprogramar"}),
            reloj=lambda: self.ahora,
        )

    def tearDown(self):
        self.temp.cleanup()

    def reservar(self, hora, mascota=1, profesional=1, servicio=1):
        return self.app.reservar(rol="recepcion", mascota_id=mascota,
            servicio_id=servicio, profesional_id=profesional,
            inicio=self.ahora.replace(hour=hora))

    def test_01_reserva_valida(self):
        cita = self.reservar(11)
        self.assertEqual(self.app.listar(rol="recepcion")[0]["id"], cita)

    def test_02_rechaza_menos_de_dos_horas(self):
        with self.assertRaises(ErrorDeCita): self.reservar(9)

    def test_03_rechaza_mascota_de_propietario_inactivo(self):
        with self.assertRaises(ErrorDeCita): self.reservar(11, mascota=5)

    def test_04_rechaza_servicio_inactivo(self):
        with self.assertRaises(ErrorDeCita): self.reservar(11, servicio=2)

    def test_05_rechaza_profesional_inactivo(self):
        with self.assertRaises(ErrorDeCita): self.reservar(11, profesional=2)

    def test_06_rechaza_horario_fuera_de_atencion(self):
        with self.assertRaises(ErrorDeCita): self.reservar(18)

    def test_07_rechaza_solapamiento(self):
        self.reservar(11)
        with self.assertRaises(ErrorDeCita): self.reservar(11)

    def test_08_permite_citas_contiguas(self):
        self.reservar(11)
        self.assertIsInstance(self.reservar(12), int)

    def test_09_rechaza_cuarta_cita_diaria(self):
        self.reservar(10, mascota=1, profesional=1)
        self.reservar(11, mascota=2, profesional=1)
        self.reservar(12, mascota=3, profesional=1)
        with self.assertRaises(ErrorDeCita): self.reservar(13, mascota=4, profesional=1)

    def test_10_cancelar_libera_el_horario(self):
        self.ahora = self.ahora.replace(hour=7)
        cita = self.reservar(11)
        self.app.cancelar(rol="recepcion", cita_id=cita)
        nueva = self.reservar(11, mascota=2)
        self.assertIsInstance(nueva, int)

    def test_11_cancelacion_con_menos_de_cuatro_horas_se_rechaza(self):
        cita = self.reservar(13)
        self.ahora = self.ahora.replace(hour=10)
        with self.assertRaises(ErrorDeCita): self.app.cancelar(rol="recepcion", cita_id=cita)

    def test_12_cancelacion_exactamente_con_cuatro_horas_se_acepta(self):
        cita = self.reservar(13)
        self.ahora = self.ahora.replace(hour=9)
        self.app.cancelar(rol="recepcion", cita_id=cita)
        self.assertEqual(self.app.listar(rol="recepcion")[0]["estado"], "Cancelada")

    def test_13_transiciones_validas_y_estado_final(self):
        cita = self.reservar(11)
        self.app.cambiar_estado(rol="recepcion", cita_id=cita, nuevo_estado="Confirmada")
        self.app.cambiar_estado(rol="recepcion", cita_id=cita, nuevo_estado="En atención")
        self.app.cambiar_estado(rol="recepcion", cita_id=cita, nuevo_estado="Completada")
        with self.assertRaises(ErrorDeCita):
            self.app.cambiar_estado(rol="recepcion", cita_id=cita, nuevo_estado="Confirmada")

    def test_14_transicion_no_permitida_se_rechaza(self):
        cita = self.reservar(11)
        with self.assertRaises(ErrorDeCita):
            self.app.cambiar_estado(rol="recepcion", cita_id=cita, nuevo_estado="Completada")

    def test_15_permiso_denegado_no_crea_cita(self):
        with self.assertRaises(ErrorDeCita):
            self.app.reservar(rol="profesional", mascota_id=1, servicio_id=1,
                profesional_id=1, inicio=self.ahora.replace(hour=11))
        self.assertEqual(self.app.listar(rol="recepcion"), [])

    def test_16_reprogramacion_valida(self):
        cita = self.reservar(11)
        self.app.reprogramar(rol="recepcion", cita_id=cita,
                             nuevo_inicio=self.ahora.replace(hour=13))
        self.assertEqual(self.app.listar(rol="recepcion")[0]["inicio"],
                         self.ahora.replace(hour=13).isoformat())

    def test_17_reprogramacion_conflictiva_no_cambia_cita(self):
        primera = self.reservar(11)
        self.reservar(13, mascota=2)
        with self.assertRaises(ErrorDeCita):
            self.app.reprogramar(rol="recepcion", cita_id=primera,
                                 nuevo_inicio=self.ahora.replace(hour=13))
        citas = self.app.listar(rol="recepcion")
        self.assertEqual(citas[0]["inicio"], self.ahora.replace(hour=11).isoformat())


if __name__ == "__main__":
    unittest.main(verbosity=2)
