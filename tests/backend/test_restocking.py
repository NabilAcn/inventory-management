"""Tests for the restocking order endpoints."""
from datetime import date, timedelta


class TestDemandForecastCostFields:
    """Demand forecasts carry the data needed to price a restock."""

    def test_forecasts_include_cost_supplier_and_lead_time(self, client):
        response = client.get("/api/demand")
        assert response.status_code == 200
        for forecast in response.json():
            assert forecast["unit_cost"] > 0
            assert forecast["supplier_name"]
            assert forecast["lead_time_days"] > 0


class TestRestockingOrderEndpoints:
    """POST/GET /api/restocking-orders"""

    def _forecast(self, client, sku):
        return next(f for f in client.get("/api/demand").json() if f["item_sku"] == sku)

    def test_create_order_prices_from_server_data(self, client):
        wdg = self._forecast(client, "WDG-001")
        response = client.post("/api/restocking-orders", json={"items": [{"item_sku": "WDG-001", "quantity": 10}]})
        assert response.status_code == 201
        order = response.json()
        assert order["id"] == "RST-0001"
        assert order["status"] == "Submitted"
        assert order["total_cost"] == round(10 * wdg["unit_cost"], 2)
        assert order["items"][0]["supplier_name"] == wdg["supplier_name"]

    def test_lead_time_is_slowest_line(self, client):
        slow = self._forecast(client, "MTR-304")
        fast = self._forecast(client, "FLT-405")
        response = client.post("/api/restocking-orders", json={"items": [
            {"item_sku": "FLT-405", "quantity": 5},
            {"item_sku": "MTR-304", "quantity": 2},
        ]})
        order = response.json()
        assert order["lead_time_days"] == max(slow["lead_time_days"], fast["lead_time_days"])
        expected = date.today() + timedelta(days=order["lead_time_days"])
        assert order["expected_delivery"] == expected.isoformat()

    def test_duplicate_skus_are_merged(self, client):
        response = client.post("/api/restocking-orders", json={"items": [
            {"item_sku": "WDG-001", "quantity": 3},
            {"item_sku": "WDG-001", "quantity": 4},
        ]})
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["quantity"] == 7

    def test_unknown_sku_returns_404(self, client):
        response = client.post("/api/restocking-orders", json={"items": [{"item_sku": "NOPE-999", "quantity": 1}]})
        assert response.status_code == 404
        assert client.get("/api/restocking-orders").json() == []

    def test_invalid_quantity_returns_422(self, client):
        for quantity in (0, -5):
            response = client.post("/api/restocking-orders", json={"items": [{"item_sku": "WDG-001", "quantity": quantity}]})
            assert response.status_code == 422

    def test_empty_items_returns_422(self, client):
        response = client.post("/api/restocking-orders", json={"items": []})
        assert response.status_code == 422

    def test_get_returns_newest_first(self, client):
        client.post("/api/restocking-orders", json={"items": [{"item_sku": "WDG-001", "quantity": 1}]})
        client.post("/api/restocking-orders", json={"items": [{"item_sku": "BRG-102", "quantity": 1}]})
        orders = client.get("/api/restocking-orders").json()
        assert [o["id"] for o in orders] == ["RST-0002", "RST-0001"]
