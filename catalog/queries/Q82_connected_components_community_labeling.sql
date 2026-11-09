/*
 ==============================================================================
 Query ID:         Q82_connected_components_community_labeling
 Title:            Graph Connected Components Labeling via Min-ID Propagation
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 Graph connected components partition isolated clusters of customers or machines. Propagating the minimum account ID across edges assigns every node in the same component a shared group ID.

 The Hidden Trap:
 Standard SQL engines lack graph primitives, forcing expensive external graph database licenses.

 The DuckDB Advantage:
 DuckDB can evaluate recursive label propagation directly on relational tables.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE graph_edges (
                node_a INT,
                node_b INT
            );
            -- Component 1: Nodes 1, 2, 3
            -- Component 2: Nodes 8, 9
            INSERT INTO graph_edges VALUES
                (1, 2), (2, 3),
                (8, 9);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Symmetric edges
            WITH RECURSIVE symmetric_edges AS (
                SELECT node_a AS src, node_b AS dst FROM graph_edges
                UNION
                SELECT node_b AS src, node_a AS dst FROM graph_edges
            ),
            components AS (
                -- Anchor: Initial component label is node itself
                SELECT src AS node_id, src AS component_id, 0 AS iteration
                FROM symmetric_edges
                
                UNION ALL
                
                -- Propagate smaller component ID across edges
                SELECT 
                    e.dst AS node_id,
                    c.component_id,
                    c.iteration + 1
                FROM components c
                JOIN symmetric_edges e ON c.node_id = e.src
                WHERE c.component_id < e.dst AND c.iteration < 5
            )
            SELECT 
                node_id,
                MIN(component_id) AS cluster_id
            FROM components
            GROUP BY node_id
            ORDER BY cluster_id, node_id;
