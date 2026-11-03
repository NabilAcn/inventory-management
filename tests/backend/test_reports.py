"""Tests for /api/reports/* endpoints, including global filter support."""


def test_quarterly_returns_expected_fields(client):
    response = client.get("/api/reports/quarterly")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    for row in data:
        for key in ("quarter", "total_orders", "total_revenue", "avg_order_value", "fulfillment_rate"):
            assert key in row


def test_quarterly_sorted_chronologically(client):
    data = client.get("/api/reports/quarterly").json()
    keys = [(r["quarter"].split("-")[1], r["quarter"]) for r in data]
    assert keys == sorted(keys)


def test_quarterly_respects_status_filter(client):
    all_total = sum(r["total_orders"] for r in client.get("/api/reports/quarterly").json())
    delivered = client.get("/api/reports/quarterly?status=Delivered").json()
    assert sum(r["total_orders"] for r in delivered) < all_total
    # Every remaining order is Delivered, so fulfillment must be 100%
    assert all(r["fulfillment_rate"] == 100 for r in delivered)


def test_monthly_trends_respects_filters(client):
    all_months = client.get("/api/reports/monthly-trends").json()
    filtered = client.get("/api/reports/monthly-trends?status=Delivered").json()
    assert sum(m["order_count"] for m in filtered) < sum(m["order_count"] for m in all_months)


def test_monthly_trends_month_filter(client):
    month = client.get("/api/reports/monthly-trends").json()[0]["month"]
    data = client.get(f"/api/reports/monthly-trends?month={month}").json()
    assert [m["month"] for m in data] == [month]


def test_reports_empty_when_no_match(client):
    assert client.get("/api/reports/quarterly?warehouse=does-not-exist").json() == []
    assert client.get("/api/reports/monthly-trends?warehouse=does-not-exist").json() == []
