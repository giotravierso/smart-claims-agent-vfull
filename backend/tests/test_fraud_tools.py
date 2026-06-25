"""Tests unitarios para los detectores de fraude."""
from datetime import datetime, timedelta

import pytest

from app.tools.fraud_tools import (
    check_amount_anomaly,
    check_document_coherence,
    check_duplicate_claims,
    check_ofac_sanctions,
    compute_risk_score,
)


# ── Detector 1: OFAC ──────────────────────────────────────────────────────

class TestOFACSanctions:

    def test_no_match_for_normal_name(self):
        result = check_ofac_sanctions("Juan Garcia")
        assert result.matched is False

    def test_exact_match_detected(self):
        result = check_ofac_sanctions("Viktor Nikolaev Kozlov")
        assert result.matched is True
        assert result.sanction_list == "SDN"

    def test_fuzzy_match_with_typo(self):
        # Pequena variacion ortografica debe detectarse
        result = check_ofac_sanctions("Viktor Nikolayev Kozlov")  # 'y' anadida
        assert result.matched is True

    def test_empty_name_returns_no_match(self):
        result = check_ofac_sanctions("")
        assert result.matched is False
        assert result.similarity == 0.0


# ── Detector 2: Anomalia de importe ──────────────────────────────────────

class TestAmountAnomaly:

    def test_normal_amount_not_flagged(self):
        result = check_amount_anomaly("danys_propis", 2500.0)
        assert result.flagged is False
        assert result.exceeded_max is False

    def test_amount_over_max_is_flagged(self):
        result = check_amount_anomaly("danys_propis", 15000.0)
        assert result.flagged is True
        assert result.exceeded_max is True

    def test_extreme_zscore_is_flagged(self):
        # mean=800, std=400; importe 5000 -> Z=10.5
        result = check_amount_anomaly("danys_mecanics", 5000.0)
        assert result.flagged is True


# ── Detector 3: Duplicados ───────────────────────────────────────────────

class TestDuplicateClaims:

    def test_no_duplicate_for_empty_history(self):
        result = check_duplicate_claims("C-A", "danys_propis", [])
        assert result.found is False

    def test_recent_duplicate_detected(self):
        recent = (datetime.utcnow() - timedelta(days=30)).isoformat()
        history = [{"id": "CLM-X", "client_id": "C-A",
                    "claim_type": "danys_propis", "created_at": recent}]
        result = check_duplicate_claims("C-A", "danys_propis", history)
        assert result.found is True
        assert "CLM-X" in result.matching_claim_ids

    def test_old_claim_not_flagged(self):
        old = (datetime.utcnow() - timedelta(days=200)).isoformat()
        history = [{"id": "CLM-Y", "client_id": "C-A",
                    "claim_type": "danys_propis", "created_at": old}]
        result = check_duplicate_claims("C-A", "danys_propis", history)
        assert result.found is False


# ── Detector 4: Coherencia documental ────────────────────────────────────

class TestDocumentCoherence:

    def test_coherent_documents_pass(self):
        result = check_document_coherence({
            "incident_date": "2026-05-10",
            "claim_date":    "2026-05-12",
        })
        assert result.incoherent is False

    def test_future_incident_date_detected(self):
        future = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
        result = check_document_coherence({"incident_date": future})
        assert result.incoherent is True

    def test_claim_before_incident_detected(self):
        result = check_document_coherence({
            "incident_date": "2026-05-10",
            "claim_date":    "2026-04-01",   # reclamacion antes del siniestro
        })
        assert result.incoherent is True


# ── Scoring compuesto ────────────────────────────────────────────────────

class TestRiskScore:

    def test_ofac_match_always_blocks(self):
        ofac = check_ofac_sanctions("Viktor Nikolaev Kozlov")
        amount_ok = check_amount_anomaly("danys_propis", 2500.0)
        dup_ok = check_duplicate_claims("C-A", "danys_propis", [])
        doc_ok = check_document_coherence({"incident_date": "2026-05-10"})
        score, verdict = compute_risk_score(ofac, amount_ok, dup_ok, doc_ok)
        assert score == 1.0
        assert verdict == "BLOCKED"

    def test_clear_when_no_signals(self):
        ofac = check_ofac_sanctions("Juan Garcia")
        amount_ok = check_amount_anomaly("danys_propis", 2500.0)
        dup_ok = check_duplicate_claims("C-A", "danys_propis", [])
        doc_ok = check_document_coherence({"incident_date": "2026-05-10"})
        score, verdict = compute_risk_score(ofac, amount_ok, dup_ok, doc_ok)
        assert verdict == "CLEAR"
        assert score < 0.25
