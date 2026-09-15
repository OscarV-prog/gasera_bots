"""REST API Repository Adapter for Centralized NestJS + PostgreSQL Backend.

Pure REST API repository with no SQLite dependency when DATA_SOURCE=api.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any
from datetime import datetime, timezone

from src.models.customer import Customer, CustomerAddress
from src.models.driver import Driver
from src.models.order import Order, OrderItem
from src.models.product import Product
from src.services.api_client import api_get, api_post, api_patch

logger = logging.getLogger(__name__)


class ApiRepository:
    """Repository implementation that communicates exclusively with the centralized NestJS REST API and PostgreSQL."""

    def __init__(self, fallback_repo: Any = None):
        self.fallback_repo = fallback_repo  # None when SQLite is deactivated
        self._last_failure_time: float = 0
        self._cooldown_seconds: float = 10.0
        self._order_id_map: dict[Any, dict] = {}

    def _should_skip_api(self) -> bool:
        """Check if remote API circuit breaker is active."""
        if not self._last_failure_time:
            return False
        return (time.time() - self._last_failure_time) < self._cooldown_seconds

    def _record_api_failure(self, error: Exception) -> None:
        """Record connection failure timestamp."""
        self._last_failure_time = time.time()
        logger.warning(f"[ApiRepository] Remote API error: {error}. Circuit cooldown {self._cooldown_seconds}s.")

    def _record_api_success(self) -> None:
        """Reset circuit breaker on successful response."""
        self._last_failure_time = 0

    # -------------------------------------------------------------------------
    # Products / Catalog
    # -------------------------------------------------------------------------

    def get_all_products(self, tenant_id: str = "petroil") -> list[Product]:
        """Fetch all available products from the NestJS REST API."""
        try:
            raw_products = api_get("/products", params={"tenantId": tenant_id}, timeout=5)
            if isinstance(raw_products, list):
                products = []
                for p in raw_products:
                    # Filtrar por tenant si el objeto lo incluye
                    p_tenant = p.get("tenantId", tenant_id)
                    if p_tenant and p_tenant != tenant_id:
                        continue

                    pid = str(p.get("id") or p.get("productId") or "")
                    name = str(p.get("name") or "")
                    price = float(p.get("pricePerUnit") or p.get("price") or 0.0)
                    category = str(p.get("category") or "CILINDRO")
                    unit = str(p.get("unitType") or p.get("unit") or "pieza")
                    desc = str(p.get("description") or f"{name} - ${price:.2f}")
                    in_stock = bool(p.get("isAvailable", p.get("in_stock", True)))
                    is_promo = bool(p.get("isPromotion", False))
                    promo_desc = float(p.get("promoDiscount", 0.0))

                    products.append(
                        Product(
                            id=pid,
                            tenant_id=tenant_id,
                            name=name,
                            description=desc,
                            price=price,
                            currency="MXN",
                            category=category,
                            unit=unit,
                            in_stock=in_stock,
                            is_promotion=is_promo,
                            promo_discount=promo_desc,
                        )
                    )
                if products:
                    self._record_api_success()
                    return products
        except Exception as e:
            self._record_api_failure(e)

        if self.fallback_repo:
            return self.fallback_repo.get_all_products(tenant_id)
        return []

    def search(self, tenant_id: str, query: str) -> list[Product]:
        """Search products by name, category or description keywords."""
        all_prods = self.get_all_products(tenant_id)
        if not query or not query.strip():
            return all_prods

        q_clean = query.lower().strip()
        matches = []
        for p in all_prods:
            if (
                q_clean in p.name.lower()
                or q_clean in p.description.lower()
                or q_clean in p.category.lower()
                or (q_clean.isdigit() and f"{q_clean} kg" in p.name.lower())
            ):
                matches.append(p)

        return matches or all_prods

    def get_product_by_id(self, tenant_id: str, product_id: str) -> Product | None:
        """Lookup a product by ID or name."""
        for p in self.get_all_products(tenant_id):
            if p.id == product_id or (product_id.lower() in p.id.lower()) or (product_id.lower() in p.name.lower()):
                return p
        if self.fallback_repo:
            return self.fallback_repo.get_product_by_id(tenant_id, product_id)
        return None

    def get_promotions(self, tenant_id: str) -> list[Product]:
        """Get active promotions from PostgreSQL."""
        return [p for p in self.get_all_products(tenant_id) if getattr(p, "is_promotion", False)]

    # -------------------------------------------------------------------------
    # Customers
    # -------------------------------------------------------------------------

    def get_customer_by_phone(self, tenant_id: str, phone: str) -> Customer | None:
        """Lookup customer profile by 10-digit phone number in PostgreSQL API."""
        clean_phone = re.sub(r"\D", "", phone) if phone else ""
        if clean_phone.startswith("521") and len(clean_phone) == 13:
            clean_phone = clean_phone[3:]
        elif clean_phone.startswith("52") and len(clean_phone) == 12:
            clean_phone = clean_phone[2:]
        if len(clean_phone) > 10:
            clean_phone = clean_phone[-10:]

        if not clean_phone:
            return None

        try:
            res = api_get("/customers", params={"tenantId": tenant_id}, timeout=5)
            if isinstance(res, list):
                # Filtrar con precisión por el número de teléfono del cliente
                for c_data in res:
                    raw_phone = re.sub(r"\D", "", str(c_data.get("phone", "")))
                    if raw_phone.startswith("521") and len(raw_phone) == 13:
                        raw_phone = raw_phone[3:]
                    elif raw_phone.startswith("52") and len(raw_phone) == 12:
                        raw_phone = raw_phone[2:]
                    if len(raw_phone) > 10:
                        raw_phone = raw_phone[-10:]

                    if raw_phone == clean_phone:
                        self._record_api_success()
                        return self._parse_api_customer(c_data, tenant_id, clean_phone)

                # Si no se encontró en la lista de PostgreSQL, es un cliente nuevo
                self._record_api_success()
                return None
            elif isinstance(res, dict) and res.get("name"):
                raw_phone = re.sub(r"\D", "", str(res.get("phone", "")))
                if raw_phone == clean_phone or not raw_phone:
                    self._record_api_success()
                    return self._parse_api_customer(res, tenant_id, clean_phone)
        except Exception as e:
            self._record_api_failure(e)

        if self.fallback_repo:
            return self.fallback_repo.get_customer_by_phone(tenant_id, phone)
        return None

    def get_customer(self, tenant_id: str, channel: str, channel_user_id: str) -> Customer | None:
        """Lookup customer by channel and user ID."""
        clean_uid = re.sub(r"\D", "", str(channel_user_id))
        if len(clean_uid) >= 10:
            return self.get_customer_by_phone(tenant_id, clean_uid[-10:])
        if self.fallback_repo:
            return self.fallback_repo.get_customer(tenant_id, channel, channel_user_id)
        return None

    def get_customer_addresses(self, customer_id: Any) -> list[CustomerAddress]:
        """Fetch saved customer addresses."""
        if not customer_id:
            return []
        try:
            res = api_get("/customers", timeout=5)
            if isinstance(res, list):
                for c in res:
                    if str(c.get("id")) == str(customer_id) or str(c.get("phone")) == str(customer_id):
                        cust = self._parse_api_customer(c, "petroil", str(c.get("phone", "")))
                        return cust.addresses
        except Exception:
            pass
        if self.fallback_repo:
            return self.fallback_repo.get_customer_addresses(customer_id)
        return []

    def save_or_update_customer(
        self,
        tenant_id: str,
        channel: str,
        channel_user_id: str,
        name: str,
        phone: str = "",
        address: str = "",
        **kwargs: Any,
    ) -> Customer:
        """Create or update customer profile in PostgreSQL."""
        clean_phone = re.sub(r"\D", "", phone) if phone else ""
        if len(clean_phone) > 10:
            clean_phone = clean_phone[-10:]

        body = {
            "tenantId": tenant_id,
            "name": name,
            "phone": clean_phone or channel_user_id,
            "address": address or "Mazatlán",
            "colonia": "Mazatlán",
            "city": "Mazatlán",
        }
        try:
            res = api_post("/customers", body, timeout=5)
            if isinstance(res, dict) and res.get("id"):
                return self._parse_api_customer(res, tenant_id, clean_phone or channel_user_id)
        except Exception as e:
            logger.debug(f"[ApiRepository] save_or_update_customer API note: {e}")

        if self.fallback_repo:
            return self.fallback_repo.save_or_update_customer(tenant_id, channel, channel_user_id, name, phone, address, **kwargs)

        return Customer(
            id=1,
            tenant_id=tenant_id,
            channel=channel,
            channel_user_id=channel_user_id,
            name=name,
            phone=clean_phone or channel_user_id,
            address=address,
            addresses=[CustomerAddress(id=1, address=address, alias="Principal")] if address else [],
        )

    def delete_customer_address(self, customer_id: Any, address_id: int) -> bool:
        """Delete customer address."""
        if self.fallback_repo:
            return self.fallback_repo.delete_customer_address(customer_id, address_id)
        return True

    def _parse_api_customer(self, data: dict, tenant_id: str, phone: str) -> Customer:
        cid = data.get("id")
        name = data.get("name") or data.get("customerName") or "Cliente"
        raw_addrs = data.get("addresses") or []
        addrs = []
        if isinstance(raw_addrs, list) and raw_addrs:
            for i, a in enumerate(raw_addrs, 1):
                if isinstance(a, dict):
                    addrs.append(
                        CustomerAddress(
                            id=i,
                            address=a.get("address", ""),
                            alias=a.get("alias", f"Dirección {i}"),
                            notes=a.get("notes", ""),
                            is_default=bool(a.get("isDefault", i == 1)),
                        )
                    )
                elif isinstance(a, str):
                    addrs.append(CustomerAddress(id=i, address=a, alias=f"Dirección {i}"))

        default_addr = data.get("address") or (addrs[0].address if addrs else "")
        if not addrs and default_addr:
            addrs = [CustomerAddress(id=1, address=default_addr, alias="Principal", is_default=True)]

        return Customer(
            id=cid,
            tenant_id=tenant_id,
            channel="api",
            channel_user_id=phone,
            name=name,
            phone=phone,
            address=default_addr,
            addresses=addrs,
        )

    # -------------------------------------------------------------------------
    # Orders
    # -------------------------------------------------------------------------

    def _map_api_status_to_local(self, api_status: str | None) -> str:
        """Map NestJS uppercase Spanish status to local standard status slug."""
        if not api_status:
            return "confirmed"
        s = str(api_status).upper().strip()
        status_map = {
            "PENDIENTE": "confirmed",
            "CONFIRMADO": "confirmed",
            "ASIGNADO": "assigned",
            "EN_RUTA": "in_route",
            "ENTREGADO": "delivered",
            "CANCELADO": "cancelled",
            "PROGRAMADO": "scheduled",
            "RECHAZADO": "rejected_by_driver",
        }
        return status_map.get(s, s.lower())

    def create_order(
        self,
        tenant_id: str,
        customer_name: str,
        customer_phone: str,
        delivery_address: str,
        items: list[dict[str, Any]],
        delivery_schedule: str = "Lo antes posible",
        payment_method: str = "Efectivo",
        notes: str = "",
        channel: str = "telegram",
        channel_user_id: str = "",
        customer_id: Any = None,
        delivery_lat: float | None = None,
        delivery_lng: float | None = None,
        scheduled_for: str | None = None,
        **kwargs: Any,
    ) -> Order:
        """Create a new order in NestJS API + PostgreSQL."""
        prods = self.get_all_products(tenant_id)
        prods_by_id = {p.id: p for p in prods}
        prods_by_name = {p.name.lower(): p for p in prods}

        api_items = []
        total_calc = 0.0
        clean_items_for_local = []

        for it in items:
            p_id = str(it.get("product_id") or it.get("productId") or "")
            p_name = str(it.get("product_name") or it.get("name") or "")
            qty = int(it.get("quantity") or it.get("qty") or 1)

            # Match against remote product UUID
            matched_prod = prods_by_id.get(p_id) or prods_by_name.get(p_name.lower())
            if not matched_prod:
                for p in prods:
                    if p.name.lower() in p_name.lower() or p_name.lower() in p.name.lower():
                        matched_prod = p
                        break
            if not matched_prod and prods:
                for p in prods:
                    if "30" in p.name:
                        matched_prod = p
                        break
                if not matched_prod:
                    matched_prod = prods[0]

            if matched_prod:
                real_p_id = matched_prod.id
                prod_name_clean = matched_prod.name
                price = matched_prod.price
            else:
                real_p_id = p_id or "945c5de8-a30e-4c0e-b6f5-909c37e9a617"
                prod_name_clean = p_name or "Cilindro de Gas LP 30 kg"
                price = float(it.get("unit_price") or 705.0)

            total_calc += price * qty
            api_items.append({"productId": str(real_p_id), "quantity": qty})
            clean_items_for_local.append({
                "product_id": real_p_id,
                "product_name": prod_name_clean,
                "quantity": qty,
                "unit_price": price,
                "subtotal": price * qty,
            })

        clean_pay = "EFECTIVO" if "efectivo" in payment_method.lower() else ("TARJETA" if "tarjeta" in payment_method.lower() or "terminal" in payment_method.lower() else "EFECTIVO")
        clean_channel = channel.upper() if channel else "TELEGRAM"

        body = {
            "tenantId": tenant_id,
            "customerName": customer_name,
            "customerPhone": customer_phone,
            "deliveryAddress": delivery_address,
            "colonia": "Mazatlán",
            "city": "Mazatlán",
            "channel": clean_channel,
            "paymentMethod": clean_pay,
            "notes": notes or "",
            "scheduledFor": scheduled_for if scheduled_for else (None if "antes posible" in delivery_schedule.lower() else delivery_schedule),
            "items": api_items,
        }

        # Backup local sync in SQLite
        if self.fallback_repo:
            try:
                self.fallback_repo.create_order(
                    tenant_id=tenant_id,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    delivery_address=delivery_address,
                    items=clean_items_for_local,
                    delivery_schedule=delivery_schedule,
                    payment_method=payment_method,
                    notes=notes,
                    channel=channel,
                    channel_user_id=channel_user_id,
                    customer_id=customer_id,
                    delivery_lat=delivery_lat,
                    delivery_lng=delivery_lng,
                    scheduled_for=scheduled_for,
                )
            except Exception as e:
                logger.debug(f"[ApiRepository] Local SQLite mirror error: {e}")

        try:
            res = api_post("/orders", body, timeout=5)
            if isinstance(res, dict) and res.get("id"):
                self._record_api_success()
                logger.info(f"[ApiRepository] Order created in NestJS API: ID={res.get('id')}, OrderNumber={res.get('orderNumber')}")
                if channel:
                    res["channel"] = channel
                if notes:
                    res["notes"] = notes
                if scheduled_for:
                    res["scheduledFor"] = scheduled_for
                if delivery_schedule:
                    res["deliverySchedule"] = delivery_schedule
                return self._parse_api_order(res, tenant_id)
        except Exception as e:
            self._record_api_failure(e)

        if self.fallback_repo:
            return self.fallback_repo.get_all_orders(tenant_id)[-1] if self.fallback_repo.get_all_orders(tenant_id) else None

        # Fallback in-memory order representation
        order_items = [
            OrderItem(
                product_id=it.get("productId", ""),
                product_name=it.get("productName", "Gas LP"),
                quantity=it.get("quantity", 1),
                unit_price=float(it.get("unitPrice", 0.0)),
                subtotal=float(it.get("subtotal", 0.0)),
            )
            for it in clean_items_for_local
        ]
        return Order(
            id=int(time.time()) % 100000,
            tenant_id=tenant_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            delivery_address=delivery_address,
            total_amount=total_calc,
            status="confirmed",
            payment_method=payment_method,
            items=order_items,
        )

    def get_order_by_id(self, tenant_id: str, order_id: Any) -> Order | None:
        """Fetch order details from PostgreSQL API or memory cache."""
        if order_id in self._order_id_map or str(order_id) in self._order_id_map:
            cached_data = self._order_id_map.get(order_id) or self._order_id_map.get(str(order_id))
            if cached_data:
                return self._parse_api_order(cached_data, tenant_id)

        try:
            res = api_get(f"/orders/{order_id}", timeout=5)
            if isinstance(res, dict) and res.get("id"):
                self._record_api_success()
                return self._parse_api_order(res, tenant_id)
        except Exception:
            pass

        try:
            res = api_get("/orders", params={"tenantId": tenant_id}, timeout=5)
            if isinstance(res, list):
                for o in res:
                    o_digits = re.findall(r"\d+", str(o.get("orderNumber") or ""))
                    o_num = int(o_digits[-1]) if o_digits else None
                    if (
                        str(o.get("id")) == str(order_id)
                        or str(o.get("orderNumber")) == str(order_id)
                        or (o_num is not None and (str(o_num) == str(order_id) or o_num == order_id))
                    ):
                        self._record_api_success()
                        return self._parse_api_order(o, tenant_id)
        except Exception as e:
            self._record_api_failure(e)

        if self.fallback_repo:
            return self.fallback_repo.get_order_by_id(tenant_id, order_id)
        return None

    def get_orders_by_customer_phone(self, tenant_id: str, phone: str, limit: int = 10) -> list[Order]:
        """Fetch orders for a given customer phone from PostgreSQL API."""
        clean_phone = re.sub(r"\D", "", phone) if phone else ""
        if len(clean_phone) > 10:
            clean_phone = clean_phone[-10:]

        try:
            res = api_get("/orders", params={"tenantId": tenant_id}, timeout=5)
            if isinstance(res, list):
                orders = []
                for o in res:
                    o_phone = re.sub(r"\D", "", str(o.get("customerPhone") or (o.get("customer", {}).get("phone") if isinstance(o.get("customer"), dict) else "")))
                    if len(o_phone) > 10:
                        o_phone = o_phone[-10:]
                    if o_phone == clean_phone:
                        orders.append(self._parse_api_order(o, tenant_id))
                if orders:
                    self._record_api_success()
                    return orders[:limit]
        except Exception as e:
            self._record_api_failure(e)

        if self.fallback_repo:
            return self.fallback_repo.get_orders_by_customer_phone(tenant_id, phone, limit=limit)
        return []

    def get_all_orders_admin(
        self, tenant_id: str = "petroil", status: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Fetch orders with driver information, item summaries, and status for Admin UI."""
        try:
            raw_orders = api_get("/orders", params={"tenantId": tenant_id}, timeout=5)
            if isinstance(raw_orders, list):
                self._record_api_success()
                result = []
                for o in raw_orders:
                    api_status = str(o.get("status") or "PENDIENTE").upper()
                    local_status = self._map_api_status_to_local(api_status)

                    if status and status != "all":
                        if status == "active":
                            if local_status not in ("confirmed", "assigned", "in_route", "rejected_by_driver"):
                                continue
                        elif local_status != status.lower():
                            continue

                    items = []
                    for it in o.get("items", []):
                        p_info = it.get("product") or {}
                        p_name = it.get("productName") or p_info.get("name") or "Gas LP"
                        p_qty = it.get("quantity") or 1
                        p_unit_price = float(it.get("unitPrice") or p_info.get("pricePerUnit") or 0.0)
                        p_subtotal = float(it.get("subtotal") or (p_qty * p_unit_price))
                        items.append({
                            "product_name": p_name,
                            "quantity": p_qty,
                            "unit_price": p_unit_price,
                            "subtotal": p_subtotal,
                        })

                    cust = o.get("customer") or {}
                    raw_id = o.get("orderNumber") or o.get("id") or 1

                    result.append({
                        "id": raw_id,
                        "customer_name": o.get("customerName") or cust.get("name") or "Cliente",
                        "customer_phone": o.get("customerPhone") or cust.get("phone") or "",
                        "delivery_address": o.get("deliveryAddress") or cust.get("address") or "",
                        "delivery_schedule": o.get("scheduledFor") or "Lo antes posible",
                        "scheduled_for": o.get("scheduledFor"),
                        "total_amount": float(o.get("totalAmount") or 0.0),
                        "currency": "MXN",
                        "status": local_status,
                        "payment_method": o.get("paymentMethod") or "Efectivo",
                        "notes": o.get("notes") or "",
                        "channel": str(o.get("channel") or "TELEGRAM").lower(),
                        "driver_id": o.get("driverId"),
                        "driver_name": o.get("driverName"),
                        "driver_phone": o.get("driverPhone"),
                        "driver_vehicle": o.get("truckPlate") or "Cilindros",
                        "driver_rating": 5.0,
                        "rating_tag": None,
                        "rating_comment": None,
                        "rejection_reason": None,
                        "rejection_driver_name": None,
                        "items": items,
                        "created_at": o.get("createdAt") or datetime.now(timezone.utc).isoformat(),
                    })
                return result[:limit]
        except Exception as e:
            self._record_api_failure(e)

        if self.fallback_repo:
            return self.fallback_repo.get_all_orders_admin(tenant_id, status=status, limit=limit)
        return []

    def get_admin_dashboard_metrics(self, tenant_id: str = "petroil") -> dict[str, Any]:
        """Get aggregated KPI metrics for the live dashboard."""
        try:
            raw_metrics = api_get("/admin/metrics", params={"tenantId": tenant_id}, timeout=5)
            orders = self.get_all_orders_admin(tenant_id, status="all")
            prods = self.get_all_products(tenant_id)

            drivers_status = self.get_all_drivers_operational_status(tenant_id)
            total_drivers = len(drivers_status)
            available_drivers = sum(1 for d in drivers_status if d.get("operational_status") == "disponible")
            en_entrega_drivers = sum(1 for d in drivers_status if d.get("operational_status") == "en_entrega")
            fuera_servicio_drivers = sum(1 for d in drivers_status if d.get("operational_status") == "fuera_servicio")

            active_orders = sum(1 for o in orders if o["status"] in ("confirmed", "assigned", "in_route", "rejected_by_driver"))
            delivered_orders = sum(1 for o in orders if o["status"] == "delivered")
            cancelled_orders = sum(1 for o in orders if o["status"] == "cancelled")
            scheduled_orders = sum(1 for o in orders if o["status"] == "scheduled")
            total_rev = sum(o["total_amount"] for o in orders if o["status"] == "delivered")
            rev_cash = sum(o["total_amount"] for o in orders if o["status"] == "delivered" and "efectivo" in (o.get("payment_method") or "").lower())
            rev_card = sum(o["total_amount"] for o in orders if o["status"] == "delivered" and ("tarjeta" in (o.get("payment_method") or "").lower() or "terminal" in (o.get("payment_method") or "").lower()))

            return {
                "total_orders": len(orders),
                "active_orders": active_orders,
                "delivered_orders": delivered_orders,
                "cancelled_orders": cancelled_orders,
                "scheduled_orders": scheduled_orders,
                "rejected_orders": 0,
                "unresolved_rejections": 0,
                "total_revenue": total_rev,
                "revenue_cash": rev_cash,
                "revenue_card": rev_card,
                "total_drivers": total_drivers or (raw_metrics.get("totalDrivers") if isinstance(raw_metrics, dict) else 4),
                "available_drivers": available_drivers or (raw_metrics.get("activeDrivers") if isinstance(raw_metrics, dict) else 3),
                "en_entrega_drivers": en_entrega_drivers,
                "fuera_servicio_drivers": fuera_servicio_drivers,
                "total_products": len(prods),
                "total_customers": len(orders) or 1,
                "avg_satisfaction": 5.0,
                "total_ratings": 0,
            }
        except Exception as e:
            self._record_api_failure(e)

        if self.fallback_repo:
            return self.fallback_repo.get_admin_dashboard_metrics(tenant_id)
        return {
            "total_orders": 0, "active_orders": 0, "delivered_orders": 0, "cancelled_orders": 0,
            "scheduled_orders": 0, "rejected_orders": 0, "unresolved_rejections": 0,
            "total_revenue": 0.0, "revenue_cash": 0.0, "revenue_card": 0.0,
            "total_drivers": 0, "available_drivers": 0, "en_entrega_drivers": 0,
            "fuera_servicio_drivers": 0, "total_products": 0, "total_customers": 0,
            "avg_satisfaction": 5.0, "total_ratings": 0,
        }

    def get_all_customers_admin(self, tenant_id: str = "petroil") -> list[dict[str, Any]]:
        """Fetch all customers from PostgreSQL API or fallback."""
        try:
            raw_cust = api_get("/customers", params={"tenantId": tenant_id}, timeout=5)
            if isinstance(raw_cust, list) and raw_cust:
                self._record_api_success()
                res = []
                for c in raw_cust:
                    res.append({
                        "id": c.get("id"),
                        "name": c.get("name") or "Sin nombre",
                        "phone": c.get("phone") or "",
                        "channel": "api",
                        "channel_user_id": c.get("phone") or "",
                        "address": c.get("address") or "",
                        "notes": "",
                        "order_count": c.get("_count", {}).get("orders", 0) if isinstance(c.get("_count"), dict) else 0,
                        "total_spent": 0.0,
                        "created_at": c.get("createdAt") or datetime.now(timezone.utc).isoformat(),
                        "addresses": [
                            {
                                "id": 1,
                                "address": c.get("address") or "Mazatlán",
                                "alias": "Principal",
                                "is_default": True,
                            }
                        ] if c.get("address") else [],
                    })
                return res
        except Exception as e:
            self._record_api_failure(e)

        if self.fallback_repo:
            return self.fallback_repo.get_all_customers_admin(tenant_id)
        return []

    def get_scheduled_agenda(self, tenant_id: str = "petroil") -> list[dict[str, Any]]:
        """Return all scheduled orders with deadline details, activation status, and countdowns."""
        if self.fallback_repo:
            return self.fallback_repo.get_scheduled_agenda(tenant_id)
        return []

    def get_all_drivers_operational_status(self, tenant_id: str = "petroil") -> list[dict[str, Any]]:
        """Get drivers status from fallback SQLite repository."""
        if self.fallback_repo:
            return self.fallback_repo.get_all_drivers_operational_status(tenant_id)
        return []

    def check_and_activate_scheduled_orders(self, tenant_id: str = "petroil") -> list[int]:
        """Check scheduled orders activation."""
        if self.fallback_repo:
            return self.fallback_repo.check_and_activate_scheduled_orders(tenant_id)
        return []

    def update_order_status(
        self,
        tenant_id: str,
        order_id: Any,
        status: str = "",
        notes_append: str = "",
        driver_id: Any = None,
        driver_name: str | None = None,
        reason: str | None = None,
        cancelled_by: str | None = None,
        **kwargs: Any,
    ) -> Order | None:
        """Update order status in NestJS API."""
        effective_status = status or kwargs.get("new_status", "pending")
        status_map = {
            "in_route": "EN_RUTA",
            "en_ruta": "EN_RUTA",
            "delivered": "ENTREGADO",
            "entregado": "ENTREGADO",
            "cancelled": "CANCELADO",
            "cancelado": "CANCELADO",
            "pending": "PENDIENTE",
            "pendiente": "PENDIENTE",
            "assigned": "ASIGNADO",
        }
        api_status = status_map.get(effective_status.lower(), effective_status.upper())

        body = {
            "status": api_status,
            "description": reason or notes_append or f"Estado actualizado a {api_status}",
            "actor": "CHOFER" if driver_id else "SISTEMA",
        }
        if driver_id:
            body["driverId"] = str(driver_id)
        if reason:
            body["rejectionReason"] = reason

        try:
            res = api_patch(f"/orders/{order_id}/status", body, timeout=5)
            if isinstance(res, dict):
                self._record_api_success()
                return self._parse_api_order(res, tenant_id)
        except Exception as e:
            self._record_api_failure(e)

        if self.fallback_repo:
            return self.fallback_repo.update_order_status(
                tenant_id=tenant_id,
                order_id=order_id,
                status=effective_status,
                notes_append=notes_append or reason or "",
            )
        return None

    def cancel_order(
        self,
        tenant_id: str,
        order_id: Any,
        cancelled_by: str = "el cliente",
        reason: str = "Cancelado a solicitud del cliente",
    ) -> Order | None:
        """Cancel order via REST API."""
        return self.update_order_status(
            tenant_id=tenant_id,
            order_id=order_id,
            new_status="cancelled",
            reason=reason,
            cancelled_by=cancelled_by,
        )

    def _parse_api_order(self, ord_dict: dict, tenant_id: str) -> Order:
        """Convert API order dictionary to Order model."""
        items = []
        for it in ord_dict.get("items", []):
            p_info = it.get("product") or {}
            items.append(
                OrderItem(
                    product_id=it.get("productId", ""),
                    product_name=it.get("productName", p_info.get("name", "Gas LP")),
                    quantity=int(it.get("quantity", 1)),
                    unit_price=float(it.get("unitPrice", p_info.get("pricePerUnit", 0.0))),
                    subtotal=float(it.get("subtotal", 0.0)),
                )
            )

        raw_id = ord_dict.get("orderNumber") or ord_dict.get("id") or 1
        digits = re.findall(r"\d+", str(raw_id))
        num_id = int(digits[-1]) if digits else (hash(str(raw_id)) % 100000)

        # Store in mapping cache so lookups by num_id, UUID, or orderNumber all succeed
        self._order_id_map[num_id] = ord_dict
        self._order_id_map[str(num_id)] = ord_dict
        if ord_dict.get("id"):
            self._order_id_map[str(ord_dict.get("id"))] = ord_dict
        if ord_dict.get("orderNumber"):
            self._order_id_map[str(ord_dict.get("orderNumber"))] = ord_dict

        cust = ord_dict.get("customer") or {}
        local_status = self._map_api_status_to_local(ord_dict.get("status"))
        sched_for = ord_dict.get("scheduledFor") or ord_dict.get("scheduled_for")
        sched_schedule = ord_dict.get("deliverySchedule") or ord_dict.get("delivery_schedule") or (sched_for or "Lo antes posible")

        if sched_for and local_status == "confirmed":
            local_status = "scheduled"

        return Order(
            id=num_id,
            tenant_id=tenant_id,
            channel=str(ord_dict.get("channel") or "dashboard").lower(),
            channel_user_id=str(ord_dict.get("channelUserId") or ord_dict.get("customerPhone") or ""),
            customer_name=ord_dict.get("customerName") or cust.get("name") or "Cliente",
            customer_phone=ord_dict.get("customerPhone") or cust.get("phone") or "",
            delivery_address=ord_dict.get("deliveryAddress") or cust.get("address") or "",
            delivery_schedule=sched_schedule,
            total_amount=float(ord_dict.get("totalAmount", 0.0)),
            status=local_status,
            payment_method=ord_dict.get("paymentMethod", "Efectivo"),
            notes=ord_dict.get("notes") or "",
            driver_id=ord_dict.get("driverId"),
            driver_name=ord_dict.get("driverName"),
            scheduled_for=sched_for,
            items=items,
            created_at=ord_dict.get("createdAt") or ord_dict.get("created_at"),
        )

    def assign_order_to_driver(
        self,
        tenant_id: str,
        order_id: Any,
        driver_id: Any,
        delivery_lat: float | None = None,
        delivery_lng: float | None = None,
    ) -> Order | None:
        """Assign an order to a driver with geocoded coordinates and update status to assigned."""
        driver_obj = self.get_driver(driver_id) if driver_id else None
        driver_name = driver_obj.name if driver_obj else None
        driver_phone = driver_obj.phone if driver_obj else None

        # Update cache if present
        if order_id in self._order_id_map or str(order_id) in self._order_id_map:
            ord_data = self._order_id_map.get(order_id) or self._order_id_map.get(str(order_id))
            if ord_data:
                ord_data["status"] = "ASIGNADO"
                ord_data["driverId"] = driver_id
                ord_data["driverName"] = driver_name
                ord_data["driverPhone"] = driver_phone

        # Try API update
        try:
            body = {
                "status": "ASIGNADO",
                "driverId": str(driver_id) if driver_id else None,
                "driverName": driver_name,
                "driverPhone": driver_phone,
            }
            api_patch(f"/orders/{order_id}/status", body, timeout=5)
        except Exception:
            pass

        if self.fallback_repo:
            try:
                self.fallback_repo.assign_order_to_driver(
                    tenant_id=tenant_id,
                    order_id=order_id,
                    driver_id=driver_id,
                    delivery_lat=delivery_lat,
                    delivery_lng=delivery_lng,
                )
            except Exception:
                pass

        order = self.get_order_by_id(tenant_id, order_id)
        if order:
            order.status = "assigned"
            order.driver_id = driver_id
            order.driver_name = driver_name
            return order
        return None

    # -------------------------------------------------------------------------
    # Driver & Vehicle & Fallback Methods
    # -------------------------------------------------------------------------
    def get_driver(self, driver_id: Any) -> Driver | None:
        if self.fallback_repo:
            return self.fallback_repo.get_driver(driver_id)
        return None

    def get_driver_by_telegram(self, telegram_user_id: int) -> Driver | None:
        if self.fallback_repo:
            return self.fallback_repo.get_driver_by_telegram(telegram_user_id)
        return None

    def get_all_drivers(self, tenant_id: str) -> list[Driver]:
        if self.fallback_repo:
            return self.fallback_repo.get_all_drivers(tenant_id)
        return []

    def get_all_drivers_admin(self, tenant_id: str = "petroil") -> list[dict[str, Any]]:
        if self.fallback_repo:
            return self.fallback_repo.get_all_drivers_admin(tenant_id)
        return []

    def get_all_vehicles(self, tenant_id: str = "petroil") -> list[Any]:
        if self.fallback_repo:
            return self.fallback_repo.get_all_vehicles(tenant_id)
        return []

    def get_all_vehicles_admin(self, tenant_id: str = "petroil") -> list[dict[str, Any]]:
        if self.fallback_repo:
            return self.fallback_repo.get_all_vehicles_admin(tenant_id)
        return []

    def save_order_rating(self, tenant_id: str, order_id: Any, driver_id: Any, customer_id: Any, rating: int, comment: str = "") -> None:
        if self.fallback_repo:
            self.fallback_repo.save_order_rating(tenant_id, order_id, driver_id, customer_id, rating, comment)

    def update_order_rating_feedback(self, tenant_id: str, order_id: Any, comment: str) -> None:
        if self.fallback_repo:
            self.fallback_repo.update_order_rating_feedback(tenant_id, order_id, comment)

    def __getattr__(self, item: str) -> Any:
        """If fallback_repo is present, delegate; otherwise return a no-op callable or None."""
        if self.fallback_repo:
            return getattr(self.fallback_repo, item)
        def _noop(*args: Any, **kwargs: Any) -> Any:
            return None
        return _noop

