-- Run as superuser: psql -U postgres -h localhost -f scripts/setup_db.sql
-- You'll be prompted for the postgres superuser password.

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'kyros') THEN
    CREATE ROLE kyros WITH LOGIN PASSWORD 'kyros';
    RAISE NOTICE 'Role kyros created.';
  ELSE
    ALTER ROLE kyros WITH PASSWORD 'kyros';
    RAISE NOTICE 'Role kyros already exists — password reset.';
  END IF;
END
$$;

-- Main DB
CREATE DATABASE kyros OWNER kyros;

-- Test DB
CREATE DATABASE kyros_test OWNER kyros;
