/*
 ==============================================================================
 Query ID:         Q72_fuzzy_entity_resolution_dedup
 Title:            Fuzzy Customer Entity Resolution across Disparate Data Sources
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Merging CRM and billing databases requires linking customers with slight name and address variations (e.g. 'Robert Smith, 123 Main St' vs 'Bob Smith, 123 Main Street').

 The Hidden Trap:
 Pairwise fuzzy string matching over millions of records is computationally prohibitive without blocking/canopy clustering.

 The DuckDB Advantage:
 DuckDB uses zip-code blocking keys before computing string similarity.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE crm_records (
                crm_id INT,
                name VARCHAR,
                zip_code VARCHAR
            );
            CREATE TABLE billing_records (
                bill_id INT,
                name VARCHAR,
                zip_code VARCHAR
            );
            INSERT INTO crm_records VALUES
                (1, 'Robert Johnson', '94107'),
                (2, 'Sarah Williams', '10001');
            INSERT INTO billing_records VALUES
                (101, 'Bob Johnson',     '94107'),
                (102, 'Sara Williams',    '10001');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Entity resolution: Match records with identical zip code and Jaro-Winkler name similarity >= 0.80
            SELECT 
                c.crm_id,
                c.name AS crm_name,
                b.bill_id,
                b.name AS billing_name,
                c.zip_code,
                ROUND(jaro_winkler_similarity(c.name, b.name), 4) AS name_similarity
            FROM crm_records c
            JOIN billing_records b
              ON c.zip_code = b.zip_code
             AND jaro_winkler_similarity(c.name, b.name) >= 0.80
            ORDER BY name_similarity DESC;
