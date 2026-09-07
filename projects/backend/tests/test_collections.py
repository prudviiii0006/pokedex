"""
AlgoRacers — Tests for Canonical 2026 F1 Dataset, Collection Book & Card History
Module: tests/test_collections.py
================================================================================
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.collection_service import collection_service
from backend.rewards.driver_pool import DriverPool

client = TestClient(app)

def test_canonical_22_drivers():
    pool = DriverPool()
    drivers = pool.get_all_drivers()
    assert len(drivers) == 22, f"Expected exactly 22 canonical drivers, found {len(drivers)}"
    
    # Check all 11 constructors exist
    constructors = pool.get_all_constructors()
    assert len(constructors) == 11, f"Expected 11 constructors, found {len(constructors)}"
    
    for c in constructors:
        team_drivers = pool.get_drivers_by_constructor(c["id"])
        assert len(team_drivers) == 2, f"Constructor {c['name']} must have exactly 2 drivers, found {len(team_drivers)}"

def test_get_drivers_api():
    response = client.get("/drivers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 22
    assert "name" in data[0]
    assert "constructor_name" in data[0]
    assert "stats" in data[0]

def test_get_constructors_api():
    response = client.get("/constructors")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 11
    assert data[0]["drivers_count"] == 2

def test_wallet_collection_book_api():
    wallet = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    response = client.get(f"/collection/{wallet}")
    assert response.status_code == 200
    data = response.json()
    assert data["wallet_address"] == wallet
    assert data["total_canonical_drivers"] == 22
    assert "overall_completion_percentage" in data
    assert "constructors" in data
    assert len(data["constructors"]) == 11

def test_card_details_and_comparison_api():
    wallet = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    # Create direct purchase to ensure at least 2 cards exist
    p1 = client.post("/purchases/direct", json={"pack_id": "basic", "wallet_address": wallet}).json()
    p2 = client.post("/purchases/direct", json={"pack_id": "premium", "wallet_address": wallet}).json()
    
    aid1 = p1["asset_id"]
    aid2 = p2["asset_id"]
    
    # Test card details
    res_card = client.get(f"/cards/{aid1}")
    assert res_card.status_code == 200
    c1 = res_card.json()
    assert c1["asset_id"] == aid1
    assert "effective_stats" in c1
    assert "level" in c1
    assert c1["lock_status"] == "AVAILABLE"
    
    # Test card history
    res_hist = client.get(f"/cards/{aid1}/history")
    assert res_hist.status_code == 200
    h1 = res_hist.json()
    assert "events" in h1
    assert len(h1["events"]) >= 1
    assert h1["events"][0]["category"] in ["ON-CHAIN", "GAME EVENT"]
    
    # Test card comparison
    res_comp = client.get(f"/cards/compare?asset_a={aid1}&asset_b={aid2}")
    assert res_comp.status_code == 200
    comp = res_comp.json()
    assert comp["label"] == "AlgoRacers Gameplay Stats"
    assert "stats_comparison" in comp
    assert "speed" in comp["stats_comparison"]
