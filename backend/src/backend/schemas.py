from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


FileKind = Literal["folder", "text", "file", "pdf", "archive", "image"]


class FileCreate(BaseModel):
    parent_path: str = "/home/agentos"
    name: str = Field(min_length=1, max_length=255)
    kind: FileKind = "folder"
    mime_type: str | None = None
    content: str | None = None
    starred: bool = False

    @field_validator("name")
    @classmethod
    def safe_name(cls, value: str) -> str:
        if value in {".", ".."} or "/" in value or any(ord(character) < 32 for character in value):
            raise ValueError("name must be a single safe path segment")
        return value


class FileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_path: str | None = None
    starred: bool | None = None

    @field_validator("name")
    @classmethod
    def safe_name(cls, value: str | None) -> str | None:
        if value is not None and (
            value in {".", ".."}
            or "/" in value
            or any(ord(character) < 32 for character in value)
        ):
            raise ValueError("name must be a single safe path segment")
        return value


class FileCopyRequest(BaseModel):
    parent_path: str


class ArchiveRequest(BaseModel):
    node_ids: list[int] = Field(min_length=1)
    parent_path: str
    name: str = Field(min_length=1, max_length=255)


class ExtractRequest(BaseModel):
    destination: str


class ContentUpdate(BaseModel):
    content: str
    mime_type: str | None = "text/plain"


class StateUpdate(BaseModel):
    value: dict[str, Any]
    expected_revision: int | None = None


class StatePatch(BaseModel):
    value: dict[str, Any]
    expected_revision: int | None = None


class EventCreate(BaseModel):
    time: str
    source: Literal["human", "remote", "system"]
    node: str = Field(min_length=1, max_length=255)
    result: Literal["ok", "error"]
    detail: str
    durationMs: int = Field(default=0, ge=0)
    input: Any = None


class CommandCreate(BaseModel):
    node: str = Field(min_length=1, max_length=255)
    input: Any = None
    source: Literal["human", "remote", "system"] = "remote"

    model_config = ConfigDict(extra="forbid")


class CompileRequest(BaseModel):
    command: str = Field(min_length=1, max_length=2000)
    references: dict[str, list[str]] = Field(default_factory=dict)


class ActionExecuteRequest(BaseModel):
    args: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False
