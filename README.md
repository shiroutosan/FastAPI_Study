# FastAPI_Study
FastAPI/GCPでの環境構築/Trraform/Github Actionsを使用したCI/CDの学習用。

# FastAPIの環境構築

## ローカルでの環境構築
# Sgt_akapen

旗艦店の商品ページに掲載する画像・テキストについて、販売情報ごとまたは販売単位ごとに誤表記有無や情報の一貫性をチェックする API を提供する。

※Sgt は Sergent（軍曹）の略

# セットアップ

## 環境構築 〜 サーバー起動（ローカルpython + poetry）

- 開発環境のOS WSL2 Ubuntu 20.04 for Windows
- python 3.11 以上
- ライブラリ管理: poetry
- pythonバージョン管理: pyenv

### pyenvのアップデート

ローカルで異なるバージョンのpythonを並行運用したい場合は、pyenvを使用する。

1）pyenvにはアップデートコマンドがないため、プラグインであるpyenv-updateを使用する。

```sh
# pyenv-updateをインストールする
$ git clone https://github.com/pyenv/pyenv-update.git $(pyenv root)/plugins/pyenv-update
# pyenvをアップデートする
$ pyenv update
```
※ Homebrew上のpyenvをアップデートする場合
```sh
$ brew update
$ brew upgrade pyenv
```

.bashrcや.zshrcに、以下をコピペする。

```
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
```

２）3.12系をpyenvコマンドでインストールして有効化する
```sh
pyenv install 3.11.7
pyenv global 3.11.7
python --version # 3.11.7が返って来ればOK
```

### poetryのセットアップ

１）インストール
```sh
curl -sSL https://install.python-poetry.org | python3 -
```

２）パスの追加

インストール時に表示されるメッセージに従って、.bashrcや.zshrcに、PATHを追加する。

sourceコマンド等で、変更を有効化する。

３）poetryの動作確認
```sh
poetry --version
```
が実行できればOK。

４）モジュールのインストール

初回のみ

```
# fastapiの依存関係を考慮してインストール
poetry init --name fastapi-study --dependency fastapi 
```

### サーバー起動

```
cd src
poetry install --no-root
poetry run main.py
```
poetry の設定を適切にしていれば VSCode のデバッガーで起動しても OK。

pyenvで仮想環境を作っている場合：

```sh
poetry shell
python main.py

# 仮想環境を抜けるとき
deactivate

# あとからモジュールを追加する場合(uvicornの例)
poetry add uvicorn[standard] pydantic[email] sqlalchemy httpx pytest
```

