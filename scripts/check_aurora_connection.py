"""Hourly check script for Aurora Serverless PostgreSQL IAM DB Authentication recovery."""
import sys
import time
import boto3
import certifi
import psycopg

DB_HOST = "reality-check-cost-tracker.cluster-c52ymc6u0ruy.us-east-2.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "postgres"
DB_IAM_USER = "sql_frontier_eval_user"
REGION = "us-east-2"
ROLE_ARN = "arn:aws:iam::596090776030:role/sql-frontier-eval-aurora-role"

def test_connection() -> bool:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}] Checking Aurora IAM DB Auth connection...")
    try:
        sts = boto3.client("sts", region_name=REGION)
        assumed = sts.assume_role(
            RoleArn=ROLE_ARN,
            RoleSessionName="hourly-aurora-recheck"
        )
        creds = assumed["Credentials"]
        scoped_rds = boto3.client(
            "rds",
            region_name=REGION,
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        )
        token = scoped_rds.generate_db_auth_token(
            DBHostname=DB_HOST, Port=DB_PORT, DBUsername=DB_IAM_USER, Region=REGION
        )
        t0 = time.perf_counter()
        conn = psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_IAM_USER,
            password=token,
            sslmode="verify-full",
            sslrootcert=certifi.where(),
            connect_timeout=25,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        with conn.cursor() as cur:
            cur.execute("SELECT current_user, current_schema(), version();")
            row = cur.fetchone()
            print(f"SUCCESS! Connected in {elapsed_ms:.1f}ms: {row}")
        conn.close()
        return True
    except Exception as exc:
        print(f"Check failed: {exc}")
        return False

if __name__ == "__main__":
    success = test_connection()
    if success:
        print("Aurora IAM Auth is OPERATIONAL! Launching full eval pipeline...")
        import subprocess
        res = subprocess.run([sys.executable, "scripts/run_aurora_eval_pipeline.py"])
        sys.exit(res.returncode)
    else:
        sys.exit(1)
