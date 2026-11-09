/*
 ==============================================================================
 Query ID:         Q63_boolean_search_negation
 Title:            High-Precision Boolean Search with Negation and Grouping
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Legal e-discovery and patent search rely on exact Boolean syntax: (patent AND battery) NOT (lithium OR phone). Negations must be strictly applied without dropping valid candidate documents.

 The Hidden Trap:
 Poor operator precedence in SQL boolean expressions causes negated terms to drop unrelated valid results.

 The DuckDB Advantage:
 DuckDB SQL evaluates complex parenthesized boolean criteria with index acceleration.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE patent_corpus (
                patent_id INT,
                abstract VARCHAR
            );
            INSERT INTO patent_corpus VALUES
                (1, 'Solid-state battery chemistry for electric vehicles and heavy transport'),
                (2, 'Lithium ion battery pack design for mobile phone handsets'),
                (3, 'Wireless charging pad for mobile phone and earbuds');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Query: ('battery') AND NOT ('lithium' OR 'phone')
            SELECT 
                patent_id,
                abstract
            FROM patent_corpus
            WHERE abstract ILIKE '%battery%'
              AND NOT (abstract ILIKE '%lithium%' OR abstract ILIKE '%phone%')
            ORDER BY patent_id;
