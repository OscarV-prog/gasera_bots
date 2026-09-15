# Product Requirements Document (PRD) — Ecosistema Gasera (Gas a tu Puerta)

**Cliente:** Grupo Petroil — División Gas (Mazatlán, Sinaloa)  
**Versión:** 3.5.0 Enterprise — Sincronizada con la Arquitectura Real Implementada (LangGraph AI Sales Agent, Omnicanalidad WhatsApp/Telegram/Call Center, PostgreSQL Corporativo Petroil, Torre de Control Web en Dominio Propio & Reportes Excel)  
**Estado:** Documento Maestro Aprobado y en Operación  
**Fuentes Oficiales de Verdad:** `product-context.md` v3.5, `product-brief.md` v3.5 y Código Fuente del Repositorio  
**Fecha:** Septiembre 2026  

---

## Control de Versiones del Documento

| Versión | Fecha | Autor | Descripción del Cambio | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **1.0.0** | 07/08/2026 | John (Product Manager) | Redacción inicial de fundamentos, alcance, actores y supuestos. | Superado |
| **2.0.0** | 10/08/2026 | John (Product Manager) | Consolidación integral de requerimientos funcionales en 5 partes. | Superado |
| **3.0.0** | 02/09/2026 | Antigravity AI & Equipo Petroil | Sincronización inicial con LangGraph, bots de Telegram y Torre de Control Web. | Superado |
| **3.5.0** | 09/09/2026 | Antigravity AI & Equipo Petroil | **Alineación Integral con el Ecosistema Real y Reglas de Negocio:**<br>• Omnicanalidad Formal: WhatsApp Cloud API, Telegram Bot y Llamadas Telefónicas/Mostrador (módulo Venta Directa en Torre de Control).<br>• Despliegue en Dominio Propio: BackOffice Web configurado en dominio institucional de Petroil (HTTPS), sin correr en localhost en producción.<br>• Base de Datos PostgreSQL de Petroil: Persistencia corporativa en PostgreSQL para producción.<br>• Horarios de Atención: Manejo de ventanas de atención (configurables/TBD) con agendamiento automático para fuera de horario.<br>• Mesa de Agenda Programada: Activación automática a **T-30 minutos**, temporizadores en vivo y reprogramación.<br>• Flota Vehicular: Separación estricta de Pipas (Litros) vs Camionetas (Cilindros).<br>• Turnos y Asistencia: Odómetro y lecturas de gas con respaldo fotográfico.<br>• Bitácora de Incidencias: Registro con motivo de rechazo y reasignación en 1 clic.<br>• Encuestas CSAT: Calificación de 1 a 5 estrellas al cliente tras la entrega. | **Aprobado / Vigente** |

---

# PARTE 1: FUNDAMENTOS Y CONTEXTO ESTRATÉGICO

---

## 1. Introducción y Propósito del Documento

### 1.1. Propósito
El presente **Product Requirements Document (PRD)** define las especificaciones funcionales, operativas, arquitectónicas y de integración para la plataforma tecnológica **Gas a Tu Puerta - Petroil**. Este documento constituye el contrato normativo que rige el comportamiento del agente de ventas con inteligencia artificial, los canales de atención (WhatsApp, Telegram y Teléfono), el bot de choferes en campo, la Torre de Control web en dominio propio, la base de datos PostgreSQL institucional, el motor de despacho logístico y el sistema de reportes ejecutivos.

### 1.2. Problema de Negocio que Resuelve
Grupo Petroil requería modernizar y optimizar la venta y despacho de Gas LP en Mazatlán, resolviendo:
* Cuellos de botella y líneas telefónicas saturadas en horas pico.
* Pérdida de ventas ante competidores por demoras en la toma de pedidos.
* Nula visibilidad para el cliente sobre el tiempo de arribo y estatus del pedido.
* Dificultad para coordinar y auditar camionetas de cilindros y pipas de tanque estacionario en ruta.
* Resistencia histórica del personal de campo ante la instalación de aplicaciones móviles pesadas (APK).
* Falta de un sistema centralizado que unifique pedidos digitales y llamadas telefónicas en una base de datos corporativa.

### 1.3. Enfoque de Solución Implementado
1. **Canal Clientes Omnicanal (WhatsApp y Telegram con IA):** Agente conversacional con IA (**LangGraph** + **DeepSeek v3**) desplegado en WhatsApp Cloud API y Telegram (`telegram_bot.py`), con teclado contextual de botones interactivos (`ui_keyboards.py`). Permite cotización instantánea, consulta de catálogo en tiempo real, selección de direcciones guardadas, geocodificación satelital, validación de horarios de atención y confirmación obligatoria previa.
2. **Canal Telefónico y Mostrador (Venta Directa en Torre de Control):** Módulo `➕ Levantar Pedido` que permite al personal de call center registrar pedidos de llamadas telefónicas con cálculo automático de importes y despacho inteligente o directo.
3. **Canal Choferes (Operación en Campo sin Fricción):** Bot de Telegram (`driver_bot.py`) con control de asistencia (odómetro y foto de tanque), recepción de pedidos con tarjeta GPS y navegación a un toque en **Google Maps** y **Waze**.
4. **Torre de Control Web (FastAPI SPA en Dominio Propio):** Consola administrativa alojada en dominio institucional seguro de Petroil (ej. `https://control.petroilgas.com`), con KPIs en vivo, tablero de pedidos, mesa de agenda con activación automática a **T-30 minutos**, bitácora de incidencias, control de pipas vs camionetas, selector Modo Claro/Oscuro y exportación a Excel.
5. **Capa de Persistencia PostgreSQL Corporativa:** Base de datos relacional PostgreSQL de Grupo Petroil con integridad referencial, índices de alto rendimiento y seguridad de nivel empresarial.

---

## 2. Objetivos del Producto y Métricas de Éxito (KPIs)

| Métrica / KPI | Definición | Meta Target | Mecanismo de Medición |
| :--- | :--- | :--- | :--- |
| **Tiempo de Toma de Pedido (Bot)** | Duración de la interacción con el bot hasta la confirmación | $< 90$ segundos | Logs de LangGraph / Telegram / WhatsApp |
| **Tiempo de Captura (Call Center)** | Tiempo de captura de llamada en módulo Venta Directa | $< 30$ segundos | Timestamp en Torre de Control Web |
| **Tasa de Despacho Automático** | % de pedidos asignados automáticamente por cercanía Haversine | $> 85\%$ | Métricas del Motor de Despacho |
| **Adherencia de Choferes** | % de choferes que registran asistencia y lecturas en Telegram | $100\%$ | Tablas `DRIVER_SHIFTS` y `TANK_READINGS` |
| **Velocidad de Reasignación** | Tiempo en notificar al nuevo chofer tras reasignación en Torre | $< 3$ segundos | BackgroundTasks en FastAPI |
| **Auditoría de Rechazos** | Trazabilidad de motivos de rechazo por choferes en campo | $100\%$ documentado | Tabla `ORDER_REJECTIONS` |
| **Satisfacción del Cliente (CSAT)** | Calificación promedio del servicio de entrega | $\ge 4.5 / 5.0$ ⭐ | Tabla `ORDER_RATINGS` |

---

## 3. Alcance General del Sistema (System Scope)

### 3.1. Dentro del Alcance (In Scope)

#### A. Agente de Ventas con IA y Botones (WhatsApp y Telegram)
* Detección contextual y despliegue automático de botones inline (`ui_keyboards.py`).
* Flujo guiado: Tipo de servicio (`Cilindros` vs `Tanque Estacionario`), catálogo real con precios, cantidades rápidas, teléfono de 10 dígitos, libreta multi-dirección, geocodificación satelital o envío de GPS, horario de entrega y métodos de pago (`Efectivo` o `Terminal / Tarjeta`).
* Validación de horarios de atención (configurables/TBD); pedidos fuera de horario se programan para el siguiente turno.
* Resumen financiero detallado con confirmación obligatoria previa (`[ ✅ Confirmar pedido ]`, `[ ✏️ Modificar ]`, `[ ❌ Cancelar ]`).
* Botón de cancelación inmediata del pedido activo (`cancel_order_client`).
* Asistente con memoria conversacional por hilo (`LangGraph StateGraph`) y registro de tools (`customer_info`, `search_products`, `create_order`, `cancel_order`, `get_order_status`, `get_promotions`).
* Encuestas de satisfacción CSAT al cliente tras completarse la entrega.

#### B. Módulo de Venta Directa / Call Center / Mostrador (Torre de Control)
* Formulario de captura rápida para llamadas telefónicas y pedidos presenciales.
* Cálculo automático de subtotales e importes.
* Opciones de despacho: automático por cercanía, asignación directa a chofer o dejar en cola pendiente.
* Agendamiento de fecha y hora pactada con el cliente.

#### C. Bot Operativo de Choferes en Telegram (`driver_bot.py`)
* Onboarding interactivo para vincular chofer, vehículo, placa y tipo de servicio.
* Control de jornada y turnos: `[ 🟢 Iniciar Turno ]`, `[ ⏸️ Pausar ]`, `[ 🛑 Terminar Turno ]`.
* Registro obligatorio de odómetro (km) y porcentaje de tanque con fotografía de evidencia.
* Recepción de pedidos asignados con tarjeta completa: Folio (#ID), Cliente, Teléfono, Dirección, Referencias, Productos, Monto a Cobrar y Método de Pago.
* Botones de acción rápida: `[ ✅ Aceptar Viaje ]`, `[ ❌ Rechazar ]` (con captura del motivo), `[ 📦 Marcar como Entregado ]`.
* Botones de navegación nativa con apertura directa en **Google Maps** (modo navegación) y **Waze**.

#### D. Torre de Control Web y Backoffice Administrativo (FastAPI SPA en Dominio Propio)
* Servidor unificado FastAPI configurado para operar en dominio institucional seguro de Petroil (HTTPS).
* Dashboard de métricas KPI en tiempo real con desglose de ventas en efectivo vs tarjeta y promedio CSAT.
* Tablero interactivo de pedidos con buscador dinámico y filtrado por estado.
* Reasignación manual de chofer en caliente con notificación push en segundo plano por Telegram/WhatsApp.
* **Mesa de Agenda Programada (Regla T-30 min):** Activación automática a 30 minutos del deadline, temporizadores de cuenta regresiva, pase inmediato `⚡ Pasar a Pedidos Ya` y reprogramación de horario `✏️ Reprogramar`.
* Monitor y bitácora de incidencias y rechazos de choferes con motivo capturado.
* CRUD de Catálogo de Productos y CRUD de Choferes con control de turnos.
* CRUD de Inventario de Vehículos (`VEHICLES`) diferenciando Pipas (Litros) vs Camionetas (Cilindros).
* Directorio de clientes con libreta de direcciones guardadas e historial de compras.
* Conmutador de **Modo Claro / Modo Oscuro** con persistencia en `localStorage` y diseño 100% responsivo.

#### E. Módulo de Reportes Ejecutivos en Excel (`src/services/reports.py`)
* Generador automatizado de libros `.xlsx` con `openpyxl`, estilos corporativos y formato contable:
  - Reporte Maestro Multi-hoja (*Pedidos & Ventas*, *Incidencias & Rechazos*, *Flota de Choferes*, *Directorio de Clientes*).
  - Reporte de Pedidos y Ventas.
  - Reporte de Incidencias y Rechazos.
  - Reporte de Flota y Choferes.
  - Directorio de Clientes.

#### F. Capa de Base de Datos PostgreSQL Corporativa
* Persistencia centralizada en servidor PostgreSQL propio de Grupo Petroil con modelos relacionales normalizados.

---

## 4. Actores del Sistema y Matriz RACI

| Función / Proceso | Cliente (Bot) | Chofer (Bot) | Operador Call Center | Despachador (Torre) | Administrador General |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Cotización y Configuración de Pedido (Bot)** | **R / A** | I | I | I | I |
| **Toma de Pedido Telefónico (Call Center)** | C | I | **R / A** | I | I |
| **Confirmación Obligatoria del Pedido** | **R / A** | I | **R / A** | I | I |
| **Asignación Automática por Haversine** | I | I | I | I | **R / A** (Sistema) |
| **Inicio y Fin de Turno con Foto y Odómetro** | I | **R / A** | I | I | C |
| **Aceptación / Rechazo de Viaje con Motivo** | I | **R / A** | I | I | I |
| **Navegación Asistida (Waze/Maps)** | I | **R / A** | I | I | I |
| **Entrega Física y Cobro** | C | **R / A** | I | I | I |
| **Activación de Agenda a T-30 min** | I | I | I | I | **R / A** (Sistema) |
| **Reasignación Manual en Caliente** | I | I | I | **R / A** | C |
| **Auditoría de Rechazos e Incidencias** | I | C | I | **R** | **A** |
| **Exportación de Reportes en Excel** | I | I | I | **R** | **A** |
| **Mantenimiento de Catálogo de Precios**| I | I | I | C | **R / A** |

---

## 5. Máquina de Estados Oficial del Pedido

```
  [Conversación IA / Llamada] ──► [confirmed] ──► [assigned] ──► [in_route] ──► [delivered]
                                        │               │             │                 │
                                        │               ├─────────────┼──► [rejected]   ▼
                                        │               │             │         │ [Encuesta CSAT ⭐]
                                        ▼               ▼             ▼         ▼
                                   [cancelled]     [cancelled]   [cancelled] [Reasignación Torre]
                                        │
                                        └──► [scheduled (fecha/hora posterior)]
                                                    │
                                                    ▼ (Al llegar a T-30 minutos)
                                           [Activación Automática a confirmed]
```

| Estado | Significado Operativo | Disparador |
| :--- | :--- | :--- |
| `confirmed` | Pedido creado formalmente con folio. En espera de asignación de chofer. | Cliente presiona `[ ✅ Confirmar pedido ]` o captura en Call Center. |
| `scheduled` | Pedido agendado para entrega en horario/día posterior. En Mesa de Agenda. | Cliente o despachador selecciona horario futuro. |
| `assigned` | Chofer asignado por Haversine o manualmente. Tarjeta enviada al bot. | Motor de despacho o reasignación manual en `/admin`. |
| `in_route` | Chofer en traslado hacia el domicilio asistido por Waze/Google Maps. | Chofer presiona `[ ✅ Aceptar Viaje ]`. |
| `rejected_by_driver` | Chofer rechazó el viaje. Registrado en `ORDER_REJECTIONS` con motivo. | Chofer presiona `[ ❌ Rechazar ]` en Telegram. |
| `delivered` | Gas surtido y cobro recibido. Se dispara encuesta CSAT al cliente. | Chofer presiona `[ 📦 Marcar como Entregado ]`. |
| `cancelled` | Pedido anulado antes de la entrega con registro de motivo. | Cliente presiona `[ ❌ Cancelar ]` o despachador cancela en Torre. |

---

# PARTE 2: ESPECIFICACIONES DETALLADAS DEL AGENTE DE VENTAS CON IA (WHATSAPP & TELEGRAM)

---

### F-BOT-01: Bienvenida y Selección de Tipo de Servicio
* **Objetivo:** Iniciar la atención comercial identificando la necesidad del cliente de forma ágil y limpia.
* **Descripción:** Al iniciar la conversación con `/start` o saludar, el bot presenta un saludo cálido institucional de Grupo Petroil y despliega dos botones inline: `[ 🛢️ Cilindros ]` y `[ 🔥 Tanque Estacionario ]`.

### F-BOT-02: Consulta y Despliegue de Catálogo Dinámico
* **Objetivo:** Mostrar únicamente las presentaciones y precios reales vigentes en la base de datos PostgreSQL de Petroil sin alucinaciones del LLM.
* **Descripción:** El sistema consulta la tabla `PRODUCTS` para el tenant `petroil` y genera botones inline con el nombre y precio formateado en MXN (ej. `[ 🟢 Cilindro de 30 kg — $670 MXN ]`).

### F-BOT-03: Selección Ágil de Cantidad
* **Objetivo:** Permitir al usuario definir el volumen de compra en un solo toque o mediante escritura manual.
* **Descripción:**
  - Para cilindros: Botones rápidos `[ 1 ]`, `[ 2 ]`, `[ 3 ]`, `[ 4 ]` y `[ ✍️ Otra cantidad ]`.
  - Para estacionario: Montos sugeridos `[ $300 ]`, `[ $500 ]`, `[ $1,000 ]`, `[ Tanque Lleno ]` y `[ ✍️ Otro monto / Litros ]`.

### F-BOT-04: Reconocimiento Telefónico y Detección de Cliente Frecuente
* **Objetivo:** Identificar al cliente en la base de datos garantizando exactitud mediante su número de celular.
* **Descripción:** El bot procesa el número a 10 dígitos limpios. Si el cliente ya existe en `CUSTOMERS`, recupera su historial y libreta de direcciones (`CUSTOMER_ADDRESSES`). Si es nuevo, solicita nombre y dirección completa.

### F-BOT-05: Libreta Multi-Dirección y Captura con GPS / Geocodificación
* **Objetivo:** Agilizar la entrega a clientes recurrentes y capturar ubicaciones exactas para nuevos pedidos.
* **Descripción:**
  - Cliente recurrente: Se listan sus direcciones guardadas (`[ 🏠 Casa Principal... ]`, `[ ➕ Ingresar Nueva Dirección ]`).
  - Nueva dirección: Opciones `[ ✍️ Escribir dirección ]` y `[ 📍 Enviar ubicación GPS ]`. Las direcciones escritas se normalizan y geocodifican mediante Nominatim (`src/services/geocoding.py`).

### F-BOT-06: Confirmación Visual de Dirección
* **Objetivo:** Evitar entregas en domicilios erróneos permitiendo corrección inmediata.
* **Descripción:** El bot muestra la dirección procesada y presenta los botones `[ ✅ Confirmar dirección ]` y `[ ✏️ Cambiar dirección ]`.

### F-BOT-07: Selección de Horario de Entrega y Manejo de Horarios de Atención
* **Objetivo:** Permitir al cliente elegir cuándo recibir su gas y gestionar solicitudes fuera del horario comercial.
* **Descripción:**
  - Despliega botones `[ ⚡ Lo antes posible ]`, `[ 🕐 Hoy por la tarde ]` y `[ 📅 Mañana ]`.
  - Si el pedido entra fuera de la ventana de atención (configuración de horarios TBD), el bot notifica cordialmente los horarios hábiles y ofrece programar el pedido (`scheduled`) para el inicio del siguiente turno disponible.

### F-BOT-08: Selección de Método de Pago
* **Objetivo:** Notificar al chofer la forma de pago requerida para llevar cambio o terminal bancaria.
* **Descripción:** Despliega los botones `[ 💵 Efectivo ]` y `[ 💳 Tarjeta (Terminal) ]`.

### F-BOT-09: Resumen Financiero y Confirmación Obligatoria Previa
* **Objetivo:** Blindar la base de datos evitando la creación de pedidos no confirmados.
* **Descripción:** El bot presenta una tarjeta resumen con desglose de productos, total a pagar, dirección, horario y método de pago, acompañada de tres botones:
  - `[ ✅ Confirmar pedido ]`
  - `[ ✏️ Modificar pedido ]`
  - `[ ❌ Cancelar ]`
* **Regla Crítica:** La tool `create_order` **NUNCA** se ejecuta hasta que el cliente presiona explícitamente `Confirmar pedido`.

### F-BOT-10: Creación Formal de Pedido y Disparo de Despacho
* **Objetivo:** Registrar la orden en PostgreSQL y disparar el motor de asignación logística.
* **Descripción:** Tras pulsar confirmar, se ejecuta `create_order`, se almacena la orden en `ORDERS` y partidas en `ORDER_ITEMS`, se genera el folio (#ID), y se dispara `dispatch_order` para buscar al chofer disponible más cercano por Haversine.

### F-BOT-11: Cancelación Rápida de Pedido Activo
* **Objetivo:** Permitir al cliente anular un pedido en caso de imprevistos sin intervención de call center.
* **Descripción:** El mensaje de pedido creado incluye un botón persistente `[ ❌ Cancelar Pedido #ID ]`. Al presionarlo, el pedido cambia a `cancelled` y el chofer asignado queda liberado automáticamente.

### F-BOT-12: Encuesta de Satisfacción CSAT
* **Objetivo:** Medir la satisfacción del cliente tras la entrega física.
* **Descripción:** Al completarse la orden (`delivered`), el bot envía un mensaje de agradecimiento solicitando calificar el servicio del 1 al 5 estrellas (`[ ⭐ ]` a `[ ⭐⭐⭐⭐⭐ ]`), registrando el resultado en `ORDER_RATINGS`.

---

# PARTE 3: ESPECIFICACIONES DEL BOT DE CHOFERES (OPERACIÓN EN CAMPO)

---

### F-DRV-01: Onboarding y Registro Guiado de Chofer en Telegram
* **Objetivo:** Enrolar a nuevos operadores de forma conversacional.
* **Descripción:** Al iniciar `driver_bot.py`, el chofer ingresa nombre completo, teléfono, tipo de vehículo (`cilindros` o `estacionario`) y placas. Se registra en `DRIVERS` vinculando su `telegram_user_id`.

### F-DRV-02: Control de Asistencia y Turnos con Lecturas de Tanque y Odómetro
* **Objetivo:** Auditar la jornada laboral y el uso de combustible de la flota.
* **Descripción:**
  - `[ 🟢 Iniciar Turno ]`: Solicita odómetro inicial (km), porcentaje de gas LP y **fotografía obligatoria del medidor/odómetro**, guardándola en `uploads/tank_readings/` y registrando el inicio en `DRIVER_SHIFTS` con `is_available = 1`.
  - `[ ⏸️ Pausar ]`: Cambia `is_available = 0` temporalmente.
  - `[ 🛑 Terminar Turno ]`: Solicita lectura final de combustible, odómetro final y fotografía, calculando los minutos trabajados y cerrando la jornada.

### F-DRV-03: Recepción de Tarjeta de Despacho con Geolocalización
* **Objetivo:** Proporcionar al chofer la información crítica del pedido en una sola vista estructurada.
* **Descripción:** El chofer recibe una notificación en Telegram con Folio, Cliente, Teléfono, Dirección, Referencias, Productos, Monto a Cobrar y Método de Pago.

### F-DRV-04: Navegación Asistida a un Toque (Google Maps y Waze)
* **Objetivo:** Guiar al chofer directamente al domicilio del cliente.
* **Descripción:** La tarjeta incorpora dos botones de navegación externa:
  - `[ 🗺️ Google Maps ]`: `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}`
  - `[ 🚗 Waze ]`: `https://waze.com/ul?ll={lat},{lng}&navigate=yes`

### F-DRV-05: Aceptación y Rechazo de Viajes con Captura de Motivo
* **Objetivo:** Permitir al chofer aceptar el viaje o reportar una incidencia para reasignación inmediata.
* **Descripción:**
  - `[ ✅ Aceptar Viaje ]`: Cambia el pedido a `in_route`.
  - `[ ❌ Rechazar ]`: Despliega menú de motivos (*Falla mecánica*, *Desabasto*, *Tráfico pesado*, etc.). El pedido cambia a `rejected_by_driver`, se inserta en `ORDER_REJECTIONS` y se genera una alerta visual en la Torre de Control.

### F-DRV-06: Conclusión de Entrega y Cobro
* **Objetivo:** Registrar la finalización exitosa del servicio y liberar la unidad.
* **Descripción:** Al completar el servicio, el chofer pulsa `[ 📦 Marcar como Entregado ]`. El pedido cambia a `delivered`, se libera al chofer y se dispara la encuesta CSAT al cliente.

---

# PARTE 4: ESPECIFICACIONES DE LA TORRE DE CONTROL WEB (EN DOMINIO PROPIO)

---

### F-ADM-01: Despliegue en Dominio Propio Institucional
* **Objetivo:** Proveer acceso seguro, profesional y de alta disponibilidad para el personal administrativo.
* **Descripción:** La Torre de Control opera bajo un dominio institucional propio de Petroil (ej. `https://control.petroilgas.com` / `https://backoffice.petroil.com.mx`) protegido por HTTPS y certificado SSL/TLS corporativo, descartando la ejecución en `localhost` para producción.

### F-ADM-02: Dashboard de Métricas KPI en Vivo
* **Endpoint:** `GET /api/admin/metrics?tenant_id=petroil`
* **Descripción:** Retorna indicadores en tiempo real: pedidos del día, facturación total, desglose de ventas en efectivo vs tarjeta, pedidos activos, choferes por estado (disponibles, en entrega, fuera de servicio), incidencias pendientes y promedio de calificación CSAT (1-5 ⭐).

### F-ADM-03: Tablero de Pedidos Activos y Reasignación en Caliente
* **Endpoints:** `GET /api/admin/orders`, `POST /api/admin/orders/{id}/reassign`
* **Descripción:** Grid reactivo con búsqueda instantánea y filtros por estado. Permite reasignar un pedido a otro chofer disponible con un clic, detonando una tarea en segundo plano (`BackgroundTasks`) que envía la tarjeta completa con GPS al Telegram/WhatsApp del nuevo chofer en menos de 2 segundos.

### F-ADM-04: Mesa de Agenda Programada y Activación Automática (Regla T-30 min)
* **Endpoints:** `GET /api/admin/agenda`, `POST /api/admin/orders/{id}/activate-now`, `PATCH /api/admin/orders/{id}/reschedule`
* **Descripción:**
  - Lista pedidos programados con cálculo en tiempo real de minutos para activación y deadline.
  - **Activación Automática:** Los pedidos se transfieren automáticamente a la mesa de despacho activa **30 minutos antes** de su hora pactada.
  - Temporizadores de cuenta regresiva (`🕒 Faltan 2h 15m`).
  - Botón de pase manual inmediato (`⚡ Pasar a Pedidos Ya`).
  - Modal de reprogramación de fecha y hora (`✏️ Reprogramar`).

### F-ADM-05: Módulo de Venta Directa / Mostrador / Call Center
* **Endpoint:** `POST /api/admin/orders`
* **Descripción:** Modal `➕ Levantar Pedido` que permite a las operadoras de call center capturar pedidos telefónicos: cliente, teléfono, dirección, productos, entrega inmediata o agendada, método de pago y tipo de asignación (automática Haversine, chofer directo o pendiente).

### F-ADM-06: Inventario de Vehículos y Unidades (`VEHICLES`)
* **Endpoints:** `GET`, `POST`, `PUT`, `DELETE /api/admin/vehicles`
* **Descripción:** Administración de flota clasificando estrictamente:
  - **Pipas de Gas Estacionario:** Capacidad en **Litros** (ej. 5,000 L).
  - **Camionetas de Cilindros:** Capacidad en **unidades de tanques** (ej. 40 cilindros).
  - Placas, modelo, chofer asignado y estatus operativo.

### F-ADM-07: Bitácora de Incidencias y Rechazos
* **Endpoint:** `GET /api/admin/rejections`
* **Descripción:** Monitor de viajes rechazados por choferes con visualización del motivo exacto reportado y botón para reasignar inmediatamente.

### F-ADM-08: Modo Claro / Modo Oscuro y Diseño Responsivo
* **Descripción:** Selector de tema en cabecera (`☀️ Modo Claro` / `🌙 Modo Oscuro`) con persistencia en `localStorage`. Interfaz responsiva para Monitores Grandes, Laptops, Tablets (con Drawer lateral y botón hamburguesa `☰`) y Smartphones.

### F-ADM-09: Generador de Reportes Ejecutivos en Excel (`openpyxl`)
* **Endpoints:** `GET /api/admin/reports/excel/master`, `/orders`, `/rejections`, `/drivers`, `/customers`
* **Descripción:** Generación en memoria (`io.BytesIO`) de libros `.xlsx` con tipografía ejecutiva, encabezados en paleta Petroil (`#1E293B`, `#2563EB`), anchos automáticos de columna y formato de moneda contable.

---

# PARTE 5: REQUISITOS NO FUNCIONALES Y ESPECIFICACIONES TÉCNICAS

---

## 6. Requisitos No Funcionales (NFRs)

* **NFR-01 (Latencia del Agente de Ventas):** El bot de clientes debe procesar las respuestas con LLM (DeepSeek v3) y adjuntar teclados inline en menos de $2.5\text{ segundos}$.
* **NFR-02 (Rendimiento de Despacho):** El cálculo de distancia Haversine y asignación de chofer debe ejecutarse en menos de $50\text{ milisegundos}$ por pedido.
* **NFR-03 (No Bloqueo en Reasignación):** Las notificaciones a choferes deben ejecutarse mediante tareas asíncronas en segundo plano (`BackgroundTasks`), respondiendo a la interfaz web en menos de $150\text{ ms}$.
* **NFR-04 (Persistencia e Integridad en PostgreSQL):** La base de datos PostgreSQL de Petroil debe operar con restricciones de clave foránea, transacciones ACID y soporte para índices espaciales.
* **NFR-05 (Seguridad de Dominio y Comunicaciones):** Toda comunicación con la Torre de Control y Webhooks debe utilizar cifrado TLS 1.3 con certificados SSL/TLS válidos sobre el dominio institucional de Petroil.
* **NFR-06 (Exportación Eficiente en Excel):** La generación de reportes Excel con `openpyxl` debe realizarse mediante streaming en memoria en menos de $2\text{ segundos}$ para volúmenes de hasta 5,000 registros.
