#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-ap-northeast-2}"
PREFIX="${SSM_PREFIX:-skn18-3-dev}"
PARAMS_FILE="${PARAMS_FILE:-$(dirname "$0")/ecs-params.txt}"

if [ ! -f "$PARAMS_FILE" ]; then
  echo "ecs-params.txt not found: $PARAMS_FILE" >&2
  exit 1
fi

# Map CFN parameter keys to runtime env vars.
declare -A MAP=(
  ["DjangoEnv"]="DJANGO_ENV"
  ["DjangoDebug"]="DJANGO_DEBUG"
  ["AllowedHosts"]="ALLOWED_HOSTS"
  ["ChatUseFakeCompile"]="CHAT_USE_FAKE_COMPILE"
  ["PostgresDb"]="POSTGRES_DB"
  ["PostgresUser"]="POSTGRES_USER"
  ["Neo4jUser"]="NEO4J_USER"
  ["LlmProvider"]="LLM_PROVIDER"
  ["WebPort"]="WEB_PORT"
  ["GenaiApiVersion"]="GENAI_API_VERSION"
  ["ModelImage"]="MODEL_IMAGE"
  ["OpenaiModel"]="OPENAI_MODEL"
  ["EmbedModelName"]="EMBED_MODEL_NAME"
  ["PgvectorDistance"]="PGVECTOR_DISTANCE"
  ["WebMemory"]="WEB_MEMORY"
  ["CeleryMemory"]="CELERY_MEMORY"
)

env_app=".env.app"
env_secrets=".env.secrets"
env_out=".env"

echo "Writing $env_app from $PARAMS_FILE..."
> "$env_app"
while IFS='=' read -r key value; do
  [ -z "$key" ] && continue
  mapped="${MAP[$key]:-}"
  if [ -n "$mapped" ]; then
    echo "${mapped}=${value}" >> "$env_app"
  fi
done < "$PARAMS_FILE"

echo "Fetching SSM parameters into $env_secrets..."
aws ssm get-parameters-by-path \
  --path "/${PREFIX}" --with-decryption --region "$REGION" \
  --query "Parameters[].{Name:Name,Value:Value}" --output text \
  | awk -F'\t' '{gsub(".*/","",$1); print $1"="$2}' > "$env_secrets"

echo "Merging into $env_out..."
cat "$env_app" "$env_secrets" > "$env_out"

echo "Done: $env_out"
