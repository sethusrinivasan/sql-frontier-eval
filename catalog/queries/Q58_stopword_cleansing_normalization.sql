/*
 ==============================================================================
 Query ID:         Q58_stopword_cleansing_normalization
 Title:            Stopword Filtering and Query Token Cleansing in SQL
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Search queries like 'what is the best laptop' contain stop words ('what', 'is', 'the') that dilute search precision if not filtered prior to catalog matching.

 The Hidden Trap:
 Leaving stopwords in keyword queries causes high-frequency words to trigger millions of false positive matches.

 The DuckDB Advantage:
 DuckDB array functions (`list_filter`) can cleanse query tokens against stopword tables.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE stopwords (word VARCHAR);
            INSERT INTO stopwords VALUES ('what'), ('is'), ('the'), ('and'), ('or'), ('a'), ('an');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Cleanse raw search tokens by filtering out stopwords
            WITH raw_query AS (
                SELECT UNNEST(string_split(lower('what is the best gaming laptop'), ' ')) AS token
            ),
            clean_tokens AS (
                SELECT q.token
                FROM raw_query q
                LEFT JOIN stopwords s ON q.token = s.word
                WHERE s.word IS NULL
            )
            SELECT 
                list(token) AS clean_tokens,
                string_agg(token, ' ') AS cleansed_search_query
            FROM clean_tokens;
