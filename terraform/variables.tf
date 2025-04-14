# Variables
variable "project_id" {
  description = "GCP project ID。tfvarsか0ら読み込む"
  type        = string
}

variable "region" {
  description = "GCPのリソースをデプロイするリージョン。tfvarsから読み込む"
  type        = string
}

variable "zone" {
  description = "リージョン内にあるデプロイエリア。tfvarsから読み込む"
  type        = string
}

variable "service_account_credentials_path" {
  description = "デプロイを行う権限を持ったサービスアカウントの認証情報ファイルパス。tfvarsから読み込む"
  type        = string
}

variable "service_name" {
  description = "Cloud Runのサービス名。Artifact Registryのリポジトリも同じ値にそろえる。tfvarsから読み込む"
  type        = string
}

variable "secrets" {
  description = "Secret Managerに登録する環境変数"
  type        = map(string)
  default     = {}    # 空のマップをデフォルト値として設定
}

variable "artifact_registry_repo" {
  description = "Artifact Registryのリポジトリ名"
  type        = string
}

#
#variable "sqlite_db_name" {
#  description = "Name of the SQLite database file"
#  default     = "sql_app.db"
#  type        = string
#}
#
#variable "sqlite_db_local_path" {
#  description = "Local path to SQLite database file to upload"
#  default     = "/app/data/sql_app.db"
#  type        = string
#}
#