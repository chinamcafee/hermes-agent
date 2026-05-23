#!/usr/bin/env bash
set -euo pipefail

export PGPASSWORD="$(cat /run/secrets/team_cloud_postgres_password)"

team_db_url="$(cat /run/secrets/team_cloud_database_url)"
team_db_password="${team_db_url#postgresql://hermes_team_user:}"
team_db_password="${team_db_password%@postgres:*}"
casdoor_db_password="$(cat /run/secrets/team_cloud_casdoor_db_password)"
spicedb_db_password="$(cat /run/secrets/team_cloud_spicedb_db_password)"

psql -v ON_ERROR_STOP=1 -h postgres -U hermes_superuser -d postgres <<SQL
do \$\$
begin
  if not exists (select 1 from pg_roles where rolname = 'hermes_team_user') then
    create role hermes_team_user login password '${team_db_password}';
  else
    alter role hermes_team_user with password '${team_db_password}';
  end if;

  if not exists (select 1 from pg_roles where rolname = 'casdoor_user') then
    create role casdoor_user login password '${casdoor_db_password}';
  else
    alter role casdoor_user with password '${casdoor_db_password}';
  end if;

  if not exists (select 1 from pg_roles where rolname = 'spicedb_user') then
    create role spicedb_user login password '${spicedb_db_password}';
  else
    alter role spicedb_user with password '${spicedb_db_password}';
  end if;
end
\$\$;
SQL

for db in hermes_team casdoor spicedb; do
  if ! psql -h postgres -U hermes_superuser -d postgres -tAc "select 1 from pg_database where datname='${db}'" | grep -q 1; then
    psql -h postgres -U hermes_superuser -d postgres -c "create database ${db}"
  fi
done

psql -v ON_ERROR_STOP=1 -h postgres -U hermes_superuser -d hermes_team <<SQL
create extension if not exists vector;
grant all privileges on database hermes_team to hermes_team_user;
grant all privileges on schema public to hermes_team_user;
SQL

psql -v ON_ERROR_STOP=1 -h postgres -U hermes_superuser -d casdoor <<SQL
grant all privileges on database casdoor to casdoor_user;
grant all privileges on schema public to casdoor_user;
SQL

psql -v ON_ERROR_STOP=1 -h postgres -U hermes_superuser -d spicedb <<SQL
grant all privileges on database spicedb to spicedb_user;
grant all privileges on schema public to spicedb_user;
SQL
