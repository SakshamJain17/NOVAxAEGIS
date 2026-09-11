from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.runtime.container import AegisRuntime


router = APIRouter(
    prefix="/api",
    tags=["aegis"],
)


class TaskRequest(BaseModel):

    instruction: str = Field(
        min_length=1,
        max_length=20_000,
    )

    constraints: dict = Field(
        default_factory=dict
    )


class TaskResponse(BaseModel):

    task_id: UUID

    version: int

    status: str

    objective: str | None = None

    response: str | None = None


def create_router(
    runtime: AegisRuntime,
) -> APIRouter:

    api = APIRouter(
        prefix="/api",
        tags=["aegis"],
    )

    @api.post(
        "/tasks",
        response_model=TaskResponse,
    )
    async def create_task(
        request: TaskRequest,
    ):

        task = await runtime.task_supervisor.create_task(
            instruction=request.instruction,
            constraints=request.constraints,
        )

        try:

            plan = await runtime.agent.run(
                task
            )

        except Exception as exc:

            task.status = task.status.FAILED
            task.touch()

            raise HTTPException(
                status_code=500,
                detail=str(exc),
            ) from exc

        return TaskResponse(
            task_id=task.task_id,
            version=task.version,
            status=task.status.value,
            objective=plan.objective,
            response=plan.final_response,
        )

    @api.get(
        "/tasks/{task_id}",
    )
    async def get_task(
        task_id: UUID,
    ):

        task = runtime.task_supervisor.get_task(
            task_id
        )

        if task is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found.",
            )

        return task.snapshot()

    return api