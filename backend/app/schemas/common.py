"""Common API response schemas."""
from typing import Any, Optional

from pydantic import BaseModel


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None

    @classmethod
    def success(cls, data: Any = None) -> dict:
        return {"code": 0, "message": "success", "data": data}

    @classmethod
    def error(cls, code: int, message: str) -> dict:
        return {"code": code, "message": message, "data": None}


class PaginationRequest(BaseModel):
    page: int = 1
    page_size: int = 20