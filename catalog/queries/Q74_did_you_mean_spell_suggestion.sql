/*
 ==============================================================================
 Query ID:         Q74_did_you_mean_spell_suggestion
 Title:            'Did You Mean?' Query Spell-Correction Suggestion Engine
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 When a query produces few results, search engines recommend a spell-corrected candidate word from the catalog vocabulary that has the lowest edit distance and highest document frequency.

 The Hidden Trap:
 Suggesting rare typos back to users rather than verified popular vocabulary terms.

 The DuckDB Advantage:
 DuckDB joins dictionary terms, calculates edit distance, and ranks by frequency in one query.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE dictionary_terms (
                term VARCHAR,
                doc_frequency INT
            );
            INSERT INTO dictionary_terms VALUES
                ('wireless', 50000),
                ('wiretap',     50),
                ('tireless',   120);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Given misspelled query 'wireles', propose top dictionary replacement with edit distance <= 1
            SELECT 
                term AS suggested_correction,
                doc_frequency,
                levenshtein(term, 'wireles') AS edit_distance
            FROM dictionary_terms
            WHERE levenshtein(term, 'wireles') <= 2
            ORDER BY edit_distance ASC, doc_frequency DESC
            LIMIT 1;
