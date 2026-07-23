"""Trigger schemas (manual fetch etc)."""
from typing import List, Optional

from pydantic import BaseModel


class TriggerFetchResponse(BaseModel):
    source: str = "all"
    status: str = "triggered"
    results: List[dict] = []