"""
Esquemas Pydantic para la API de reclamaciones.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Request ───────────────────────────────────────────────────────────────

class ClaimCreateRequest(BaseModel):
    """Cuerpo del POST /api/v1/claims/"""
    claim_id:         str | None = Field(
        default=None, description="Si se omite, el backend genera uno automatico."
    )
    client_id:        str
    client_email:     str       = "cliente@example.com"
    claim_type:       str       = Field(
        default="default",
        description="danys_propis | responsabilitat | robatori | danys_mecanics | default",
    )
    channel:          str       = "email"
    amount_requested: float     = Field(default=0.0, ge=0)
    documents:        list[str] = Field(default_factory=list)
    text:             str       = ""


# ── Responses ─────────────────────────────────────────────────────────────

class ClaimResponse(BaseModel):
    """Respuesta del POST /api/v1/claims/ y de GET /{id}."""
    model_config = ConfigDict(from_attributes=True)

    claim_id:           str
    status:             str
    decision:           str | None       = None
    amount_paid:        float | None     = None
    amount_requested:   float | None     = None
    hitl_required:      bool             = False
    termination_reason: str | None       = None
    reasoning_trace:    list[str]        = Field(default_factory=list)


class AgentDecisionItem(BaseModel):
    """Una decision del Chain of Thought persistida."""
    model_config = ConfigDict(from_attributes=True)

    id:            int
    agent:         str
    action:        str
    reasoning:     str
    confidence:    float | None = None
    hitl_required: bool         = False
    created_at:    str | None   = None


class ClaimTraceResponse(BaseModel):
    """Respuesta del GET /{id}/trace."""
    claim_id:  str
    decisions: list[AgentDecisionItem]


class ClaimListItem(BaseModel):
    """Item del listado de reclamaciones."""
    model_config = ConfigDict(from_attributes=True)

    id:               str
    client_id:        str
    claim_type:       str
    status:           str
    amount_requested: float | None
    amount_approved:  float | None
    created_at:       str | None = None
