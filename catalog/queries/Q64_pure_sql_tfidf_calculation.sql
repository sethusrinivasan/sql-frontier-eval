/*
 ==============================================================================
 Query ID:         Q64_pure_sql_tfidf_calculation
 Title:            TF-IDF (Term Frequency - Inverse Document Frequency) in Pure SQL
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 TF-IDF is the foundational algorithm of information retrieval. Calculating it directly in SQL provides deep insight into term uniqueness across a corpus without requiring Python.

 The Hidden Trap:
 Calculating document frequency across millions of documents requires careful window partitioning to avoid Cartesian explosions.

 The DuckDB Advantage:
 DuckDB window functions compute corpus document counts (N) and term frequencies in parallel.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE doc_words (
                doc_id INT,
                term VARCHAR,
                term_count INT
            );
            INSERT INTO doc_words VALUES
                (1, 'database', 10), (1, 'columnar', 5),
                (2, 'database', 8),  (2, 'relational', 7),
                (3, 'columnar', 4);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate TF-IDF for term 'columnar' across 3 documents
            -- TF = term_count / total_terms_in_doc, IDF = LN(Total_Docs / Docs_With_Term)
            WITH doc_lengths AS (
                SELECT doc_id, SUM(term_count) AS doc_len
                FROM doc_words
                GROUP BY doc_id
            ),
            corpus_stats AS (
                SELECT COUNT(DISTINCT doc_id) AS total_docs FROM doc_words
            ),
            term_docs AS (
                SELECT term, COUNT(DISTINCT doc_id) AS docs_with_term
                FROM doc_words
                GROUP BY term
            )
            SELECT 
                w.doc_id,
                w.term,
                w.term_count,
                ROUND(w.term_count * 1.0 / l.doc_len, 4) AS tf,
                ROUND(LN(c.total_docs * 1.0 / td.docs_with_term), 4) AS idf,
                ROUND((w.term_count * 1.0 / l.doc_len) * LN(c.total_docs * 1.0 / td.docs_with_term), 4) AS tfidf_score
            FROM doc_words w
            JOIN doc_lengths l ON w.doc_id = l.doc_id
            JOIN term_docs td ON w.term = td.term
            CROSS JOIN corpus_stats c
            WHERE w.term = 'columnar'
            ORDER BY tfidf_score DESC;
