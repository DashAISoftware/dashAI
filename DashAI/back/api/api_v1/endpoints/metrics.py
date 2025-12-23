import asyncio
import json
import logging

from fastapi import APIRouter, Depends, WebSocket
from fastapi.websockets import WebSocketDisconnect
from kink import di, inject
from sqlalchemy.orm import sessionmaker

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dependencies.database.models import Metric, Run

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{run_id}")
@inject
async def live_metrics_websocket(
    websocket: WebSocket,
    run_id: int,
    session_factory: sessionmaker = Depends(lambda: di["session_factory"]),
):
    await websocket.accept()

    try:
        while True:
            with session_factory() as db:
                metrics = db.query(Metric).filter_by(run_id=run_id).all()
                run = db.get(Run, run_id)

                payload: dict[str, dict[str, dict]] = {}

                for metric in metrics:
                    split = metric.split.name
                    level = metric.level.name

                    payload.setdefault(split, {})
                    payload[split][level] = metric.results

                if run:
                    payload["run_status"] = run.status.name

            # Send update
            await websocket.send_text(json.dumps(payload))

            # If run finished or errored → close cleanly
            if run and run.status in {RunStatus.FINISHED, RunStatus.ERROR}:
                await websocket.close(code=1000)
                break

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for run_id: {run_id}")

    except Exception:
        logger.exception("WebSocket error")
        await websocket.close(code=1011)
