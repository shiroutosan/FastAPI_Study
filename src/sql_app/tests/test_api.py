from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from ..main import app
from ..database import SessionLocal, engine
import pytest

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

# 問題1のテスト
def test_create_user(test_db, client):
    """POST /users/ のエンドポイントに対する正常系テスト。
    - リクエスト送信時に正常系（status=200）のレスポンスが返却されること
    - /users/{user_id}にリクエストを送信し、登録したユーザーの情報がレスポンスとして返却されること
    """
    response = client.post(
        "/users/",
        json={"email": "deadpool@example.com", "password": "chimicHangas4life"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "deadpool@example.com"
    assert "id" in data
    assert "token" in data  # トークンが生成されているか
    assert "password" not in data
    user_id = data["id"]
    user_token = data["token"]

    response = client.get(f"/users/{user_id}", headers={"X-API-TOKEN": user_token})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["email"] == "deadpool@example.com"
    assert data["id"] == user_id
    
    
    
error_message_email = {"field": "email", "message": "メールアドレスの形式が正しくありません。"}
error_message_password = {
    "field": "password",
    "message": "パスワードは半角英数字のみ8文字以上で構成し、数字・大文字・小文字を最低1文字ずつ含めてください。"
}

def test_create_duplicate_user(test_db, client):
    """POST /users/ のエンドポイントに対する異常系テスト。
    - 登録済ユーザーのemailを含むリクエスト送信時に異常系（status=400）のレスポンスが返却されること
    - 上記エラーパターンで、登録済ユーザーである旨のレスポンスメッセージが返却されること。
    """
    response = client.post(
        "/users/",
        json={"email": "user_1@example.com", "password": "chimicHangas4life"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    
    duplicate_response = client.post(
        "/users/",
        json={"email": data["email"], "password": "ABcd1234"},
    )
    
    assert duplicate_response.status_code == 400, duplicate_response.text
    assert duplicate_response.json()["detail"] == "登録済のメールアドレスです。"
    

@pytest.mark.parametrize(
    # ここで指定した変数名が、テスト関数内で使用可能
    ["email", "password", "expected_detail"],
    # 複数のパラメーターを定義できる
    [
      # 上記の順番(data_in, expected_status, expected_data)で変数を記述する
      pytest.param(
        "tekitounaemail", "1234ABcd", [error_message_email],
        id="email誤り"
      ),
      pytest.param(
        "ok@example.com", ".", [error_message_password],
        id="passwordが8文字未満"
      ),
      pytest.param(
        "ok@example.com", "aaaaBBBB", [error_message_password],
        id="passwordに数字がない"
      ),
      pytest.param(
        "ok@example.com", "abcd1234", [error_message_password],
        id="passwordに大文字がない"
      ),
      pytest.param(
        "ok@example.com", "1234ABCD", [error_message_password],
        id="passwordに小文字がない"
      ),
      pytest.param(
        "ok@example.com", "1234ABCD.", [error_message_password],
        id="passwordに半角英数字以外を含む"
      ),
      pytest.param(
        "ok@examplecom", "1234ABCD.", [error_message_email, error_message_password],
        id="email, password両方誤り"
      ),
    ],
)
def test_create_user_invalid_params(test_db, client, email, password, expected_detail):
    """POST /users/ のエンドポイントに対する異常系テスト。
    - リクエスト送信時に異常系（status=422）のレスポンスが返却されること
    - バリデーションチェック結果に対応したメッセージがレスポンスに含まれること
    """
    response = client.post(
        "/users/",
        json={"email": email, "password": password},
    )
    assert response.status_code == 422, response.text
    data = response.json()
    assert data["detail"] == expected_detail


# 問題2のテスト
def test_read_items_for_user(test_db, client):
    """GET/POST /me/items のエンドポイントに対する正常系テスト。
    - リクエスト送信時に正常系（status=200）のレスポンスが返却されること
    - GET /me/items からのレスポンスに、X-API-TOKENを保有するユーザーがownerのitemだけが含まれること
    """
    # 1. ユーザー作成 (認証不要) 排他性を確認するため、2人分作成
    response_user_1 = client.post(
        "/users/",
        json={"email": "test@example.com", "password": "secretPASS1234"},
    )
    assert response_user_1.status_code == 200
    
    created_user_1 = response_user_1.json()
    print(created_user_1)
    token_1 = created_user_1["token"]
    assert created_user_1["id"] == 1
    
    response_user_2 = client.post(
        "/users/",
        json={"email": "test2@example.com", "password": "secretPASS1234"},
    )
    assert response_user_2.status_code == 200
    
    created_user_2 = response_user_2.json()
    token_2 = created_user_2["token"]

    # 2. 作成したuser_1で Item を2つ作成
    item_1 = {"title": "Task A", "description": "First task"}
    item_2 = {"title": "Task B", "description": "Second task"}

    response_item_1 = client.post(
        f"/me/items/",
        json=item_1,
        headers={"X-API-TOKEN": token_1},
    )
    assert response_item_1.status_code == 200

    response_item_2 = client.post(
        f"/me/items/",
        json=item_2,
        headers={"X-API-TOKEN": token_1},
    )
    assert response_item_2.status_code == 200

    # 3. GET /me/items で自分のアイテムのみ取得できる
    response_user_1_items = client.get("/me/items", headers={"X-API-TOKEN": token_1})
    assert response_user_1_items.status_code == 200
    assert response_user_1_items.json() == {
        "items":[
            {
                'id': 1,
                'title': item_1['title'],
                'description': item_1['description'],
                'owner_id': 1,
            },
            {
                'id': 2,
                'title': item_2['title'],
                'description': item_2['description'],
                'owner_id': 1,
            }
        ],
        "message": "ok"
    }
    
    # 4. GET /me/items で結果が空だった時に専用のメッセージが返却される
    response_user_2_items_blank = client.get("/me/items", headers={"X-API-TOKEN": token_2})
    assert response_user_2_items_blank.status_code == 200
    assert response_user_2_items_blank.json() ==  {"items": [], "message": "タスクが1件も登録されていません。"}
    
    # 5. user2のitemを追加し、GET /me/items にuser1のitemが含まれないことを確認する
    item_3 = {"title": "Task C", "description": "First task"}

    response_item_3 = client.post(
        f"/me/items/",
        json=item_3,
        headers={"X-API-TOKEN": token_2},
    )
    assert response_item_3.status_code == 200
    
    response_user_2_items_includes = client.get("/me/items", headers={"X-API-TOKEN": token_2})
    assert response_user_2_items_includes.status_code == 200
    assert response_user_2_items_includes.json() == {
        "items":[
            {
                'id': 3,
                'title': item_3['title'],
                'description': item_3['description'],
                'owner_id': 2,
            },
        ],
        "message": "ok"
    }

    
# 問題3のテスト
def test_delete_user(test_db, client):
    # 1. ユーザA作成 (ID=1相当)
    response_a = client.post("/users/", json={"email": "a@example.com", "password": "abCD1234"})
    user_a = response_a.json()
    token_a = user_a["token"]

    # 2. ユーザB作成 (ID=2相当)
    response_b = client.post("/users/", json={"email": "b@example.com", "password": "abCD1234"})
    user_b = response_b.json()
    token_b = user_b["token"]

    # 3. ユーザC作成 (ID=3相当)
    response_c = client.post("/users/", json={"email": "c@example.com", "password": "abCD1234"})
    user_c = response_c.json()
    token_c = user_c["token"]

    # 4. ユーザBのアイテムを3つ作成する
    for i in range(3):
        client.post(
            f"/users/{user_b['id']}/items/",
            json={"title": f"Task B{i}", "description": f"Bさんのタスク{i}"},
            headers={"X-API-TOKEN": token_b},
        )

    # 5. ユーザBを削除 (is_active=False)
    #    → Bが持っていたアイテムは「最もIDが小さい 他の有効ユーザ(A or C)」= A の所有物になる
    response_delete_b = client.delete(
        f"/users/{user_b['id']}",
        headers={"X-API-TOKEN": token_a},  # 誰のトークンで削除を呼ぶか、運用ポリシーを定める必要がある
    )
    assert response_delete_b.status_code == 200

    deleted_b_info = response_delete_b.json()
    assert deleted_b_info["id"] == user_b["id"]
    assert deleted_b_info["is_active"] == False  # 削除(= 無効化)された
    
    # 6. /users/{b} を GET して is_active=False が返る
    response_get_b = client.get(f"/users/{user_b['id']}", headers={"X-API-TOKEN": token_a})
    b_data = response_get_b.json()
    assert b_data["is_active"] == False
    
   # print(client.get("/items", headers={"X-API-TOKEN": token_a}).json())

    # 7. B が所有していたアイテムが A に移動したか確認する
    #    Aのトークンで /me/items を呼び出し、アイテム3つが含まれるか検証
    response_a_me_items = client.get("/me/items", headers={"X-API-TOKEN": token_a})
    assert response_a_me_items.status_code == 200
    items_a = response_a_me_items.json()
    assert len(items_a['items']) == 3

    # 8. /items/ を通じてIDとowner_idを直接確認
    response_all_items = client.get("/items", headers={"X-API-TOKEN": token_a})
    all_items_data = response_all_items.json()
    # Bが作成した "Task B0", "Task B1", "Task B2" の owner_id が A になっているか確認
    tasks_for_b = [item for item in all_items_data['items'] if item["title"].startswith("Task B")]
    assert len(tasks_for_b) == 3
    for task in tasks_for_b:
        assert task["owner_id"] == user_a["id"]


# 問題1・3のテスト（異常系）
def test_read_users_unauthorized(test_db, client):
    """GET /users/ のエンドポイントに対する異常系テスト。
    - X-API-TOKENがリクエストヘッダに含まれない場合に、その旨通知するメッセージがレスポンスに含まれること
    - X-API-TOKENに対するバリデーションチェック結果に対応したメッセージがレスポンスに含まれること
    - X-API-TOKENから特定したユーザーが削除されている場合に、その旨通知するメッセージがレスポンスに含まれること
    """
    
    response = client.get("/users/")
    assert response.status_code == 401
    assert response.json()["detail"] == "X-API-TOKENの値がリクエストに含まれていません。"
    
    response = client.get("/users/", headers={"X-API-TOKEN": "uncertainvalue"})
    assert response.status_code == 401
    assert response.json()["detail"] == "X-API-TOKENの値が不正です。"
    
    # ユーザーを作成する
    response_user = client.post(
        "/users/",
        json={"email": "test@example.com", "password": "secretPASS1234"},
    )
    assert response_user.status_code == 200
    user = response_user.json()
    # ユーザーを削除 (is_active=False)
    response_delete = client.delete(
        f"/users/{user['id']}",
        headers={"X-API-TOKEN": user['token']},  # 自分で自分の情報を削除可とするか、運用ポリシーを定める必要がある
    )
    assert response_delete.status_code == 200
    
    response = client.get("/users/", headers={"X-API-TOKEN": user['token']})
    assert response.status_code == 403
    assert response.json()["detail"] == "ユーザーの情報は削除されています。"
