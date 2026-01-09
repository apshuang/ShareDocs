from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class DocumentOperation(Base):
    __tablename__ = "document_operations"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    operation_type = Column(String(20), nullable=False)  # 共有4种类型，insert, delete, format, replace
    operation_data = Column(JSON, nullable=False)  # 操作数据（JSON格式）
    sequence_number = Column(Integer, nullable=False, index=True)  # 操作版本号
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    version_before = Column(Integer, nullable=False)
    version_after = Column(Integer, nullable=False)
    
    document = relationship("Document", backref="operations")
    user = relationship("User", backref="operations")

