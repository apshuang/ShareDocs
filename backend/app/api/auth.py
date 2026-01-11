from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse
from app.utils.password import verify_password, get_password_hash
from app.utils.jwt import create_access_token, get_current_user
from app.config import settings
from datetime import timedelta

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password
    )
    
    try:
        db.add(user)
        db.commit()  # 因为关了自动commit，需要手动commit持久化
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="注册失败，用户名或邮箱已存在"
        )
    
    return {
        "success": True,
        "data": {
            "user_id": user.id,
            "username": user.username,
            "email": user.email
        },
        "message": "注册成功"
    }


@router.post("/login", response_model=dict)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id, "username": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        },
        "message": "登录成功"
    }


@router.post("/refresh", response_model=dict)
async def refresh_token(current_user: User = Depends(get_current_user)):
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": current_user.id, "username": current_user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        },
        "message": "Token 刷新成功"
    }


@router.get("/me", response_model=dict)
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat()
        },
        "message": "获取成功"
    }


@router.get("/users", response_model=dict)
async def search_users(
    q: Optional[str] = Query(None, description="搜索关键词（用户名或ID）"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    
    if q:
        try:
            user_id = int(q)
            query = query.filter(User.id == user_id)
        except ValueError:
            query = query.filter(User.username.ilike(f"%{q}%"))
    
    users = query.limit(limit).all()
    
    users_list = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
        for user in users
        if user.id != current_user.id
    ]
    
    return {
        "success": True,
        "data": {
            "users": users_list
        },
        "message": "获取成功"
    }



