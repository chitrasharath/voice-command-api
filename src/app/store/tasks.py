from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate

tasks: list[dict[str, int | str | bool]] = []
_next_id: int = 1


class TaskNotFoundError(Exception):
    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")


def _to_task(raw: dict[str, int | str | bool]) -> Task:
    return Task(id=int(raw["id"]), title=str(raw["title"]), done=bool(raw["done"]))


def list_tasks() -> list[Task]:
    return [_to_task(task) for task in tasks]


def create_task(payload: TaskCreate) -> Task:
    global _next_id
    task = {
        "id": _next_id,
        "title": payload.title,
        "done": payload.done,
    }
    tasks.append(task)
    _next_id += 1
    return _to_task(task)


def replace_task(task_id: int, payload: TaskReplace) -> Task:
    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks[index] = {
                "id": task_id,
                "title": payload.title,
                "done": payload.done,
            }
            return _to_task(tasks[index])
    raise TaskNotFoundError(task_id)


def patch_task(task_id: int, payload: TaskUpdate) -> Task:
    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            if payload.title is not None:
                task["title"] = payload.title
            if payload.done is not None:
                task["done"] = payload.done
            return _to_task(task)
    raise TaskNotFoundError(task_id)


def delete_task(task_id: int) -> dict[str, str]:
    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(index)
            return {"message": f"Task {task_id} deleted"}
    raise TaskNotFoundError(task_id)
