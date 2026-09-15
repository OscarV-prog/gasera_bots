# Plan de Implementación — Epics, Features y Stories
## Ecosistema Digital Gasera (Gas a tu Puerta) — Grupo Petroil

**Cliente:** Grupo Petroil — División Gas (Mazatlán, Sinaloa)  
**Versión:** 3.5.0 Enterprise — Sincronizada con la Arquitectura Real Implementada (LangGraph AI Sales Agent, Omnicanalidad WhatsApp/Telegram/Call Center, PostgreSQL Corporativo Petroil, Torre de Control Web en Dominio Propio & Reportes Excel)  
**Estado:** Documento Maestro de Planificación Ágil Aprobado y Vigente  
**Fuentes Oficiales de Verdad:** `product-context.md` v3.5, `prd.md` v3.5, `architecture.md` v3.5, `user-flows.md` v3.5 y Código Fuente del Repositorio  
**Fecha:** Septiembre 2026  

---

## Control de Versiones de Planificación

| Versión | Fecha | Descripción | Estado |
| :--- | :--- | :--- | :--- |
| **1.0.0** | 11/08/2026 | Propuesta inicial teórica de 12 Epics para microservicios y app móvil. | Superado |
| **2.0.0** | 18/08/2026 | Sincronización con el roadmap multicanal preliminar. | Superado |
| **3.0.0** | 02/09/2026 | Reestructuración ágil con LangGraph y bots de Telegram. | Superado |
| **3.5.0** | 09/09/2026 | **Alineación Integral con el Ecosistema Completo de Negocio:**<br>• Inclusión de omnicanalidad (WhatsApp, Telegram y Llamadas Telefónicas / Mostrador).<br>• Despliegue de Torre de Control en Dominio Propio institucional (no localhost).<br>• Persistencia en PostgreSQL corporativo de Petroil.<br>• Historias de Mesa de Agenda Programada (T-30 min), Horarios de Atención, Control de Pipas vs Camionetas y CSAT. | **Aprobado / Vigente** |

---

# ÍNDICE GENERAL DE ÉPICAS

| ID | Nombre de la Épica | Módulos y Código Involucrado | Estado |
| :--- | :--- | :--- | :---: |
| **EPIC-01** | Agente Conversacional de Ventas con IA (WhatsApp & Telegram) y Horarios | `telegram_bot.py`, `src/channels/*`, `src/graphs/`, `src/nodes/`, `src/tools/` | ✅ Implementado |
| **EPIC-02** | Módulo de Venta Directa, Call Center y Mostrador (Llamadas Telefónicas) | `src/admin/router.py`, `src/admin/static/*`, `src/services/dispatch.py` | ✅ Implementado |
| **EPIC-03** | Bot de Choferes, Turnos con Odómetro/Foto y Despacho en Campo | `driver_bot.py`, `src/models/driver.py`, `src/services/notifications.py` | ✅ Implementado |
| **EPIC-04** | Motor de Despacho Haversine y Mesa de Agenda Programada (T-30 min) | `src/services/dispatch.py`, `src/services/geocoding.py` | ✅ Implementado |
| **EPIC-05** | Torre de Control Web en Dominio Propio, Flota e Incidencias | `src/app.py`, `src/admin/*`, `src/database/schema.py` | ✅ Implementado |
| **EPIC-06** | Módulo de Reportes Excel y Persistencia PostgreSQL Corporativa | `src/services/reports.py`, `src/repositories/*`, PostgreSQL Petroil | ✅ Implementado |

---

# EPIC-01: Agente Conversacional de Ventas con IA (WhatsApp & Telegram) y Horarios

**Objetivo:** Implementar la atención comercial automatizada de Gas LP en WhatsApp y Telegram mediante un agente inteligente con LangGraph y DeepSeek v3, combinando procesamiento de lenguaje natural con menús interactivos, validación de horarios de atención y confirmación obligatoria.

---

## STORY-01.1: Menú Inicial Híbrido y Selección de Tipo de Servicio
* **ID:** `STORY-01.1`
* **Descripción:** Como cliente interesado en comprar gas, quiero opciones claras de tipo de servicio para elegir rápidamente entre cilindros y tanque estacionario.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: El cliente inicia conversación con el bot
    Given que el cliente abre el chat en WhatsApp o Telegram y saluda
    When el bot procesa el mensaje
    Then responde con un saludo de bienvenida institucional de Grupo Petroil
    And despliega exactamente dos botones: "[ 🛢️ Cilindros ]" y "[ 🔥 Tanque Estacionario ]"
    And no muestra opciones ambiguas
  ```

---

## STORY-01.2: Despliegue de Catálogo Dinámico con Precios de PostgreSQL
* **ID:** `STORY-01.2`
* **Descripción:** Como cliente, quiero ver los productos reales y precios oficiales vigentes en Mazatlán para tomar una decisión informada sin alucinaciones de precios.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Selección de servicio de cilindros
    Given que el cliente presiona "[ 🛢️ Cilindros ]"
    When el bot ejecuta la consulta de productos activos para el tenant "petroil"
    Then obtiene las presentaciones (10 kg, 20 kg, 30 kg, 45 kg) con sus precios actuales desde la tabla 'PRODUCTS' en PostgreSQL
    And genera botones dinámicos con precio en MXN (ej. "[ 🟢 Cilindro de 30 kg — $670 MXN ]")
  ```

---

## STORY-01.3: Validación de Horarios de Atención y Gestión Fuera de Horario
* **ID:** `STORY-01.3`
* **Descripción:** Como cliente que escribe fuera del horario de servicio comercial, quiero que el bot me informe amablemente el horario y me permita agendar mi pedido para el siguiente turno disponible.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Pedido recibido fuera del horario de atención comercial
    Given que el cliente solicita gas fuera de la ventana de atención configurada
    When el sistema valida el horario actual
    Then el bot informa cordialmente los horarios de atención de Grupo Petroil
    And ofrece agendar el pedido ("scheduled") para ser despachado a primera hora del siguiente turno hábil
  ```

---

## STORY-01.4: Identificación Telefónica por 10 Dígitos y Libreta Multi-Dirección
* **ID:** `STORY-01.4`
* **Descripción:** Como cliente recurrente, quiero que el bot reconozca mis domicilios guardados para no tener que escribirlos en cada pedido.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Cliente frecuente con direcciones previas
    Given que el cliente proporciona su teléfono de 10 dígitos "6699123501"
    When el agente ejecuta la tool "customer_info"
    Then el sistema recupera al cliente de 'CUSTOMERS' y sus domicilios de 'CUSTOMER_ADDRESSES'
    And despliega botones inline con sus direcciones guardadas más la opción "[ ➕ Ingresar Nueva Dirección ]"
  ```

---

## STORY-01.5: Resumen Financiero y Confirmación Obligatoria Previa
* **ID:** `STORY-01.5`
* **Descripción:** Como cliente, quiero revisar el resumen completo de mi compra antes de que se genere para asegurar que no haya errores de producto o dirección.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Confirmación de orden previa a persistencia
    Given que el cliente ha seleccionado producto, cantidad, dirección, horario y método de pago
    When el bot genera la tarjeta de resumen financiero
    Then muestra los botones "[ ✅ Confirmar pedido ]", "[ ✏️ Modificar pedido ]" y "[ ❌ Cancelar ]"
    And la orden NO existe en la base de datos hasta que el cliente pulsa "[ ✅ Confirmar pedido ]"
    And al pulsar confirmar, se ejecuta "create_order", generando el folio (#ID) y disparando el despacho logístico
  ```

---

## STORY-01.6: Encuesta de Satisfacción CSAT
* **ID:** `STORY-01.6`
* **Descripción:** Como cliente que recibió su gas, quiero calificar el servicio del chofer de 1 a 5 estrellas.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Envío de encuesta CSAT
    Given que el chofer marca el pedido como "delivered"
    When el sistema detecta la entrega completada
    Then envía un mensaje al cliente solicitando calificar el servicio con estrellas ("[ ⭐ ]" a "[ ⭐⭐⭐⭐⭐ ]")
    And almacena la calificación en 'ORDER_RATINGS' actualizando el promedio del chofer
  ```

---

# EPIC-02: Módulo de Venta Directa, Call Center y Mostrador (Llamadas Telefónicas)

**Objetivo:** Permitir al personal de oficina capturar pedidos generados por llamadas telefónicas o en mostrador directamente desde la Torre de Control Web, integrándolos de inmediato al motor de despacho.

---

## STORY-02.1: Captura Rápida de Pedidos Telefónicos en Torre de Control
* **ID:** `STORY-02.1`
* **Descripción:** Como operadora de call center, quiero un formulario rápido de captura (`➕ Levantar Pedido`) para registrar llamadas telefónicas en menos de 30 segundos.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Registro de pedido por llamada telefónica
    Given que la operadora atiende una llamada y abre el modal "[ ➕ Levantar Pedido ]"
    When ingresa el teléfono, nombre, dirección y selecciona los productos
    Then el modal calcula automáticamente los subtotales y el importe total
    And permite seleccionar entrega inmediata o agendada (con fecha/hora de deadline)
    And al guardar, inserta la orden en 'ORDERS' y detona el despacho logístico
  ```

---

# EPIC-03: Bot de Choferes, Turnos con Odómetro/Foto y Despacho en Campo

**Objetivo:** Desarrollar un bot operativo en Telegram (`driver_bot.py`) para los choferes en campo que permita la gestión de turnos con fotos de tanque y odómetro, recepción de viajes con Waze y Google Maps, y reporte de entregas e incidencias.

---

## STORY-03.1: Control de Asistencia con Lectura de Tanque, Odómetro y Fotografía
* **ID:** `STORY-03.1`
* **Descripción:** Como chofer, quiero iniciar y cerrar mi turno registrando mi kilometraje y porcentaje de gas con foto de evidencia para auditoría de combustible.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Inicio de jornada laboral con foto
    Given que el chofer presiona "[ 🟢 Iniciar Turno ]"
    When ingresa su odómetro (km), porcentaje de gas y envía la fotografía del medidor
    Then el bot guarda la imagen en 'uploads/tank_readings/' e inserta el registro en 'TANK_READINGS'
    And actualiza 'DRIVER_SHIFTS' y establece 'is_available = 1' en 'DRIVERS'
    And queda habilitado para recibir viajes del motor de despacho
  ```

---

## STORY-03.2: Tarjeta de Viaje con Navegación en Waze y Google Maps
* **ID:** `STORY-03.2`
* **Descripción:** Como chofer, quiero recibir alertas con enlaces directos a Waze y Google Maps para abrir la ruta en modo navegación con un solo toque.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Recepción de viaje asignado
    Given que se asigna un pedido al chofer activo
    When el bot envía la notificación sonora y la tarjeta de viaje
    Then incluye folio, cliente, teléfono, dirección, referencias, productos y monto a cobrar
    And presenta los botones "[ 🗺️ Google Maps ]" y "[ 🚗 Waze ]" con las coordenadas de entrega
    And al presionar cualquier botón, el dispositivo abre la app correspondiente en modo navegación giro a giro
  ```

---

## STORY-03.3: Aceptación y Rechazo de Viajes con Captura de Motivo
* **ID:** `STORY-03.3`
* **Descripción:** Como chofer, quiero reportar si no puedo atender un viaje indicando el motivo exacto para que la Torre de Control lo reasigne de inmediato.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Rechazo estructurado de viaje
    Given que el chofer recibe una tarjeta de viaje y presiona "[ ❌ Rechazar ]"
    When selecciona o escribe el motivo (ej. "Falla mecánica", "Desabasto", "Tráfico pesado")
    Then el pedido cambia a estatus "rejected_by_driver"
    And se inserta un registro en 'ORDER_REJECTIONS' con el order_id, driver_id y motivo
    And se genera una alerta visual en la Torre de Control Web para reasignación en 1 clic
  ```

---

# EPIC-04: Motor de Despacho Haversine y Mesa de Agenda Programada (T-30 min)

**Objetivo:** Desarrollar los algoritmos de geocodificación satelital, cálculo de proximidad por Haversine y el motor de activación automática para pedidos agendados.

---

## STORY-04.1: Despacho Automático por Cercanía Haversine
* **ID:** `STORY-04.1`
* **Descripción:** Como despachador, quiero que el sistema asigne automáticamente el pedido al chofer disponible más cercano compatible con el tipo de vehículo.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Despacho automático por Haversine
    Given un pedido confirmado con coordenadas de entrega
    When se ejecuta "dispatch_order"
    Then consulta todos los choferes con "is_available = 1" compatibles con el tipo de unidad
    And calcula la distancia Haversine en kilómetros entre cada chofer y el cliente
    And asigna la orden al chofer con menor distancia, pasando el estatus a "assigned"
    And dispara la notificación push al chofer seleccionado
  ```

---

## STORY-04.2: Activación Automática de Pedidos Agendados a T-30 Minutos
* **ID:** `STORY-04.2`
* **Descripción:** Como operador, quiero que los pedidos programados para un horario posterior entren automáticamente a la mesa de despacho activa 30 minutos antes de su deadline.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Activación automática a T-30 minutos
    Given un pedido en estado "scheduled" con fecha/hora pactada
    When el reloj del sistema llega exactamente a 30 minutos antes de la hora pactada
    Then el motor de agenda cambia el estado a "confirmed"
    And detona automáticamente el despacho por Haversine hacia el chofer más cercano
    And actualiza el temporizador en la Torre de Control Web
  ```

---

## STORY-04.3: Pase Inmediato y Reprogramación Manual de Agenda
* **ID:** `STORY-04.3`
* **Descripción:** Como despachador, quiero pasar un pedido agendado a la mesa activa de inmediato o reprogramar su fecha/hora si el cliente lo solicita.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Pase manual y reprogramación
    Given un pedido en la Mesa de Agenda
    When el operador presiona "[ ⚡ Pasar a Pedidos Ya ]"
    Then el pedido se activa inmediatamente para despacho sin esperar el tiempo automático
    When el operador presiona "[ ✏️ Reprogramar ]"
    Then permite actualizar la fecha y hora pactada en la base de datos
  ```

---

# EPIC-05: Torre de Control Web en Dominio Propio, Flota e Incidencias

**Objetivo:** Construir una SPA moderna en FastAPI desplegada en el dominio institucional propio de Petroil con KPIs en vivo, reasignación en caliente, control de pipas vs camionetas, bitácora de incidencias y Modo Claro/Oscuro.

---

## STORY-05.1: Despliegue en Dominio Propio y Dashboard de Métricas
* **ID:** `STORY-05.1`
* **Descripción:** Como supervisor, quiero acceder a la Torre de Control mediante un dominio corporativo seguro (`https://control.petroilgas.com`) y visualizar KPIs en tiempo real.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Acceso seguro y métricas KPI
    Given que el operador accede al dominio institucional con HTTPS
    When la SPA carga y consulta "GET /api/admin/metrics"
    Then despliega: pedidos activos, facturación total, desglose efectivo vs tarjeta, unidades disponibles y promedio CSAT
  ```

---

## STORY-05.2: Reasignación Manual en Caliente con Push Asíncrono
* **ID:** `STORY-05.2`
* **Descripción:** Como despachador, quiero reasignar un pedido rechazado o con demora a otro chofer en 1 clic y que el nuevo operador reciba la alerta al instante.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Reasignación en caliente
    Given un pedido con folio #35 asignado originalmente al Chofer A
    When el operador abre el modal de reasignación, selecciona al Chofer B y confirma
    Then el endpoint "POST /api/admin/orders/35/reassign" actualiza 'driver_id'
    And encola una tarea asíncrona ("BackgroundTasks") que envía la tarjeta completa con GPS al Chofer B en < 2 segundos
  ```

---

## STORY-05.3: Administración de Flota Vehicular (Pipas vs Camionetas)
* **ID:** `STORY-05.3`
* **Descripción:** Como gerente de operaciones, quiero administrar el inventario de pipas (Litros) y camionetas (Cilindros) con placas y choferes asignados.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Gestión de unidades vehiculares
    Given el módulo de Flota Vehicular en la Torre de Control
    When se registra una pipa de gas estacionario
    Then se captura su capacidad en Litros (ej. 5,000 L), placas, modelo y chofer asignado
    When se registra una camioneta de reparto
    Then se captura su capacidad en número de cilindros (ej. 40 tanques) y placas
  ```

---

## STORY-05.4: Conmutador de Modo Claro / Modo Oscuro
* **ID:** `STORY-05.4`
* **Descripción:** Como usuario del panel, quiero alternar entre Modo Claro y Modo Oscuro con persistencia en mi navegador.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Alternancia de tema visual
    Given la interfaz de la Torre de Control
    When el usuario presiona el botón "☀️ Modo Claro" / "🌙 Modo Oscuro"
    Then el tema cambia inmediatamente ajustando la paleta de colores
    And guarda la preferencia en 'localStorage' para futuras sesiones
  ```

---

# EPIC-06: Módulo de Reportes Excel y Persistencia PostgreSQL Corporativa

**Objetivo:** Desarrollar un servicio automatizado en Python con `openpyxl` para generar libros Excel profesionales y asegurar la persistencia en PostgreSQL corporativo de Petroil.

---

## STORY-06.1: Exportación del Libro Maestro en Excel (.xlsx)
* **ID:** `STORY-06.1`
* **Descripción:** Como directivo o auditor contable, quiero descargar un archivo Excel consolidado con múltiples hojas formateadas profesionalmente.
* **Criterios de Aceptación (Gherkin):**
  ```gherkin
  Scenario: Descarga del Libro Maestro
    Given que el usuario presiona "[ 📊 Reporte Maestro ]" en la barra de reportes
    When el servidor procesa "GET /api/admin/reports/excel/master"
    Then genera en memoria un libro XLSX con 4 hojas: "Pedidos & Ventas", "Incidencias & Rechazos", "Flota de Choferes" y "Directorio de Clientes"
    And aplica la paleta corporativa Petroil (encabezados Dark Slate #1E293B, títulos #0F172A, bordes delgados)
    And inicia la descarga en el navegador con formato contable y anchos automáticos
  ```
