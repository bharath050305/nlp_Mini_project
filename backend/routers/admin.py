"""
backend/routers/admin.py

Staff-only admin views. Currently just the Agent Registry (v5) — a
read-only listing of every agent's declared capabilities, for
explainability. See agents/registry.py's docstring for what this is
and, importantly, what it deliberately is not (a runtime permission
sandbox).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agents.registry import AGENT_REGISTRY
from backend.deps import require_role
from backend.schemas_api import AgentCapabilityOut

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_role("staff"))])


@router.get("/agents", response_model=list[AgentCapabilityOut])
def list_agents() -> list[AgentCapabilityOut]:
    return [
        AgentCapabilityOut(
            name=a.name, module=a.module, description=a.description, reads=a.reads, writes=a.writes,
            risk=a.risk, autonomy=a.autonomy,
        )
        for a in AGENT_REGISTRY
    ]
