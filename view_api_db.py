"""Script interactivo para inspeccionar la base de datos de PostgreSQL (API NestJS) en tiempo real."""

import argparse
import datetime
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Forzar UTF-8 en terminal de Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()

from src.services.api_client import api_get, get_api_base_url, is_api_online

TENANT_ID = os.getenv("TENANT_ID", "petroil")


def mostrar_datos_api():
    base_url = get_api_base_url()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 85)
    print(f"🌐 BASE DE DATOS CENTRALIZADA (POSTGRESQL / NESTJS API)")
    print(f"📍 URL API: {base_url}  |  🏢 Tenant: {TENANT_ID}")
    print(f"🕒 Consulta: {now_str}")
    print("=" * 85)

    if not is_api_online(timeout=4):
        print("❌ Error: La API remota no responde o está fuera de línea.")
        return

    # 1. CLIENTES REGISTRADOS
    print("\n👤 TABLA: customers (Clientes Registrados en PostgreSQL)")
    print("-" * 85)
    try:
        customers = api_get("/customers", params={"tenantId": TENANT_ID}, timeout=5)
        if isinstance(customers, list) and customers:
            for i, c in enumerate(customers, 1):
                cid = c.get("id", "N/A")
                name = c.get("name", "Sin nombre")
                phone = c.get("phone", "Sin teléfono")
                addr = c.get("address", "Sin dirección registrada")
                col = c.get("colonia") or c.get("city") or "Mazatlán"
                ctype = c.get("customerType", "REGISTRADO")
                created = c.get("createdAt", "")[:19].replace("T", " ")
                num_orders = c.get("_count", {}).get("orders", 0) if isinstance(c.get("_count"), dict) else 0

                print(f"🔹 [{i}] {name}  |  📞 Tel: {phone}  |  🏷️ Tipo: {ctype}")
                print(f"    📍 Domicilio: {addr} ({col})")
                print(f"    🆔 UUID: {cid}")
                print(f"    📦 Pedidos asociados: {num_orders}  |  📅 Registrado: {created}")
                print()
        else:
            print("   ℹ️ No hay clientes registrados actualmente en esta base de datos.")
    except Exception as e:
        print(f"   ❌ Error al consultar clientes: {e}")

    # 2. PEDIDOS REGISTRADOS
    print("\n📋 TABLA: orders (Pedidos Registrados en PostgreSQL)")
    print("-" * 85)
    try:
        orders = api_get("/orders", params={"tenantId": TENANT_ID}, timeout=5)
        if isinstance(orders, list) and orders:
            for i, o in enumerate(orders, 1):
                oid = o.get("id") or o.get("orderNumber") or "N/A"
                cname = o.get("customerName", "Cliente")
                cphone = o.get("customerPhone", "")
                total = o.get("totalAmount", 0.0)
                status = o.get("status", "PENDIENTE")
                pay = o.get("paymentMethod", "EFECTIVO")
                created = o.get("createdAt", "")[:19].replace("T", " ")
                items = o.get("items", [])
                items_str = ", ".join(f"{it.get('quantity', 1)}x {it.get('productName', 'Producto')}" for it in items) if items else "Sin items"

                print(f"🔹 [{i}] Pedido #{oid}  |  Estado: [{status}]  |  Total: ${total:.2f} MXN")
                print(f"    👤 Cliente: {cname} ({cphone})  |  💳 Pago: {pay}")
                print(f"    📍 Entrega: {o.get('deliveryAddress', 'N/A')}")
                print(f"    📦 Items: {items_str}")
                print(f"    📅 Fecha: {created}")
                print()
        else:
            print("   ℹ️ No hay pedidos registrados actualmente en esta base de datos.")
    except Exception as e:
        print(f"   ❌ Error al consultar pedidos: {e}")

    # 3. CATÁLOGO DE PRODUCTOS
    print("\n📦 TABLA: products (Catálogo de Productos en PostgreSQL)")
    print("-" * 85)
    try:
        prods = api_get("/products", params={"tenantId": TENANT_ID}, timeout=5)
        if isinstance(prods, list) and prods:
            for p in prods:
                name = p.get("name", "")
                price = p.get("pricePerUnit", 0.0)
                cat = p.get("category", "")
                unit = p.get("unitType", "pieza")
                avail = "🟢 Disponible" if p.get("isAvailable", True) else "🔴 Agotado"
                print(f"   • {name:<35} | ${price:>7.2f} MXN / {unit:<6} | Cat: {cat:<12} | {avail}")
        else:
            print("   ℹ️ No hay productos registrados.")
    except Exception as e:
        print(f"   ❌ Error al consultar catálogo: {e}")

    print("\n" + "=" * 85)


def modo_en_vivo(intervalo: int = 3):
    """Monitorea y actualiza la pantalla en tiempo real."""
    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            mostrar_datos_api()
            print(f"👀 Monitoreo en vivo activo (refrescando cada {intervalo}s)... Presiona Ctrl+C para salir.")
            time.sleep(intervalo)
    except KeyboardInterrupt:
        print("\n👋 Monitoreo en vivo detenido.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visor de base de datos PostgreSQL (NestJS API)")
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Monitorear y refrescar en vivo en la consola cada 3 segundos",
    )
    args = parser.parse_args()

    if args.watch:
        modo_en_vivo()
    else:
        mostrar_datos_api()
