import re

from fastapi import HTTPException, status
from pydantic import ValidationError

from src.app.schemas.voice import (
    InstructionPayload,
    TaskCreate,
    TaskReplace,
    TaskUpdate,
)
from src.app.store.tasks import (
    TaskNotFoundError,
    create_task,
    delete_task,
    list_tasks,
    patch_task,
    replace_task,
)

_TASKS_PATH_RE = re.compile(r"^/tasks(?:/(\d+))?$")
_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def execute_instruction(instruction: InstructionPayload):
    method = instruction.method.strip().upper()
    if method not in _ALLOWED_METHODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported HTTP method: {instruction.method}",
        )

    match = _TASKS_PATH_RE.match(instruction.endpoint.strip())
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported endpoint: {instruction.endpoint}",
        )

    task_id_str = match.group(1)
    params = instruction.params or {}

    try:
        if method == "GET":
            if task_id_str is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="GET /tasks does not accept a task id in the path.",
                )
            return list_tasks()

        if method == "POST":
            if task_id_str is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="POST /tasks does not accept a task id in the path.",
                )
            return create_task(TaskCreate.model_validate(params))

        if task_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{method} requires a task id in the endpoint path.",
            )

        task_id = int(task_id_str)

        if method == "PUT":
            return replace_task(task_id, TaskReplace.model_validate(params))
        if method == "PATCH":
            return patch_task(task_id, TaskUpdate.model_validate(params))
        if method == "DELETE":
            if params:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="DELETE /tasks/{id} does not accept params.",
                )
            return delete_task(task_id)

    except TaskNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.errors(),
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Could not execute instruction for {method} {instruction.endpoint}",
    )
