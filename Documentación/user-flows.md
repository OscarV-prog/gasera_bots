# User Flows & Navigation — Ecosistema Digital Gasera (Gas a tu Puerta)

**Cliente:** Grupo Petroil — División Gas (Mazatlán, Sinaloa)  
**Versión:** 3.5.0 Enterprise — Consolidada con la Arquitectura Real Implementada (LangGraph AI Sales Agent, Omnicanalidad WhatsApp/Telegram/Call Center, PostgreSQL Corporativo Petroil, Torre de Control Web en Dominio Propio & Despacho Haversine)  
**Estado:** Documento Maestro de Flujos de Usuario Aprobado y Vigente  
**Fuentes Oficiales de Verdad:** `product-context.md` v3.5, `prd.md` v3.5, `architecture.md` v3.5 y Código Fuente del Repositorio  
**Fecha:** Septiembre 2026  

---

## 1. Propósito

El presente documento define la arquitectura de navegación, flujos de interacción y secuencias operativas del ecosistema **Gas a Tu Puerta - Petroil**, estructurado bajo el patrón canónico:
$$\text{ACTOR} \longrightarrow \text{ENTRADA} \longrightarrow \text{CANAL / PANTALLA} \longrightarrow \text{ACCIÓN} \longrightarrow \text{DECISIÓN} \longrightarrow \text{RESULTADO OPERATIVO}$$

Este artefacto refleja la operación real del sistema:
* **Canal Clientes Omnicanal:** Agente conversacional con IA (LangGraph + DeepSeek v3) en **WhatsApp** y **Telegram** con teclados interactivos, validación de horarios de atención y encuestas CSAT.
* **Canal Telefónico y Mostrador:** Módulo de Venta Directa en la Torre de Control Web (`➕ Levantar Pedido`) para captura ágil de llamadas de call center.
* **Canal Choferes:** Bot operativo en Telegram (`driver_bot.py`) con control de asistencia (odómetro y foto obligatoria), tarjetas de viaje GPS y enlaces directos a **Google Maps** y **Waze**.
* **Torre de Control Web (Dominio Propio Institucional):** Consola administrativa SPA servida en `https://control.petroilgas.com` con monitoreo en vivo, mesa de agenda con activación automática a **T-30 minutos**, reasignación en caliente con push, bitácora de rechazos, control de pipas vs camionetas y descarga de reportes Excel (`openpyxl`).

---

## 2. Mapa General de Flujos del Ecosistema

```mermaid
graph TD
    subgraph "1. Captación de Pedidos (Omnicanal)"
        C_Digital[Cliente en WhatsApp / Telegram] --> C_Chat[Interacción con Agente IA]
        C_Chat --> C_Svc[Paso 0: Tipo de Servicio]
        C_Svc --> C_Prod[Paso 1: Catálogo y Precios Reales PostgreSQL]
        C_Prod --> C_Qty[Paso 2: Selección de Cantidad]
        C_Qty --> C_Phone[Paso 3: Teléfono 10 dígitos / Reconocimiento]
        C_Phone --> C_Addr[Paso 4: Dirección Guardada o GPS/Texto]
        C_Addr --> C_Hours{¿Dentro de Horario de Atención?}
        C_Hours -->|No| C_OffHours[Informa horario y programa entrega para siguiente turno]
        C_Hours -->|Sí| C_Sched[Paso 5: Horario Inmediato o Programado]
        C_OffHours --> C_Pay[Paso 6: Método de Pago]
        C_Sched --> C_Pay
        C_Pay --> C_Summary[Paso 7: Resumen Financiero y Confirmación Obligatoria]
        C_Summary -->|Confirmar| C_OrderCreated[Pedido Creado #Folio]

        C_Call[Cliente por Teléfono / Mostrador] --> CC_Desk[Operadora en Torre de Control Web]
        CC_Desk --> CC_Modal[Modal: ➕ Levantar Pedido]
        CC_Modal --> C_OrderCreated
    end

    subgraph "2. Motor de Despacho & Mesa de Agenda"
        C_OrderCreated --> OrderType{¿Inmediato o Programado?}
        OrderType -->|Programado > 30 min| AgendaQueue[Mesa de Agenda: Estado scheduled]
        AgendaQueue -->|Llega a T-30 minutos| AutoActive[Activación Automática a confirmed]
        OrderType -->|Inmediato| D_Geo[Geocodificación Nominatim]
        AutoActive --> D_Geo
        D_Geo --> D_Hav[Cálculo de Proximidad Haversine]
        D_Hav --> D_Assign[Asignación automática a Chofer más cercano]
    end

    subgraph "3. Operación en Campo (Canal Choferes)"
        D_Assign --> DRV_Alert[Alerta Push en Telegram con Tarjeta GPS]
        DRV_Alert --> DRV_Decide{¿Acepta el viaje?}
        DRV_Decide -->|Aceptar| DRV_Route[En Ruta: Abre Google Maps o Waze]
        DRV_Decide -->|Rechazar| DRV_Reject[Captura motivo en ORDER_REJECTIONS]
        DRV_Route --> DRV_Deliver[Arribo, Cobro y Marcar como Entregado]
        DRV_Deliver --> DRV_CSAT[Disparo de Encuesta CSAT ⭐ al Cliente]
    end

    subgraph "4. Supervisión y Resiliencia (Torre de Control en Dominio Propio)"
        DRV_Reject --> TC_Alert[Alerta en Torre de Control /admin]
        TC_Alert --> TC_Reassign[Reasignación Manual en Caliente en 1 Clic]
        TC_Reassign -->|Push en Background| DRV_Alert
        TC_Monitor[Monitoreo de KPIs, Flota y Turnos]
        TC_Excel[Exportación de Libro Maestro Excel]
    end
```

---

# PARTE 1: FLUJOS DEL CANAL CLIENTES (WHATSAPP & TELEGRAM BOT CON IA)

---

## 3. Flujo C-01: Ciclo de Compra Guiado con Menús Interactivos

### 3.1. Resumen del Flujo
El cliente solicita gas por WhatsApp o Telegram. El asistente IA analiza el mensaje y despliega teclados interactivos sin exigir escritura manual en pasos estructurados.

### 3.2. Paso a Paso Detallado

```
Paso 0: Bienvenida & Tipo de Servicio
 ├─ Bot: "¡Hola! Bienvenido a Gas a Tu Puerta - Petroil ⛽ ¿Qué servicio necesitas hoy?"
 └─ Botones: [ 🛢️ Cilindros ]  [ 🔥 Tanque Estacionario ]

Paso 1: Catálogo y Precios Reales
 ├─ (Si seleccionó Cilindros): Consulta PostgreSQL para tenant 'petroil'.
 └─ Botones:
     [ 🟢 Cilindro de 30 kg — $670 MXN ]
     [ 🔵 Cilindro de 20 kg — $450 MXN ]
     [ 🟡 Cilindro de 45 kg — $1,010 MXN ]
     [ ⚪ Cilindro de 10 kg — $230 MXN ]

Paso 2: Selección Ágil de Cantidad
 ├─ (Si cilindros): Botones: [ 1 ]  [ 2 ]  [ 3 ]  [ 4 ]  [ ✍️ Otra cantidad ]
 └─ (Si estacionario): Botones: [ $300 ]  [ $500 ]  [ $1,000 ]  [ Tanque Lleno ]  [ ✍️ Otro monto ]

Paso 3: Identificación Telefónica y Reconocimiento
 ├─ Bot: "Por favor indícame tu número celular a 10 dígitos."
 └─ Cliente escribe: "6699123501" -> Sistema depura y ejecuta 'customer_info'.

Paso 4: Libreta de Direcciones o Nueva Dirección
 ├─ Si cliente frecuente:
 │   Bot: "¡Qué gusto saludarte de nuevo, Oscar! ¿A cuál de tus domicilios enviamos tu gas?"
 │   Botones:
 │     [ 🏠 Casa Principal: Mision San Javier 5246... ]
 │     [ 🏢 Local Centro: Ángel Flores 101... ]
 │     [ ➕ Ingresar Nueva Dirección ]
 └─ Si cliente nuevo o selecciona 'Nueva Dirección':
     Botones: [ ✍️ Escribir dirección ]  [ 📍 Enviar ubicación GPS ]

Paso 5: Validación de Horario de Atención y Programación
 ├─ Si dentro de horario:
 │   Botones: [ ⚡ Lo antes posible ]  [ 🕐 Hoy por la tarde ]  [ 📅 Mañana ]
 └─ Si fuera de horario (configuración TBD):
     Bot: "Nuestro horario de atención ha concluido por hoy. ¿Deseas agendar tu pedido para mañana a primera hora?"
     Botones: [ 📅 Agendar para Mañana a las 8:00 AM ]  [ ✏️ Elegir otra hora ]

Paso 6: Método de Pago
 ├─ Bot: "¿Cómo deseas realizar tu pago?"
 └─ Botones: [ 💵 Efectivo ]  [ 💳 Tarjeta (Terminal) ]

Paso 7: Resumen Financiero y Confirmación Obligatoria Previa
 ├─ Bot:
 │   "📋 Resumen de tu pedido:
 │    • 1x Cilindro de Gas LP 30 kg — $670.00 MXN
 │    👤 Cliente: Oscar Vizcarra Sánchez
 │    📍 Dirección: Mision San Javier 5246, Fracc. Misiones
 │    📅 Horario: Lo antes posible
 │    💰 Total a Pagar: $670.00 MXN (💵 Efectivo)
 │
 │    ¿Tus datos son correctos?"
 └─ Botones:
     [ ✅ Confirmar pedido ]   [ ✏️ Modificar pedido ]   [ ❌ Cancelar ]

Paso 8: Creación de Pedido y Seguimiento
 ├─ Al presionar [ ✅ Confirmar pedido ]:
 │   1. Se ejecuta tool 'create_order' -> inserta en ORDERS y ORDER_ITEMS con folio (#ID).
 │   2. Dispara despacho automático Haversine hacia el chofer más cercano.
 │   3. Responde al cliente con folio y botón persistente:
 └─ Botón: [ ❌ Cancelar Pedido #35 ]

Paso 9: Encuesta de Satisfacción CSAT
 └─ Al completarse la entrega (delivered), el bot envía:
     "¡Tu servicio ha sido completado! ⭐ ¿Cómo calificarías la atención de tu chofer?"
     Botones: [ ⭐ ] [ ⭐⭐ ] [ ⭐⭐⭐ ] [ ⭐⭐⭐⭐ ] [ ⭐⭐⭐⭐⭐ ]
```

---

# PARTE 2: FLUJO DE VENTA TELEFÓNICA / CALL CENTER (TORRE DE CONTROL)

---

## 4. Flujo CC-01: Captura Rápida de Llamadas Telefónicas

```mermaid
graph TD
    CallIn[Cliente llama al teléfono de Petroil] --> AgentDesk[Operadora atiende la llamada]
    AgentDesk --> OpenModal[Abre modal '➕ Levantar Pedido' en https://control.petroilgas.com]
    OpenModal --> SearchPhone[Ingresa número de 10 dígitos]
    SearchPhone --> AutoFill{¿Cliente registrado?}
    AutoFill -->|Sí| FillData[Autocompleta nombre y direcciones registradas]
    AutoFill -->|No| EnterData[Captura nombre y nueva dirección]
    FillData & EnterData --> SelectItems[Selecciona productos y cantidades]
    SelectItems --> SetSchedule[Selecciona horario: Inmediato o Programado]
    SetSchedule --> SelectPay[Selecciona método de pago: Efectivo o Tarjeta]
    SelectPay --> DispatchOpt{Tipo de Asignación}
    DispatchOpt -->|Automático| AutoHav[Despacho inteligente por cercanía Haversine]
    DispatchOpt -->|Directo| PickDriver[Selecciona chofer específico de la lista]
    DispatchOpt -->|Pendiente| HoldQueue[Queda en cola de pedidos sin chofer]
    AutoHav & PickDriver & HoldQueue --> SaveOrder[Guarda orden en PostgreSQL y emite confirmación]
```

---

# PARTE 3: FLUJOS DEL CANAL CHOFERES (TELEGRAM BOT)

---

## 5. Flujo D-01: Control de Turno con Odómetro y Fotografía de Evidencia

```mermaid
graph TD
    Start[Chofer abre driver_bot.py] --> RegCheck{¿Registrado?}
    RegCheck -->|No| Onboarding[Captura Nombre, Teléfono, Unidad, Placas]
    Onboarding --> MenuTurno[Menú de Turnos]
    RegCheck -->|Sí| MenuTurno

    MenuTurno --> B_Start[Presiona: Iniciar Turno]
    B_Start --> PromptOdo[Solicita Odómetro inicial en km]
    PromptOdo --> PromptGas[Solicita Porcentaje de Tanque/Gas LP]
    PromptGas --> PromptPhoto[Solicita FOTOGRAFÍA obligatoria del medidor]
    PromptPhoto --> SaveShift[Guarda en uploads/tank_readings/ y DRIVER_SHIFTS]
    SaveShift --> StateAvail[is_available = 1 / Habilitado para despacho]

    StateAvail --> WorkFlow[Recibe Viajes Asignados]
    WorkFlow --> B_Pause[Presiona: Pausar Turno]
    B_Pause --> StatePause[is_available = 0 / Temporalmente inactivo]
    StatePause --> B_Resume[Presiona: Reanudar] --> StateAvail

    WorkFlow --> B_End[Presiona: Terminar Turno]
    B_End --> EndReading[Solicita odómetro final, porcentaje y foto de cierre]
    EndReading --> CalcDuration[Calcula minutos trabajados y cierra turno en DRIVER_SHIFTS]
```

---

## 6. Flujo D-02: Recepción, Navegación y Entrega de Viajes

```mermaid
graph TD
    Alert[Notificación de Viaje en Telegram] --> ReviewCard[Revisa Folio, Dirección, Teléfono, Total y Productos]
    ReviewCard --> Choice{Decisión del Chofer}

    Choice -->|Rechazar| PromptReason[Selecciona motivo de rechazo: Falla mecánica, Desabasto, Tráfico...]
    PromptReason --> SaveRejection[Guarda en ORDER_REJECTIONS y pasa a rejected_by_driver]
    SaveRejection --> NotifyTC[Alerta en Torre de Control Web para reasignación en 1 clic]

    Choice -->|Aceptar Viaje| AcceptOrder[Estatus: in_route]
    AcceptOrder --> NavOptions[Botones de Navegación Externa]
    NavOptions -->|Tap Google Maps| OpenGMaps[Abre Google Maps en modo navegación]
    NavOptions -->|Tap Waze| OpenWaze[Abre Waze con coordenadas exactas]

    OpenGMaps & OpenWaze --> Arrival[Llegada a Domicilio del Cliente]
    Arrival --> Discharge[Suministro físico de gas y Cobro]
    Discharge --> TapDeliver[Presiona: Marcar como Entregado]
    TapDeliver --> FinalStatus[Estatus: delivered / Chofer liberado / Disparo de CSAT al cliente]
```

---

# PARTE 4: FLUJOS DE LA TORRE DE CONTROL WEB (DOMINIO PROPIO)

---

## 7. Flujo TC-01: Monitoreo y Reasignación en Caliente

```mermaid
graph TD
    LoginTC[Operador entra a https://control.petroilgas.com] --> LoadKPIs[Carga métricas en tiempo real /api/admin/metrics]
    LoadKPIs --> ViewGrid[Visualiza Tablero de Pedidos Activos]
    ViewGrid --> FilterSearch[Filtra por estado o busca por cliente/folio]

    FilterSearch --> Incident{¿Hay orden rechazada o chofer averiado?}
    Incident -->|No| NormalMonitoring[Monitoreo continuo y auditoría]
    Incident -->|Sí| ClickReassign[Clic en botón '🛻 Reasignar' del pedido]

    ClickReassign --> OpenModal[Modal: Selecciona nuevo chofer de lista activa]
    OpenModal --> ConfirmReassign[Presiona: Confirmar Reasignación]
    ConfirmReassign --> API_Post[POST /api/admin/orders/{id}/reassign]
    API_Post --> DB_Update[Actualiza driver_id en PostgreSQL]
    API_Post --> BkgTask[FastAPI BackgroundTasks: Envía tarjeta con GPS a Telegram/WhatsApp del nuevo Chofer]
    BkgTask --> DriverAlert[El nuevo chofer recibe la alerta en < 2 segundos]
    DB_Update --> GridRefreshed[Tablero actualizado en tiempo real]
```

---

## 8. Flujo TC-02: Mesa de Agenda Programada (Regla T-30 Minutos)

```mermaid
graph TD
    ViewAgenda[Operador ingresa a pestaña 'Agenda' en Torre de Control] --> LoadAgenda[Carga pedidos en estado 'scheduled']
    LoadAgenda --> Timers[Visualiza temporizadores de cuenta regresiva: '🕒 Faltan 2h 15m']
    
    Timers --> AutoEvent{¿Faltan 30 min para el deadline?}
    AutoEvent -->|Sí| AutoPromote[El motor transfiere el pedido a estado 'confirmed' y detona despacho Haversine]
    
    Timers --> ManualAction{Acción del Operador}
    ManualAction -->|Pase Directo| PassNow[Presiona '⚡ Pasar a Pedidos Ya' -> Activación inmediata]
    ManualAction -->|Reprogramar| Resched[Presiona '✏️ Reprogramar' -> Modifica fecha y hora pactada]
```

---

## 9. Flujo TC-03: Generación y Descarga de Reportes Excel (.xlsx)

```mermaid
graph TD
    TC_Panel[Panel de Control Web /admin] --> ReportBar[Barra de Exportación de Reportes]
    ReportBar --> UserChoice{Selección del Reporte}

    UserChoice -->|Reporte Maestro (4 Hojas)| ReqMaster[GET /api/admin/reports/excel/master]
    UserChoice -->|Pedidos y Ventas| ReqOrders[GET /api/admin/reports/excel/orders]
    UserChoice -->|Incidencias y Rechazos| ReqRej[GET /api/admin/reports/excel/rejections]
    UserChoice -->|Flota y Choferes| ReqDrivers[GET /api/admin/reports/excel/drivers]
    UserChoice -->|Directorio Clientes| ReqCust[GET /api/admin/reports/excel/customers]

    ReqMaster & ReqOrders & ReqRej & ReqDrivers & ReqCust --> SvcExcel[openpyxl procesa datos de PostgreSQL en memoria BytesIO]
    SvcExcel --> StreamDown[StreamingResponse con cabecera application/vnd.openxmlformats]
    StreamDown --> BrowserSave[Navegador descarga archivo .xlsx formateado inmediatamente]
```
