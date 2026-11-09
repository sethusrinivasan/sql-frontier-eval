/*
 ==============================================================================
 Query ID:         Q50_contrastive_triplet_loss_evaluation
 Title:            Contrastive Triplet Evaluation: Anchor-Positive-Negative Separation
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 In embedding model evaluation, high-quality models satisfy the triplet condition: distance(anchor, positive) + margin < distance(anchor, negative). We evaluate model margin violations directly in SQL.

 The Hidden Trap:
 Validating embedding models often requires ad-hoc PyTorch scripts; SQL evaluation enables continuous monitoring in production.

 The DuckDB Advantage:
 DuckDB computes margin violations across millions of triplets in seconds.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE eval_triplets (
                triplet_id INT,
                anchor_vec FLOAT[2],
                positive_vec FLOAT[2],
                negative_vec FLOAT[2]
            );
            INSERT INTO eval_triplets VALUES
                -- Good triplet: pos is close, neg is far
                (1, [1.0, 0.0]::FLOAT[2], [0.95, 0.05]::FLOAT[2], [0.1, 0.9]::FLOAT[2]),
                -- Violated triplet: neg is closer than pos!
                (2, [1.0, 0.0]::FLOAT[2], [0.5, 0.5]::FLOAT[2],   [0.9, 0.1]::FLOAT[2]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Compute triplet margin violation with margin = 0.2
            -- Violation = GREATEST(0, dist(a, p) - dist(a, n) + margin)
            SELECT 
                triplet_id,
                ROUND(array_distance(anchor_vec, positive_vec), 4) AS dist_pos,
                ROUND(array_distance(anchor_vec, negative_vec), 4) AS dist_neg,
                ROUND(
                    GREATEST(0.0, array_distance(anchor_vec, positive_vec) - array_distance(anchor_vec, negative_vec) + 0.20), 4
                ) AS triplet_margin_loss,
                CASE 
                    WHEN (array_distance(anchor_vec, positive_vec) - array_distance(anchor_vec, negative_vec) + 0.20) > 0 
                    THEN 'VIOLATION' 
                    ELSE 'SATISFIED' 
                END AS evaluation_status
            FROM eval_triplets
            ORDER BY triplet_id;
