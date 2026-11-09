/*
 ==============================================================================
 Query ID:         Q86_multiparent_allocation_cost_rollup
 Title:            Multi-Parent Shared Infrastructure Cost Allocation Rollup
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 Cloud infrastructure (e.g. shared Kubernetes cluster) is co-owned by multiple products with fractional split percentages. Costs must cascade down to consumer business units.

 The Hidden Trap:
 Failing to multiply split percentages down the DAG results in allocated costs exceeding 100% of actual spend.

 The DuckDB Advantage:
 DuckDB calculates fractional cost propagation with exact decimal precision.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE cost_nodes (
                node_id VARCHAR,
                monthly_cost DECIMAL(10,2)
            );
            CREATE TABLE cost_allocations (
                parent_node VARCHAR,
                child_node VARCHAR,
                allocation_pct DOUBLE
            );
            INSERT INTO cost_nodes VALUES ('K8S_SHARED', 10000.00);
            INSERT INTO cost_allocations VALUES
                ('K8S_SHARED', 'PRODUCT_SEARCH', 0.60),
                ('K8S_SHARED', 'PRODUCT_CHECKOUT', 0.40);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Allocate parent cost to child business units
            SELECT 
                a.parent_node,
                a.child_node,
                a.allocation_pct,
                n.monthly_cost AS raw_parent_cost,
                ROUND(n.monthly_cost * a.allocation_pct, 2) AS allocated_cost
            FROM cost_allocations a
            JOIN cost_nodes n ON a.parent_node = n.node_id
            ORDER BY allocated_cost DESC;
