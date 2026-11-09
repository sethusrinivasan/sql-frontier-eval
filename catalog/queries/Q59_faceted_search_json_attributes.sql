/*
 ==============================================================================
 Query ID:         Q59_faceted_search_json_attributes
 Title:            Faceted Search Aggregations over Semi-Structured JSON Attributes
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 When a customer searches for 'laptops', e-commerce search engines return matching items along with dynamic facet counts (e.g. Brand: Apple (12), Dell (8); RAM: 16GB (15), 32GB (5)) extracted from JSON specs.

 The Hidden Trap:
 Running separate queries for each facet dimension multiplies query latency and database load.

 The DuckDB Advantage:
 DuckDB extracts JSON paths (`->>`) and aggregates multiple facet dimensions in parallel.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE electronics_catalog (
                item_id INT,
                title VARCHAR,
                specs JSON
            );
            INSERT INTO electronics_catalog VALUES
                (1, 'MacBook Pro 16', '{"brand": "Apple", "ram": "32GB", "screen": 16}'),
                (2, 'MacBook Air 13', '{"brand": "Apple", "ram": "16GB", "screen": 13}'),
                (3, 'XPS 15 Laptop',  '{"brand": "Dell",  "ram": "16GB", "screen": 15}'),
                (4, 'ThinkPad X1',    '{"brand": "Lenovo","ram": "16GB", "screen": 14}');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Extract faceted breakdown of matching laptop brands and RAM capacities
            WITH matching_items AS (
                SELECT 
                    item_id,
                    title,
                    specs->>'brand' AS brand,
                    specs->>'ram' AS ram
                FROM electronics_catalog
            )
            SELECT 
                'brand' AS facet_dimension,
                brand AS facet_value,
                COUNT(*) AS match_count
            FROM matching_items
            GROUP BY brand
            UNION ALL
            SELECT 
                'ram' AS facet_dimension,
                ram AS facet_value,
                COUNT(*) AS match_count
            FROM matching_items
            GROUP BY ram
            ORDER BY facet_dimension, match_count DESC, facet_value ASC;
