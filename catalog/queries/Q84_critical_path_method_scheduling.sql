/*
 ==============================================================================
 Query ID:         Q84_critical_path_method_scheduling
 Title:            Task Scheduling Critical Path Method (CPM) Duration Analysis
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 Project managers identify the 'Critical Path'—the longest sequence of dependent tasks that dictates the minimum project completion time.

 The Hidden Trap:
 Adding task durations without considering parallel execution branches yields an unrealistically inflated project timeline.

 The DuckDB Advantage:
 DuckDB recursive CTEs trace parallel branch durations and calculate maximum path length.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE project_tasks (
                task_code VARCHAR,
                prerequisite_code VARCHAR,
                duration_days INT
            );
            INSERT INTO project_tasks VALUES
                ('START', NULL, 0),
                ('DESIGN', 'START', 10),
                ('BUILD_FRONTEND', 'DESIGN', 15),
                ('BUILD_BACKEND',  'DESIGN', 25), -- Longest branch
                ('DEPLOY', 'BUILD_BACKEND', 5);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Find the longest path (Critical Path) from START to DEPLOY
            WITH RECURSIVE task_paths AS (
                SELECT 
                    task_code,
                    duration_days AS cumulative_days,
                    task_code AS path_str
                FROM project_tasks
                WHERE prerequisite_code IS NULL
                
                UNION ALL
                
                SELECT 
                    t.task_code,
                    p.cumulative_days + t.duration_days,
                    p.path_str || ' -> ' || t.task_code
                FROM task_paths p
                JOIN project_tasks t ON p.task_code = t.prerequisite_code
            )
            SELECT 
                task_code,
                cumulative_days AS critical_path_duration,
                path_str
            FROM task_paths
            ORDER BY cumulative_days DESC
            LIMIT 1;
