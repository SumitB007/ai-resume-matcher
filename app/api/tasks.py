"""Task endpoints — track status of Celery background jobs."""

import logging
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.task import TaskStatusResponse
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get background task status",
)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieve the status and result of a Celery background task by its task_id.

    Returns:
    - PENDING: Task is waiting for execution or unknown
    - STARTED / PROCESSING: Task is currently executing
    - SUCCESS: Task completed successfully (result returned)
    - FAILURE: Task failed with an error
    """
    try:
        async_result = AsyncResult(task_id, app=celery_app)
        state = async_result.state
        ready = async_result.ready()

        progress = None
        step = None
        result_data = None
        error_msg = None

        if state == "SUCCESS":
            result_data = async_result.result
        elif state == "FAILURE":
            error_msg = str(async_result.result) if async_result.result else "Task failed"
        elif isinstance(async_result.info, dict):
            progress = async_result.info.get("progress")
            step = async_result.info.get("step")
            result_data = async_result.info

        return TaskStatusResponse(
            task_id=task_id,
            status=state,
            ready=ready,
            successful=async_result.successful() if ready else None,
            progress=progress,
            step=step,
            result=result_data,
            error=error_msg,
        )
    except Exception as e:
        logger.error(f"Error querying task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve task status: {e}",
        )
