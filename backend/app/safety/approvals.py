from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ApprovalRequest:
    request_id: UUID

    task_id: UUID
    task_version: int

    tool_name: str
    arguments: dict

    created_at: datetime

    _future: asyncio.Future[bool]

    resolved_at: datetime | None = None
    resolved_by: str | None = None
    decision: bool | None = None

    @property
    def pending(self) -> bool:
        return not self._future.done()


class ApprovalNotFoundError(KeyError):
    pass


class ApprovalAlreadyResolvedError(RuntimeError):
    pass


class ApprovalManager:
    """
    Human-in-the-loop approval manager.

    Approval requests are bound to:
        task_id
        task_version

    This is important because an approval generated for task v1
    must never automatically authorize an action belonging to v2.
    """

    def __init__(self) -> None:
        self._requests: dict[
            UUID,
            ApprovalRequest,
        ] = {}

        self._lock = asyncio.Lock()

    async def request(
        self,
        *,
        task_id: UUID,
        task_version: int,
        tool_name: str,
        arguments: dict,
        timeout: float | None = None,
    ) -> bool:
        """
        Create an approval request and suspend execution until
        the request is resolved.

        Returns:
            True  -> approved
            False -> denied / expired
        """

        loop = asyncio.get_running_loop()

        request_id = uuid4()

        future: asyncio.Future[bool] = (
            loop.create_future()
        )

        request = ApprovalRequest(
            request_id=request_id,
            task_id=task_id,
            task_version=task_version,
            tool_name=tool_name,
            arguments=dict(arguments),
            created_at=utc_now(),
            _future=future,
        )

        async with self._lock:
            self._requests[request_id] = request

        try:
            if timeout is None:
                decision = await future
            else:
                try:
                    decision = await asyncio.wait_for(
                        asyncio.shield(future),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    await self.resolve(
                        request_id=request_id,
                        approved=False,
                        resolved_by="system.timeout",
                    )
                    decision = False

            return decision

        finally:
            async with self._lock:
                self._requests.pop(
                    request_id,
                    None,
                )

    async def resolve(
        self,
        *,
        request_id: UUID,
        approved: bool,
        resolved_by: str = "user",
    ) -> None:
        """
        Resolve a pending approval.

        Resolution is idempotency-protected so a request cannot
        be approved and denied simultaneously.
        """

        async with self._lock:
            request = self._requests.get(
                request_id
            )

            if request is None:
                raise ApprovalNotFoundError(
                    f"Unknown approval request: "
                    f"{request_id}"
                )

            if request._future.done():
                raise ApprovalAlreadyResolvedError(
                    f"Approval request already resolved: "
                    f"{request_id}"
                )

            request.decision = approved
            request.resolved_by = resolved_by
            request.resolved_at = utc_now()

            request._future.set_result(
                approved
            )

    async def deny(
        self,
        *,
        request_id: UUID,
        resolved_by: str = "user",
    ) -> None:
        await self.resolve(
            request_id=request_id,
            approved=False,
            resolved_by=resolved_by,
        )

    async def approve(
        self,
        *,
        request_id: UUID,
        resolved_by: str = "user",
    ) -> None:
        await self.resolve(
            request_id=request_id,
            approved=True,
            resolved_by=resolved_by,
        )

    async def cancel_for_task(
        self,
        *,
        task_id: UUID,
        current_version: int | None = None,
    ) -> int:
        """
        Invalidate pending approvals for a task.

        If current_version is supplied, approvals belonging to
        older task versions are denied.

        Returns the number of cancelled requests.
        """

        cancelled = 0

        async with self._lock:
            requests = tuple(
                self._requests.values()
            )

            for request in requests:

                if request.task_id != task_id:
                    continue

                if current_version is not None:
                    if (
                        request.task_version
                        >= current_version
                    ):
                        continue

                if request._future.done():
                    continue

                request.decision = False
                request.resolved_by = (
                    "system.task_version_invalidated"
                )
                request.resolved_at = utc_now()

                request._future.set_result(False)

                cancelled += 1

        return cancelled

    async def get(
        self,
        request_id: UUID,
    ) -> ApprovalRequest:
        async with self._lock:
            request = self._requests.get(
                request_id
            )

            if request is None:
                raise ApprovalNotFoundError(
                    f"Unknown approval request: "
                    f"{request_id}"
                )

            return request

    async def pending(
        self,
        *,
        task_id: UUID | None = None,
    ) -> list[ApprovalRequest]:
        async with self._lock:
            requests = [
                request
                for request in self._requests.values()
                if request.pending
            ]

            if task_id is not None:
                requests = [
                    request
                    for request in requests
                    if request.task_id == task_id
                ]

            return requests

    async def clear(self) -> None:
        """
        Deny every outstanding approval.

        Useful during runtime shutdown.
        """

        async with self._lock:
            requests = tuple(
                self._requests.values()
            )

            for request in requests:
                if request._future.done():
                    continue

                request.decision = False
                request.resolved_by = (
                    "system.shutdown"
                )
                request.resolved_at = utc_now()

                request._future.set_result(False)

            self._requests.clear()