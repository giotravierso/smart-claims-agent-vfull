"""
Tests de integracion de la API REST.
Usan httpx.AsyncClient sobre la app FastAPI con SQLite en memoria.
"""
import os
import random

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.pop("ANTHROPIC_API_KEY", None)


@pytest.fixture(autouse=True)
def _fixed_seed():
    """Semilla fija para que check_fraud (mock random) sea reproducible."""
    random.seed(7)


@pytest.mark.asyncio
async def test_create_claim_returns_decision(test_db):
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/api/v1/claims/", json={
            "client_id":        "C-API",
            "claim_type":       "danys_propis",
            "amount_requested": 2500.0,
            "documents":        ["foto_danys", "factura", "denuncia_companyia"],
            "text":             "Reclamacion por danos en mi vehiculo.",
        })
    assert response.status_code == 201
    body = response.json()
    assert body["status"] in {"resolved", "rejected", "pending_review", "validating"}
    assert "reasoning_trace" in body


@pytest.mark.asyncio
async def test_get_claim_after_processing(test_db):
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # 1. Crea
        post = await client.post("/api/v1/claims/", json={
            "claim_id":         "CLM-GET",
            "client_id":        "C-API-2",
            "claim_type":       "danys_propis",
            "amount_requested": 2500.0,
            "documents":        ["foto_danys", "factura", "denuncia_companyia"],
        })
        assert post.status_code == 201

        # 2. Lee
        get = await client.get("/api/v1/claims/CLM-GET")
        assert get.status_code == 200
        assert get.json()["claim_id"] == "CLM-GET"


@pytest.mark.asyncio
async def test_get_claim_not_found_returns_404(test_db):
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/claims/CLM-NO-EXISTE")
    assert response.status_code == 404
