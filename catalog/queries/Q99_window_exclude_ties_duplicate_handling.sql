/*
 ==============================================================================
 Query ID:         Q99_window_exclude_ties_duplicate_handling
 Title:            Window Frame Ties Exclusion: EXCLUDE TIES for Unbiased Cumulative Totals
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 In financial ranking, when multiple entities have the exact same score, evaluating cumulative rank metrics without self-reinforcing duplicate ties prevents tied participants from skewing percentiles.

 The Hidden Trap:
 Tied participants mutually inflate each other's cumulative metrics.

 The DuckDB Advantage:
 DuckDB supports `EXCLUDE TIES` in window frames.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE gaming_scores (
                player_id INT,
                score INT
            );
            INSERT INTO gaming_scores VALUES
                (1, 500),
                (2, 450),
                (3, 450), -- Tie
                (4, 300);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate cumulative score excluding tied peers at the current rank
            SELECT 
                player_id,
                score,
                SUM(score) OVER (
                    ORDER BY score DESC
                    RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    EXCLUDE TIES
                ) AS cumulative_score_excluding_tied_peers
            FROM gaming_scores
            ORDER BY score DESC, player_id;
