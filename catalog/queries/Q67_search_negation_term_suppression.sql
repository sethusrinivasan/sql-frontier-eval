/*
 ==============================================================================
 Query ID:         Q67_search_negation_term_suppression
 Title:            Dynamic Negative Keyword Exclusion in E-Commerce Filters
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 A user searches 'monitor -curved' to find flat computer monitors. The engine must extract positive search terms and suppress any record containing the negative terms.

 The Hidden Trap:
 Negative keywords must not exclude items where the negative term appears with negation qualifiers (e.g. 'not curved').

 The DuckDB Advantage:
 DuckDB regex matching and exclusion conditions execute in a single scan.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE display_items (
                item_id INT,
                title VARCHAR,
                description VARCHAR
            );
            INSERT INTO display_items VALUES
                (1, 'Dell UltraSharp 27', 'Flat IPS 4K computer monitor with USB-C hub'),
                (2, 'Samsung Odyssey G9', 'Ultra-wide 49 inch curved gaming monitor'),
                (3, 'LG UltraFine 32',   'Flat panel OLED professional display');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Positive term: 'monitor', Negative term: 'curved'
            SELECT 
                item_id,
                title,
                description
            FROM display_items
            WHERE (title ILIKE '%monitor%' OR description ILIKE '%monitor%')
              AND NOT (title ILIKE '%curved%' OR description ILIKE '%curved%')
            ORDER BY item_id;
