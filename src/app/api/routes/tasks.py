from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate
from src.app.store.tasks import (
    TaskNotFoundError,
    create_task,
    delete_task,
    list_tasks,
    patch_task,
    replace_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def get_tasks() -> list[Task]:
    return list_tasks()


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task_route(payload: TaskCreate) -> Task:
    return create_task(payload)


@router.put("/{task_id}", response_model=Task)
def replace_task_route(task_id: int, payload: TaskReplace) -> Task:
    try:
        return replace_task(task_id, payload)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{task_id}", response_model=Task)
def update_task_route(task_id: int, payload: TaskUpdate) -> Task:
    try:
        return patch_task(task_id, payload)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{task_id}")
def delete_task_route(task_id: int) -> dict[str, str]:
    try:
        return delete_task(task_id)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
