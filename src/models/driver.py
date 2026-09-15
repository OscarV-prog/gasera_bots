"""Driver data model for delivery dispatch."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class Driver(BaseModel):
    """Delivery driver profile."""

    id: int | str | None = None
    tenant_id: str = "petroil"
    name: str
    phone: str
    telegram_user_id: str | None = None
    vehicle_id: int | str | None = None
    unit_identifier: str | None = None
    vehicle_type: Literal["cilindros", "estacionario", "ambos"] = "cilindros"
    vehicle_plate: str = ""
    zone: str = "General"
    is_available: bool = True
    current_lat: float | None = None
    current_lng: float | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_display(self) -> str:
        """Format driver summary for display."""
        status_icon = "🟢 Disponible" if self.is_available else "🔴 Ocupado / Fuera de turno"
        v_icon = "🚛 Pipa Estacionaria" if self.vehicle_type == "estacionario" else "🛻 Camioneta de Cilindros"
        plate_str = f" ({self.vehicle_plate})" if self.vehicle_plate else ""
        return (
            f"👤 **{self.name}** {plate_str}\n"
            f"📱 Tel: {self.phone}\n"
            f"🚘 Tipo: {v_icon}\n"
            f"📍 Zona: {self.zone}\n"
            f"⚡ Estado: {status_icon}"
        )
