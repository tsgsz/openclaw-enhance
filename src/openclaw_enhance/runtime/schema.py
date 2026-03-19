from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RuntimeState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    last_updated_utc: datetime = Field(default_factory=datetime.utcnow)
    doctor_last_ok: bool = False
    active_project: str | None = None
    project_occupancy: dict[str, str] = Field(default_factory=dict)


class ConfigPatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changed_keys: list[str]
    backup_path: str


class OwnershipContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    namespace: str
    payload: dict[str, Any]
