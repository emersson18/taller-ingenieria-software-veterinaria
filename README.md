# Módulo de agendamiento veterinario

Núcleo de reglas de negocio para reservar, cancelar, reprogramar, consultar y cambiar estados de citas. Implementado con Python y SQLite de la biblioteca estándar.

## Requisitos

- Python 3.10 o posterior.
- No requiere instalar paquetes externos.

## Estructura

- `agendamiento.py`: módulo funcional.
- `test_agendamiento.py`: 17 pruebas automatizadas.
- `demo_local.py`: demostración interactiva por consola con SQLite persistente.
- `web_local.py`: formulario web en español para registrar citas y cambiar su estado.
- `evidencia_pruebas.txt`: salida de la última ejecución.
- `documentacion_notion.md`: secciones 5 a 9 listas para copiar a Notion.

## Ejecutar pruebas

Desde esta carpeta:

```bash
python -m unittest -v
```

## Ver una cita registrarse

Desde esta carpeta, ejecuta:

```bash
python demo_local.py
```

El programa registra una cita de demostración, muestra su identificador y enumera las citas guardadas. La base persistente se crea como `demostracion.sqlite` en esta carpeta y está excluida de Git. Cada ejecución agrega otra cita en un día libre.

## Abrir el entorno web local

Desde esta carpeta, ejecuta:

```bash
python web_local.py
```

Abre `http://127.0.0.1:8000` en el navegador. El formulario usa catálogos de ejemplo y guarda en `citas_web.sqlite`, excluido de Git. Detén el servidor con `Ctrl+C` en la terminal. Es una demostración educativa local: no incluye autenticación real ni debe exponerse a internet.

## Integración

Al crear `Agendamiento`, la aplicación debe proporcionar funciones para consultar mascotas, servicios y profesionales, validar horarios y autorizar operaciones. Los datos maestros y la autenticación no están incluidos en este módulo.

En producción, pasa una ruta de base de datos en una carpeta persistente y protegida. No se deben registrar credenciales ni detalles internos en mensajes visibles al usuario.

## Respaldo

Detén las escrituras de la aplicación y copia el archivo SQLite configurado a un almacenamiento de respaldo seguro. La ruta de base de datos no está fijada en el código.
