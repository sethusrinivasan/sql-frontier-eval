/*
 ==============================================================================
 Query ID:         Q39_maximal_marginal_relevance_mmr
 Title:            Maximal Marginal Relevance (MMR) Diversity Reranking in SQL
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 Standard vector retrieval often returns 5 virtually identical articles. MMR penalizes redundancy by selecting documents that are similar to the query but dissimilar to already-selected documents.

 The Hidden Trap:
 Pure relevance search creates echo-chamber search results with zero content diversity.

 The DuckDB Advantage:
 DuckDB can compute inter-candidate similarity matrix in memory to penalize redundancy.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE news_articles (
                article_id INT,
                headline VARCHAR,
                vec FLOAT[2]
            );
            INSERT INTO news_articles VALUES
                (1, 'Fed cuts interest rates by 25 bps',      [0.99, 0.05]::FLOAT[2]),
                (2, 'Central bank lowers benchmark 25 bps',   [0.98, 0.06]::FLOAT[2]), -- Redundant clone
                (3, 'Tech stock rally follows monetary shift', [0.80, 0.45]::FLOAT[2]); -- Diverse relevant

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- First candidate is highest query similarity; score subsequent candidates by query sim minus similarity to article 1
            WITH ranked_candidates AS (
                SELECT 
                    article_id,
                    headline,
                    vec,
                    array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) AS query_sim
                FROM news_articles
            )
            SELECT 
                c.article_id,
                c.headline,
                ROUND(c.query_sim, 4) AS query_relevance,
                ROUND(array_cosine_similarity(c.vec, top1.vec), 4) AS redundancy_with_top1,
                -- MMR formula: 0.7 * Sim(doc, query) - 0.3 * Sim(doc, top1)
                ROUND(0.7 * c.query_sim - 0.3 * array_cosine_similarity(c.vec, top1.vec), 4) AS mmr_score
            FROM ranked_candidates c
            CROSS JOIN (SELECT vec FROM ranked_candidates ORDER BY query_sim DESC LIMIT 1) top1
            ORDER BY mmr_score DESC;
