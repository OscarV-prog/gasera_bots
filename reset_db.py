"""Script para limpiar o reiniciar datos en la base de datos SQLite."""

import argparse
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.database.connection import get_db_connection, get_db_path
from src.database.schema import init_db


def eliminar_cliente_por_telefono(telefono: str):
    """Elimina un cliente y todos sus pedidos/direcciones por número de teléfono."""
    clean_tel = "".join(filter(str.isdigit, telefono))
    with get_db_connection() as conn:
        custs = conn.execute(
            "SELECT id, name, phone FROM customers WHERE phone LIKE ? OR phone LIKE ?",
            (f"%{telefono}%", f"%{clean_tel}%"),
        ).fetchall()

        if not custs:
            print(f"⚠️ No se encontró ningún cliente con el teléfono: {telefono}")
            return

        cust_ids = [c["id"] for c in custs]
        placeholders = ",".join("?" for _ in cust_ids)

        conn.execute(f"DELETE FROM customer_addresses WHERE customer_id IN ({placeholders})", cust_ids)
        
        orders = conn.execute(f"SELECT id FROM orders WHERE customer_id IN ({placeholders})", cust_ids).fetchall()
        order_ids = [o["id"] for o in orders]
        if order_ids:
            ord_p = ",".join("?" for _ in order_ids)
            conn.execute(f"DELETE FROM order_items WHERE order_id IN ({ord_p})", order_ids)
            conn.execute(f"DELETE FROM orders WHERE id IN ({ord_p})", order_ids)

        conn.execute(f"DELETE FROM customers WHERE id IN ({placeholders})", cust_ids)
        print(f"✅ Se eliminaron con éxito los datos y pedidos del cliente ({telefono}).")


def reiniciar_toda_la_bd():
    """Borra el archivo SQLite y lo recrea desde cero con los catálogos limpios."""
    db_path = get_db_path()
    if db_path.exists():
        os.remove(db_path)
        print(f"🗑️ Archivo de base de datos eliminado: {db_path}")

    init_db()
    print("✅ Base de datos reiniciada y catálogo de productos resembrado desde cero.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reiniciar base de datos o borrar un cliente")
    parser.add_argument("--phone", "-p", type=str, help="Teléfono del cliente a eliminar")
    parser.add_argument("--all", "-a", action="store_true", help="Reiniciar toda la base de datos desde cero")

    args = parser.parse_args()

    if args.phone:
        eliminar_cliente_por_telefono(args.phone)
    elif args.all:
        reiniciar_toda_la_bd()
    else:
        print("Uso:")
        print("  python reset_db.py --phone 6699123501   (Borrar un cliente específico)")
        print("  python reset_db.py --all                (Reiniciar toda la base de datos)")
