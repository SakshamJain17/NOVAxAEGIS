from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(
    prefix="/api/approvals",
    tags=["approvals"],
)


class ApprovalDecision(BaseModel):

    decision: Literal[
        "approve",
        "deny",
    ]


def get_runtime():

    from app.main import get_runtime

    return get_runtime()


# ======================================================================
# PENDING
# ======================================================================


@router.get("")
async def pending_approvals():

    runtime = get_runtime()

    approvals = await runtime.approvals.pending()

    return {
        "success": True,
        "approvals": approvals,
        "count": len(approvals),
    }


# ======================================================================
# RESOLVE
# ======================================================================


@router.post("/{request_id}")
async def resolve_approval(
    request_id: str,
    request: ApprovalDecision,
):

    runtime = get_runtime()

    approved = (
        request.decision == "approve"
    )

    try:

        result = await runtime.approvals.resolve(
            request_id,
            approved=approved,
        )

        return {
            "success": True,
            "resolved": True,
            "request_id": request_id,
            "decision": request.decision,
            "result": result,
        }

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc