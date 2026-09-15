# Product Context: Ecosistema Venta Gasera (Gas a tu Puerta)

**Cliente:** Grupo Petroil — División Gas (Mazatlán, Sinaloa)  
**Versión:** 3.5 Enterprise — Consolidada con Arquitectura Real Implementada (LangGraph AI, Omnicanalidad WhatsApp/Telegram/Call Center, PostgreSQL Corporativo Petroil, Torre de Control Web en Dominio Propio & Despacho Logístico)  
**Estado:** Confirmado / Sistema Construido y en Operación  
**Fecha:** Septiembre 2026  

---

## 1. Visión General del Proyecto y Propósito

El proyecto **Gas a Tu Puerta - Petroil** tiene como objetivo principal transformar y digitalizar la operación comercial y logística de venta y distribución de gas LP a domicilio (cilindros de 10, 20, 30 y 45 kg y recarga por litro en tanque estacionario) en la plaza de Mazatlán, Sinaloa.

Históricamente, el modelo operativo dependía exclusivamente de la **atención telefónica manual**, lo que provocaba saturación de líneas en horas pico, nula visibilidad del pedido para el cliente, llamadas perdidas y opacidad sobre la disponibilidad y rutas de los choferes en campo.

El sistema implementado resolvió este desafío mediante un **ecosistema tecnológico integral, omnicanal y de alta adopción**, sustentado en cuatro pilares fundamentales:

1. **Canal de Clientes Inteligente y Omnicanal (WhatsApp y Telegram con IA):**
   Un agente de ventas conversacional orquestado con **LangGraph** y modelos de lenguaje avanzados (**DeepSeek v3** vía OpenRouter), potenciado con una **experiencia híbrida de botones interactivos (`ui_keyboards.py`)**. Esto elimina la fricción de escribir mensajes largos, guiando al usuario paso a paso con catálogo real de productos y precios, selección de direcciones guardadas, geolocalización satelital (Nominatim / GPS nativo), validación de horarios de atención y confirmación previa obligatoria.
2. **Canal Telefónico, Call Center y Mostrador (Vía Telefónica / Presencial):**
   Módulo integrado en la Torre de Control Web (`➕ Levantar Pedido`) que permite a los operadores de oficina capturar pedidos originados por llamadas telefónicas o en mostrador en menos de 30 segundos, integrándolos de inmediato al motor de despacho inteligente o asignándolos directamente a un chofer.
3. **Canal de Choferes sin Fricción de Instalación (Bot de Choferes en Telegram):**
   En lugar de forzar la instalación y mantenimiento de aplicaciones móviles nativas (APK) en los teléfonos de los repartidores, se desplegó un bot operativo en Telegram ([`driver_bot.py`](file:///c:/Users/Prestamo%20ASKE/Desktop/prueba-2-lapp/langgraph-sales-agent/driver_bot.py)). Este canal permite control de turnos en tiempo real, registro fotográfico de lecturas de tanque y odómetro, recepción instantánea de pedidos con coordenadas GPS, navegación a un toque con **Waze** y **Google Maps** (modo navegación giro a giro), reporte de rechazos justificados con motivo y confirmación de cobro.
4. **Torre de Control y Backoffice Administrativo Web (Desplegado en Dominio Propio):**
   Una aplicación web moderna (SPA) servida mediante **FastAPI**, configurada para operar en un **dominio propio institucional de Grupo Petroil** con conexión segura HTTPS (ej. `https://control.petroilgas.com` / `https://backoffice.petroil.com.mx`), descartando el uso de `localhost` en entornos productivos. Brinda métricas KPI en vivo, mesa de agenda con activación automática a **T-30 minutos**, reasignación de choferes en caliente con disparo de alertas push, bitácora de incidencias, administración de flota vehicular (pipas vs camionetas), encuestas de satisfacción CSAT (1 a 5 ⭐), conmutador de **Modo Claro / Modo Oscuro** y un **motor de reportes ejecutivos en Excel (`openpyxl`)**.
5. **Capa de Persistencia Empresarial en PostgreSQL Propia de Petroil:**
   Base de datos relacional corporativa alojada en la infraestructura de **PostgreSQL de Petroil**, que garantiza integridad transaccional, soporte de consultas geoespaciales, aislamiento seguro multi-tenant y respaldos continuos (manteniendo SQLite para desarrollo y pruebas locales).

---

## 2. Ecosistema de Canales y Aplicaciones

El ecosistema opera de manera unificada compartiendo la base de datos PostgreSQL institucional de Petroil y los servicios centrales de geocodificación y despacho:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           ECOSISTEMA INTEGRAL DE VENTA Y DESPACHO                               │
├───────────────────────────────┬───────────────────────────────┬─────────────────────────────────┤
│    CANAL CLIENTES (VENTA)     │    TORRE DE CONTROL (WEB)     │     CANAL CHOFERES (CAMPO)      │
├───────────────────────────────┼───────────────────────────────┼─────────────────────────────────┤
│ • WhatsApp Cloud API & Bot IA │ • Dominio Propio Institucional│ • Bot de Telegram Operativo     │
│ • Bot de Telegram con IA      │   (https://control.petroilgas)│   (driver_bot.py)               │
│ • Llamadas telefónicas vía    │ • Servidor FastAPI de alta    │ • Onboarding guiado en chat     │
│   módulo Venta Directa        │   velocidad (Puerto 3000 prod)│ • Control de Asistencia y Turnos│
│ • Teclados y menús interactivos│ • Dashboard KPIs en vivo      │   (Entrada, Pausa, Salida)      │
│ • Catálogo y precios en vivo  │ • Mesa de Agenda (T-30 min)   │ • Auditoría de odómetro y tanque│
│ • Libreta Multi-Dirección     │ • Grid de Pedidos con filtros │   con fotografía obligatoria    │
│ • Geolocalización y GPS       │ • Reasignación en caliente    │ • Recepción de viajes con GPS   │
│ • Validación Horario Atención │   con Push a Telegram/WhatsApp│ • Navegación directa en 1 toque │
│ • Confirmación obligatoria    │ • Bitácora de Rechazos/Motivos│   (Waze y Google Maps)          │
│ • Encuestas CSAT (1-5 ⭐)     │ • CRUD Pipas vs Camionetas    │ • Botones Aceptar / Rechazar    │
│                               │ • Venta Directa / Call Center │ • Reporte de Cobro y Entrega    │
│                               │ • Modo Claro / Modo Oscuro    │                                 │
│                               │ • Exportador Excel (4 hojas)  │                                 │
└───────────────────────────────┴───────────────────────────────┴─────────────────────────────────┘
```

---

## 3. Entidades Principales del Dominio

1. **Cliente (`CUSTOMERS`)**: Usuario registrado en el sistema identificado prioritariamente por su número de teléfono celular limpio de 10 dígitos y su canal de procedencia (WhatsApp, Telegram, Teléfono / Call Center, Web).
2. **Dirección del Cliente (`CUSTOMER_ADDRESSES`)**: Libreta multi-dirección vinculada a cada cliente. Almacena calle, número, colonia, referencias de fachada/entre calles, alias (`Casa Principal`, `Local Centro`, etc.), bandera de dirección predeterminada (`is_default`) y coordenadas geográficas (`lat`, `lng`).
3. **Chofer / Operador (`DRIVERS`)**: Operador de reparto registrado con nombre, teléfono, identificador de Telegram (`telegram_user_id`), unidad vehicular asignada (`vehicle_id`), estatus de disponibilidad (`is_available`), estado operativo (`disponible`, `en_entrega`, `fuera_servicio`), calificación promedio CSAT, total de entregas y última ubicación GPS reportada (`current_lat`, `current_lng`).
4. **Vehículo / Unidad de Reparto (`VEHICLES`)**: Registro formal del inventario vehicular de Petroil clasificado estrictamente en:
   - **Pipas de Gas Estacionario:** Con capacidad medida en **Litros** (ej. 5,000 L, 8,000 L).
   - **Camionetas de Cilindros:** Con capacidad medida en **número de tanques/cilindros** (ej. 30, 40, 50 tanques).
   - Registra además placas, modelo, chofer asignado y estatus operativo (`activa`, `mantenimiento`, `inactiva`).
5. **Turnos de Chofer (`DRIVER_SHIFTS`)**: Bitácora de asistencia que registra hora de entrada (`check_in_at`), hora de salida (`check_out_at`), duración neta trabajada en minutos, lecturas iniciales/finales y estado del turno.
6. **Lecturas de Tanque y Odómetro (`TANK_READINGS`)**: Auditoría física que almacena el tipo de lectura (`inicio_turno`, `fin_turno`, `recarga_planta`), porcentaje de gas LP, odómetro en km, ruta de la fotografía de evidencia (`uploads/tank_readings/`) y notas.
7. **Catálogo de Productos (`PRODUCTS`)**: Presentaciones oficiales de Gas LP activas para el tenant (Cilindros de 10 kg, 20 kg, 30 kg, 45 kg y Litro Estacionario), precio unitario en MXN, categoría, existencia (`in_stock`), y banderas de promoción.
8. **Pedido (`ORDERS`)**: Orden formal de compra generada tras la confirmación explícita del cliente o captura en Call Center. Registra cliente, dirección completa, coordenadas de entrega (`delivery_lat`, `delivery_lng`), horario solicitado (`delivery_schedule`), fecha pactada (`scheduled_for`), método de pago (`Efectivo`, `Terminal / Tarjeta`), total en MXN, chofer asignado (`driver_id`), notas y estatus operativo.
9. **Partidas del Pedido (`ORDER_ITEMS`)**: Desglose de cada producto solicitado dentro de la orden, cantidad, precio unitario y subtotal.
10. **Rechazo / Incidencia de Chofer (`ORDER_REJECTIONS`)**: Registro auditable generado cuando un chofer rechaza un viaje asignado. Almacena el `order_id`, `driver_id`, nombre del chofer, motivo estructurado del rechazo (*Falla mecánica*, *Desabasto*, *Tráfico pesado*, etc.) y estado de resolución para seguimiento en la Torre de Control.
11. **Calificación y Encuesta de Satisfacción (`ORDER_RATINGS`)**: Evaluación del servicio (1 a 5 estrellas) y comentarios libres enviados por el cliente al completarse la entrega.

---

## 4. Flujos Operativos y Ciclos de Vida

### 4.1. Ciclo de Vida del Pedido

El pedido transita por la siguiente máquina de estados formal:

```
  [Conversación IA / Llamada] ──► [Confirmado (confirmed)] ──► [Asignado (assigned)] ──► [En Ruta (in_route)] ──► [Entregado (delivered)]
                                           │                           │                        │                          │
                                           │                           ├────────────────────────┼──► [Rechazado]           ▼
                                           │                           │                        │          │        [Encuesta CSAT ⭐]
                                           ▼                           ▼                        ▼          ▼
                                      [Cancelado]                 [Cancelado]              [Cancelado] [Reasignación Torre]
                                           │
                                           └──► [Programado para fecha/hora posterior (scheduled)]
                                                       │
                                                       ▼ (Al llegar a T-30 minutos del deadline)
                                              [Activación Automática a Mesa Activa]
```

* **Conversación IA / Resumen Previo:** El cliente interactúa con el bot seleccionando productos y dirección. La orden **no existe en la base de datos** hasta que el cliente o el despachador pulsa `[ ✅ Confirmar pedido ]`.
* **Confirmado (`confirmed`):** Pedido formalmente creado con folio identificador (#ID).
* **Programado (`scheduled`):** Pedido cuya fecha u hora de entrega corresponde a un horario posterior. Permanece en la Mesa de Agenda.
* **Activación Automática (Regla T-30 min):** Al llegar a 30 minutos antes de la hora pactada, el sistema transfiere automáticamente el pedido a la cola de despacho activo.
* **Asignado (`assigned`):** El motor de despacho logístico ([`src/services/dispatch.py`](file:///c:/Users/Prestamo%20ASKE/Desktop/prueba-2-lapp/langgraph-sales-agent/src/services/dispatch.py)) calcula mediante la fórmula de Haversine el chofer disponible más cercano y envía la tarjeta de viaje a su bot.
* **En Ruta (`in_route`):** El chofer presiona `[ ✅ Aceptar Viaje ]` e inicia el traslado asistido por Waze o Google Maps.
* **Rechazado (`rejected_by_driver`):** Si el chofer no puede atender el viaje, pulsa `[ ❌ Rechazar ]` indicando el motivo exacto. El pedido pasa a este estado y se registra en `ORDER_REJECTIONS`, alertando a la Torre de Control para reasignación manual inmediata.
* **Entregado (`delivered`):** El chofer arriba al domicilio, efectúa el suministro de gas, cobra el importe y presiona `[ 📦 Marcar como Entregado ]`. El sistema dispara la encuesta CSAT al cliente.
* **Cancelado (`cancelled`):** Anulado por el cliente (mediante el botón inline `[ ❌ Cancelar Pedido #ID ]`) o cancelado manualmente por el operador de la Torre de Control con registro del motivo.

---

## 5. Reglas de Negocio Confirmadas

### 5.1. Conversión de Tarifas y Catálogo Dinámico
* **Precios en Base de Datos:** Los precios de cilindros y litro estacionario se leen en tiempo real de la base de datos PostgreSQL institucional de Petroil.
* **Cilindros:** Venta por unidad entera con precios cerrados (ej. Cilindro 30 kg = $670.00 MXN).
* **Estacionario:** Cotización en pesos o litros con conversión exacta a la tarifa configurada (ej. $12.50 MXN / Litro).
* **Actualización Centralizada:** Cualquier ajuste de precios se realiza directamente desde la Torre de Control Web y toma efecto inmediato en los canales de venta.

### 5.2. Horarios de Atención Comercial y Operativa
* **Ventanas de Servicio:** El sistema cuenta con soporte para validar horarios de atención (parámetros configurables actualmente en definición / TBD por la directiva de Petroil).
* **Gestión Fuera de Horario:** Si un cliente intenta realizar un pedido fuera del horario comercial, el asistente de IA le informa cordialmente los horarios hábiles y le ofrece programar su entrega (`scheduled`) para el inicio del siguiente turno hábil.

### 5.3. Identificación Estricta del Cliente y Libreta Multi-Dirección
* **Validación a 10 Dígitos:** La búsqueda de clientes se realiza depurando el número a 10 dígitos numéricos limpios.
* **Clientes Frecuentes vs. Nuevos:** Si el cliente ya existe, el bot le presenta de inmediato sus domicilios anteriores como botones interactivos (`[ 🏠 Casa Principal... ]`, `[ ➕ Nueva Dirección ]`). Si es nuevo, solicita amablemente nombre y domicilio.
* **Confirmación de Domicilio:** Siempre se ofrece confirmación visual antes de avanzar al método de pago.

### 5.4. Operación de Choferes, Turnos y Control de Combustible
* **Control de Asistencia:** El chofer debe iniciar turno con lectura de odómetro y porcentaje de tanque con fotografía obligatoria.
* **Disponibilidad:** Un chofer solo puede recibir viajes si su estado es `Disponible` (`is_available = 1`).
* **Navegación Externa:** Las tarjetas de despacho integran enlaces dinámicos con formato URI universal para apertura nativa:
  - Google Maps: `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}`
  - Waze: `https://waze.com/ul?ll={lat},{lng}&navigate=yes`

### 5.5. Torre de Control en Dominio Propio y Reasignación en Caliente
* **Dominio Institucional Seguro:** Acceso mediante dominio corporativo con certificados TLS/SSL válidos y roles de acceso.
* **Reasignación sin Bloqueos:** El operador puede reasignar un pedido a cualquier chofer activo con un clic. Esta acción actualiza el pedido y genera una tarea en segundo plano (`BackgroundTasks`) que envía la tarjeta completa con botones de navegación al bot del nuevo chofer asignado.

### 5.6. Exportación Ejecutiva y Auditoría de Datos
* **Reportes en Excel:** El sistema integra generación nativa de libros `.xlsx` con tipografía, encabezados corporativos, bordes y formatos contables mediante `openpyxl`, permitiendo auditorías de ventas, incidencias de choferes, directorio de clientes y desempeño operativo.
