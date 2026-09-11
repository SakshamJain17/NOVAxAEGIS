from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from app.runtime.event_bus import EventBus
from app.runtime.events import Event


LOGGER = logging.getLogger(
    "aegis.websocket"
)


MAX_QUEUE_SIZE = 256


@dataclass(slots=True)
class WebSocketClient:
    connection_id: UUID
    websocket: WebSocket

    subscribed_tasks: set[UUID] = field(
        default_factory=set
    )

    receive_all: bool = True

    queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda:
            asyncio.Queue(
                maxsize=MAX_QUEUE_SIZE
            )
    )

    sender_task: asyncio.Task | None = None

    connected_at: datetime | None = None


class WebSocketManager:
    """
    Realtime event gateway between AEGIS backend
    and desktop/frontend clients.
    """

    def __init__(
        self,
        event_bus: EventBus,
    ) -> None:
        self.event_bus = event_bus

        self._clients: dict[
            UUID,
            WebSocketClient
        ] = {}

        self._lock = asyncio.Lock()

        self.event_bus.subscribe_all(
            self._handle_event
        )

    async def connect(
        self,
        websocket: WebSocket,
    ) -> WebSocketClient:

        await websocket.accept()

        client = WebSocketClient(
            connection_id=uuid4(),
            websocket=websocket,
            connected_at=datetime.utcnow(),
        )

        async with self._lock:
            self._clients[
                client.connection_id
            ] = client

        client.sender_task = asyncio.create_task(
            self._sender_loop(client)
        )

        await self._send(
            client,
            {
                "type": "connection.established",
                "connection_id": str(
                    client.connection_id
                ),
                "service": "AEGIS",
            },
        )

        LOGGER.info(
            "WebSocket connected: %s",
            client.connection_id,
        )

        return client

    async def disconnect(
        self,
        client: WebSocketClient,
    ) -> None:

        async with self._lock:
            self._clients.pop(
                client.connection_id,
                None,
            )

        if client.sender_task:
            client.sender_task.cancel()

            try:
                await client.sender_task
            except asyncio.CancelledError:
                pass

        LOGGER.info(
            "WebSocket disconnected: %s",
            client.connection_id,
        )

    async def _sender_loop(
        self,
        client: WebSocketClient,
    ) -> None:

        try:
            while True:
                message = await client.queue.get()

                await client.websocket.send_text(
                    json.dumps(
                        message,
                        default=str,
                    )
                )

        except asyncio.CancelledError:
            raise

        except Exception:
            LOGGER.exception(
                "WebSocket sender failed: %s",
                client.connection_id,
            )

    async def _send(
        self,
        client: WebSocketClient,
        message: dict[str, Any],
    ) -> None:

        try:
            client.queue.put_nowait(
                message
            )

        except asyncio.QueueFull:
            LOGGER.warning(
                "WebSocket queue overflow: %s",
                client.connection_id,
            )

            try:
                await client.websocket.close(
                    code=1013,
                    reason="AEGIS event stream overloaded",
                )
            except Exception:
                pass

    async def _handle_event(
        self,
        event: Event,
    ) -> None:

        message = {
            "type": "aegis.event",
            "event": jsonable_encoder(
                event
            ),
        }

        async with self._lock:
            clients = tuple(
                self._clients.values()
            )

        for client in clients:

            if not self._client_accepts_event(
                client,
                event,
            ):
                continue

            await self._send(
                client,
                message,
            )

    @staticmethod
    def _client_accepts_event(
        client: WebSocketClient,
        event: Event,
    ) -> bool:

        if client.receive_all:
            return True

        if event.task_id is None:
            return True

        return (
            event.task_id
            in client.subscribed_tasks
        )

    async def subscribe_task(
        self,
        client: WebSocketClient,
        task_id: UUID,
    ) -> None:

        client.subscribed_tasks.add(
            task_id
        )

        client.receive_all = False

        await self._send(
            client,
            {
                "type": "subscription.updated",
                "task_id": str(task_id),
            },
        )

    async def unsubscribe_task(
        self,
        client: WebSocketClient,
        task_id: UUID,
    ) -> None:

        client.subscribed_tasks.discard(
            task_id
        )

        await self._send(
            client,
            {
                "type": "subscription.updated",
                "task_id": str(task_id),
                "subscribed": False,
            },
        )

    async def subscribe_all(
        self,
        client: WebSocketClient,
    ) -> None:

        client.receive_all = True

        await self._send(
            client,
            {
                "type": "subscription.updated",
                "scope": "all",
            },
        )

    async def broadcast_system(
        self,
        payload: dict[str, Any],
    ) -> None:

        async with self._lock:
            clients = tuple(
                self._clients.values()
            )

        message = {
            "type": "system.event",
            "payload": payload,
        }

        for client in clients:
            await self._send(
                client,
                message,
            )

    async def shutdown(self) -> None:

        async with self._lock:
            clients = tuple(
                self._clients.values()
            )

        for client in clients:
            try:
                await client.websocket.close()
            except Exception:
                pass

        self.event_bus.unsubscribe_all(
            self._handle_event
        )

        self._clients.clear()


async def websocket_endpoint(
    websocket: WebSocket,
    manager: WebSocketManager,
) -> None:

    client = await manager.connect(
        websocket
    )

    try:

        while True:

            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:

                await manager._send(
                    client,
                    {
                        "type": "error",
                        "error": "Invalid JSON",
                    },
                )

                continue

            message_type = message.get(
                "type"
            )

            if message_type == "ping":

                await manager._send(
                    client,
                    {
                        "type": "pong"
                    },
                )

            elif message_type == "subscribe":

                task_id = message.get(
                    "task_id"
                )

                if not task_id:
                    await manager.subscribe_all(
                        client
                    )
                    continue

                try:
                    parsed_task_id = UUID(
                        task_id
                    )
                except ValueError:

                    await manager._send(
                        client,
                        {
                            "type": "error",
                            "error":
                                "Invalid task ID",
                        },
                    )

                    continue

                await manager.subscribe_task(
                    client,
                    parsed_task_id,
                )

            elif message_type == "unsubscribe":

                task_id = message.get(
                    "task_id"
                )

                if task_id:

                    try:
                        parsed_task_id = UUID(
                            task_id
                        )

                        await manager.unsubscribe_task(
                            client,
                            parsed_task_id,
                        )

                    except ValueError:
                        pass

            elif message_type == "subscribe_all":

                await manager.subscribe_all(
                    client
                )

            else:

                await manager._send(
                    client,
                    {
                        "type": "error",
                        "error":
                            f"Unknown message type: {message_type}",
                    },
                )

    except WebSocketDisconnect:
        pass

    except Exception:
        LOGGER.exception(
            "WebSocket endpoint failure"
        )

    finally:
        await manager.disconnect(
            client
        )