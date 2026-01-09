from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any


class OperationRequest(BaseModel):
    type: Literal["insert", "delete", "format", "replace"] = Field(..., description="操作类型")
    from_pos: int = Field(..., ge=0, description="起始位置（字符索引）")
    to_pos: int = Field(..., ge=0, description="结束位置（字符索引）")
    content: Optional[str] = Field(None, description="插入或替换的内容")
    marks: Optional[Dict[str, Any]] = Field(None, description="格式化标记（用于 format 操作）")
    base_version: int = Field(..., ge=0, description="操作基于的版本号")

