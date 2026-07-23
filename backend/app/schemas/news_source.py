"""Source management schemas."""
from typing import Optional

from pydantic import BaseModel, Field


class AddSourceRequest(BaseModel):
    name: Optional[str] = None
    source_type: str = Field(..., pattern="^(rss|crawler)$")
    url: str