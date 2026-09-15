# Architecture Design Document (ADD) — Ecosistema Gasera (Gas a tu Puerta)

**Cliente:** Grupo Petroil — División Gas (Mazatlán, Sinaloa)  
**Versión:** 3.5.0 Enterprise — Sincronizada con la Arquitectura Real Implementada (LangGraph AI Sales Agent, Omnicanalidad WhatsApp/Telegram/Call Center, PostgreSQL Corporativo Petroil, Torre de Control Web en Dominio Propio, Despacho Haversine & Reportes Excel)  
**Estado:** Documento de Arquitectura Aprobado y Operativo  
**Fuentes Oficiales de Verdad:** `product-context.md` v3.5, `prd.md` v3.5 y Código Fuente del Repositorio  
**Fecha:** Septiembre 2026  

---

## Control de Versiones del Documento

| Versión | Fecha | Autor | Descripción del Cambio | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **1.0.0** | 07/08/2026 | Winston (System Architect) | Estrategia inicial teórica y modelado C4 Nivel 1 y 2. | Superado |
| **2.0.0** | 10/08/2026 | Winston (System Architect) | Modelo de datos conceptual y diseño relacional preliminar. | Superado |
| **3.0.0** | 02/09/2026 | Antigravity AI & Equipo Petroil | Sincronización inicial con LangGraph, bots de Telegram y Torre de Control Web. | Superado |
| **3.5.0** | 09/09/2026 | Antigravity AI & Equipo Petroil | **Alineación Integral con la Arquitectura Empresarial de Producción:**<br>• Despliegue en Dominio Propio: BackOffice Web configurado en dominio institucional de Petroil (HTTPS / TLS 1.3), descartando localhost en producción.<br>• Persistencia en PostgreSQL Corporativo: Base de datos PostgreSQL propia de Petroil con soporte relacional, índices espaciales y transacciones ACID.<br>• Omnicanalidad: Integración de WhatsApp Cloud API, Telegram Bots y Módulo de Venta Directa / Call Center.<br>• Módulo de Horarios de Atención: Interceptor de horarios comerciales con agendamiento automático.<br>• Motor de Agenda Programada: Promoción automática a mesa activa a **T-30 minutos**.<br>• Esquema Extendido: Tablas `VEHICLES`, `DRIVER_SHIFTS`, `TANK_READINGS`, `ORDER_RATINGS` y `ORDER_REJECTIONS`. | **Aprobado / Vigente** |

---

# PARTE 1: ESTRATEGIA ARQUITECTÓNICA Y MODELADO C4

---

## 1. Objetivos de la Arquitectura

El propósito de la arquitectura del ecosistema **Gas a Tu Puerta - Petroil** es proporcionar una solución integral, de alto rendimiento, escalable y con alta disponibilidad para la venta, captura omnicanal y despacho logístico de Gas LP en Mazatlán.

Los pilares arquitectónicos implementados son:
1. **Atención Conversacional Omnicanal con IA:** Orquestación de grafos conversacionales mediante **LangGraph** y LLM (**DeepSeek v3** vía OpenRouter), combinada con **WhatsApp Cloud API** y **Telegram Inline Keyboards** para guiar al cliente de manera estructurada en productos, precios, direcciones y pagos.
2. **Canal Telefónico y Call Center Integrado:** Módulo de Venta Directa en la Torre de Control Web para captura rápida de llamadas telefónicas y pedidos presenciales.
3. **Operación en Campo Ligera y Universal:** Bot de Telegram para Choferes (`driver_bot.py`) con control de asistencia (check-in/out con odómetro y foto de tanque), recepción de viajes con tarjeta GPS y navegación en **Waze** y **Google Maps**.
4. **Torre de Control Web en Dominio Institucional Propio:** Servidor backend en **FastAPI** (`src/app.py`) montando una SPA moderna servida bajo un dominio corporativo seguro de Petroil (ej. `https://control.petroilgas.com` / `https://backoffice.petroil.com.mx`), con soporte de temas Claro/Oscuro y diseño 100% responsivo.
5. **Despacho Logístico Inteligente y Agenda Automatizada:** Geocodificación precisa con OpenStreetMap (Nominatim), cálculo de proximidad Haversine y mesa de agenda con activación automática a **T-30 minutos** antes del deadline.
6. **Persistencia Empresarial en PostgreSQL de Petroil:** Almacenamiento relacional, seguro y transaccional alojado en la infraestructura corporativa de PostgreSQL de Grupo Petroil.
7. **Reportes Ejecutivos en Memoria:** Servicio de generación automatizada de libros de cálculo Excel (`.xlsx`) mediante `openpyxl` con streaming no bloqueante (`io.BytesIO`).

---

## 2. Diagramas C4 del Sistema

### 2.1. C4 — Nivel 1: Diagrama de Contexto del Sistema

```mermaid
graph TD
    User_Digital[Cliente Digital: WhatsApp / Telegram] -->|Chat con IA / Botones Interactivos| Sys[Ecosistema Gas a Tu Puerta - Petroil]
    User_Phone[Cliente Telefónico / Mostrador] -->|Llamada Telefónica / Presencial| CallCenter[Operadora Call Center]
    CallCenter -->|Módulo Venta Directa| Sys
    Driver[Chofer / Operador en Campo] -->|Telegram Bot / Turnos / Fotos / GPS| Sys
    Admin[Supervisor / Despachador en Oficina] -->|Navegador Web / Dominio Propio Petroil| Sys

    Sys -->|Inferencia LLM| OpenRouter[OpenRouter API / DeepSeek v3]
    Sys -->|Geocodificación Satelital| Nominatim[OpenStreetMap / Nominatim API]
    Sys -->|Navegación Móvil| NavApps[Google Maps / Waze]
    Sys -->|Persistencia Corporativa| PostgresDB[(Base de Datos PostgreSQL Petroil)]
    Sys -->|Archivos XLSX| ExcelViewer[Microsoft Excel / Suite Ofimática]
```

---

### 2.2. C4 — Nivel 2: Diagrama de Contenedores

```mermaid
graph TD
    subgraph "Clientes y Canales de Captación"
        WA_Client[Cliente en WhatsApp]
        TG_Client[Cliente en Telegram]
        Call_Client[Cliente por Teléfono]
    end

    subgraph "Personal Operativo y de Campo"
        TG_Driver[Chofer en Telegram Bot]
        Web_Admin[Operador en Torre de Control Web<br>https://control.petroilgas.com]
    end

    subgraph "Infraestructura Backend Petroil (FastAPI / Python 3.11+)"
        Proxy[Nginx / Cloudflare Reverse Proxy<br>HTTPS / TLS 1.3]
        AppServer[FastAPI Server - Puerto 3000<br>src/app.py]
        
        Proxy --> AppServer
        Web_Admin --> Proxy

        AdminRouter[Admin Router REST<br>src/admin/router.py]
        WebhookRouters[Multi-Channel Webhooks<br>src/channels/*]
        
        AppServer --> AdminRouter
        AppServer --> WebhookRouters

        BotClient[Bot de Clientes<br>telegram_bot.py]
        BotDriver[Bot de Choferes<br>driver_bot.py]

        subgraph "Cerebro IA (LangGraph)"
            GraphCore[Sales Agent StateGraph<br>src/graphs/ & src/nodes/]
            ToolRegistry[Tool Registry<br>customer_info, search_products, create_order...]
            GraphCore --> ToolRegistry
        end

        subgraph "Servicios de Negocio (src/services/)"
            UIKeyboards[UI Keyboards Service<br>ui_keyboards.py]
            DispatchSvc[Dispatch Engine<br>dispatch.py]
            GeoSvc[Geocoding & GPS<br>geocoding.py]
            AgendaSvc[Agenda Scheduler T-30<br>dispatch.py]
            ReportSvc[Excel Reports Service<br>reports.py]
            NotifSvc[Notification Service<br>notifications.py]
        end

        subgraph "Capa de Persistencia Empresarial"
            Repo[Data Repository Protocol<br>src/repositories/*]
            PostgresDB[(PostgreSQL Petroil<br>Base de Datos Corporativa)]
            SQLiteDev[(SQLite Local Dev<br>data/sales_agent.db)]
            Repo --> PostgresDB
            Repo -.-> SQLiteDev
        end

        subgraph "Almacenamiento de Evidencias"
            Uploads[(Fotos Medidores / Odómetro<br>uploads/tank_readings/)]
        end
    end

    WA_Client -->|Webhook Cloud API| WebhookRouters
    TG_Client -->|Telegram Bot API| BotClient
    Call_Client -->|Atención Telefónica| Web_Admin
    
    BotClient --> GraphCore
    BotClient --> UIKeyboards
    WebhookRouters --> GraphCore

    ToolRegistry --> Repo
    ToolRegistry --> DispatchSvc

    DispatchSvc --> GeoSvc
    DispatchSvc --> Repo
    DispatchSvc --> NotifSvc

    AgendaSvc --> Repo
    AgendaSvc --> DispatchSvc

    NotifSvc --> TG_Driver
    TG_Driver --> BotDriver
    BotDriver --> Repo
    BotDriver --> Uploads
    BotDriver --> NavApps[Google Maps / Waze]

    AdminRouter --> Repo
    AdminRouter --> NotifSvc
    AdminRouter --> ReportSvc
```

---

# PARTE 2: MODELO DE DATOS Y ESQUEMA RELACIONAL POSTGRESQL

---

## 3. Esquema Relacional de Base de Datos (PostgreSQL Petroil)

La persistencia de datos corporativa opera sobre **PostgreSQL de Petroil**, configurada con llaves foráneas, restricciones de unicidad, índices B-Tree y soporte geoespacial.

### 3.1. Diagrama Entidad-Relación (ERD Completo)

```mermaid
erDiagram
    CUSTOMERS ||--o{ CUSTOMER_ADDRESSES : "tiene"
    CUSTOMERS ||--o{ ORDERS : "realiza"
    CUSTOMERS ||--o{ ORDER_RATINGS : "califica"
    DRIVERS ||--o{ ORDERS : "entrega"
    DRIVERS ||--o{ DRIVER_SHIFTS : "registra"
    DRIVERS ||--o{ TANK_READINGS : "audita"
    DRIVERS ||--o{ ORDER_REJECTIONS : "declina"
    DRIVERS ||--o{ ORDER_RATINGS : "evaluado_en"
    VEHICLES ||--o{ DRIVERS : "asignado_a"
    ORDERS ||--|{ ORDER_ITEMS : "contiene"
    ORDERS ||--o{ ORDER_REJECTIONS : "genera"
    ORDERS ||--o{ ORDER_RATINGS : "recibe"
    PRODUCTS ||--o{ ORDER_ITEMS : "referenciado_en"

    CUSTOMERS {
        int id PK "Autoincremental"
        varchar tenant_id "petroil"
        varchar channel "whatsapp | telegram | phone | web"
        varchar channel_user_id "ID en el canal"
        varchar name "Nombre completo"
        varchar phone UK "10 dígitos limpios"
        varchar address "Dirección principal"
        text notes "Referencias adicionales"
        timestamp created_at "UTC"
        timestamp updated_at "UTC"
    }

    CUSTOMER_ADDRESSES {
        int id PK "Autoincremental"
        int customer_id FK "Referencias CUSTOMERS(id)"
        varchar address "Calle, número y colonia"
        varchar alias "Casa Principal, Local Centro..."
        text notes "Referencias visuales y entre calles"
        int is_default "1 = Sí, 0 = No"
        numeric lat "Latitud GPS"
        numeric lng "Longitud GPS"
        timestamp created_at "UTC"
        timestamp updated_at "UTC"
    }

    VEHICLES {
        int id PK "Autoincremental"
        varchar tenant_id "petroil"
        varchar identifier UK "Unidad M-0258"
        varchar plate UK "Placas vehiculares"
        varchar model "Marca y Modelo"
        varchar vehicle_type "pipa | camioneta"
        numeric capacity_liters "Capacidad en Litros (Pipas)"
        int capacity_cylinders "Capacidad en Tanques (Camionetas)"
        varchar status "activa | mantenimiento | inactiva"
        int driver_id FK "Chofer asignado"
        text notes "Observaciones mecánicas"
        timestamp created_at "UTC"
    }

    DRIVERS {
        int id PK "Autoincremental"
        varchar tenant_id "petroil"
        varchar name "Nombre completo del operador"
        varchar phone "Teléfono de contacto"
        varchar telegram_user_id UK "Chat ID único en Telegram"
        int vehicle_id FK "Referencias VEHICLES(id)"
        varchar vehicle_type "cilindros | estacionario | ambos"
        varchar vehicle_plate "Placas vehiculares"
        varchar zone "Zona asignada (Norte, Sur, Centro...)"
        int is_available "1 = Disponible, 0 = Ocupado / Fuera"
        varchar status "disponible | en_entrega | fuera_servicio"
        numeric current_lat "Última latitud GPS reportada"
        numeric current_lng "Última longitud GPS reportada"
        numeric rating "Calificación promedio CSAT"
        int total_deliveries "Total de entregas completadas"
        timestamp created_at "UTC"
        timestamp updated_at "UTC"
    }

    DRIVER_SHIFTS {
        int id PK "Autoincremental"
        int driver_id FK "Referencias DRIVERS(id)"
        varchar tenant_id "petroil"
        varchar vehicle_plate "Placa de la unidad utilizada"
        timestamp check_in_at "Hora de entrada"
        timestamp check_out_at "Hora de salida"
        varchar initial_reading "Odómetro y combustible inicial"
        varchar final_reading "Odómetro y combustible final"
        int duration_minutes "Minutos netos laborados"
        varchar status "activo | pausado | completado"
    }

    TANK_READINGS {
        int id PK "Autoincremental"
        int driver_id FK "Referencias DRIVERS(id)"
        varchar tenant_id "petroil"
        varchar vehicle_plate "Placas del vehículo"
        varchar reading_type "inicio_turno | fin_turno | recarga"
        numeric fuel_percentage "Porcentaje de gas LP (0-100%)"
        numeric odometer_km "Kilometraje del odómetro"
        varchar photo_path "Ruta de fotografía de evidencia"
        text notes "Observaciones de la lectura"
        timestamp created_at "UTC"
    }

    PRODUCTS {
        varchar id PK "gas-lp-10kg, gas-lp-30kg, estacionario..."
        varchar tenant_id PK "petroil"
        varchar name "Nombre comercial"
        text description "Descripción de presentación"
        numeric price "Precio unitario en MXN"
        varchar currency "MXN"
        varchar category "cilindros | estacionario"
        int in_stock "1 = En existencia, 0 = Agotado"
        int is_promoted "1 = Promoción activa, 0 = Regular"
        varchar promotion_text "Texto promocional"
        timestamp created_at "UTC"
    }

    ORDERS {
        int id PK "Folio numérico autoincremental"
        varchar tenant_id "petroil"
        int customer_id FK "Referencias CUSTOMERS(id)"
        int driver_id FK "Referencias DRIVERS(id)"
        varchar customer_name "Nombre del cliente"
        varchar customer_phone "Teléfono celular (10 dígitos)"
        varchar delivery_address "Dirección de entrega"
        varchar delivery_schedule "Lo antes posible | Programado"
        timestamp scheduled_for "Fecha/Hora pactada (Agenda)"
        numeric total_amount "Total a cobrar en MXN"
        varchar currency "MXN"
        varchar status "confirmed | scheduled | assigned | in_route | delivered | rejected_by_driver | cancelled"
        varchar payment_method "Efectivo | Terminal / Tarjeta"
        text notes "Referencias e indicaciones"
        varchar channel "whatsapp | telegram | phone | web"
        varchar channel_user_id "ID de usuario en el canal"
        numeric delivery_lat "Latitud de entrega"
        numeric delivery_lng "Longitud de entrega"
        timestamp assigned_at "Timestamp de asignación"
        timestamp delivered_at "Timestamp de entrega"
        timestamp created_at "Timestamp de creación"
        timestamp updated_at "Timestamp de actualización"
    }

    ORDER_ITEMS {
        int id PK "Autoincremental"
        int order_id FK "Referencias ORDERS(id)"
        varchar product_id "Identificador del producto"
        varchar product_name "Nombre del producto vendido"
        int quantity "Cantidad de unidades"
        numeric unit_price "Precio unitario al crear orden"
        numeric subtotal "Subtotal en MXN"
    }

    ORDER_REJECTIONS {
        int id PK "Autoincremental"
        varchar tenant_id "petroil"
        int order_id FK "Referencias ORDERS(id)"
        int driver_id FK "Referencias DRIVERS(id)"
        varchar driver_name "Nombre del chofer que declinó"
        varchar reason "Motivo estructurado del rechazo"
        int is_resolved "0 = Pendiente, 1 = Resuelto"
        timestamp created_at "Timestamp de rechazo"
        timestamp resolved_at "Timestamp de reasignación"
        int resolved_by_driver_id FK "Nuevo chofer asignado"
    }

    ORDER_RATINGS {
        int id PK "Autoincremental"
        int order_id FK "Referencias ORDERS(id)"
        int customer_id FK "Referencias CUSTOMERS(id)"
        int driver_id FK "Referencias DRIVERS(id)"
        varchar tenant_id "petroil"
        int rating "Calificación 1 a 5 estrellas"
        text feedback "Comentarios del cliente"
        timestamp created_at "Timestamp de calificación"
    }
```

---

# PARTE 3: ESPECIFICACIÓN DE APIS REST Y WEBHOOKS

---

## 4. Endpoints de la Torre de Control Web (`/api/admin/...`)

### 4.1. Métricas y KPIs del Tablero
* **`GET /api/admin/metrics?tenant_id=petroil`**
  - **Propósito:** Retorna KPIs consolidados en tiempo real.
  - **Payload de Respuesta (200 OK):**
    ```json
    {
      "orders_today": 48,
      "orders_today_pct_change": 14.2,
      "total_revenue_today": 32160.00,
      "revenue_cash": 22400.00,
      "revenue_card": 9760.00,
      "active_orders": 6,
      "active_drivers": 10,
      "drivers_available": 7,
      "drivers_busy": 3,
      "drivers_offline": 2,
      "unresolved_rejections": 1,
      "csat_average": 4.85,
      "csat_total_ratings": 37
    }
    ```

### 4.2. Pedidos, Reasignación y Venta Directa
* **`GET /api/admin/orders?tenant_id=petroil&status={status}&search={query}&limit=200`**
* **`POST /api/admin/orders`** (Módulo Venta Directa / Call Center):
  ```json
  {
    "tenant_id": "petroil",
    "customer_name": "Restaurante El Faro",
    "customer_phone": "6699123501",
    "delivery_address": "Paseo Claussen 45, Col. Centro",
    "delivery_schedule": "Lo antes posible",
    "payment_method": "Efectivo",
    "items": [
      { "product_id": "gas-lp-30kg", "quantity": 2, "unit_price": 670.0 }
    ],
    "dispatch_type": "auto"
  }
  ```
* **`POST /api/admin/orders/{order_id}/reassign`**:
  - Reasigna a nuevo chofer y despacha notificación push asíncrona (`BackgroundTasks`) con Waze/Maps a Telegram/WhatsApp en $<2\text{ s}$.

### 4.3. Mesa de Agenda Programada (Regla T-30 min)
* **`GET /api/admin/agenda?tenant_id=petroil`**: Lista pedidos programados con cálculo de tiempo para activación.
* **`POST /api/admin/orders/{order_id}/activate-now`**: Pase directo a la mesa activa sin esperar el tiempo automático.
* **`PATCH /api/admin/orders/{order_id}/reschedule`**: Reprograma fecha y hora pactada.

### 4.4. Flota de Vehículos (Pipas vs Camionetas)
* **`GET /api/admin/vehicles?tenant_id=petroil`**
* **`POST /api/admin/vehicles`** / **`PUT /api/admin/vehicles/{id}`**
  ```json
  {
    "identifier": "Pipa P-01",
    "plate": "TX-4521-A",
    "model": "International 2024",
    "vehicle_type": "pipa",
    "capacity_liters": 5000.0,
    "capacity_cylinders": null,
    "driver_id": 3,
    "status": "activa"
  }
  ```

### 4.5. Reportes Excel (.xlsx con `openpyxl`)
* **`GET /api/admin/reports/excel/master`**: Descarga Libro Maestro con 4 hojas formateadas.
* **`GET /api/admin/reports/excel/orders`**: Reporte detallado de pedidos.
* **`GET /api/admin/reports/excel/rejections`**: Bitácora de incidencias y motivos.
* **`GET /api/admin/reports/excel/drivers`**: Rendimiento y asistencia de choferes.
* **`GET /api/admin/reports/excel/customers`**: Directorio y domicilios de clientes.

---

# PARTE 4: DESPLIEGUE, INFRAESTRUCTURA Y TOPOLOGÍA DE PRODUCCIÓN

---

## 5. Arquitectura de Despliegue en Dominio Propio

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    TOPOLOGÍA DE PRODUCCIÓN EN DOMINIO PROPIO PETROIL                            │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                 │
│  [ Internet / Usuarios Clientes y Personal ]                                                    │
│         │                                                                                       │
│         ▼                                                                                       │
│  [ Nginx / Traefik Reverse Proxy + Certificados SSL/TLS (Let's Encrypt / Cloudflare) ]          │
│   ├── Dominio Backoffice: https://control.petroilgas.com                                        │
│   ├── Dominio Webhooks:   https://api.petroilgas.com/webhooks/...                               │
│   └── Redirección HTTP -> HTTPS automática                                                      │
│         │                                                                                       │
│         ▼                                                                                       │
│  [ Servidor de Aplicación FastAPI (Uvicorn Workers) ] ── Puerto 3000                            │
│   ├── Servidor SPA: /admin & /static/admin                                                      │
│   ├── Endpoints REST: /api/admin/...                                                            │
│   └── Motor de Tareas Asíncronas (BackgroundTasks)                                              │
│         │                                                                                       │
│         ├──────────────────────────────────────────┐                                            │
│         ▼                                          ▼                                            │
│  [ Base de Datos PostgreSQL Corporativa ]   [ Almacenamiento Seguro de Fotos ]                  │
│   (Servidor PostgreSQL Grupo Petroil)        (uploads/tank_readings/)                           │
│   ├── Puerto 5432 / SSL Requerido                                                              │
│   ├── Pool de Conexiones Optimizado                                                             │
│   └── Backups Automatizados Continuos                                                           │
│                                                                                                 │
│  [ Servicios Externos Integrados ]                                                              │
│   ├── WhatsApp Cloud API (https://graph.facebook.com)                                           │
│   ├── Telegram Bot API (https://api.telegram.org)                                               │
│   ├── OpenRouter LLM API (DeepSeek v3)                                                          │
│   └── OpenStreetMap Nominatim Geocoding                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.1. Variables de Entorno de Producción (`.env`)
```ini
# Configuración del LLM
OPENROUTER_API_KEY="sk-or-v1-tu-api-key"
LLM_MODEL="deepseek/deepseek-chat"

# Tokens de Canales Conversacionales
TELEGRAM_BOT_TOKEN="123456789:ABC-Clientes"
TELEGRAM_DRIVER_BOT_TOKEN="987654321:ZYX-Choferes"
WHATSAPP_TOKEN="EAAB..."
WHATSAPP_PHONE_NUMBER_ID="104928374..."

# Base de Datos Corporativa PostgreSQL Petroil
DATABASE_URL="postgresql+asyncpg://petroil_user:password_seguro@db.petroil.internal:5432/petroil_gas"
DATABASE_PATH="data/sales_agent.db" # Fallback local SQLite

# Dominio y Parámetros del Servidor
BASE_DOMAIN="https://control.petroilgas.com"
HOST="0.0.0.0"
PORT=3000
DEFAULT_CITY="Mazatlán, Sinaloa, México"

# Reglas Operativas
AGENDA_ACTIVATION_MINUTES=30
```
