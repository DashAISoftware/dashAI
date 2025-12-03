import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from urllib.parse import unquote_plus  # NOTE: plus -> space

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.exceptions import HTTPException
from kink import di, inject
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, ValueTarget
from streaming_form_data.validators import MaxSizeValidator

from DashAI.back.dependencies.database.utils import find_entity_by_huey_id
from DashAI.back.dependencies.job_queues import BaseJobQueue
from DashAI.back.dependencies.job_queues.base_job_queue import JobQueueError
from DashAI.back.dependencies.registry import ComponentRegistry
from DashAI.back.job.base_job import JobError

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/is_empty")
@inject
async def is_queue_empty(
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """
    Check if the job queue is empty.
    """
    try:
        logger.debug("Checking if job queue is empty")
        is_empty = job_queue.is_empty()
        logger.debug(f"Queue empty status: {is_empty}")
        return {"is_empty": is_empty}
    except Exception as e:
        logger.exception(f"Error checking if queue is empty: {e}")
        return {"is_empty": True, "error": str(e)}


@router.get("/changes")
@inject
async def get_job_changes(
    since: str = Query(
        default="1970-01-01 00:00:00.000000",
        description="UTC ISO8601 or 'YYYY-MM-DD HH:MM:SS[.ffffff]'",
    ),
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """
    Get jobs that have changed since the given timestamp (UTC).
    """
    try:
        since_decoded = unquote_plus(since)

        jobs = job_queue.changes_since(since_decoded)
        all_jobs = job_queue.to_list()

        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

        is_queue_empty = job_queue.is_empty()
        recently_completed = any(j.get("status") in ("finished", "error") for j in jobs)

        return {
            "jobs": jobs,
            "cursor": current_time,
            "server_now": current_time,
            "queue_empty": is_queue_empty,
            "recently_completed": recently_completed,
            "all_jobs": all_jobs,
        }
    except Exception as e:
        logger.exception(f"Error retrieving job changes: {e}")
        current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        return {
            "jobs": [],
            "cursor": current_time,
            "server_now": current_time,
            "queue_empty": True,
            "recently_completed": False,
            "all_jobs": [],
            "error": str(e),
        }


@router.get("/status/{task_id}")
@inject
async def get_job_status(
    task_id: str,
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Get status of a specific job."""
    try:
        return job_queue.status(task_id)
    except JobQueueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get("/{job_id}")
@inject
async def get_job(
    job_id: str,
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Return the selected job from the job queue."""
    try:
        return job_queue.peek(job_id)
    except JobQueueError as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        ) from e


@router.get("/")
@inject
async def get_jobs(
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """
    Get all jobs from the queue.
    """
    try:
        return job_queue.to_list()
    except Exception as e:
        logger.exception(f"Error retrieving jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve jobs: {str(e)}",
        ) from e


@router.get("/{job_id}/details")
@inject
async def get_job_details(
    job_id: str, job_queue: BaseJobQueue = Depends(lambda: di["job_queue"])
):
    """
    Get detailed information about a job, including its associated entity.
    """
    try:
        entity_info = find_entity_by_huey_id(job_id)
        if not entity_info:
            return {"id": job_id, "no_entity": True}

        task_info = job_queue.status(job_id)
        entity_info.update(task_info)

        return entity_info
    except JobQueueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving job details: {str(e)}",
        ) from e


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def enqueue_job(
    request: Request,
    component_registry: ComponentRegistry = Depends(lambda: di["component_registry"]),
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Create a runner job and put it in the job queue."""
    try:
        logger.debug("Starting job enqueue process")
        MAX_FILE_SIZE = 4 * 1024**3  # 4GB
        content_type = request.headers.get("content-type", "")
        logger.debug(f"Request content type: {content_type}")

        # parse multipart/form-data with file
        if "multipart/form-data" in content_type and "filename" in request.headers:
            filename = request.headers.get("filename", "uploaded_file")
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, filename)

            parser = StreamingFormDataParser(headers=request.headers)
            parser.register(
                "file", FileTarget(file_path, validator=MaxSizeValidator(MAX_FILE_SIZE))
            )
            job_type_target = ValueTarget()
            kwargs_target = ValueTarget()
            n_sample_target = ValueTarget()
            parser.register("job_type", job_type_target)
            parser.register("kwargs", kwargs_target)
            parser.register("n_sample", n_sample_target)

            async for chunk in request.stream():
                parser.data_received(chunk)

            job_type = job_type_target.value.decode() if job_type_target.value else None
            kwargs_str = kwargs_target.value.decode() if kwargs_target.value else None
            n_sample = (
                int(n_sample_target.value.decode()) if n_sample_target.value else None
            )

            if not job_type or not kwargs_str:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Missing job_type or kwargs",
                )

            kwargs = json.loads(kwargs_str)
            kwargs.update(
                file_path=file_path,
                temp_dir=temp_dir,
                filename=filename,
                n_sample=n_sample,
            )

        # parse regular form data
        else:
            form = await request.form()
            job_type = form.get("job_type")
            kwargs_str = form.get("kwargs")

            if not job_type or not kwargs_str:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Missing job_type or kwargs",
                )

            kwargs = json.loads(kwargs_str)

        # instantiate job with only primitive args
        JobClass = component_registry[job_type]["class"]
        job = JobClass(**kwargs)

        # mark delivered
        try:
            job.set_status_as_delivered()
        except JobError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Job not delivered",
            ) from e

        # enqueue
        try:
            job_id = job_queue.put(job).id
            return {"id": job_id}
        except JobQueueError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Job not enqueued: {str(e)}",
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}",
            ) from e
    except Exception as e:
        logging.exception(f"Uncaught error in enqueue_job: {e}")
        raise


@router.delete("/all")
@inject
async def cancel_all_jobs(
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Delete all jobs from the job queue."""
    try:
        # Usar una función en HueyJobQueue para eliminar todos los jobs
        count = job_queue.delete_all_jobs()
        return {"deleted": count}
    except Exception as e:
        logging.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error canceling all jobs: {str(e)}",
        ) from e


@router.delete("/{job_id}")
@inject
async def cancel_job(
    job_id: str,
    job_queue: BaseJobQueue = Depends(lambda: di["job_queue"]),
):
    """Delete the job with id job_id from the job queue."""
    try:
        success = job_queue.delete_from_db(job_id)
        if success:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )
    except Exception as e:
        logging.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error canceling job: {str(e)}",
        ) from e


@router.patch("/")
async def update_job():
    """Placeholder for job update."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Method not implemented"
    )
