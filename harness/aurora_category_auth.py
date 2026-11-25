"""
Aurora PostgreSQL Category-Specific Least-Privilege IAM & Database Roles.

Provides deterministic, category-scoped IAM roles and PostgreSQL users/roles
for evaluating SQL Frontier Benchmark tasks on Amazon Aurora Serverless v2.

Naming convention (fixed prefix/suffix for idempotent re-use):
- IAM Role:       sql-eval-<cat_slug>-role
- IAM Policy:     sql-eval-<cat_slug>-policy
- Postgres Role:  sql_eval_r_<cat_slug>
- Postgres User:  sql_eval_u_<cat_slug>
- Schema Sandbox: sql_eval_s_<cat_slug>
"""
import re
import json
try:
    import boto3
except ImportError:
    boto3 = None
from typing import Dict, Any, List

ACCOUNT_ID = "596090776030"
REGION = "us-east-2"
CLUSTER_RESOURCE_ID = "cluster-DJLU4ZBVHZ6HGQCZTXR7YKDQ7Q"
INSTANCE_RESOURCE_ID = "db-2XO26BXAL55XZVXHWHEXH5DD4I"

# Master category mapping with clean, deterministic slugs
CATEGORY_SLUG_MAP = {
    "Algorithmic Efficiency / Window Distinct": "algo_efficiency_window",
    "Graph & Hierarchy": "graph_hierarchy",
    "Metric Inflation / Chasm Trap": "metric_inflation_chasm",
    "Non-SARGable Partition Pruning": "nonsargable_partition",
    "Quadratic Self-Joins vs Range Windows": "quadratic_self_joins",
    "SCD Type 2 Point-in-Time Joins": "scd_type_2_pit",
    "Search & Retrieval": "search_retrieval",
    "Sessionization (Gaps & Islands)": "sessionization_gaps",
    "Strict Funnel Precedence": "strict_funnel_precedence",
    "Temporal & Time-Series": "temporal_time_series",
    "Three-Valued Logic in Anti-Joins": "three_valued_logic",
    "Vector & Embeddings": "vector_embeddings",
    "Vector & Retrieval": "vector_retrieval",
    "Warehouse & Statistical": "warehouse_statistical",
    "Window Frame Default Bounds": "window_frame_bounds",
}

def get_category_slug(category: str) -> str:
    """Returns deterministic fixed-suffix slug for any category name."""
    if category in CATEGORY_SLUG_MAP:
        return CATEGORY_SLUG_MAP[category]
    clean = re.sub(r"[^a-z0-9]+", "_", category.lower()).strip("_")
    return clean[:28]

def get_role_names(category: str) -> Dict[str, str]:
    """Generates all deterministic names for a given category."""
    slug = get_category_slug(category)
    return {
        "slug": slug,
        "iam_role_name": f"sql-eval-{slug}-role",
        "iam_policy_name": f"sql-eval-{slug}-policy",
        "iam_role_arn": f"arn:aws:iam::{ACCOUNT_ID}:role/sql-eval-{slug}-role",
        "pg_role": f"sql_eval_r_{slug}",
        "pg_user": f"sql_eval_u_{slug}",
        "pg_schema": f"sql_eval_s_{slug}",
    }

def ensure_all_iam_roles() -> Dict[str, str]:
    """Idempotently provisions or reuses all 15 category-specific IAM roles and policies."""
    if boto3 is None:
        raise RuntimeError("boto3 must be installed to manage IAM roles")
    iam = boto3.client("iam", region_name=REGION)
    created_or_verified = {}
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    for cat_name, slug in CATEGORY_SLUG_MAP.items():
        names = get_role_names(cat_name)
        role_name = names["iam_role_name"]
        policy_name = names["iam_policy_name"]
        pg_user = names["pg_user"]

        # 1. Create or verify role
        try:
            iam.get_role(RoleName=role_name)
            # update trust policy to ensure validity
            iam.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=json.dumps(trust_policy)
            )
        except iam.exceptions.NoSuchEntityException:
            iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"Scoped IAM DB Auth role for category {cat_name} in sql-frontier-eval",
            )

        # 2. Scoped rds-db:connect policy (strictly for this category's pg_user)
        policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": f"Connect{slug.replace('_', '').capitalize()}DbUser",
                    "Effect": "Allow",
                    "Action": "rds-db:connect",
                    "Resource": [
                        f"arn:aws:rds-db:{REGION}:{ACCOUNT_ID}:dbuser:{CLUSTER_RESOURCE_ID}/{pg_user}",
                        f"arn:aws:rds-db:{REGION}:{ACCOUNT_ID}:dbuser:{INSTANCE_RESOURCE_ID}/{pg_user}",
                        f"arn:aws:rds-db:{REGION}:{ACCOUNT_ID}:dbuser:*/{pg_user}",
                    ],
                }
            ],
        }
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_doc),
        )
        created_or_verified[cat_name] = names["iam_role_arn"]
        
    return created_or_verified

if __name__ == "__main__":
    print(f"Provisioning / verifying all {len(CATEGORY_SLUG_MAP)} category IAM roles...")
    roles = ensure_all_iam_roles()
    for cat, arn in sorted(roles.items()):
        print(f"  [OK] {cat} -> {arn}")

def generate_pg_bootstrap_sql() -> str:
    """Generates the idempotent SQL script to create all 15 category users, roles, and schemas."""
    statements = []
    for cat_name, slug in CATEGORY_SLUG_MAP.items():
        names = get_role_names(cat_name)
        pg_role = names["pg_role"]
        pg_user = names["pg_user"]
        pg_schema = names["pg_schema"]

        statements.append(f"""
        -- Category: {cat_name}
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{pg_role}') THEN
                CREATE ROLE {pg_role};
            END IF;
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{pg_user}') THEN
                CREATE USER {pg_user} WITH LOGIN IN ROLE {pg_role};
            END IF;
        END
        $$;

        GRANT rds_iam TO {pg_user};
        GRANT {pg_role} TO {pg_user};
        GRANT {pg_user} TO postgres;
        GRANT {pg_role} TO postgres;
        GRANT CONNECT ON DATABASE postgres TO {pg_user}, {pg_role};

        CREATE SCHEMA IF NOT EXISTS {pg_schema} AUTHORIZATION {pg_role};
        GRANT ALL ON SCHEMA {pg_schema} TO {pg_role};
        ALTER USER {pg_user} SET search_path = {pg_schema}, public;
        REVOKE CREATE ON SCHEMA public FROM {pg_user}, {pg_role};
        """)
    return "\n".join(statements)

def generate_pg_cleanup_sql() -> str:
    """Generates the teardown SQL script to completely remove all category schemas, users, and roles."""
    statements = []
    for cat_name, slug in CATEGORY_SLUG_MAP.items():
        names = get_role_names(cat_name)
        pg_role = names["pg_role"]
        pg_user = names["pg_user"]
        pg_schema = names["pg_schema"]

        statements.append(f"""
        DROP SCHEMA IF EXISTS {pg_schema} CASCADE;
        REVOKE ALL ON DATABASE postgres FROM {pg_user}, {pg_role};
        REVOKE rds_iam FROM {pg_user};
        DROP USER IF EXISTS {pg_user};
        DROP ROLE IF EXISTS {pg_role};
        """)
    return "\n".join(statements)

def cleanup_all_iam_roles() -> None:
    """Deletes all 15 category-specific IAM roles and policies."""
    if boto3 is None:
        raise RuntimeError("boto3 must be installed to manage IAM roles")
    iam = boto3.client("iam", region_name=REGION)
    for cat_name in CATEGORY_SLUG_MAP.keys():
        names = get_role_names(cat_name)
        role_name = names["iam_role_name"]
        policy_name = names["iam_policy_name"]
        try:
            iam.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
        except Exception:
            pass
        try:
            iam.delete_role(RoleName=role_name)
            print(f"Deleted IAM role {role_name}")
        except Exception as ex:
            print(f"Failed to delete {role_name}: {ex}")

