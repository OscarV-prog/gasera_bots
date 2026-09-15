# Especificación UX/UI del Ecosistema Digital Gasera (Gas a tu Puerta)

**Cliente:** Grupo Petroil — División Gas (Mazatlán, Sinaloa)  
**Versión:** 3.5.0 Enterprise — Consolidada con la Interfaz Conversacional Omnicanal (WhatsApp/Telegram), Bot de Choferes y Torre de Control Web en Dominio Propio  
**Estado:** Documento Maestro de Diseño UX/UI Aprobado y Vigente  
**Fuentes Oficiales de Verdad:** `product-context.md` v3.5, `prd.md` v3.5, `user-flows.md` v3.5 y Código Fuente del Repositorio  
**Fecha:** Septiembre 2026  

---

## 1. Fundamentos de Diseño y Sistema de Tokens Visuales

El ecosistema **Gas a Tu Puerta - Petroil** opera bajo una filosofía híbrida:
> **Botones y menús interactivos deterministas para selección estructurada + Conversación natural inteligente para resolución de dudas y referencias de entrega.**

### 1.1. Paleta de Colores Corporativa (Design Tokens)

| Token | Nombre del Color | Hex Code | Uso Principal |
| :--- | :--- | :---: | :--- |
| `--color-brand-primary` | Dark Slate Blue | `#1E293B` | Encabezados, barras de navegación, texto principal y fondos de tablas. |
| `--color-brand-accent` | Royal Blue | `#2563EB` | Botones de acción primaria, enlaces activos e indicadores de foco. |
| `--color-gas-orange` | Petroil Gas Orange | `#F59E0B` | Llamados a la acción de venta, acentos de cilindros y alertas de horario. |
| `--color-status-success`| Emerald Green | `#10B981` | Botones de confirmación (`Confirmar pedido`, `Aceptar Viaje`), badges `delivered`. |
| `--color-status-warning`| Amber Alert | `#F59E0B` | Badges de estado `in_route`, `assigned` y advertencias de chofer en pausa. |
| `--color-status-danger` | Crimson Red | `#EF4444` | Botones de cancelación, rechazo de viaje y badges `cancelled`, `rejected_by_driver`. |
| `--color-status-purple` | Purple Agenda | `#8B5CF6` | Badges de estado `scheduled` y temporizadores de cuenta regresiva en Agenda. |
| `--color-bg-dark` | Obsidian Navy | `#0B1120` | Fondo general de la aplicación en Modo Oscuro. |
| `--color-card-dark` | Slate Navy Glass | `#1E293B` | Fondo de tarjetas y paneles translúcidos en Modo Oscuro. |
| `--color-bg-light` | Slate Light 50 | `#F8FAFC` | Fondo general de la aplicación en Modo Claro. |
| `--color-card-light` | Pure White | `#FFFFFF` | Fondo de tarjetas y paneles en Modo Claro. |
| `--color-border-subtle` | Slate Border 200 | `#E2E8F0` | Líneas divisorias, bordes de modales y tarjetas. |

---

### 1.2. Sistema de Temas Claro / Oscuro con Persistencia

* **Conmutador Visual:** Botón interactivo `☀️ Modo Claro` / `🌙 Modo Oscuro` disponible en la barra superior y pie lateral de la Torre de Control Web.
* **Persistencia:** Guarda la selección en `localStorage.getItem('theme')` aplicando la clase `theme-light` o `theme-dark` en la etiqueta raíz `<html>`.
* **Modo Oscuro (Default):** Diseñado para salas de control y monitoreo continuo, con fondos profundos Obsidian Navy y acentos esmeralda/cian de alto contraste.
* **Modo Claro:** Diseñado para oficinas administrativas iluminadas, con fondos Slate limpios y tarjetas blancas con sombras suaves.

---

### 1.3. Responsividad y Adaptabilidad de Pantallas

| Dispositivo / Resolución | Breakpoint | Comportamiento UX/UI |
| :--- | :--- | :--- |
| **Monitores Grandes / Ultrawide** | $\ge 1920\text{px}$ | Layout fluido en ancho completo con métricas en 4 columnas y tablas expandidas. |
| **Laptops y Notebooks** | $1280\text{px} - 1600\text{px}$ | Distribución balanceada, modales con scroll interno y tablas sin pérdida de datos. |
| **Tablets (iPad, Android)** | $768\text{px} - 1024\text{px}$ | Barra lateral colapsable convertida en cajón deslizable (Drawer) activado con botón hamburguesa `☰`. |
| **Smartphones** | $320\text{px} - 767\text{px}$ | Métricas en cuadrícula de 2 columnas, botones táctiles grandes ($\ge 44\text{px}$) y tablas con scroll horizontal optimizado. |

---

# PARTE 1: UX/UI DE LA INTERFAZ CONVERSACIONAL (WHATSAPP & TELEGRAM)

---

## 2. Especificación de Menús y Teclados Interactivos

El bot de clientes genera teclados dinámicos (`ui_keyboards.py`) que evitan la fatiga de escritura.

### 2.1. Catálogo de Teclados Contextuales

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. TIPO DE SERVICIO                                                         │
│ ┌───────────────────────────────────┬─────────────────────────────────────┐ │
│ │          🛢️ Cilindros              │       🔥 Tanque Estacionario        │ │
│ └───────────────────────────────────┴─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. CATÁLOGO DINÁMICO (PRECIOS REALES POSTGRESQL)                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                   🟢 Cilindro de 30 kg — $670 MXN                       │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │                   🔵 Cilindro de 20 kg — $450 MXN                       │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │                   🟡 Cilindro de 45 kg — $1,010 MXN                     │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │                   ⚪ Cilindro de 10 kg — $230 MXN                       │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. CANTIDADES RÁPIDAS (CILINDROS)                                           │
│ ┌───────────────┬───────────────┬───────────────┬─────────────────────────┐ │
│ │       1       │       2       │       3       │            4            │ │
│ ├───────────────┴───────────────┴───────────────┴─────────────────────────┤ │
│ │                           ✍️ Otra cantidad                              │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. LIBRETA DE DIRECCIONES GUARDADAS                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │        🏠 Casa Principal: Mision San Javier 5246, Misiones...            │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │        🏢 Local Centro: Calle Ángel Flores 101, Centro...               │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │                       ➕ Ingresar Nueva Dirección                        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. HORARIOS DE ENTREGA                                                      │
│ ┌─────────────────────────┬──────────────────────────┬────────────────────┐ │
│ │   ⚡ Lo antes posible   │   🕐 Hoy por la tarde    │     📅 Mañana      │ │
│ └─────────────────────────┴──────────────────────────┴────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. MÉTODOS DE PAGO                                                          │
│ ┌───────────────────────────────────┬─────────────────────────────────────┐ │
│ │            💵 Efectivo            │        💳 Tarjeta (Terminal)        │ │
│ └───────────────────────────────────┴─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│ 7. RESUMEN FINANCIERO Y CONFIRMACIÓN OBLIGATORIA                            │
│ ┌───────────────────────────────────┬─────────────────────────────────────┐ │
│ │       ✅ Confirmar pedido         │          ✏️ Modificar pedido         │ │
│ ├───────────────────────────────────┴─────────────────────────────────────┤ │
│ │                            ❌ Cancelar                                   │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│ 8. ENCUESTA DE SATISFACCIÓN CSAT                                            │
│ ┌───────┬──────────┬─────────────┬────────────────┬──────────────────────┐ │
│ │  ⭐   │   ⭐⭐   │    ⭐⭐⭐   │     ⭐⭐⭐⭐   │       ⭐⭐⭐⭐⭐     │ │
│ └───────┴──────────┴─────────────┴────────────────┴──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# PARTE 2: UX/UI DEL CANAL CHOFERES (TELEGRAM BOT)

---

## 3. Tarjetas de Despacho y Botones de Acción en Campo

### 3.1. Tarjeta de Viaje Asignado (`driver_bot.py`)
Diseñada con tipografía monoespaciada y alto contraste para lectura rápida en cabina:

```text
🚨 ¡NUEVO PEDIDO ASIGNADO!

📋 Folio: #35
👤 Cliente: Oscar Vizcarra Sánchez
📞 Teléfono: `6699123501`
📍 Dirección: Calle General Ángel Flores 101, Col. Centro
📝 Referencias: Edificio amarillo de 3 pisos, local comercial
📅 Horario: Hoy a las 4:00 PM
💰 Total a Cobrar: $670.00 MXN (💵 Efectivo)

📦 Productos:
  • 1x Cilindro de Gas LP 30 kg
```

### 3.2. Teclado de Acciones del Chofer

```
┌───────────────────────────────────┬─────────────────────────────────────┐
│          ✅ Aceptar Viaje         │             ❌ Rechazar             │
├───────────────────────────────────┼─────────────────────────────────────┤
│          🗺️ Google Maps           │               🚗 Waze               │
└───────────────────────────────────┴─────────────────────────────────────┘
```

* **Comportamiento:**
  - `[ 🗺️ Google Maps ]`: Abre URL de navegación giro a giro con coordenadas: `https://www.google.com/maps/dir/?api=1&destination=23.200577,-106.418606`.
  - `[ 🚗 Waze ]`: Abre enlace de navegación directa en Waze: `https://waze.com/ul?ll=23.200577,-106.418606&navigate=yes`.
  - Al aceptar viaje (`in_route`), el teclado cambia a:
    ```
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                       📦 Marcar como Entregado                          │
    └─────────────────────────────────────────────────────────────────────────┘
    ```
  - Al presionar `[ ❌ Rechazar ]`, despliega menú de motivos (*Falla mecánica*, *Desabasto*, *Tráfico pesado*, *Fuera de zona*).

---

# PARTE 3: UX/UI DE LA TORRE DE CONTROL WEB (EN DOMINIO PROPIO)

---

## 4. Arquitectura de la Interfaz Web de Administración

La aplicación web de administración opera en el dominio corporativo seguro `https://control.petroilgas.com`.

### 4.1. Estructura y Distribución Espacial

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [PETROIL GAS]  Torre de Control — Control Tower              [☀️ Modo Claro] 🟢 En Vivo | 12:45 │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────────────┐ │
│ │  PEDIDOS ACTIVOS  │ │ VENTAS COBRADAS   │ │  INCIDENCIAS PEND │ │     CALIFICACIÓN CSAT     │ │
│ │        48         │ │   $32,160 MXN     │ │         1         │ │         4.85 / 5.0 ⭐   │ │
│ │ (💵 $22k / 💳 $9k)│ │                   │ │ (Reasignar en 1c) │ │      (37 Encuestas)     │ │
│ └───────────────────┘ └───────────────────┘ └───────────────────┘ └───────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [📊 Dashboard] [📦 Pedidos] [🕒 Mesa Agenda (T-30)] [⚠️ Incidencias] [🚛 Flota] [➕ Levantar]   │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [🔍 Buscar cliente, folio o dirección...]  [Estado: Todos ▼]  [Chofer: Todos ▼]  [🔄 Refrescar] │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ FOLIO  CLIENTE       TELÉFONO    DIRECCIÓN                TOTAL     CHOFER       ESTADO    ACCIÓN   │
│ #35    Oscar Vizcarra 6699123501  Gral. Ángel Flores Centro $670.00   Oscar Lopez  ASIGNADO  [🛻 Reasig]│
│ #34    María Benítez  6691234567  Av. Del Mar 402          $450.00   Juan Pérez   EN RUTA   [🛻 Reasig]│
│ #33    Rest. Mariscos 6699887766  Zona Dorada 1200         $1,250.00 Carlos Ruiz  ENTREGADO Detalle │
├─────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 📥 EXPORTAR REPORTES EXCEL (.xlsx):                                                             │
│ [📊 Libro Maestro (4 Hojas)]  [📋 Pedidos]  [⚠️ Incidencias/Rechazos]  [🚛 Choferes] [👥 Clientes]│
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 4.2. Badges de Estado Semánticos

| Estado | Color de Fondo | Color de Texto | Significado Visual |
| :--- | :---: | :---: | :--- |
| `confirmed` | `#DBEAFE` (Azul claro) | `#1E40AF` | Pedido registrado, en espera de asignación de chofer. |
| `scheduled` | `#F3E8FF` (Púrpura claro)| `#6B21A8` | Pedido en Mesa de Agenda; cuenta regresiva activa. |
| `assigned` | `#FEF3C7` (Ámbar claro) | `#92400E` | Asignado a chofer; alerta enviada al bot. |
| `in_route` | `#E0E7FF` (Índigo claro)| `#3730A3` | Chofer en traslado con Waze/Google Maps. |
| `delivered` | `#D1FAE5` (Verde claro)| `#065F46` | Entrega concluida, cobro registrado y CSAT enviada. |
| `rejected_by_driver` | `#FEE2E2` (Rojo claro)| `#991B1B` | Chofer declinó el viaje; alerta para reasignación en Torre. |
| `cancelled` | `#F1F5F9` (Gris claro) | `#475569` | Cancelado por cliente o administración con motivo. |

---

### 4.3. Componentes Especiales de la Torre de Control

#### A. Mesa de Agenda Programada (Regla T-30 Minutos)
* Visualización de pedidos con deadline futuro.
* Temporizadores dinámicos: `🕒 Faltan 2h 15m` o `⚡ Se activa en 8 min`.
* Botón de pase manual inmediato: `[ ⚡ Pasar a Pedidos Ya ]`.
* Botón de reprogramación: `[ ✏️ Reprogramar ]`.

#### B. Modal de Venta Directa / Call Center (`➕ Levantar Pedido`)
* Formulario flotante accesible en todo momento para recepción de llamadas telefónicas.
* Autocompletado de clientes recurrentes al escribir 10 dígitos.
* Selector de productos con cálculo reactivo de subtotales.
* Selector de despacho: Automático (Haversine), Chofer Directo o Cola Pendiente.

#### C. Modal de Reasignación en Caliente
* Menú desplegable con choferes activos indicando su unidad vehicular y estado (`🟢 Disponible` o `🟡 En Entrega`).
* Envío de push asíncrono a Telegram/WhatsApp en $<2\text{ s}$ sin recargar la página.
