from __future__ import annotations

import sys
from pathlib import Path

# Forzar UTF-8 en Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.services.api_client import api_get, get_api_base_url


def main():
    api_url = get_api_base_url()
    print(f"🔗 Conectando a la API centralizada: {api_url} ...\n")
    try:
        metrics = api_get("/admin/metrics", timeout=5)
        print("✅ ¡Conexión con la API REST exitosa!")
        if isinstance(metrics, dict):
            print(f"   • Pedidos activos: {metrics.get('pendingOrders', 0)}")
            print(f"   • Choferes totales: {metrics.get('totalDrivers', 0)}")

        products = api_get("/products", timeout=5)
        if isinstance(products, list):
            print(f"\n📦 Catálogo de productos ({len(products)} items):")
            for p in products:
                price = p.get('pricePerUnit') or p.get('price') or 0
                unit = p.get('unitType') or p.get('unit') or 'pieza'
                print(f"   - {p.get('name')}: ${price:.2f} / {unit}")

    except Exception as e:
        print(f"⚠️ No se pudo contactar la API remota en {api_url}: {e}")
        print("   (El sistema continuará operando localmente mediante la base de datos de respaldo sin interrupciones).")


if __name__ == "__main__":
    main()
