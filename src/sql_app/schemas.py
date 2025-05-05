from typing import List, Optional
import re
from logging import getLogger

from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict
from pydantic_core import PydanticCustomError

logger = getLogger(__name__)

class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None


class ItemCreate(ItemBase):
    pass


class Item(ItemBase):
    id: int
    owner_id: int
        
    model_config = ConfigDict(
        from_attributes=True
    )

        
class ItemList(BaseModel):
    items: List[Item]
    message: Optional[str] = None


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    email: EmailStr # メールアドレスは EmailStr で自動バリデーション可能
    password: str
    
    @field_validator("password")
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise PydanticCustomError(
                "password.too_short",
                "Password must be at least 8 characters."
            )
        if not any(c.islower() for c in v):
            raise PydanticCustomError(
                "password.no_lowercase",
                "Password must contain a lowercase letter."
            )
        if not any(c.isupper() for c in v):
            raise PydanticCustomError(
                "password.no_uppercase",
                "Password must contain an uppercase letter."
            )
        if not any(c.isdigit() for c in v):
            raise PydanticCustomError(
                "password.no_digit",
                "Password must contain a number."
            )
        return v

class User(UserBase):
    id: int
    is_active: bool
    items: List[Item] = []

    model_config = ConfigDict(
        from_attributes=True
    )


class UserCreateResponse(User):
    token: str
