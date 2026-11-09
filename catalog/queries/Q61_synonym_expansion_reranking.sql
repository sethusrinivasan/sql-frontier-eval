/*
 ==============================================================================
 Query ID:         Q61_synonym_expansion_reranking
 Title:            Dynamic Query Synonym Expansion via Relational Thesaurus
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 When a customer searches for 'sofa', they also expect to see listings titled 'couch' or 'settee'. Expanding queries using a synonym thesaurus bridges terminology gaps.

 The Hidden Trap:
 Hardcoding synonyms into client-side application code makes vocabulary updates inflexible.

 The DuckDB Advantage:
 DuckDB joins query tokens to relational synonym tables to score documents with expanded terms.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE synonym_thesaurus (
                base_term VARCHAR,
                synonym VARCHAR
            );
            CREATE TABLE furniture_items (
                item_id INT,
                description VARCHAR
            );
            INSERT INTO synonym_thesaurus VALUES
                ('sofa', 'couch'),
                ('sofa', 'settee'),
                ('sofa', 'loveseat');
            INSERT INTO furniture_items VALUES
                (1, 'Modern Italian leather sofa with oak legs'),
                (2, 'Vintage velvet couch in emerald green'),
                (3, 'Solid wood dining table and 6 chairs');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Expand search term 'sofa' with all relational synonyms and match inventory
            WITH expanded_terms AS (
                SELECT 'sofa' AS search_term
                UNION
                SELECT synonym FROM synonym_thesaurus WHERE base_term = 'sofa'
            )
            SELECT 
                f.item_id,
                f.description,
                t.search_term AS matched_alias
            FROM furniture_items f
            JOIN expanded_terms t 
              ON f.description ILIKE ('%' || t.search_term || '%')
            ORDER BY f.item_id;
