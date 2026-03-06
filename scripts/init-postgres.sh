#!/usr/bin/env bash
# Creates multiple PostgreSQL databases in a single postgres container.
# Called automatically by the postgres Docker entrypoint.
set -euo pipefail

function create_user_and_database() {
  local database=$1
  local username=$2
  local password=$3
  echo "  Creating user '${username}' and database '${database}'"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER ${username} WITH PASSWORD '${password}';
    CREATE DATABASE ${database};
    GRANT ALL PRIVILEGES ON DATABASE ${database} TO ${username};
    \c ${database}
    GRANT ALL ON SCHEMA public TO ${username};
EOSQL
}

create_user_and_database litellm  litellm  litellm_password
create_user_and_database langfuse langfuse langfuse_password

echo "PostgreSQL databases initialized."
