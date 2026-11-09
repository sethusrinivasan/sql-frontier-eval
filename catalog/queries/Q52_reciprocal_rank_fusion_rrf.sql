/*
 ==============================================================================
 Query ID:         Q52_reciprocal_rank_fusion_rrf
 Title:            Reciprocal Rank Fusion (RRF) Hybrid Search (BM25 + Dense Vectors)
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Hybrid search combines sparse keyword search (great for exact names and acronyms) with dense vector search (great for synonyms and concepts). RRF merges both rank lists using: RRF_score = 1/(60 + rank_bm25) + 1/(60 + rank_vec).

 The Hidden Trap:
 Adding raw BM25 scores (range 0 to 50+) directly to cosine similarity scores (range 0 to 1) allows BM25 to completely drown out vector relevance.

 The DuckDB Advantage:
 DuckDB window functions compute dense ranks across both retrieval channels and fuse them in a single query.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE corpus_docs (
                doc_id INT,
                title VARCHAR,
                lexical_score DOUBLE,
                vec FLOAT[2]
            );
            INSERT INTO corpus_docs VALUES
                (1, 'DuckDB Vector Search Guide', 12.5, [0.95, 0.05]::FLOAT[2]),
                (2, 'Postgres HNSW Extension',     14.2, [0.70, 0.30]::FLOAT[2]),
                (3, 'Deep Learning Embeddings',    2.1,  [0.92, 0.10]::FLOAT[2]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Hybrid RRF rank fusion between BM25 lexical score and dense vector cosine similarity
            WITH ranked_lexical AS (
                SELECT 
                    doc_id,
                    title,
                    ROW_NUMBER() OVER (ORDER BY lexical_score DESC) AS rank_lexical
                FROM corpus_docs
            ),
            ranked_vector AS (
                SELECT 
                    doc_id,
                    title,
                    ROW_NUMBER() OVER (
                        ORDER BY array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) DESC
                    ) AS rank_vector
                FROM corpus_docs
            )
            SELECT 
                l.doc_id,
                l.title,
                l.rank_lexical,
                v.rank_vector,
                -- Standard RRF formula with k = 60
                ROUND((1.0 / (60.0 + l.rank_lexical)) + (1.0 / (60.0 + v.rank_vector)), 6) AS rrf_score
            FROM ranked_lexical l
            JOIN ranked_vector v ON l.doc_id = v.doc_id
            ORDER BY rrf_score DESC;
