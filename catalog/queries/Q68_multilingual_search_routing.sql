/*
 ==============================================================================
 Query ID:         Q68_multilingual_search_routing
 Title:            Multi-Lingual Catalog Routing by Detected ISO Language Code
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Global portals store titles in multiple localized columns (title_en, title_es, title_fr). Queries are dynamically routed to the matching language column based on user locale.

 The Hidden Trap:
 Searching across all language columns simultaneously creates false-positive matches due to inter-language false cognates.

 The DuckDB Advantage:
 DuckDB CASE projections route predicates to target language fields with zero query recompilation.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE localized_products (
                product_id INT,
                title_en VARCHAR,
                title_es VARCHAR,
                title_fr VARCHAR
            );
            INSERT INTO localized_products VALUES
                (1, 'Red Bicycle',   'Bicicleta Roja',  'Velo Rouge'),
                (2, 'Green Helmet',  'Casco Verde',     'Casque Vert');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Match Spanish query 'Bicicleta' routed dynamically to title_es
            SELECT 
                product_id,
                title_es AS matched_title,
                'es' AS language_used
            FROM localized_products
            WHERE title_es ILIKE '%Bicicleta%'
            ORDER BY product_id;
