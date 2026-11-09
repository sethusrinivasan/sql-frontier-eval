/*
 ==============================================================================
 Query ID:         Q62_autocomplete_prefix_popularity
 Title:            Search Autocomplete Suggestion with Popularity Frequency Weighting
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 As users type 'air...', instant search suggests 'air fryer' (100k searches) before 'air mattress' (5k searches). Suggestions must match the prefix AND rank by historical popularity.

 The Hidden Trap:
 Alphabetical sorting of prefix matches suggests obscure terms before popular items.

 The DuckDB Advantage:
 DuckDB prefix filtering (`prefix_query || '%'`) combined with ordering indices produces sub-millisecond suggestions.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE search_telemetry (
                query_string VARCHAR,
                monthly_search_volume INT,
                conversion_rate DECIMAL(4,3)
            );
            INSERT INTO search_telemetry VALUES
                ('air fryer ninja', 120000, 0.085),
                ('airpods pro 2',    250000, 0.120),
                ('air mattress queen', 15000, 0.040),
                ('airplane pillow',     3000, 0.025);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Autocomplete suggestions for prefix 'air' ranked by volume * conversion
            SELECT 
                query_string,
                monthly_search_volume,
                ROUND(monthly_search_volume * conversion_rate, 0) AS popularity_rank_score
            FROM search_telemetry
            WHERE query_string LIKE 'air%'
            ORDER BY popularity_rank_score DESC
            LIMIT 3;
