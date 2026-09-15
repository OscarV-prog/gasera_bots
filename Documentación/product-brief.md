# Product Brief: Ecosistema Venta Gasera (Gas a tu Puerta)

**Cliente:** Grupo Petroil — División Gas (Mazatlán, Sinaloa)  
**Versión:** 3.5 Enterprise — Alineada con la Arquitectura Real Implementada (LangGraph AI, Omnicanalidad WhatsApp/Telegram/Call Center, PostgreSQL Petroil, Torre de Control Web en Dominio Propio & Despacho Logístico)  
**Fuente Oficial de Verdad:** `product-context.md` v3.5  
**Estado:** Confirmado / Sistema Operativo y Validado  
**Fecha:** Septiembre 2026  

---

## 1. Executive Summary

El proyecto **Gas a Tu Puerta - Petroil** transforma integralmente la captación comercial, la experiencia de usuario y la logística de última milla para la venta y distribución de Gas LP (cilindros de 10, 20, 30 y 45 kg y recarga en tanque estacionario por litro) en la plaza de Mazatlán, Sinaloa.

Históricamente, la operación dependía de la **atención telefónica manual**, lo que provocaba saturación de líneas en horas pico, llamadas perdidas, nula visibilidad del estatus para el cliente y opacidad en las rutas de los repartidores en campo.

La solución sustituyó y modernizó este modelo mediante un **ecosistema tecnológico omnicanal, ágil, sin barreras de instalación y de alta adopción operativa**:

1. **Agente de Ventas con Inteligencia Artificial (Omnicanal: WhatsApp y Telegram):** Bot conversacional orquestado con **LangGraph** y **DeepSeek v3** (vía OpenRouter), complementado con una **experiencia guiada de botones interactivos (`ui_keyboards.py`)**. Ofrece catálogo dinámico con precios reales sincronizados, selección ágil de cantidades, reconocimiento por 10 dígitos de teléfono, libreta multi-dirección, geocodificación satelital (Nominatim) o GPS nativo, validación de horarios de atención y confirmación previa obligatoria antes de generar el pedido.
2. **Módulo de Venta Directa, Call Center y Mostrador (Vía Telefónica / Presencial):** Integrado en la Torre de Control Web, permite a las operadoras de call center y encargados de mostrador levantar pedidos telefónicos o presenciales en segundos, con cálculo automático de importes, asignación inteligente a choferes o pase a cola pendiente. Las llamadas telefónicas forman parte integral de los canales atendidos por el sistema.
3. **Bot Operativo de Choferes en Telegram (`driver_bot.py`):** Elimina por completo la necesidad de mantener costosas aplicaciones móviles nativas (APK). Los choferes gestionan su asistencia (check-in/check-out con odómetro y lectura de tanque con fotografía de evidencia), reciben viajes en tiempo real con tarjeta GPS, y abren la ruta con un solo toque directamente en **Waze** o **Google Maps** (modo navegación giro a giro).
4. **Torre de Control y Backoffice Administrativo Web (Desplegado en Dominio Propio):** Aplicación web moderna (SPA) servida mediante **FastAPI**, configurada para operar en un **dominio propio institucional de Petroil** con conexión segura HTTPS (ej. `https://control.petroilgas.com` / `https://backoffice.petroil.com.mx`), descartando el uso de `localhost` en producción. Incorpora KPIs en vivo, tablero de pedidos activos, mesa de agenda con activación automática a **T-30 minutos**, bitácora de incidencias y rechazos con motivo exacto, control de flota vehicular (pipas vs camionetas), encuestas de satisfacción CSAT (1-5 ⭐), conmutador de **Modo Claro / Modo Oscuro** y un **generador de reportes ejecutivos en Excel con `openpyxl`**.
5. **Capa de Persistencia Empresarial en PostgreSQL Propia de Petroil:** Almacenamiento centralizado, transaccional y de alta disponibilidad alojado en la infraestructura de **PostgreSQL corporativa de Petroil**, garantizando integridad relacional, soporte geoespacial, auditoría y seguridad de datos empresariales (con SQLite reservado para entornos de desarrollo y pruebas locales).

---

## 2. Product Vision

> *"Convertir a la división de gas de Grupo Petroil en el referente tecnológico indiscutible en la distribución de Gas LP en el noroeste de México, ofreciendo a los clientes una experiencia de compra inmediata, omnicanal e inteligente mediante IA (WhatsApp, Telegram y Call Center), mientras se optimiza la productividad de la flota con despacho geolocalizado en tiempo real, persistencia en PostgreSQL propio y una Torre de Control Web de alto rendimiento en dominio institucional."*

---

## 3. Business Problem

1. **Saturación y Demoras Telefónicas:** Líneas ocupadas en horarios de alta demanda, causando fricción y fuga de clientes hacia gaseras competidoras.
2. **Incertidumbre del Cliente:** Desconocimiento sobre el tiempo estimado de entrega y el estatus real del servicio ("¿cuándo llega mi gas?").
3. **Opacidad y Falta de Control en Campo:** Dificultad para coordinar camionetas de cilindros y pipas de estacionario en tránsito, auditar lecturas de combustible y asignar pedidos de manera óptima según ubicación geográfica.
4. **Fricción Tecnológica con Choferes:** Rechazo histórico de los repartidores hacia aplicaciones móviles nativas por problemas de compatibilidad, saturación de memoria en teléfonos o descargas complejas en tiendas de apps.
5. **Falta de Trazabilidad Centralizada:** Necesidad de consolidar las ventas digitales, telefónicas y de mostrador en una única base de datos PostgreSQL institucional con reportes directivos descargables en Excel.

---

## 4. Opportunity Statement & Solución Construida

* **Omnicanalidad Real (WhatsApp, Telegram y Teléfono):** Cobertura total del mercado permitiendo a los clientes comprar por su canal preferido: mensajería instantánea automatizada con IA o llamada telefónica tradicional atendida por personal de call center en la Torre de Control.
* **Experiencia de Compra Guiada (Híbrida):** Combinación de botones interactivos para pasos estructurados (productos, cantidades, horarios, pagos) con conversación natural inteligente para resolución de dudas y referencias de entrega.
* **Manejo Dinámico de Horarios de Atención:** El sistema incorpora lógica para consultar y aplicar las ventanas de atención comercial/operativa (actualmente configurables / TBD por la directiva de Petroil), informando al cliente y agendando pedidos fuera de horario para el siguiente turno hábil disponible.
* **Despacho Logístico Automatizado por Cercanía:** Motor con fórmula de Haversine que geocodifica la dirección del cliente vía Nominatim y asigna de inmediato al chofer disponible más cercano.
* **Mesa de Agenda con Activación Automática (30 min antes de Deadline):** Los pedidos programados se transfieren a la mesa de despacho activa automáticamente **30 minutos antes** de su hora pactada.
* **Control Centralizado en Dominio Propio:** Torre de Control Web en FastAPI alojada en dominio institucional seguro de Petroil con visibilidad total, reasignación en caliente, control de pipas vs camionetas, asistencia de choferes y exportación en Excel.
* **Base de Datos PostgreSQL Corporativa:** Infraestructura de persistencia robusta, segura y escalable propiedad de Grupo Petroil.

---

## 5. Product Goals

1. **Automatizar la Venta Digital:** Permitir que los clientes ordenen cilindros o gas estacionario en menos de 60 segundos a través de WhatsApp o Telegram con el agente IA.
2. **Centralizar la Venta Telefónica y Mostrador:** Habilitar el módulo de Venta Directa en la Torre de Control para que el personal capture pedidos de llamadas telefónicas en menos de 30 segundos.
3. **Despacho Eficiente en Campo:** Reducir tiempos de entrega asignando automáticamente el chofer en turno más próximo geográficamente mediante Haversine.
4. **Navegación Asistida a Choferes:** Entregar enlaces nativos de Waze y Google Maps con las coordenadas exactas de entrega en cada viaje.
5. **Resiliencia Operativa:** Permitir que la Torre de Control reasigne pedidos en caliente si un chofer rechaza o reporta una avería mecánica.
6. **Auditoría de Flota y Combustible:** Controlar asistencia, odómetro y porcentaje de tanque con fotografía obligatoria.
7. **Inteligencia de Negocio y Auditoría Directiva:** Facilitar la descarga inmediata de libros Excel multiciudad y multihoja formateados con métricas de ventas, pedidos, choferes, incidencias y clientes.

---

## 6. Success Metrics (KPIs)

| Categoría | Indicador Clave (KPI) | Meta Target | Mecanismo de Medición |
| :--- | :--- | :--- | :--- |
| **Tiempo de Toma de Pedido (Bot)** | Duración de la interacción con el bot hasta la confirmación | $< 90$ segundos | Logs de LangGraph / Telegram / WhatsApp |
| **Tiempo de Captura (Call Center)** | Tiempo de captura de llamada en módulo Venta Directa | $< 30$ segundos | Timestamp en Torre de Control Web |
| **Asignación Automática** | % de pedidos asignados automáticamente por cercanía Haversine | $> 85\%$ | Motor de Despacho (`dispatch.py`) |
| **Adherencia de Choferes** | % de choferes que registran asistencia y lecturas en el bot | $100\%$ | Tablas `driver_shifts` y `tank_readings` |
| **Respuesta a Reasignaciones** | Tiempo de notificación al nuevo chofer ante reasignación en Torre | $< 3$ segundos | Push en Telegram/WhatsApp vía BackgroundTasks |
| **Trazabilidad de Incidencias** | Registro con motivo estructurado de rechazos de viaje | $100\%$ documentado | Tabla `order_rejections` |
| **Satisfacción del Cliente (CSAT)** | Calificación promedio del servicio de entrega | $\ge 4.5 / 5.0$ ⭐ | Tabla `order_ratings` |

---

## 7. Stakeholders

* **Directiva de Grupo Petroil:** Interesada en liderazgo de mercado, rentabilidad, control de flota y reportes ejecutivos consolidados en Excel.
* **Gerencia de Operaciones y Logística:** Supervisores que monitorean la flota en la Torre de Control Web en dominio propio y gestionan reasignaciones en caliente.
* **Operadoras de Call Center y Mostrador:** Personal que atiende llamadas telefónicas y pedidos presenciales capturando directamente en la Torre de Control.
* **Choferes de Reparto (Pipas y Camionetas):** Operadores que utilizan el bot de Telegram para gestionar su jornada, enviar lecturas y navegar hacia los clientes.
* **Clientes Residenciales y Comerciales:** Familias y negocios en Mazatlán que solicitan Gas LP por WhatsApp, Telegram o teléfono.

---

## 8. User Personas

### 8.1. María — Cliente Residencial Digital (Mazatlán)
* **Perfil:** Ama de casa en Fracc. Misiones.
* **Necesidad:** Pedir su cilindro de 30 kg rápidamente por WhatsApp/Telegram sin esperar en el teléfono y conociendo el precio exacto.
* **Experiencia:** Abre el bot, presiona `[ 🛢️ Cilindros ]`, selecciona `[ 🟢 Cilindro de 30 kg — $670 MXN ]`, confirma su dirección guardada con un toque, elige efectivo, revisa el resumen financiero y confirma.

### 8.2. Don Roberto — Cliente Tradicional por Teléfono
* **Perfil:** Dueño de restaurante en el Centro Histórico.
* **Necesidad:** Llamar por teléfono para pedir recarga de gas estacionario de $1,500 MXN para entrega a las 3:00 PM.
* **Experiencia:** Llama al número de Petroil; la operadora abre el módulo `➕ Levantar Pedido` en la Torre de Control, busca su teléfono, selecciona gas estacionario, programa la entrega para las 3:00 PM y el sistema lo agenda automáticamente.

### 8.3. Carlos — Chofer de Camioneta de Cilindros
* **Perfil:** Repartidor de campo con unidad vehicular M-0258.
* **Necesidad:** Ver sus viajes asignados con claridad, no perderse en colonias complejas y registrar su jornada fácilmente.
* **Experiencia:** Inicia turno en Telegram subiendo su kilometraje y foto de medidor, recibe alertas de viaje con tarjeta GPS, presiona `[ 🗺️ Google Maps ]` o `[ 🚗 Waze ]` para navegar, y marca `[ 📦 Marcar como Entregado ]` al cobrar.

### 8.4. Laura — Despachadora en Torre de Control (Backoffice)
* **Perfil:** Supervisora operativa en oficinas de Petroil.
* **Necesidad:** Monitorear pedidos en tiempo real, supervisar la mesa de agenda programada, atender incidencias de choferes y exportar reportes a Excel.
* **Experiencia:** Accede desde su navegador a `https://control.petroilgas.com`, visualiza el mapa y tabla en vivo, conmuta entre Modo Claro y Oscuro según la iluminación, reasigna pedidos con 1 clic y descarga el Libro Maestro en Excel.

---

## 9. Ecosystem Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          ARQUITECTURA DEL ECOSISTEMA VENTA GASERA                               │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  [ CLIENTES WHATSAPP / TELEGRAM ] ──► Bots con IA (LangGraph + DeepSeek)                        │
│                                       (Botones UI + Conversación)                               │
│                                                   │                                             │
│  [ CLIENTES VÍA TELEFÓNICA ] ───────► Operadora Call Center ──► [ TORRE DE CONTROL WEB ]       │
│                                                                  Dominio Propio Petroil         │
│                                                   │              (https://control.petroilgas.com)
│                                                   ▼                        │                    │
│                                            Motor de Despacho               │                    │
│                                            (Nominatim + Haversine)         ▼                    │
│                                                   │                 Base de Datos PostgreSQL    │
│                                                   ▼                 (Corporativa Petroil)       │
│  [ CHOFERES ] ◄── Bot Telegram (driver_bot.py) ───┘                        │                    │
│                   (Turnos, Fotos, Waze/Maps, Estatus)                      ▼                    │
│                                                                     Reportes Excel (.xlsx)      │
│                                                                     (openpyxl)                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Scope (Alcance de la Solución Construida)

### 10.1. Canales de Captación de Clientes (Omnicanal)
* **WhatsApp Cloud API & Telegram Bot:** Asistente IA (LangGraph) con catálogo de Tools (`customer_info`, `search_products`, `create_order`, `cancel_order`, `get_order_status`, `get_promotions`).
* **Canal Telefónico / Call Center / Mostrador:** Módulo `➕ Levantar Pedido` en la Torre de Control para captura inmediata con autocompletado y despacho automático o asignación directa.
* **Detección contextual de botones interactivos (`ui_keyboards.py`):** Tipo de servicio, catálogo real con precios, cantidades rápidas, libreta de direcciones, métodos de pago y resumen financiero.
* **Manejo de Horarios de Atención:** Validación de ventanas de servicio (TBD/configurables); pedidos fuera de horario se programan automáticamente para el siguiente turno.
* **Confirmación previa obligatoria:** Ningún pedido se escribe en la base de datos hasta ser confirmado explícitamente por el cliente o despachador.
* **Encuestas CSAT:** Disparo automático de encuesta de 1 a 5 estrellas al cliente tras completarse la entrega.

### 10.2. Canal Choferes (Operación en Campo)
* **Bot de Telegram (`driver_bot.py`):** Onboarding conversacional de unidad y placas.
* **Control de Asistencia y Turnos:** Registro de entrada (`check_in_at`), salida (`check_out_at`), odómetro y lecturas de tanque con fotografía obligatoria guardada en almacenamiento seguro.
* **Recepción de Viajes:** Tarjeta estructurada con Folio, Cliente, Teléfono, Dirección, Referencias, Productos, Monto a Cobrar y Método de Pago.
* **Navegación Asistida:** Enlaces directos a **Google Maps** (modo navegación) y **Waze**.
* **Acciones Rápidas:** Aceptar viaje, rechazar viaje con motivo estructurado y marcar como entregado y cobrado.

### 10.3. Torre de Control Web y Backoffice Administrativo (Dominio Propio)
* **Despliegue en Dominio Propio Institucional:** Acceso seguro vía HTTPS (ej. `https://control.petroilgas.com`) con servidor FastAPI de alto rendimiento.
* **Dashboard de KPIs en Tiempo Real:** Pedidos activos, incidencias pendientes, estado de choferes, ventas totales, desglose efectivo vs tarjeta y promedio CSAT.
* **Tablero de Pedidos Activos:** Búsqueda en tiempo real, filtros por estado y reasignación rápida con alerta push inmediata al chofer.
* **Mesa de Agenda Programada (Regla T-30 min):** Activación automática 30 minutos antes de la hora pactada, temporizadores de cuenta regresiva, filtros de fecha (Hoy/Mañana/Todos), pase inmediato manual (`⚡ Pasar a Pedidos Ya`) y reprogramación de horario (`✏️ Reprogramar`).
* **Bitácora de Incidencias y Rechazos:** Monitor de motivos de rechazo en campo con alerta visual y botón de reasignación.
* **Inventario de Vehículos (`VEHICLES`):** Administración diferenciada de Pipas de Estacionario (Litros) vs Camionetas de Cilindros (Tanques), placas, modelos y operadores asignados.
* **Directorio de Clientes:** Padrón de clientes, historial de compras, gasto total acumulado y libreta multi-dirección.
* **Tema Visual Adaptativo y Responsivo:** Selector conmutable de **Modo Claro / Modo Oscuro** con guardado en `localStorage`, adaptado para Monitores Grandes, Laptops, Tablets (Drawer hamburguesa) y Celulares.

### 10.4. Persistencia en PostgreSQL y Reportes Excel
* **Base de Datos PostgreSQL Propia de Petroil:** Persistencia robusta, esquemas relacionales, índices GiST y soporte transaccional corporativo.
* **Generador de Reportes Excel (`openpyxl`):** Exportación de Libro Maestro con 4 hojas formateadas (*Pedidos & Ventas*, *Incidencias & Rechazos*, *Flota de Choferes*, *Directorio de Clientes*) y reportes especializados.

---

## 11. Aspectos Resueltos vs. Próximas Fases

| Aspecto | Estado Original | Resolución Implementada en Versión 3.5 |
| :--- | :--- | :--- |
| **Dominio y Despliegue de Torre de Control** | *Localhost:3000* | **Resuelto:** Configuración para despliegue en **dominio propio institucional de Petroil** con HTTPS, proxy inverso y alta disponibilidad. |
| **Canales de Captación** | *Solo Telegram* | **Resuelto:** Ecosistema omnicanal formalizado: **WhatsApp**, **Telegram** y **Llamadas Telefónicas / Call Center / Mostrador** integrados. |
| **Base de Datos Corporativa** | *SQLite local* | **Resuelto:** Arquitectura empresarial sobre **PostgreSQL propio de Petroil**, manteniendo SQLite para entornos de prueba. |
| **Horarios de Atención Comercial** | *No especificado* | **Resuelto:** Lógica de validación de horarios configurables (TBD), con respuesta cordial del bot y programación automática para el siguiente turno. |
| **Gestión de Agenda Programada** | *Cola estática* | **Resuelto:** Mesa de agenda con activación automática a **T-30 minutos**, temporizadores en vivo y pase manual. |
| **Control de Asistencia y Flota** | *Básico* | **Resuelto:** Check-in/check-out con odómetro y foto de tanque, más separación estricta de Pipas (Litros) vs Camionetas (Cilindros). |
| **Calidad de Servicio (CSAT)** | *No medido* | **Resuelto:** Encuestas automáticas de 1 a 5 estrellas al cliente tras la entrega con métricas en Torre de Control. |
