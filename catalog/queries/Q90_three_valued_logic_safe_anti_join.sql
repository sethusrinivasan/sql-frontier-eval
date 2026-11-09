/*
 ==============================================================================
 Query ID:         Q90_three_valued_logic_safe_anti_join
 Title:            Three-Valued Logic Safe Anti-Join (Eliminating the NOT IN NULL Trap)
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 Marketing queries to find active customers who have not churned often use `WHERE id NOT IN (SELECT customer_id FROM churned_users)`. If a single `NULL` exists in `churned_users`, SQL three-valued logic causes the entire query to return ZERO rows.

 The Hidden Trap:
 In SQL, `val NOT IN (1, NULL)` evaluates to `UNKNOWN`, which evaluates to `FALSE` in WHERE clauses, silently discarding every single record.

 The DuckDB Advantage:
 Using `NOT EXISTS` or `ANTI JOIN` avoids three-valued logic traps and compiles to optimal hash anti-joins.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE all_customers (customer_id INT, name VARCHAR);
            CREATE TABLE churned_customers (customer_id INT);
            INSERT INTO all_customers VALUES (1, 'Alice'), (2, 'Bob'), (3, 'Charlie');
            -- Note the presence of a NULL record in the churned table!
            INSERT INTO churned_customers VALUES (2), (NULL);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Robust anti-join that is immune to NULL records in the subquery
            SELECT 
                c.customer_id,
                c.name
            FROM all_customers c
            WHERE NOT EXISTS (
                SELECT 1 
                FROM churned_customers ch 
                WHERE ch.customer_id = c.customer_id
            )
            ORDER BY c.customer_id;
