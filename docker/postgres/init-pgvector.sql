-- Runs once, on first database initialisation (docker-entrypoint-initdb.d).
-- Why this file exists: the initial Alembic migration creates VECTOR(384) columns
-- but never creates the pgvector extension itself, so migrations fail on a fresh
-- database until the extension exists. Creating it here makes `docker compose up`
-- a true one-command setup.
CREATE EXTENSION IF NOT EXISTS vector;
