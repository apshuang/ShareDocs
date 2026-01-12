"""
权限管理的单元测试
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.database import Base
from app.models.document import Document
from app.models.document_share import DocumentShare, PermissionType
from app.models.user import User
from app.utils.permission import (
    has_document_access,
    get_user_permission
)


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_users(db_session):
    """创建测试用户"""
    user1 = User(id=1, username="user1", email="user1@test.com", password_hash="hash1")
    user2 = User(id=2, username="user2", email="user2@test.com", password_hash="hash2")
    user3 = User(id=3, username="user3", email="user3@test.com", password_hash="hash3")
    
    db_session.add_all([user1, user2, user3])
    db_session.commit()
    
    return {"user1": user1, "user2": user2, "user3": user3}


@pytest.fixture
def test_document(db_session, test_users):
    """创建测试文档"""
    document = Document(
        id=1,
        title="Test Document",
        owner_id=test_users["user1"].id,
        content_path="data/documents/1.md",
        current_version=0
    )
    db_session.add(document)
    db_session.commit()
    return document


class TestHasDocumentAccess:
    """测试文档访问权限检查"""
    
    def test_owner_has_all_permissions(self, db_session, test_users, test_document):
        """测试所有者拥有所有权限"""
        owner = test_users["user1"]
        
        assert has_document_access(db_session, test_document.id, owner.id, PermissionType.READ) == True
        assert has_document_access(db_session, test_document.id, owner.id, PermissionType.EDIT) == True
        assert has_document_access(db_session, test_document.id, owner.id, PermissionType.ADMIN) == True
    
    def test_shared_user_with_read_permission(self, db_session, test_users, test_document):
        """测试有读权限的分享用户"""
        shared_user = test_users["user2"]
        
        share = DocumentShare(
            document_id=test_document.id,
            user_id=shared_user.id,
            permission=PermissionType.READ,
            shared_by=test_users["user1"].id
        )
        db_session.add(share)
        db_session.commit()
        
        assert has_document_access(db_session, test_document.id, shared_user.id, PermissionType.READ) == True
        assert has_document_access(db_session, test_document.id, shared_user.id, PermissionType.EDIT) == False
        assert has_document_access(db_session, test_document.id, shared_user.id, PermissionType.ADMIN) == False
    
    def test_shared_user_with_edit_permission(self, db_session, test_users, test_document):
        """测试有编辑权限的分享用户"""
        shared_user = test_users["user2"]
        
        share = DocumentShare(
            document_id=test_document.id,
            user_id=shared_user.id,
            permission=PermissionType.EDIT,
            shared_by=test_users["user1"].id
        )
        db_session.add(share)
        db_session.commit()
        
        assert has_document_access(db_session, test_document.id, shared_user.id, PermissionType.READ) == True
        assert has_document_access(db_session, test_document.id, shared_user.id, PermissionType.EDIT) == True
        assert has_document_access(db_session, test_document.id, shared_user.id, PermissionType.ADMIN) == False
    
    def test_shared_user_with_admin_permission(self, db_session, test_users, test_document):
        """测试有管理员权限的分享用户"""
        shared_user = test_users["user2"]
        
        share = DocumentShare(
            document_id=test_document.id,
            user_id=shared_user.id,
            permission=PermissionType.ADMIN,
            shared_by=test_users["user1"].id
        )
        db_session.add(share)
        db_session.commit()
        
        assert has_document_access(db_session, test_document.id, shared_user.id, PermissionType.READ) == True
        assert has_document_access(db_session, test_document.id, shared_user.id, PermissionType.EDIT) == True
        assert has_document_access(db_session, test_document.id, shared_user.id, PermissionType.ADMIN) == True
    
    def test_user_without_access(self, db_session, test_users, test_document):
        """测试没有访问权限的用户"""
        unauthorized_user = test_users["user3"]
        
        assert has_document_access(db_session, test_document.id, unauthorized_user.id, PermissionType.READ) == False
        assert has_document_access(db_session, test_document.id, unauthorized_user.id, PermissionType.EDIT) == False
        assert has_document_access(db_session, test_document.id, unauthorized_user.id, PermissionType.ADMIN) == False
    
    def test_nonexistent_document(self, db_session, test_users):
        """测试不存在的文档"""
        user = test_users["user1"]
        assert has_document_access(db_session, 999, user.id, PermissionType.READ) == False


class TestGetUserPermission:
    """测试获取用户权限"""
    
    def test_owner_permission(self, db_session, test_users, test_document):
        """测试所有者的权限"""
        owner = test_users["user1"]
        permission = get_user_permission(db_session, test_document.id, owner.id)
        assert permission == PermissionType.ADMIN
    
    def test_shared_user_read_permission(self, db_session, test_users, test_document):
        """测试分享用户的读权限"""
        shared_user = test_users["user2"]
        
        share = DocumentShare(
            document_id=test_document.id,
            user_id=shared_user.id,
            permission=PermissionType.READ,
            shared_by=test_users["user1"].id
        )
        db_session.add(share)
        db_session.commit()
        
        permission = get_user_permission(db_session, test_document.id, shared_user.id)
        assert permission == PermissionType.READ
    
    def test_shared_user_edit_permission(self, db_session, test_users, test_document):
        """测试分享用户的编辑权限"""
        shared_user = test_users["user2"]
        
        share = DocumentShare(
            document_id=test_document.id,
            user_id=shared_user.id,
            permission=PermissionType.EDIT,
            shared_by=test_users["user1"].id
        )
        db_session.add(share)
        db_session.commit()
        
        permission = get_user_permission(db_session, test_document.id, shared_user.id)
        assert permission == PermissionType.EDIT
    
    def test_unauthorized_user_permission(self, db_session, test_users, test_document):
        """测试未授权用户的权限"""
        unauthorized_user = test_users["user3"]
        permission = get_user_permission(db_session, test_document.id, unauthorized_user.id)
        assert permission == PermissionType.READ  # 默认返回READ
    
    def test_nonexistent_document_permission(self, db_session, test_users):
        """测试不存在文档的权限"""
        user = test_users["user1"]
        permission = get_user_permission(db_session, 999, user.id)
        assert permission == PermissionType.READ  # 默认返回READ

