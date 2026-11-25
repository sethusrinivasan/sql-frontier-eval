import pytest
from harness.aurora_category_auth import (
    CATEGORY_SLUG_MAP,
    get_category_slug,
    get_role_names,
    generate_pg_bootstrap_sql,
    generate_pg_cleanup_sql,
)

def test_category_slug_uniqueness():
    assert len(CATEGORY_SLUG_MAP) == 15
    slugs = [get_category_slug(c) for c in CATEGORY_SLUG_MAP.keys()]
    assert len(slugs) == len(set(slugs)), "Category slugs must be unique"

def test_name_length_limits():
    for cat_name in CATEGORY_SLUG_MAP.keys():
        names = get_role_names(cat_name)
        assert len(names["iam_role_name"]) <= 64, f"IAM role name too long: {names['iam_role_name']}"
        assert len(names["iam_policy_name"]) <= 128, f"IAM policy name too long: {names['iam_policy_name']}"
        assert len(names["pg_role"]) <= 63, f"Postgres role name too long: {names['pg_role']}"
        assert len(names["pg_user"]) <= 63, f"Postgres user name too long: {names['pg_user']}"
        assert len(names["pg_schema"]) <= 63, f"Postgres schema name too long: {names['pg_schema']}"

def test_generated_sql_idempotency():
    bootstrap_sql = generate_pg_bootstrap_sql()
    assert "DO $$" in bootstrap_sql
    assert "GRANT rds_iam TO" in bootstrap_sql
    assert "REVOKE CREATE ON SCHEMA public" in bootstrap_sql

    cleanup_sql = generate_pg_cleanup_sql()
    assert "DROP SCHEMA IF EXISTS" in cleanup_sql
    assert "DROP USER IF EXISTS" in cleanup_sql
    assert "DROP ROLE IF EXISTS" in cleanup_sql
