/*
 ==============================================================================
 Query ID:         Q76_bill_of_materials_recursive_rollup
 Title:            Hierarchical Bill of Materials (BOM) Cost Rollup via Recursive CTE
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 Manufacturing an electric vehicle requires thousands of nested parts (Car -> Battery Pack -> Cell Module -> Lithium Cathode). Calculating unit cost requires rolling up quantities across arbitrary depth levels.

 The Hidden Trap:
 Fixed joins only support fixed depth hierarchies (e.g. 3 levels max). If an assembly has 6 levels, fixed joins miss the lowest-tier parts entirely.

 The DuckDB Advantage:
 DuckDB executes `WITH RECURSIVE` queries in memory with zero row-materialization overhead.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE bom_parts (
                parent_part VARCHAR,
                child_part VARCHAR,
                quantity_needed INT,
                unit_cost DECIMAL(10,2)
            );
            INSERT INTO bom_parts VALUES
                ('EV_CAR', 'CHASSIS', 1, 5000.00),
                ('EV_CAR', 'BATTERY_PACK', 1, 0.00),
                ('BATTERY_PACK', 'BATTERY_MODULE', 4, 0.00),
                ('BATTERY_MODULE', 'LITHIUM_CELL', 100, 15.00);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Recursively expand BOM tree to compute total quantity of base components
            WITH RECURSIVE bom_tree AS (
                -- Anchor: Top-level components of EV_CAR
                SELECT 
                    parent_part,
                    child_part,
                    quantity_needed AS total_qty,
                    1 AS depth
                FROM bom_parts
                WHERE parent_part = 'EV_CAR'
                
                UNION ALL
                
                -- Recursive: Multiply quantity down the hierarchy tree
                SELECT 
                    t.child_part AS parent_part,
                    b.child_part,
                    t.total_qty * b.quantity_needed AS total_qty,
                    t.depth + 1 AS depth
                FROM bom_tree t
                JOIN bom_parts b ON t.child_part = b.parent_part
            )
            SELECT 
                child_part,
                total_qty,
                depth
            FROM bom_tree
            ORDER BY depth, child_part;
