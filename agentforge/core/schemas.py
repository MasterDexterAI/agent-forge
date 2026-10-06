from typing import Literal

from pydantic import BaseModel, Field


class Subtask(BaseModel):
    id: int
    title: str
    description: str
    acceptance_criteria: list[str] = Field(min_length=1)


class Plan(BaseModel):
    summary: str
    modules: list[str] = Field(min_length=1, max_length=8)
    interface: str
    subtasks: list[Subtask] = Field(min_length=1, max_length=6)


class FileWrite(BaseModel):
    path: str
    content: str


class TestSuiteSpec(BaseModel):
    files: list[FileWrite] = Field(min_length=1, max_length=6)


class CodePatch(BaseModel):
    files: list[FileWrite] = Field(min_length=1, max_length=20)
    notes: str = ""


class Review(BaseModel):
    verdict: Literal["approve", "fix", "replan"]
    score: float = Field(ge=0, le=1)
    comments: list[str] = Field(default_factory=list)
