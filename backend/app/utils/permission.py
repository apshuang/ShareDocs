from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.document_share import DocumentShare, PermissionType


def has_document_access(db: Session, document_id: int, user_id: int, required_permission: PermissionType = PermissionType.READ) -> bool:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return False
    
    if document.owner_id == user_id:
        return True
    
    share = db.query(DocumentShare).filter(
        DocumentShare.document_id == document_id,
        DocumentShare.user_id == user_id
    ).first()
    
    if not share:
        return False
    
    permission_levels = {
        PermissionType.READ: 1,
        PermissionType.EDIT: 2,
        PermissionType.ADMIN: 3
    }
    
    user_permission_level = permission_levels.get(share.permission, 0)
    required_level = permission_levels.get(required_permission, 0)
    
    return user_permission_level >= required_level


def get_user_documents_query(db: Session, user_id: int):
    from sqlalchemy import or_
    return db.query(Document).filter(
        or_(
            Document.owner_id == user_id,
            Document.id.in_(
                db.query(DocumentShare.document_id).filter(
                    DocumentShare.user_id == user_id
                )
            )
        )
    )


def get_user_permission(db: Session, document_id: int, user_id: int) -> PermissionType:
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        return PermissionType.READ
    
    if document.owner_id == user_id:
        return PermissionType.ADMIN
    
    share = db.query(DocumentShare).filter(
        DocumentShare.document_id == document_id,
        DocumentShare.user_id == user_id
    ).first()
    
    if not share:
        return PermissionType.READ
    
    return share.permission

