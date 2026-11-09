/*
 ==============================================================================
 Query ID:         Q51_fts_bm25_lexical_search
 Title:            DuckDB Full-Text Search (FTS) BM25 Term Relevance Scoring
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Traditional databases use simple `LIKE '%search%'` which treats 1 mention the same as 10 mentions and ignores document frequency. BM25 scores term saturation and document rarity.

 The Hidden Trap:
 ILIKE matches substrings blindly (e.g. 'cat' matches 'scattered' or 'certificate') with zero relevancy ranking.

 The DuckDB Advantage:
 DuckDB has native full-text indexing via the `fts` extension (`PRAGMA create_fts_index` and `match_bm25`).
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
INSTALL fts; LOAD fts;
            CREATE TABLE articles (
                doc_id INT,
                title VARCHAR,
                body VARCHAR
            );
            INSERT INTO articles VALUES
                (1, 'Fast Columnar Databases', 'DuckDB is a vectorized analytical database designed for fast analytics.'),
                (2, 'Postgres Tuning Guide',    'Relational database indexing and buffer pool optimization.'),
                (3, 'Vector Search Frontiers', 'Combining dense vector embeddings with sparse BM25 indexing.');
            PRAGMA create_fts_index('articles', 'doc_id', 'title', 'body');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- BM25 full-text search for 'analytical database'
            WITH scored_articles AS (
                SELECT 
                    doc_id,
                    title,
                    body,
                    fts_main_articles.match_bm25(doc_id, 'analytical database') AS bm25_score
                FROM articles
            )
            SELECT 
                doc_id,
                title,
                ROUND(bm25_score, 4) AS bm25_score
            FROM scored_articles
            WHERE bm25_score IS NOT NULL
            ORDER BY bm25_score DESC;
