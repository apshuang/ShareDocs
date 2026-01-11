from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class PermissionType(str, enum.Enum):
    READ = "read"
    EDIT = "edit"
    ADMIN = "admin"


class DocumentShare(Base):
    __tablename__ = "document_shares"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    permission = Column(Enum(PermissionType), nullable=False, default=PermissionType.EDIT)
    shared_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    document = relationship("Document", backref="shares")
    user = relationship("User", foreign_keys=[user_id], backref="shared_documents")
    sharer = relationship("User", foreign_keys=[shared_by], backref="shared_by_me")

