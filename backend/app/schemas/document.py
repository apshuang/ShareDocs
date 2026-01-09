from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="文档标题")
    content: str = Field(default="", description="文档内容（Markdown格式）")


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="文档标题")


class DocumentResponse(BaseModel):
    id: int
    title: str
    owner_id: int
    content: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    id: int
    title: str
    owner_id: int
    current_version: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int

