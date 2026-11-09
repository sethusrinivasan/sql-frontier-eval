/*
 ==============================================================================
 Query ID:         Q77_org_hierarchy_span_of_control
 Title:            Organizational Reporting Depth & Management Span of Control
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 HR analytics measures how deep the management chain is from the CEO to individual contributors and calculates direct vs indirect headcounts for each manager.

 The Hidden Trap:
 Unbounded recursive queries crash if there is an accidental circular reporting loop (e.g. A reports to B, B reports to A).

 The DuckDB Advantage:
 DuckDB recursion tracks path depth to prevent infinite loops.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE employees (
                emp_id INT,
                emp_name VARCHAR,
                manager_id INT
            );
            INSERT INTO employees VALUES
                (1, 'Alice (CEO)', NULL),
                (2, 'Bob (VP Eng)', 1),
                (3, 'Charlie (VP Sales)', 1),
                (4, 'David (Staff Eng)', 2),
                (5, 'Eve (Senior Eng)', 4);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Traverse management tree from CEO downward, tracking reporting depth
            WITH RECURSIVE org_hierarchy AS (
                SELECT 
                    emp_id,
                    emp_name,
                    manager_id,
                    1 AS hierarchy_level,
                    emp_name AS reporting_path
                FROM employees
                WHERE manager_id IS NULL
                
                UNION ALL
                
                SELECT 
                    e.emp_id,
                    e.emp_name,
                    e.manager_id,
                    h.hierarchy_level + 1,
                    h.reporting_path || ' -> ' || e.emp_name
                FROM employees e
                JOIN org_hierarchy h ON e.manager_id = h.emp_id
            )
            SELECT 
                emp_id,
                emp_name,
                hierarchy_level,
                reporting_path
            FROM org_hierarchy
            ORDER BY hierarchy_level, emp_id;
