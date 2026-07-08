from pydantic import BaseModel
from datetime import date
from typing import Literal


class Task(BaseModel):
    id: str
    title: str
    description: str
    priority: Literal["high", "medium", "low"]
    due_date: date
    sender: str
    email_id: str | None = None
    completed: bool = False


class TasksResponse(BaseModel):
    tasks: list[Task]
    total: int
