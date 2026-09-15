"""Vehicle data model for fleet management."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class Vehicle(BaseModel):
    """Vehicle unit profile (pipa de gas o camioneta de cilindros)."""

    id: int | str | None = None
    tenant_id: str = "petroil"
    unit_identifier: str  # Ej: PIPA-01, CAM-04, C-02
    plate: str            # Ej: VZ-8472-A
    model: str            # Ej: Ford F-350 2022, Dodge Ram 4000
    vehicle_type: Literal["pipa", "camioneta", "ambos"] = "camioneta"
    pipa_capacity_liters: float | None = None   # Litros de gas si es pipa
    cylinder_capacity_count: int | None = None  # Capacidad máxima de cilindros si carga cilindros
    status: Literal["active", "maintenance", "inactive"] = "active"
    notes: str = ""
    assigned_driver_id: int | str | None = None
    assigned_driver_name: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_display(self) -> str:
        """Format vehicle summary string."""
        type_icon = "🚛 Pipa" if self.vehicle_type == "pipa" else ("🛻 Camioneta" if self.vehicle_type == "camioneta" else "🚚 Mixto")
        cap_str = ""
        if self.vehicle_type == "pipa" and self.pipa_capacity_liters:
            cap_str = f" | {self.pipa_capacity_liters:,.0f} L"
        elif self.cylinder_capacity_count:
            cap_str = f" | {self.cylinder_capacity_count} Cilindros"
        return f"{type_icon} {self.unit_identifier} [{self.plate}] - {self.model}{cap_str}"
