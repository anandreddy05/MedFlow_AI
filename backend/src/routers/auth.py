import os
from fastapi import APIRouter, Depends, HTTPException
from datetime import timedelta, datetime, timezone
from pydantic import BaseModel
from src.models import User
from passlib.context import CryptContext
from src.database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from starlette import status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from enum import Enum
from dotenv import load_dotenv

from src.utils.logger import get_logger, log_ctx

load_dotenv()

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")


class RoleEnum(str, Enum):
    doctor = "doctor"
    nurse = "nurse"
    patient = "patient"
    finance = "finance"
    admin = "admin"
    registration = "registration"


class CreateUserRequest(BaseModel):
    email: str
    role: RoleEnum
    full_name: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


def authenticate_user(email: str, password: str, db):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user


def create_access_token(
    username: str, user_id: int, role: str, expires_delta: timedelta
):
    encode = {"sub": username, "id": user_id, "role": role}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        role: str = payload.get("role")
        if username is None or user_id is None:
            logger.warning(
                "Authorization failed: invalid token payload",
                extra=log_ctx(user_id=user_id, username=username),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user.",
            )
        return {"username": username, "id": user_id, "role": role}
    except JWTError:
        logger.warning("Authorization failed: JWT validation error")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user."
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    logger.info(
        "Create user request",
        extra=log_ctx(email=create_user_request.email, role=create_user_request.role),
    )
    create_user_model = User(
        email=create_user_request.email,
        role=create_user_request.role,
        full_name=create_user_request.full_name,
        hashed_password=bcrypt_context.hash(create_user_request.password),
        is_active=True,
    )
    db.add(create_user_model)
    db.commit()
    logger.info(
        "User created",
        extra=log_ctx(email=create_user_request.email, role=create_user_request.role),
    )


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency
):
    logger.info("Login attempt", extra=log_ctx(username=form_data.username))
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        logger.warning(
            "Authorization failure: invalid credentials",
            extra=log_ctx(username=form_data.username),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user."
        )
    token = create_access_token(
        str(user.email),
        int(user.id),
        str(user.role),
        timedelta(hours=6),
    )
    logger.info(
        "Login successful",
        extra=log_ctx(user_id=user.id, role=str(user.role), email=user.email),
    )
    return {"access_token": token, "token_type": "bearer"}
