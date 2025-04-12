import secrets
from sqlalchemy.orm import Session

from . import models, schemas


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_token(db: Session, token: str):
    return db.query(models.User).filter(models.User.token == token).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = models.User(
        email=user.email, 
        hashed_password=fake_hashed_password,
        is_active=True,
        token=secrets.token_hex(16),  # 16進数ランダム文字列をトークンとして発行
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_items(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Item).order_by(models.Item.id).limit(limit).offset(skip).all()


def get_items_for_user(db: Session, user_id:int, skip: int = 0, limit: int = 100):
    return db.query(models.Item).filter(models.Item.owner_id == user_id).offset(skip).limit(limit).all()


def create_user_item(db: Session, item: schemas.ItemCreate, user_id: int):
    db_item = models.Item(title=item.title, description=item.description, owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def deactivate_user_and_reassign_items(db: Session, user_id: int):
    """
    指定のユーザを無効化し、そのユーザが所有していた Item を
    最も ID が小さい他の有効なユーザに移行する。
    """
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        # ユーザが存在しない場合
        return None

    # すでに非アクティブなら何もしない
    if db_user.is_active is False:
        return db_user
    else:
        # ユーザを無効化
        db_user.is_active = False
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # 「最も ID が小さい有効ユーザ」を検索する
        new_owner = (
            db.query(models.User)
            .filter(models.User.is_active == True, models.User.id != user_id)
            .order_by(models.User.id.asc())
            .first()
        )

        if not new_owner:
            new_owner_id = None # 有効なユーザーがいないときは、owner_idをNULLにする
        else:
            new_owner_id = new_owner.id

        # アイテム所有権を new_owner に移す
        db.query(models.Item).filter(models.Item.owner_id == user_id).update(
            {"owner_id": new_owner_id}
        )
        db.commit()

        return db_user