#!/bin/bash
set -e

# ヘルプ関数
usage() {
  echo "Usage: $0 [--plan|--apply] <env>"
  echo "  <env>: prod or stg"
  exit 1
}

ACTION=$1
VAR_FILE="stg.tfvars"

# Terraform の初期化
terraform init

# 引数に応じた Terraform コマンドの実行
case "$ACTION" in
  --plan)
    echo "Executing terraform plan with var-file ${VAR_FILE}..."
    terraform plan -var-file="$VAR_FILE"
    ;;
  --apply)
    echo "Executing terraform apply with var-file ${VAR_FILE}..."
    terraform plan -out=tfplan -var-file="$VAR_FILE"
    terraform apply -auto-approve tfplan
    ;;
  *)
    usage
    ;;
esac