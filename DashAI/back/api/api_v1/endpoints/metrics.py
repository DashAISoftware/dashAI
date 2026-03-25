import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, WebSocket
from fastapi.websockets import WebSocketDisconnect
from kink import di, inject

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dependencies.database.models import Metric, Run

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{run_id}")
@inject
async def live_metrics_websocket(
    websocket: WebSocket,
    run_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    import asyncio
    import json

    await websocket.accept()

    last_timestamp = None
    first_send = True

    try:
        while True:
            with session_factory() as db:
                query = db.query(Metric).filter(Metric.run_id == run_id)

                # First send: get all metrics
                # Subsequent sends: get only new metrics
                if not first_send and last_timestamp is not None:
                    query = query.filter(Metric.timestamp > last_timestamp)

                # Order by step and timestamp to ensure correct sequence
                metrics = query.order_by(
                    Metric.step,
                    Metric.timestamp,
                ).all()

                run = db.get(Run, run_id)

            # Update last_timestamp
            if metrics:
                last_timestamp = metrics[-1].timestamp

            # Structure payload
            # split -> level ->
            # metric_name -> list of {step, value, timestamp}
            payload: dict[str, dict[str, dict[str, list]]] = {}
            for metric in metrics:
                split = metric.split.name
                level = metric.level.name
                name = metric.name

                payload.setdefault(split, {}).setdefault(level, {}).setdefault(
                    name, []
                ).append(
                    {
                        "step": metric.step,
                        "value": metric.value,
                        "timestamp": metric.timestamp.isoformat(),
                    }
                )

            if run:
                payload["run_status"] = run.status.name

            if payload:
                await websocket.send_text(json.dumps(payload))

            first_send = False

            if run and run.status in {RunStatus.FINISHED, RunStatus.ERROR}:
                await websocket.close(code=1000)
                break

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
