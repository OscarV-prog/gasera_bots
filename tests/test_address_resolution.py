"""Tests for GPS reverse geocoding and human-readable address resolution."""

import unittest
from src.services.geocoding import reverse_geocode, resolve_gps_address_to_name
from src.repositories import get_repository
from src.models.customer import CustomerAddress


class TestAddressResolution(unittest.TestCase):
    def test_reverse_geocode_returns_street_name(self):
        # Coordinates in Mazatlán Centro
        addr = reverse_geocode(23.199568, -106.423632)
        self.assertIsInstance(addr, str)
        self.assertNotIn("latitud", addr.lower())
        self.assertNotIn("longitud", addr.lower())
        # Should include street and Mazatlán
        self.assertTrue("calle" in addr.lower() or "heriberto" in addr.lower() or "centro" in addr.lower())

    def test_resolve_gps_address_to_name(self):
        raw = "Ubicación GPS (23.19957, -106.42363) - Edificio color amarillo"
        resolved = resolve_gps_address_to_name(raw)
        self.assertNotIn("Ubicación GPS", resolved)
        self.assertIn("Edificio color amarillo", resolved)
        self.assertTrue("heriberto" in resolved.lower() or "centro" in resolved.lower())

    def test_resolve_normal_address_unchanged(self):
        normal = "Av. Del Mar 123, Mazatlán"
        self.assertEqual(resolve_gps_address_to_name(normal), normal)

    def test_repo_get_customer_addresses_auto_resolves(self):
        repo = get_repository()
        # Test customer 4 who previously had GPS coordinates
        addrs = repo.get_customer_addresses(4)
        for a in addrs:
            self.assertNotIn("Ubicación GPS", a.address)


if __name__ == "__main__":
    unittest.main()
