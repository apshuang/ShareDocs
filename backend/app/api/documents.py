from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import os
from app.database import get_db
from app.models.document import Document
from app.models.document_operation import DocumentOperation
from app.models.document_share import DocumentShare, PermissionType
from app.models.user import User
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse, DocumentListResponse
from app.schemas.operation import OperationRequest
from app.schemas.share import DocumentShareCreate, DocumentShareResponse
from app.utils.jwt import get_current_user
from app.utils.operation import apply_operation
from app.utils.permission import has_document_access, get_user_documents_query, get_user_permission
from app.websocket.manager import manager
from app.config import settings

router = APIRouter(prefix="/api/documents", tags=["文档"])


def ensure_documents_dir():
    os.makedirs(settings.DOCUMENTS_DIR, exist_ok=True)


def get_document_file_path(document_id: int) -> str:
    return os.path.join(settings.DOCUMENTS_DIR, f"{document_id}.md")


def read_document_content(document_id: int) -> str:
    file_path = get_document_file_path(document_id)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def write_document_content(document_id: int, content: str):
    ensure_documents_dir()
    file_path = get_document_file_path(document_id)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = Document(
        title=document_data.title,
        owner_id=current_user.id,
        content_path="",
        current_version=0
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    document.content_path = get_document_file_path(document.id)
    db.commit()
    
    write_document_content(document.id, document_data.content)
    
    return {
        "success": True,
        "data": {
            "id": document.id,
            "title": document.title,
            "owner_id": document.owner_id,
            "current_version": document.current_version,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat()
        },
        "message": "文档创建成功"
    }


@router.get("", response_model=dict)
async def get_documents(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = get_user_documents_query(db, current_user.id)
    
    if search:
        query = query.filter(Document.title.ilike(f"%{search}%"))
    
    total = query.count()
    
    offset = (page - 1) * page_size
    documents = query.order_by(Document.updated_at.desc()).offset(offset).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    items = []
    for doc in documents:
        permission = get_user_permission(db, doc.id, current_user.id)
        items.append({
            "id": doc.id,
            "title": doc.title,
            "owner_id": doc.owner_id,
            "is_owner": doc.owner_id == current_user.id,
            "permission": permission.value,
            "current_version": doc.current_version,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat()
        })
    
    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        },
        "message": "获取成功"
    }


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_document_access(db, document_id, current_user.id, PermissionType.READ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在或无权访问"
        )
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    content = read_document_content(document.id)
    user_permission = get_user_permission(db, document_id, current_user.id)
    
    return {
        "success": True,
        "data": {
            "id": document.id,
            "title": document.title,
            "owner_id": document.owner_id,
            "content": content,
            "current_version": document.current_version,
            "permission": user_permission.value,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat()
        },
        "message": "获取成功"
    }


@router.patch("/{document_id}", response_model=dict)
async def update_document(
    document_id: int,
    document_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    if document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有文档所有者可以修改标题"
        )
    
    if document_data.title is not None:
        document.title = document_data.title
    
    db.commit()
    db.refresh(document)
    
    return {
        "success": True,
        "data": {
            "id": document.id,
            "title": document.title,
            "updated_at": document.updated_at.isoformat()
        },
        "message": "更新成功"
    }


@router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    if document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有文档所有者可以删除文档"
        )
    
    file_path = get_document_file_path(document.id)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.delete(document)
    db.commit()
    
    return {
        "success": True,
        "message": "文档删除成功"
    }


@router.get("/{document_id}/editors", response_model=dict)
async def get_document_editors(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_document_access(db, document_id, current_user.id, PermissionType.READ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在或无权访问"
        )
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    editors_query = db.query(
        DocumentOperation.user_id,
        User.username,
        User.color,
        func.max(DocumentOperation.timestamp).label('last_edit_time')
    ).join(
        User, DocumentOperation.user_id == User.id
    ).filter(
        DocumentOperation.document_id == document_id
    ).group_by(
        DocumentOperation.user_id, User.username, User.color
    ).order_by(
        func.max(DocumentOperation.timestamp).desc()
    )
    
    editors = editors_query.all()
    
    editors_list = [
        {
            "user_id": editor.user_id,
            "username": editor.username,
            "color": editor.color or '#FFA07A',
            "last_edit_time": editor.last_edit_time.isoformat() if editor.last_edit_time else None
        }
        for editor in editors
    ]
    
    return {
        "success": True,
        "data": {
            "editors": editors_list,
            "last_updated": document.updated_at.isoformat()
        },
        "message": "获取成功"
    }


@router.post("/{document_id}/operations", response_model=dict)
async def apply_document_operation(
    document_id: int,
    operation: OperationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not has_document_access(db, document_id, current_user.id, PermissionType.EDIT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权编辑此文档"
        )
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    # 这里先使用一种很暴力的办法来判断（当前还是只支持单用户编辑的，在支持多用户时，这里就有相应的冲突解决措施）
    if operation.base_version != document.current_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"版本冲突：操作基于版本 {operation.base_version}，但当前版本是 {document.current_version}"
        )
    
    content = read_document_content(document.id)
    
    try:
        operation_dict = operation.model_dump()
        new_content = apply_operation(content, operation_dict)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"操作应用失败: {str(e)}"
        )
    
    version_before = document.current_version
    version_after = version_before + 1
    
    write_document_content(document.id, new_content)
    
    document.current_version = version_after
    db.commit()
    
    operation_record = DocumentOperation(
        document_id=document.id,
        user_id=current_user.id,
        operation_type=operation.type,
        operation_data=operation.model_dump(),
        sequence_number=version_after,
        version_before=version_before,
        version_after=version_after
    )
    db.add(operation_record)
    db.commit()
    
    operation_data = operation.model_dump()
    operation_data["version"] = version_after
    
    await manager.broadcast_to_document(
        {
            "type": "operation_applied",
            "data": {
                "document_id": document_id,
                "operation": operation_data,
                "version": version_after
            }
        },
        document_id,
        exclude_user_id=current_user.id
    )
    
    return {
        "success": True,
        "data": {
            "version": version_after,
            "operation": operation.model_dump()
        },
        "message": "操作应用成功"
    }


@router.post("/{document_id}/shares", response_model=dict)
async def share_document(
    document_id: int,
    share_data: DocumentShareCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    if document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有文档所有者可以分享文档"
        )
    
    if share_data.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能分享给自己"
        )
    
    target_user = db.query(User).filter(User.id == share_data.user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标用户不存在"
        )
    
    existing_share = db.query(DocumentShare).filter(
        DocumentShare.document_id == document_id,
        DocumentShare.user_id == share_data.user_id
    ).first()
    
    if existing_share:
        existing_share.permission = share_data.permission
        existing_share.shared_by = current_user.id
        db.commit()
        db.refresh(existing_share)
        
        return {
            "success": True,
            "data": {
                "id": existing_share.id,
                "document_id": existing_share.document_id,
                "user_id": existing_share.user_id,
                "username": target_user.username,
                "permission": existing_share.permission.value,
                "shared_by": existing_share.shared_by,
                "created_at": existing_share.created_at.isoformat(),
                "updated_at": existing_share.updated_at.isoformat()
            },
            "message": "分享权限已更新"
        }
    
    new_share = DocumentShare(
        document_id=document_id,
        user_id=share_data.user_id,
        permission=share_data.permission,
        shared_by=current_user.id
    )
    
    db.add(new_share)
    db.commit()
    db.refresh(new_share)
    
    return {
        "success": True,
        "data": {
            "id": new_share.id,
            "document_id": new_share.document_id,
            "user_id": new_share.user_id,
            "username": target_user.username,
            "permission": new_share.permission.value,
            "shared_by": new_share.shared_by,
            "created_at": new_share.created_at.isoformat(),
            "updated_at": new_share.updated_at.isoformat()
        },
        "message": "文档分享成功"
    }


@router.get("/{document_id}/shares", response_model=dict)
async def get_document_shares(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    if document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有文档所有者可以查看分享列表"
        )
    
    shares = db.query(DocumentShare, User).join(
        User, DocumentShare.user_id == User.id
    ).filter(
        DocumentShare.document_id == document_id
    ).all()
    
    shares_list = [
        {
            "id": share.id,
            "document_id": share.document_id,
            "user_id": share.user_id,
            "username": user.username,
            "permission": share.permission.value,
            "shared_by": share.shared_by,
            "created_at": share.created_at.isoformat(),
            "updated_at": share.updated_at.isoformat()
        }
        for share, user in shares
    ]
    
    return {
        "success": True,
        "data": {
            "shares": shares_list
        },
        "message": "获取成功"
    }


@router.delete("/{document_id}/shares/{share_id}", response_model=dict)
async def unshare_document(
    document_id: int,
    share_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    if document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有文档所有者可以取消分享"
        )
    
    share = db.query(DocumentShare).filter(
        DocumentShare.id == share_id,
        DocumentShare.document_id == document_id
    ).first()
    
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分享记录不存在"
        )
    
    db.delete(share)
    db.commit()
    
    return {
        "success": True,
        "message": "取消分享成功"
    }



