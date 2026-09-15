"""Script para inspeccionar el contenido de la base de datos SQLite en tiempo real."""

import argparse
import datetime
import os
import sys
import time

# Forzar UTF-8 en terminal de Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.database.connection import get_db_connection, get_db_path


def mostrar_base_de_datos():
    db_path = get_db_path()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 80)
    print(f"🗄️  BASE DE DATOS SQLITE: {db_path.resolve()}")
    print(f"🕒 Última actualización: {now_str}")
    print("=" * 80)

    if not db_path.exists():
        print("⚠️ El archivo de base de datos aún no existe.")
        return

    with get_db_connection() as conn:
        # 1. Clientes y sus N Direcciones
        print("\n👤 TABLA: customers & customer_addresses (Clientes y sus Direcciones)")
        print("-" * 80)
        clientes = conn.execute(
            "SELECT id, tenant_id, channel, name, phone, notes FROM customers ORDER BY id DESC"
        ).fetchall()
        if clientes:
            for c in clientes:
                notas = f" | Notas: {c['notes']}" if c['notes'] else ""
                print(f"\n🔹 Cliente ID #{c['id']} | [{c['channel']}] {c['name']} | Tel: {c['phone']}{notas}")
                
                # Obtener direcciones del cliente
                addrs = conn.execute(
                    "SELECT id, address, alias, is_default, notes FROM customer_addresses WHERE customer_id = ? ORDER BY is_default DESC, id ASC",
                    (c["id"],),
                ).fetchall()

                if addrs:
                    for i, a in enumerate(addrs, 1):
                        def_tag = " ⭐ [PREDETERMINADA]" if a["is_default"] else f" 🏷️ [{a['alias']}]" if a["alias"] != "Principal" else ""
                        ref = f" (Ref: {a['notes']})" if a["notes"] else ""
                        print(f"      {i}. 📍{def_tag} {a['address']}{ref}")
                else:
                    print("      (Sin direcciones registradas)")
        else:
            print("   (No hay clientes registrados)")

        # 2. Choferes y Unidades
        print("\n🚗 TABLA: drivers (Choferes y Unidades de Reparto)")
        print("-" * 80)
        choferes = conn.execute(
            "SELECT id, name, phone, telegram_user_id, vehicle_type, vehicle_plate, zone, is_available FROM drivers ORDER BY id ASC"
        ).fetchall()
        if choferes:
            for d in choferes:
                status_icon = "🟢 DISPONIBLE" if d["is_available"] else "🔴 OCUPADO / FUERA DE TURNO"
                tg_status = f" | Telegram ID: {d['telegram_user_id']}" if d['telegram_user_id'] else " | (Sin vincular a Telegram)"
                print(f"🔹 Chofer ID #{d['id']} | {d['name']} | Tel: {d['phone']} | {d['vehicle_plate']} [{d['vehicle_type'].upper()}]")
                print(f"   Zona: {d['zone']} | Estado: {status_icon}{tg_status}")
        else:
            print("   (No hay choferes registrados)")

        # 3. Pedidos
        print("\n📋 TABLA: orders (Pedidos Realizados)")
        print("-" * 80)
        pedidos = conn.execute(
            """
            SELECT o.id, o.tenant_id, o.customer_name, o.customer_phone, o.delivery_address,
                   o.delivery_schedule, o.total_amount, o.currency, o.status, o.payment_method,
                   o.driver_id, d.name as driver_name, o.created_at
            FROM orders o
            LEFT JOIN drivers d ON o.driver_id = d.id
            ORDER BY o.id DESC
            """
        ).fetchall()
        if pedidos:
            for o in pedidos:
                pay = o['payment_method'] or 'Efectivo'
                sched = o['delivery_schedule'] or 'Lo antes posible'
                driver_str = f" | 🚗 Chofer: {o['driver_name']}" if o['driver_name'] else " | ⚠️ Sin chofer asignado"
                print(f"🔹 Pedido #{o['id']} | Estado: [{o['status'].upper()}]{driver_str} | Total: ${o['total_amount']} {o['currency']}")
                print(f"   Cliente: {o['customer_name']} | Tel: {o['customer_phone']}")
                print(f"   Dirección: {o['delivery_address']}")
                print(f"   📅 Horario: {sched} | 💳 Pago: {pay}")
                print(f"   Fecha: {o['created_at']}")
        else:
            print("   (No hay pedidos registrados aún)")

        # 4. Detalle de Pedidos
        print("\n📦 TABLA: order_items (Productos por Pedido)")
        print("-" * 80)
        items = conn.execute(
            "SELECT id, order_id, product_name, quantity, unit_price, subtotal FROM order_items ORDER BY order_id DESC, id ASC"
        ).fetchall()
        if items:
            for it in items:
                print(f"   -> [Pedido #{it['order_id']}] {it['quantity']}x {it['product_name']} a ${it['unit_price']:.2f} = Subtotal: ${it['subtotal']:.2f}")
        else:
            print("   (No hay items registrados)")

        # 5. Resumen de Productos
        print("\n⛽ TABLA: products (Catálogo Petroil en BD)")
        print("-" * 80)
        productos = conn.execute(
            "SELECT id, name, price, currency, category, in_stock FROM products WHERE tenant_id = 'petroil' ORDER BY price ASC"
        ).fetchall()
        if productos:
            for p in productos:
                stock = "Disponible" if p['in_stock'] else "Agotado"
                print(f"   [{p['id']}] {p['name']} -> ${p['price']} {p['currency']} ({p['category']}) [{stock}]")
        else:
            print("   (No hay productos cargados)")

    print("\n" + "=" * 80)


def modo_en_vivo(intervalo: int = 2):
    """Monitorea y actualiza la pantalla en tiempo real."""
    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")
            mostrar_base_de_datos()
            print(f"👀 Modo en vivo activo (refrescando cada {intervalo}s)... Presiona Ctrl+C para salir.")
            time.sleep(intervalo)
    except KeyboardInterrupt:
        print("\n👋 Monitoreo en vivo detenido.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visor de base de datos SQLite")
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Monitorear y refrescar en vivo en la consola cada 2 segundos",
    )
    args = parser.parse_args()

    if args.watch:
        modo_en_vivo()
    else:
        mostrar_base_de_datos()
