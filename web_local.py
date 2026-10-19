"""Interfaz web local de demostración para el módulo de agendamiento.

Iniciar con: python web_local.py
Abrir: http://127.0.0.1:8000
Solo para demostración académica local; no implementa autenticación real.
"""

from datetime import datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from agendamiento import (
    Agendamiento,
    ErrorDeCita,
    Mascota,
    Profesional,
    Servicio,
    TRANSICIONES,
    ZONA,
)


CARPETA = Path(__file__).parent
BASE_DATOS = CARPETA / "citas_web.sqlite"

# Catálogos de ejemplo. En el sistema completo se consultarían a sus módulos.
MASCOTAS = {
    1: {"dato": Mascota(1, 100, True), "nombre": "Luna - perro de Ana Pérez"},
    2: {"dato": Mascota(2, 200, True), "nombre": "Milo - gato de Carlos Ruiz"},
}
SERVICIOS = {
    1: {"dato": Servicio(1, 60, True), "nombre": "Consulta general (60 min)"},
    2: {"dato": Servicio(2, 30, True), "nombre": "Control breve (30 min)"},
}
PROFESIONALES = {
    1: {"dato": Profesional(1, True), "nombre": "Dra. Valentina Gómez"},
    2: {"dato": Profesional(2, True), "nombre": "Dr. Mateo Torres"},
}


def horario_publicado(profesional_id: int, inicio: datetime, fin: datetime) -> bool:
    """Horario de muestra: todos los días, de 08:00 a 18:00."""
    return profesional_id in PROFESIONALES and inicio.hour >= 8 and fin.hour <= 18


def autorizar(rol: str, operacion: str) -> bool:
    """Autorización fija solo para la demostración local."""
    return rol == "recepcion"


APP = Agendamiento(
    ruta_bd=BASE_DATOS,
    obtener_mascota=lambda clave: MASCOTAS.get(clave, {}).get("dato"),
    obtener_servicio=lambda clave: SERVICIOS.get(clave, {}).get("dato"),
    obtener_profesional=lambda clave: PROFESIONALES.get(clave, {}).get("dato"),
    horario_valido=horario_publicado,
    autorizar=autorizar,
)


def pagina(mensaje: str = "", tipo: str = "ok") -> str:
    citas = APP.listar(rol="recepcion")
    opciones_mascotas = "".join(
        f'<option value="{clave}">{escape(item["nombre"])}</option>'
        for clave, item in MASCOTAS.items()
    )
    opciones_servicios = "".join(
        f'<option value="{clave}">{escape(item["nombre"])}</option>'
        for clave, item in SERVICIOS.items()
    )
    opciones_profesionales = "".join(
        f'<option value="{clave}">{escape(item["nombre"])}</option>'
        for clave, item in PROFESIONALES.items()
    )

    filas = []
    for cita in citas:
        mascota = MASCOTAS.get(cita["mascota_id"], {}).get("nombre", "Mascota")
        servicio = SERVICIOS.get(cita["servicio_id"], {}).get("nombre", "Servicio")
        profesional = PROFESIONALES.get(cita["profesional_id"], {}).get("nombre", "Profesional")
        inicio = datetime.fromisoformat(cita["inicio"]).strftime("%d/%m/%Y %H:%M")
        fin = datetime.fromisoformat(cita["fin"]).strftime("%H:%M")
        siguientes = TRANSICIONES[cita["estado"]]
        accion_estado = ""
        if siguientes:
            opciones = "".join(
                f'<option value="{escape(estado)}">{escape(estado)}</option>'
                for estado in sorted(siguientes)
            )
            accion_estado = f'''<form class="inline" method="post" action="/estado">
                <input type="hidden" name="cita_id" value="{cita['id']}">
                <select name="nuevo_estado" aria-label="Nuevo estado">{opciones}</select>
                <button class="secundario" type="submit">Cambiar estado</button>
            </form>'''
        filas.append(f'''<tr>
            <td>#{cita['id']}</td><td>{escape(mascota)}</td>
            <td>{escape(servicio)}</td><td>{escape(profesional)}</td>
            <td>{inicio}–{fin}</td><td><span class="estado">{escape(cita['estado'])}</span></td>
            <td>{accion_estado}</td>
        </tr>''')

    tabla = "".join(filas) or '<tr><td colspan="7" class="vacio">Aún no hay citas. Registra la primera usando el formulario.</td></tr>'
    aviso = f'<div class="aviso {escape(tipo)}">{escape(mensaje)}</div>' if mensaje else ""
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agendamiento veterinario</title>
<style>
 :root {{ color-scheme: light; font-family: Segoe UI, Arial, sans-serif; color: #18312d; background: #f3f7f5; }}
 body {{ margin: 0; }} header {{ background: #176b58; color: white; padding: 26px max(calc((100% - 1080px)/2), 24px); }}
 header h1 {{ margin: 0 0 6px; font-size: 25px; }} header p {{ margin: 0; opacity: .9; }}
 main {{ max-width: 1080px; margin: 26px auto; padding: 0 18px 36px; }}
 .aviso {{ padding: 12px 15px; border-radius: 8px; margin-bottom: 18px; }}
 .ok {{ background: #e3f5ec; color: #155b39; }} .error {{ background: #fde9e7; color: #8c2820; }}
 section {{ background: white; border: 1px solid #dbe7e2; border-radius: 12px; padding: 22px; margin-bottom: 22px; box-shadow: 0 3px 12px #173c3010; }}
 h2 {{ margin: 0 0 17px; font-size: 20px; }} .formulario {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 15px; }}
 label {{ display: grid; gap: 7px; font-weight: 600; font-size: 14px; }} select, input {{ width: 100%; box-sizing: border-box; padding: 11px; border: 1px solid #b8cbc3; border-radius: 7px; background: white; font: inherit; }}
 button {{ background: #176b58; color: white; border: 0; padding: 11px 16px; border-radius: 7px; font: inherit; font-weight: 600; cursor: pointer; }}
 button:hover {{ background: #105441; }} .formulario button {{ grid-column: 1 / -1; justify-self: start; }}
 .nota {{ font-size: 13px; color: #576c65; margin: 14px 0 0; }} .tabla-wrap {{ overflow-x: auto; }}
 table {{ border-collapse: collapse; width: 100%; min-width: 800px; }} th, td {{ text-align: left; padding: 11px 9px; border-bottom: 1px solid #e3ece8; vertical-align: middle; }} th {{ color: #456158; font-size: 13px; }}
 .estado {{ background: #e8f1ed; border-radius: 20px; padding: 5px 9px; white-space: nowrap; }}
 .inline {{ display: flex; gap: 6px; align-items: center; }} .inline select {{ min-width: 130px; padding: 8px; }} .secundario {{ padding: 8px 10px; font-size: 13px; white-space: nowrap; }}
 .vacio {{ color: #647770; text-align: center; padding: 24px; }} footer {{ font-size: 12px; color: #687d75; margin-top: 20px; }}
 @media (max-width: 650px) {{ .formulario {{ grid-template-columns: 1fr; }} header {{ padding: 22px; }} main {{ margin-top: 16px; }} section {{ padding: 17px; }} }}
</style></head><body>
<header><h1>Clínica veterinaria · Citas</h1><p>Demostración local del módulo de agendamiento</p></header>
<main>{aviso}
<section><h2>Registrar una cita</h2>
<form class="formulario" method="post" action="/reservar">
 <label>Mascota<select name="mascota_id" required>{opciones_mascotas}</select></label>
 <label>Servicio<select name="servicio_id" required>{opciones_servicios}</select></label>
 <label>Profesional<select name="profesional_id" required>{opciones_profesionales}</select></label>
 <label>Fecha y hora de inicio<input type="datetime-local" name="inicio" required></label>
 <button type="submit">Registrar cita</button>
</form>
<p class="nota">Reglas activas: mínimo 2 horas de anticipación, horario de 08:00 a 18:00, sin cruces por profesional y máximo 3 citas activas diarias por propietario. Zona horaria UTC−05:00.</p>
</section>
<section><h2>Citas registradas</h2><div class="tabla-wrap"><table>
<thead><tr><th>ID</th><th>Mascota / propietario</th><th>Servicio</th><th>Profesional</th><th>Fecha y hora</th><th>Estado</th><th>Acciones</th></tr></thead>
<tbody>{tabla}</tbody></table></div>
<footer>Demostración educativa local. Usa datos de ejemplo; no tiene inicio de sesión real ni debe publicarse como servicio de producción.</footer>
</section></main></body></html>'''


class ManejadorWeb(BaseHTTPRequestHandler):
    def responder_html(self, contenido: str, estado: int = 200) -> None:
        datos = contenido.encode("utf-8")
        self.send_response(estado)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self) -> None:
        self.responder_html(pagina())

    def do_POST(self) -> None:
        longitud = int(self.headers.get("Content-Length", "0"))
        if longitud > 10000:
            self.responder_html(pagina("La solicitud es demasiado grande.", "error"), 413)
            return
        formulario = parse_qs(self.rfile.read(longitud).decode("utf-8"), strict_parsing=False)
        valor = lambda clave: formulario.get(clave, [""])[0]
        try:
            if self.path == "/reservar":
                hora = datetime.fromisoformat(valor("inicio"))
                if hora.tzinfo is None:
                    hora = hora.replace(tzinfo=ZONA)
                cita_id = APP.reservar(
                    rol="recepcion",
                    mascota_id=int(valor("mascota_id")),
                    servicio_id=int(valor("servicio_id")),
                    profesional_id=int(valor("profesional_id")),
                    inicio=hora,
                )
                self.responder_html(pagina(f"Cita #{cita_id} registrada correctamente."))
                return
            if self.path == "/estado":
                APP.cambiar_estado(
                    rol="recepcion",
                    cita_id=int(valor("cita_id")),
                    nuevo_estado=valor("nuevo_estado"),
                )
                self.responder_html(pagina("Estado de la cita actualizado correctamente."))
                return
            self.responder_html(pagina("La operación solicitada no existe.", "error"), 404)
        except (ErrorDeCita, ValueError, TypeError, OverflowError):
            self.responder_html(pagina("No se pudo registrar o actualizar la cita. Revisa los datos y las reglas de horario.", "error"), 400)

    def log_message(self, formato: str, *args: object) -> None:
        # Evita imprimir datos del formulario en la consola del servidor.
        super().log_message(formato, *args)


if __name__ == "__main__":
    direccion = ("127.0.0.1", 8000)
    print("Servidor de demostración iniciado en http://127.0.0.1:8000")
    print(f"Las citas se guardan en: {BASE_DATOS}")
    print("Para detenerlo, vuelve a esta ventana y presiona Ctrl+C.")
    with ThreadingHTTPServer(direccion, ManejadorWeb) as servidor:
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")
