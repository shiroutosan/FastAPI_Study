from typing import List
from logging import getLogger, DEBUG

from fastapi import Depends, FastAPI, Request, HTTPException, Header, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
logger = getLogger(__name__)
#logger.setLevel(DEBUG)

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    リクエストバリデーションエラー全般に対するカスタムハンドラ。
    EmailStrやpasswordのregex/min_lengthエラーを拾って独自メッセージに書き換える。
    """
    # Pydantic が集めたバリデーションエラー情報 (list[dict])
    raw_errors = exc.errors()

    custom_errors = []
    for err in raw_errors:
        loc = err.get("loc", [])    # 例: ("body","password"), ("body","email") etc.
        msg = err.get("msg", "")   # 例: "value is not a valid email address", "string does not match regex"
        err_type = err.get("type", "")  # 例: "value_error.email", "value_error.str.regex", etc.

        # email フィールドに関するエラー
        if "email" in loc:
            if "valid email address" in msg or "value_error.email" in err_type:
                custom_errors.append({
                    "field": "email",
                    "message": "メールアドレスの形式が正しくありません。"
                })
            else:
                # 他の理由で email がNGになる場合(あまりないが)
                custom_errors.append({
                    "field": "email",
                    "message": f"メールアドレスの入力が不正です: {msg}"
                })

        # password フィールドに関するエラー
        elif "password" in loc:
            # 最低文字数エラー または 正規表現にマッチしないエラー
            if err_type in ["password.too_short", "password.no_lowercase", 
                            "password.no_uppercase", "password.no_digit", ]:
                custom_errors.append({
                    "field": "password",
                    "message": "パスワードは半角英数字のみ8文字以上で構成し、数字・大文字・小文字を最低1文字ずつ含めてください。"
                })
            else:
                # 予期せぬ別のエラーの場合
                custom_errors.append({
                    "field": "password",
                    "message": f"パスワードの入力が不正です: {msg}"
                })

        else:
            # 他のフィールドやクエリパラメータに対するエラー
            # 必要に応じて別途文言を変える
            custom_errors.append({
                "field": loc[-1] if loc else "unknown",
                "message": msg,
            })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": custom_errors},
    )

# データベース依存関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_session = Depends(get_db)


# "X-API-TOKEN" というヘッダから認証トークンを取得する設定
api_key_header = APIKeyHeader(name="X-API-TOKEN", auto_error=False)

# 認証用依存関数
def get_current_user(
    x_api_token: str = Depends(api_key_header),
    db: Session = Depends(get_db),
):
    """
    X-API-TOKEN ヘッダの値(token)からユーザを特定・認証する。
    """
    # ヘッダが存在しない場合
    if x_api_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-TOKENの値がリクエストに含まれていません。",
        )

    # DB から該当トークンのユーザを取得
    user = crud.get_user_by_token(db, token=x_api_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-TOKENの値が不正です。",
        )
    elif user.is_active == False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ユーザーの情報は削除されています。",
        )
    return user


# 以下、エンドポイントに対応するRouter
@app.get("/health-check")
def health_check(db: Session = Depends(get_db)):
    logger.info("リクエストが来たよ")
    return {"status": "ok"}


@app.post("/users/", response_model=schemas.UserCreateResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    新規ユーザーを作成する。このエンドポイントだけは認証不要。
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
       raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="登録済のメールアドレスです。")
    new_user = crud.create_user(db=db, user=user)
    
    # 作成直後のユーザ情報に token が含まれていることを前提にレスポンスを返す
    return schemas.UserCreateResponse(
        id=new_user.id,
        email=new_user.email,
        is_active=new_user.is_active,
        items=[],
        token=new_user.token,
    )


@app.get("/users/", response_model=List[schemas.User])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/users/{user_id}/items/", response_model=schemas.Item)
def create_item_for_user(
    user_id: int,
    item: schemas.ItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_user_item(db=db, item=item, user_id=user_id)

@app.post("/me/items/", response_model=schemas.Item)
def create_item_for_self(
    item: schemas.ItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.create_user_item(db=db, item=item, user_id=current_user.id)

@app.get("/me/items/", response_model=schemas.ItemList)
def read_items_for_user(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    items = crud.get_items_for_user(db, skip=skip, limit=limit, user_id=current_user.id)
    
    if not items:
        # 200 OK で空リストとメッセージを返却
        return {
            "items": [],
            "message": "タスクが1件も登録されていません。"
        }

    # 取得できた場合
    return {"items": items, "message": "ok"}


@app.get("/items/", response_model=schemas.ItemList)
def read_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    items = crud.get_items(db, skip=skip, limit=limit)
    
    if not items:
        # 200 OK で空リストとメッセージを返却
        return {
            "items": [],
            "message": "タスクが1件も登録されていません。"
        }

    # 取得できた場合
    return {"items": items, "message": "ok"}


@app.delete("/users/{user_id}", response_model=schemas.User)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), 
    ):
     """
     ユーザを削除(active=False)とし、
     そのユーザが所有していた Item の所有権を他の有効ユーザへ移行する。
     """
     db_user = crud.deactivate_user_and_reassign_items(db, user_id)
     if db_user is None:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ユーザーが見つかりません。")
     return db_user
