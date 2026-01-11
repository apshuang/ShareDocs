from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.document_share import PermissionType


class DocumentShareCreate(BaseModel):
    user_id: int = Field(..., description="被分享的用户ID")
    permission: PermissionType = Field(PermissionType.EDIT, description="权限级别")


class DocumentShareResponse(BaseModel):
    id: int
    document_id: int
    user_id: int
    username: str
    permission: PermissionType
    shared_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

