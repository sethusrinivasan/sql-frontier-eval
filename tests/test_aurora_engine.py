import unittest
from unittest.mock import patch, MagicMock
from harness.engine import SQLEvalEngine
from harness.aurora_category_auth import get_role_names

class TestAuroraEngineCategoryAuth(unittest.TestCase):
    @patch("harness.engine.boto3")
    @patch("harness.engine.psycopg2")
    def test_aurora_category_role_switching(self, mock_psycopg2, mock_boto3):
        # Setup mock STS client
        mock_sts = MagicMock()
        mock_sts.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "ASIA_TEST_KEY",
                "SecretAccessKey": "TEST_SECRET",
                "SessionToken": "TEST_SESSION_TOKEN",
            }
        }
        
        # Setup mock RDS client
        mock_rds = MagicMock()
        mock_rds.generate_db_auth_token.return_value = "db-auth-token-xyz"
        
        def boto_client_side_effect(service, **kwargs):
            if service == "sts":
                return mock_sts
            elif service == "rds":
                return mock_rds
            return MagicMock()

        mock_boto3.client.side_effect = boto_client_side_effect

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn

        # Initialize Aurora Engine
        engine = SQLEvalEngine(engine_type="aurora")
        self.assertIsNone(engine.aurora_current_category)

        # 1. Reset sandbox with First Category: Algorithmic Efficiency
        cat_1 = "Algorithmic Efficiency / Window Distinct"
        engine.reset_sandbox(category=cat_1)

        names_1 = get_role_names(cat_1)
        self.assertEqual(engine.aurora_current_category, cat_1)
        mock_sts.assume_role.assert_called_with(
            RoleArn=names_1["iam_role_arn"],
            RoleSessionName=f"sql-eval-{names_1['slug']}"
        )
        mock_rds.generate_db_auth_token.assert_called_with(
            DBHostname=engine.aurora_host,
            Port=5432,
            DBUsername=names_1["pg_user"],
            Region="us-east-2"
        )
        mock_psycopg2.connect.assert_called_with(
            host=engine.aurora_host,
            port=5432,
            dbname="postgres",
            user=names_1["pg_user"],
            password="db-auth-token-xyz",
            sslmode="verify-full",
            sslrootcert=unittest.mock.ANY,
            connect_timeout=15
        )
        # Verify schema isolation was applied
        mock_cursor.execute.assert_any_call(f"SET search_path TO {names_1['pg_schema']}, public;")

        # 2. Reset sandbox with Second Category: Temporal & Time-Series
        cat_2 = "Temporal & Time-Series"
        engine.reset_sandbox(category=cat_2)

        names_2 = get_role_names(cat_2)
        self.assertEqual(engine.aurora_current_category, cat_2)
        mock_sts.assume_role.assert_called_with(
            RoleArn=names_2["iam_role_arn"],
            RoleSessionName=f"sql-eval-{names_2['slug']}"
        )
        mock_rds.generate_db_auth_token.assert_called_with(
            DBHostname=engine.aurora_host,
            Port=5432,
            DBUsername=names_2["pg_user"],
            Region="us-east-2"
        )
        mock_psycopg2.connect.assert_called_with(
            host=engine.aurora_host,
            port=5432,
            dbname="postgres",
            user=names_2["pg_user"],
            password="db-auth-token-xyz",
            sslmode="verify-full",
            sslrootcert=unittest.mock.ANY,
            connect_timeout=15
        )
        mock_cursor.execute.assert_any_call(f"SET search_path TO {names_2['pg_schema']}, public;")
