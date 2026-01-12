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
from app.utils.conflict import (
    check_operation_conflict,
    transform_operation_for_conflict_resolution
)
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
    
    operation_dict = operation.model_dump()
    
    if operation.base_version == document.current_version:
        content = read_document_content(document.id)
        
        if operation.type == "insert" and operation.from_pos > len(content):
            operation_dict["from_pos"] = len(content)
            operation_dict["to_pos"] = len(content)
        
        pending_operations = db.query(DocumentOperation).filter(
            DocumentOperation.document_id == document_id,
            DocumentOperation.sequence_number > operation.base_version
        ).count()
        
        if pending_operations > 0:
            history_operations = db.query(DocumentOperation).filter(
                DocumentOperation.document_id == document_id,
                DocumentOperation.sequence_number > operation.base_version,
                DocumentOperation.sequence_number <= document.current_version
            ).order_by(DocumentOperation.sequence_number).all()
            
            history_ops_list = [op.operation_data for op in history_operations]
            
            has_conflict, conflict_message = check_operation_conflict(
                operation_dict,
                history_ops_list
            )
            
            if has_conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=conflict_message
                )
        
        try:
            new_content = apply_operation(content, operation_dict)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"操作应用失败: {str(e)}"
            )
    else:
        history_operations = db.query(DocumentOperation).filter(
            DocumentOperation.document_id == document_id,
            DocumentOperation.sequence_number > operation.base_version,
            DocumentOperation.sequence_number <= document.current_version
        ).order_by(DocumentOperation.sequence_number).all()
        
        history_ops_list = [op.operation_data for op in history_operations]
        
        base_operations = db.query(DocumentOperation).filter(
            DocumentOperation.document_id == document_id,
            DocumentOperation.sequence_number <= operation.base_version
        ).order_by(DocumentOperation.sequence_number).all()
        
        base_content = ""
        for base_op in base_operations:
            try:
                base_content = apply_operation(base_content, base_op.operation_data)
            except ValueError as e:
                base_content = read_document_content(document.id)
                break
        
        has_conflict, conflict_message = check_operation_conflict(
            operation_dict,
            history_ops_list
        )
        
        if has_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=conflict_message
            )
        
        # 根据历史操作调整当前操作的位置
        # 先计算应用历史操作后的文档长度（用于检查插入操作是否超出范围）
        temp_content = base_content
        for hist_op in history_ops_list:
            try:
                temp_content = apply_operation(temp_content, hist_op)
            except ValueError:
                # 如果应用失败，使用base_content的长度
                temp_content = base_content
                break
        
        adjusted_content_length = len(temp_content)
        
        # 调整当前操作的位置（考虑历史操作的影响）
        transformed_operation = transform_operation_for_conflict_resolution(
            operation_dict,
            history_ops_list,
            adjusted_content_length
        )
        
        # 对于插入操作，如果调整后位置仍然超出范围，调整到文档结尾
        if transformed_operation.get("type") == "insert":
            adjusted_from = transformed_operation.get("from_pos", 0)
            if adjusted_from > adjusted_content_length:
                transformed_operation["from_pos"] = adjusted_content_length
                transformed_operation["to_pos"] = adjusted_content_length
        
        # 应用调整后的操作到 base_version 的内容
        try:
            new_content = apply_operation(base_content, transformed_operation)
            # 更新 operation_dict 为调整后的操作
            operation_dict = transformed_operation
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"操作应用失败: {str(e)}"
            )
        
        # 应用历史操作到新内容
        for hist_op in history_ops_list:
            try:
                new_content = apply_operation(new_content, hist_op)
            except ValueError as e:
                # 如果应用历史操作失败，说明有严重问题
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"应用历史操作失败: {str(e)}"
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



