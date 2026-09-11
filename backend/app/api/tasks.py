from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.runtime.service import TaskService


router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"],
)


# ======================================================================
# REQUEST MODELS
# ======================================================================


class CreateTaskRequest(BaseModel):

    instruction: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
    )

    constraints: list[str] = Field(
        default_factory=list,
        max_length=100,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class InterruptTaskRequest(BaseModel):

    new_instruction: str | None = Field(
        default=None,
        max_length=10_000,
    )

    constraints: list[str] | None = Field(
        default=None,
        max_length=100,
    )


# ======================================================================
# SERVICE
# ======================================================================


def task_service() -> TaskService:

    from app.main import get_runtime

    runtime = get_runtime()

    return runtime.task_service


# ======================================================================
# CREATE
# ======================================================================


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    request: CreateTaskRequest,
):

    try:

        task = await task_service().create(
            instruction=request.instruction,
            constraints=request.constraints,
            metadata=request.metadata,
        )

        return {
            "success": True,
            "task": task,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# ======================================================================
# LIST
# ======================================================================


@router.get("")
async def list_tasks():

    tasks = await task_service().list()

    return {
        "success": True,
        "tasks": tasks,
        "count": len(tasks),
    }


# ======================================================================
# ACTIVE EXECUTIONS
# ======================================================================


@router.get("/runtime/executions")
async def active_executions():

    executions = (
        await task_service()
        .active_executions()
    )

    return {
        "success": True,
        "executions": executions,
        "count": len(executions),
    }


# ======================================================================
# GET TASK
# ======================================================================


@router.get("/{task_id}")
async def get_task(
    task_id: str,
):

    try:

        task = await task_service().get(
            task_id
        )

        return {
            "success": True,
            "task": task,
        }

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# ======================================================================
# RUN
# ======================================================================


@router.post("/{task_id}/run")
async def run_task(
    task_id: str,
):

    try:

        task = await task_service().run(
            task_id
        )

        return {
            "success": True,
            "accepted": True,
            "task": task,
        }

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


# ======================================================================
# INTERRUPT
# ======================================================================


@router.post("/{task_id}/interrupt")
async def interrupt_task(
    task_id: str,
    request: InterruptTaskRequest,
):

    try:

        task = await task_service().interrupt(
            task_id,
            new_instruction=request.new_instruction,
            constraints=request.constraints,
        )

        return {
            "success": True,
            "interrupted": True,
            "task": task,
        }

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# ======================================================================
# CANCEL
# ======================================================================


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
):

    try:

        task = await task_service().cancel(
            task_id
        )

        return {
            "success": True,
            "cancelled": True,
            "task": task,
        }

    except KeyError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc