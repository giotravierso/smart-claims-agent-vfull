"""
Modelos SQLAlchemy del dominio Smart-Claims.

Tres entidades:
- Claim:          expediente de reclamación.
- AgentDecision:  log de decisión de un agente (Chain of Thought persistido).
- HitlFeedback:   override humano sobre una decisión automática.

El `values_callable` en el Enum del status es esencial: sin él, SQLAlchemy
guarda los nombres Python ('OPEN') mientras MariaDB tiene los valores en
minúsculas ('open'), provocando un LookupError al leer.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ClaimStatus(str, enum.Enum):
    OPEN            = "open"
    VALIDATING      = "validating"
    EXTRACTING      = "extracting"
    CHECKING_POLICY = "checking_policy"
    CHECKING_FRAUD  = "checking_fraud"
    RESOLVED        = "resolved"
    REJECTED        = "rejected"
    PENDING_REVIEW  = "pending_review"
    CLOSED          = "closed"


class Claim(Base):
    __tablename__ = "claims"

    id:         Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id:  Mapped[str] = mapped_column(String(64), nullable=False)
    claim_type: Mapped[str] = mapped_column(String(64), nullable=False)
    channel:    Mapped[str] = mapped_column(String(16), default="email")

    status: Mapped[ClaimStatus] = mapped_column(
        Enum(
            ClaimStatus,
            values_callable=lambda x: [e.value for e in x],
            native_enum=True,
            name="claimstatus",
        ),
        default=ClaimStatus.OPEN,
    )

    amount_requested: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_approved:  Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    decisions: Mapped[list["AgentDecision"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan",
    )


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id:       Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.id", ondelete="CASCADE"),
    )

    agent:         Mapped[str]          = mapped_column(String(48), nullable=False)
    action:        Mapped[str]          = mapped_column(String(128), nullable=False)
    reasoning:     Mapped[str]          = mapped_column(Text,  nullable=False)
    confidence:    Mapped[float | None] = mapped_column(Float, nullable=True)
    hitl_required: Mapped[bool]         = mapped_column(Boolean, default=False)
    created_at:    Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)

    claim: Mapped["Claim"] = relationship(back_populates="decisions")


class HitlFeedback(Base):
    __tablename__ = "hitl_feedback"

    id:          Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    claim_id:    Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.id", ondelete="CASCADE"),
    )
    decision_id: Mapped[int] = mapped_column(
        ForeignKey("agent_decisions.id", ondelete="CASCADE"),
    )

    reviewer:        Mapped[str]          = mapped_column(String(64), nullable=False)
    original_action: Mapped[str]          = mapped_column(String(128), nullable=False)
    final_action:    Mapped[str]          = mapped_column(String(128), nullable=False)
    override_reason: Mapped[str | None]   = mapped_column(Text, nullable=True)
    created_at:      Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow)
