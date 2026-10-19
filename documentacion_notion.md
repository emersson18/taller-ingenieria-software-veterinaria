# Taller de Ingeniería de Software I – Clínica Veterinaria

## 5. Casos de prueba

### Entorno de ejecución

- Fecha de ejecución: 19 de octubre de 2026.
- Herramienta: `unittest` de la biblioteca estándar de Python.
- Comando: `python -m unittest -v` (ejecutado con Python del runtime de Codex).
- Resultado: 17 pruebas ejecutadas; 17 aprobadas.
- Entorno de verificación adicional: Python 3.15 de Windows.
- Evidencia de consola: `evidencia_pruebas.txt`.
- Datos: SQLite temporal por prueba; hora fija simulada para que las reglas de tiempo sean reproducibles; datos maestros simulados mediante funciones proveedoras.

### Casos y resultados

| ID | Requisito/regla y objetivo | Precondiciones, datos y pasos resumidos | Esperado | Obtenido | Estado/evidencia |
|---|---|---|---|---|---|
| CP-01 | RN-03, RN-04, RF-08: reservar una cita válida | Datos activos; reservar servicio de 60 min para mascota 1, profesional 1, a las 11:00 | Se crea una cita Programada con fin calculado a las 12:00 | Creación y consulta de la cita correctas | Aprobado; `test_01_reserva_valida` |
| CP-02 | RN-04: rechazar menos de 2 h de anticipación | Hora actual 08:00; intentar reservar a las 09:00 | Rechazar sin crear cita | Se genera error de regla | Aprobado; `test_02_rechaza_menos_de_dos_horas` |
| CP-03 | RN-02: mascota de propietario inactivo | Mascota asociada a propietario inactivo; intentar reservar a las 11:00 | Rechazar | Se genera error de regla | Aprobado; `test_03_rechaza_mascota_de_propietario_inactivo` |
| CP-04 | RN-03: servicio activo | Intentar reservar un servicio inactivo | Rechazar | Se genera error de regla | Aprobado; `test_04_rechaza_servicio_inactivo` |
| CP-05 | RN-03: profesional activo | Intentar reservar con profesional inactivo | Rechazar | Se genera error de regla | Aprobado; `test_05_rechaza_profesional_inactivo` |
| CP-06 | RN-03: horario publicado | Servicio de 60 min; reservar a las 18:00 cuando el horario termina a las 18:00 | Rechazar porque la cita termina a las 19:00 | Se genera error de horario | Aprobado; `test_06_rechaza_horario_fuera_de_atencion` |
| CP-07 | RN-05: evitar solapamiento | Reservar 11:00–12:00; volver a reservar el mismo intervalo y profesional | Rechazar segunda reserva | Se genera error de conflicto | Aprobado; `test_07_rechaza_solapamiento` |
| CP-08 | RN-05: intervalos contiguos | Reservar 11:00–12:00 y luego 12:00–13:00 con el mismo profesional | Aceptar ambas | Segunda cita aceptada | Aprobado; `test_08_permite_citas_contiguas` |
| CP-09 | RN-06: máximo de 3 citas activas | Mismo propietario con citas a las 10:00, 11:00 y 12:00; intentar cuarta a las 13:00 | Rechazar la cuarta | Se genera error de límite | Aprobado; `test_09_rechaza_cuarta_cita_diaria` |
| CP-10 | RN-07: cancelada libera horario | Reservar a las 11:00 con 4 h de anticipación; cancelar; reservar otra mascota al mismo horario | Cancelar y permitir nueva reserva | Horario liberado y reutilizado | Aprobado; `test_10_cancelar_libera_el_horario` |
| CP-11 | RN-07: cancelación tardía | Cita a las 13:00; intentar cancelar a las 10:00 | Rechazar por menos de 4 h | Se genera error de anticipación | Aprobado; `test_11_cancelacion_con_menos_de_cuatro_horas_se_rechaza` |
| CP-12 | RN-07: límite exacto de cancelación | Cita a las 13:00; cancelar a las 09:00 | Aceptar exactamente a 4 h | Cita queda Cancelada | Aprobado; `test_12_cancelacion_exactamente_con_cuatro_horas_se_acepta` |
| CP-13 | RN-08: transiciones válidas y estado final | Programada → Confirmada → En atención → Completada; intentar volver a Confirmada | Aceptar flujo válido y rechazar cambio desde estado final | Flujo aceptado; cambio final rechazado | Aprobado; `test_13_transiciones_validas_y_estado_final` |
| CP-14 | RN-08: transición inválida | Intentar Programada → Completada | Rechazar | Se genera error de transición | Aprobado; `test_14_transicion_no_permitida_se_rechaza` |
| CP-15 | RN-11/RF-14: permiso | Rol profesional intenta reservar; después consultar citas con recepción | Rechazar y no alterar citas | Error de permiso; lista permanece vacía | Aprobado; `test_15_permiso_denegado_no_crea_cita` |
| CP-16 | RF-10: reprogramación válida | Crear cita a las 11:00 y moverla a las 13:00 | Actualizar inicio y fin | Nuevo inicio y fin calculado guardados | Aprobado; `test_16_reprogramacion_valida` |
| CP-17 | RN-12: reprogramación conflictiva sin cambios parciales | Cita A a las 11:00 y cita B a las 13:00; mover A a las 13:00 | Rechazar y conservar A a las 11:00 | Conflicto rechazado; cita A sin cambios | Aprobado; `test_17_reprogramacion_conflictiva_no_cambia_cita` |

### Defecto encontrado y corrección

En la primera ejecución, varias pruebas mostraron que las citas insertadas no estaban disponibles al abrir una conexión nueva. La causa fue que el nuevo administrador de conexiones cerraba SQLite sin confirmar la transacción abierta. Se ajustó el administrador para confirmar cuando la operación termina correctamente y revertir cuando ocurre una excepción. En la reejecución final, las 17 pruebas aprobaron.

La primera ejecución también reveló una limitación de permisos del directorio temporal predeterminado del entorno Windows. El fixture se cambió para crear su SQLite temporal junto a las pruebas y limpiarlo al terminar. Es un ajuste del entorno de pruebas, no un defecto funcional del módulo.

Al ejecutar las pruebas con Python 3.15 instalado en Windows apareció otro problema de entorno: no estaba instalada la base `tzdata`, requerida por `ZoneInfo("America/Bogota")` en algunas instalaciones de Windows. Se sustituyó por el offset fijo `UTC-05:00` de Colombia, que no aplica horario de verano, tanto en el módulo como en las pruebas. Las 17 pruebas se volvieron a ejecutar con ese Python y aprobaron.

### Demostración en navegador

Se agregó `web_local.py`, una interfaz web local en español para registrar citas, ver el listado y aplicar transiciones de estado permitidas. Se ejecuta con `python web_local.py` y se abre en `http://127.0.0.1:8000`. Usa catálogos simulados y la base persistente `citas_web.sqlite`; no incluye autenticación real ni integración con módulos maestros. La interfaz no se ha verificado en los tres navegadores ni con pruebas de carga.

### Límites de la evidencia

Las pruebas verifican reglas funcionales con datos maestros simulados. No prueban todavía una interfaz web, integración real de autenticación, 10 usuarios concurrentes, rendimiento con el volumen de la guía ni una carrera paralela real entre dos procesos. Para afirmar esos requisitos como verificados se requiere integrar los módulos y añadir pruebas de carga y concurrencia.

## 6. Solicitudes de cambio

| Solicitud | Clasificación | Justificación | Requisitos/componentes afectados | Cambio propuesto | Regresión propuesta |
|---|---|---|---|---|---|
| SC-01. Doble reserva | Correctivo | Corrige un comportamiento defectuoso que permite dos confirmaciones incompatibles. | RN-05, RN-12; Agendamiento, persistencia y disponibilidad | Mantener la validación del solapamiento y proteger lectura e inserción con una transacción que serialice reservas concurrentes. | Lanzar dos solicitudes paralelas para mismo profesional y franja; debe existir una sola cita. Comprobar que una cita contigua sí se acepta y una cita cancelada no bloquea el horario. |
| SC-02. Recordatorios | Perfectivo | Añade una capacidad nueva de consulta y seguimiento que mejora el servicio existente. | RF-09 y nuevos requisitos de recordatorio; Agendamiento, notificaciones y datos de propietarios | Consultar citas próximas por rango; registrar estado, fecha y resultado del envío sin exponer datos de contacto en logs. | Consultar rangos vacíos y con citas; evitar duplicar envíos; verificar que cancelar una cita la excluya del envío pendiente. |
| SC-03. Historial preventivo | Perfectivo | Amplía las funciones del sistema al añadir un nuevo registro clínico por mascota. | RF-04, RN-10 y nuevo requisito de historial; Mascotas, Atención e historial, Acceso y usuarios | Crear registros de controles/vacunación asociados a mascota y autor; permitir consulta solo a profesionales autorizados; preservar historial. | Guardar y consultar registros; rechazar rol no autorizado; validar mascota existente; verificar que desactivar una mascota no borre el historial. |

## 7. Gestión con Git

### Estructura propuesta

```text
gestion_citas/
├── agendamiento.py
├── test_agendamiento.py
├── evidencia_pruebas.txt
├── documentacion_notion.md
├── README.md
└── .gitignore
```

### Comandos recomendados

```bash
git init -b main
git add README.md .gitignore
git commit -m "docs: crear estructura inicial del proyecto"

git switch -c feat/agendamiento
git add agendamiento.py
git commit -m "feat: implementar reglas de agendamiento"

git switch -c test/casos-agendamiento
git add test_agendamiento.py evidencia_pruebas.txt
git commit -m "test: cubrir reglas principales de citas"
git switch feat/agendamiento
git merge --no-ff test/casos-agendamiento

git switch -c docs/informe-tecnico
git add documentacion_notion.md
git commit -m "docs: documentar pruebas y cambios"
git switch main
git merge --no-ff feat/agendamiento
git merge --no-ff docs/informe-tecnico
git log --oneline --graph --decorate
```

El repositorio local no tiene remoto configurado. Después de crear un repositorio vacío en GitHub, GitLab u otro servicio autorizado por el curso, vincularlo y publicar `main`:

```bash
git remote add origin <URL_DEL_REPOSITORIO>
git push -u origin main
```

Enlace para completar: **[PEGAR AQUÍ EL ENLACE DEL REPOSITORIO]**.

## 8. Uso de inteligencia artificial

- Herramienta: ChatGPT/Codex, como asistente de análisis, generación y revisión de código.
- Prompt representativo: “Implementa un módulo de agendamiento en Python que valide anticipación mínima de dos horas, horarios activos, solapamientos por profesional, máximo de tres citas activas por propietario, cancelación con cuatro horas, transiciones permitidas y persistencia SQLite. Mantén las dependencias externas inyectadas y explica las decisiones.”
- Revisión solicitada: “Propón casos de prueba para reglas normales, límites, errores, permisos y reprogramación; informa qué datos de prueba necesita cada caso.”
- Ajustes realizados: se agregó la reprogramación que faltaba en el código inicial; se configuró manejo de transacciones con confirmación y reversión; se añadió almacenamiento persistente SQLite; se separaron proveedores de datos maestros y autorización mediante funciones inyectadas; se preparó un reloj fijo y base temporal para pruebas reproducibles.
- Responsabilidad del equipo: revisar reglas y código, entender los límites y comprobar los resultados. La autorización real, los datos maestros, la interfaz y pruebas de carga aún deben integrarse antes de presentar el sistema completo como terminado.

## 9. Informe técnico final

### Portada

**Sistema de gestión de citas para una clínica veterinaria**  
Taller de Ingeniería de Software I  
Integrantes: [COMPLETAR]  
Docente: [COMPLETAR]  
Institución: [COMPLETAR]  
Fecha: [COMPLETAR]

### Introducción y solución

El proyecto propone un sistema web para gestionar propietarios, mascotas, servicios, profesionales, horarios y citas veterinarias. Se documentó una descomposición modular y se implementó únicamente el núcleo de Agendamiento de citas, junto con una interfaz web de demostración local. El módulo aplica reglas de reserva, cancelación, reprogramación y transición de estados, y conserva las citas en SQLite.

### Contenido que debe integrarse al informe

1. Análisis de requisitos, validaciones y supuestos.
2. Propuesta modular, interfaces, dependencias y justificación de cohesión/acoplamiento.
3. Selección del módulo Agendamiento y delimitación de alcance.
4. Explicación de implementación y decisiones técnicas, incluida la demostración web local.
5. Tabla de 17 casos, resultados, evidencia y defecto corregido.
6. Análisis de SC-01, SC-02 y SC-03 y sus regresiones propuestas.
7. Uso de Git y herramienta de IA, prompts y ajustes.
8. Conclusiones, anexos y enlace al repositorio.

### Conclusiones

La separación modular permite concentrar las reglas de citas sin hacer que Agendamiento administre los datos maestros. Las pruebas automatizadas aprobaron los casos ejecutados y detectaron un problema de confirmación de transacciones que fue corregido. La interfaz web local permite registrar y consultar citas de demostración; para completar la solución se deben integrar autorización real, proveedores de datos maestros, pruebas de concurrencia paralela y pruebas de rendimiento.

### Anexos y entrega

- Código: `agendamiento.py`.
- Interfaz local: `web_local.py`.
- Pruebas: `test_agendamiento.py`.
- Evidencia de ejecución: `evidencia_pruebas.txt`.
- Repositorio: [PEGAR ENLACE].
- Exportar este contenido desde Notion o trasladarlo al formato que indique el docente; verificar que tablas, evidencias y enlace estén legibles antes de entregar.
