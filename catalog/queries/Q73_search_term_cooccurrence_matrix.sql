/*
 ==============================================================================
 Query ID:         Q73_search_term_cooccurrence_matrix
 Title:            Search Term Co-Occurrence Matrix (Market Basket of Search Queries)
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 To suggest related searches, engines analyze queries searched together in the same session (e.g. users searching 'monitor' also search 'hdmi cable' 42% of the time).

 The Hidden Trap:
 Self-joining search sessions without ordering (`a.term < b.term`) doubles matrix size with duplicate reversed pairs.

 The DuckDB Advantage:
 DuckDB computes symmetric co-occurrence frequencies in a single pass.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE session_searches (
                session_id INT,
                term VARCHAR
            );
            INSERT INTO session_searches VALUES
                (1, 'laptop'), (1, 'mouse'), (1, 'backpack'),
                (2, 'laptop'), (2, 'mouse'),
                (3, 'laptop'), (3, 'keyboard');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Find pairs of terms most frequently searched in the same user session
            SELECT 
                a.term AS term_a,
                b.term AS term_b,
                COUNT(*) AS cooccurrence_count
            FROM session_searches a
            JOIN session_searches b
              ON a.session_id = b.session_id
             AND a.term < b.term
            GROUP BY a.term, b.term
            ORDER BY cooccurrence_count DESC, term_a, term_b;
