/*
 ==============================================================================
 Query ID:         Q79_graph_cycle_detection_visited_array
 Title:            Cycle Detection in Directed Dependency Graphs with Visited Array
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 In build systems (e.g. Webpack, Bazel) or task scheduling, circular dependencies (Task A -> Task B -> Task A) cause deadlocks. The engine must detect cycles and abort gracefully.

 The Hidden Trap:
 Standard recursive CTEs without cycle tracking loop infinitely until the database crashes with out-of-memory errors.

 The DuckDB Advantage:
 DuckDB array lists (`list_contains`) allow tracking visited paths directly inside recursive CTE state.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE task_dependencies (
                task_id VARCHAR,
                depends_on VARCHAR
            );
            INSERT INTO task_dependencies VALUES
                ('compile', 'codegen'),
                ('codegen', 'lint'),
                ('lint', 'compile'); -- Circular cycle!

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Detect circular loops using array path tracking
            WITH RECURSIVE path_finder AS (
                SELECT 
                    task_id,
                    depends_on,
                    [task_id] AS visited_path,
                    false AS has_cycle
                FROM task_dependencies
                
                UNION ALL
                
                SELECT 
                    p.task_id,
                    d.depends_on,
                    list_append(p.visited_path, d.task_id),
                    list_contains(p.visited_path, d.depends_on) AS has_cycle
                FROM path_finder p
                JOIN task_dependencies d ON p.depends_on = d.task_id
                WHERE NOT p.has_cycle AND array_length(p.visited_path) < 10
            )
            SELECT 
                task_id,
                depends_on,
                visited_path,
                has_cycle
            FROM path_finder
            WHERE has_cycle = true
            LIMIT 1;
