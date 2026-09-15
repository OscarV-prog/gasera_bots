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
        api_items = []
        total_calc = 0.0
        for it in items:
            p_id = it.get("product_id") or it.get("productId") or "gas-lp-30kg"
            qty = int(it.get("quantity") or it.get("qty") or 1)
            price = float(it.get("unit_price") or it.get("price") or 0.0)
            if price == 0.0:
                p_obj = self.get_product_by_id(tenant_id, str(p_id))
                price = p_obj.price if p_obj else 705.0
            total_calc += price * qty
            api_items.append({"productId": str(p_id), "quantity": qty})

        body = {
            "tenantId": tenant_id,
            "customerName": customer_name,
            "customerPhone": customer_phone,
            "deliveryAddress": delivery_address,
            "colonia": "Mazatlán",
            "city": "Mazatlán",
            "channel": channel.upper() if channel else "TELEGRAM",
            "paymentMethod": payment_method.upper() if payment_method else "EFECTIVO",
            "notes": notes or "",
            "scheduledFor": scheduled_for if scheduled_for else (None if "antes posible" in delivery_schedule.lower() else delivery_schedule),
            "items": api_items,
        }

        try:
            res = api_post("/orders", body, timeout=5)
            if isinstance(res, dict) and res.get("id"):
                self._record_api_success()
                logger.info(f"[ApiRepository] Order created in NestJS API: ID={res.get('id')}, OrderNumber={res.get('orderNumber')}")
                return self._parse_api_order(res, tenant_id)
        except Exception as e:
            self._record_api_failure(e)

        if self.fallback_repo:
            return self.fallback_repo.create_order(
                tenant_id=tenant_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                delivery_address=delivery_address,
                items=items,
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

        # Fallback in-memory order representation
        order_items = [
            OrderItem(
                product_id=it.get("productId", ""),
                product_name=it.get("productName", "Gas LP"),
                quantity=it.get("quantity", 1),
                unit_price=float(it.get("unitPrice", 0.0)),
                subtotal=float(it.get("subtotal", 0.0)),
            )
            for it in items
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
        """Fetch order details from PostgreSQL API."""
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
                    if str(o.get("id")) == str(order_id) or str(o.get("orderNumber")) == str(order_id):
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
                    o_phone = re.sub(r"\D", "", str(o.get("customerPhone", "")))
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
            items.append(
                OrderItem(
                    product_id=it.get("productId", ""),
                    product_name=it.get("productName", it.get("name", "Gas LP")),
                    quantity=int(it.get("quantity", 1)),
                    unit_price=float(it.get("unitPrice", it.get("price", 0.0))),
                    subtotal=float(it.get("subtotal", 0.0)),
                )
            )

        raw_id = ord_dict.get("id") or ord_dict.get("orderNumber") or 1
        num_id = int(raw_id) if str(raw_id).isdigit() else (int(time.time()) % 100000)

        return Order(
            id=num_id,
            tenant_id=tenant_id,
            customer_name=ord_dict.get("customerName", "Cliente"),
            customer_phone=ord_dict.get("customerPhone", ""),
            delivery_address=ord_dict.get("deliveryAddress", ""),
            total_amount=float(ord_dict.get("totalAmount", 0.0)),
            status=str(ord_dict.get("status", "pending")).lower(),
            payment_method=ord_dict.get("paymentMethod", "Efectivo"),
            items=items,
        )

    # -------------------------------------------------------------------------
    # Driver & Rating methods
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
