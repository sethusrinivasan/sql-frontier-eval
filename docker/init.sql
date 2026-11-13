-- ==============================================================================
-- SQL FRONTIER EVAL: POSTGRESQL EXTENSIONS & COMPATIBILITY LAYER
-- ==============================================================================

-- 1. Enable Key Frontier Extensions
CREATE EXTENSION IF NOT EXISTS vector;          -- pgvector: Vector similarity & HNSW indexing
CREATE EXTENSION IF NOT EXISTS pg_trgm;         -- Trigram indexing & fuzzy string similarity
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;    -- Levenshtein, Soundex, Metaphone
CREATE EXTENSION IF NOT EXISTS tablefunc;       -- Crosstab, connectby
CREATE EXTENSION IF NOT EXISTS btree_gist;      -- GiST indexes for temporal range & exclusion
CREATE EXTENSION IF NOT EXISTS ltree;           -- Hierarchical tree labels
CREATE EXTENSION IF NOT EXISTS hstore;          -- Key-value document storage
CREATE EXTENSION IF NOT EXISTS intarray;        -- Integer array operations
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";     -- UUID generation

-- 2. DuckDB / ANSI Data Type Compatibility
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'double') THEN
        CREATE DOMAIN "double" AS double precision;
    END IF;
END $$;

-- 3. Vector Similarity Functions
CREATE OR REPLACE FUNCTION array_cosine_similarity(a anycompatiblearray, b anycompatiblearray)
RETURNS double precision AS $$
DECLARE
    vec_a vector;
    vec_b vector;
BEGIN
    vec_a := replace(replace(a::text, '{', '['), '}', ']')::vector;
    vec_b := replace(replace(b::text, '{', '['), '}', ']')::vector;
    RETURN (1.0 - (vec_a <=> vec_b))::double precision;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION array_cosine_similarity(a vector, b vector)
RETURNS double precision AS $$
    SELECT (1.0 - (a <=> b))::double precision;
$$ LANGUAGE sql IMMUTABLE;

-- Array / Vector Euclidean Distance (<->)
CREATE OR REPLACE FUNCTION array_distance(a anycompatiblearray, b anycompatiblearray)
RETURNS double precision AS $$
DECLARE
    vec_a vector;
    vec_b vector;
BEGIN
    vec_a := replace(replace(a::text, '{', '['), '}', ']')::vector;
    vec_b := replace(replace(b::text, '{', '['), '}', ']')::vector;
    RETURN (vec_a <-> vec_b)::double precision;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION array_distance(a vector, b vector)
RETURNS double precision AS $$
    SELECT (a <-> b)::double precision;
$$ LANGUAGE sql IMMUTABLE;

-- 4. Date and Temporal Differences: date_diff(unit, start, end)
CREATE OR REPLACE FUNCTION date_diff(unit text, start_ts timestamp, end_ts timestamp)
RETURNS double precision AS $$
DECLARE
    diff_interval interval;
BEGIN
    diff_interval := end_ts - start_ts;
    CASE lower(unit)
        WHEN 'second', 'seconds' THEN
            RETURN EXTRACT(EPOCH FROM diff_interval);
        WHEN 'minute', 'minutes' THEN
            RETURN EXTRACT(EPOCH FROM diff_interval) / 60.0;
        WHEN 'hour', 'hours' THEN
            RETURN EXTRACT(EPOCH FROM diff_interval) / 3600.0;
        WHEN 'day', 'days' THEN
            RETURN EXTRACT(EPOCH FROM diff_interval) / 86400.0;
        WHEN 'week', 'weeks' THEN
            RETURN EXTRACT(EPOCH FROM diff_interval) / (86400.0 * 7.0);
        WHEN 'month', 'months' THEN
            RETURN (EXTRACT(YEAR FROM end_ts) - EXTRACT(YEAR FROM start_ts)) * 12.0 +
                   (EXTRACT(MONTH FROM end_ts) - EXTRACT(MONTH FROM start_ts));
        WHEN 'year', 'years' THEN
            RETURN EXTRACT(YEAR FROM end_ts) - EXTRACT(YEAR FROM start_ts);
        ELSE
            RETURN EXTRACT(EPOCH FROM diff_interval) / 86400.0;
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION date_diff(unit text, start_d date, end_d date)
RETURNS double precision AS $$
    SELECT date_diff(unit, start_d::timestamp, end_d::timestamp);
$$ LANGUAGE sql IMMUTABLE;

-- 5. Fuzzy String Similarity (Jaro-Winkler)
CREATE OR REPLACE FUNCTION jaro_winkler_similarity(s1 text, s2 text)
RETURNS double precision AS $$
BEGIN
    -- Use pg_trgm similarity or Levenshtein normalized similarity
    IF s1 = s2 THEN RETURN 1.0; END IF;
    IF s1 IS NULL OR s2 IS NULL THEN RETURN NULL; END IF;
    RETURN similarity(s1, s2)::double precision;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 6. Median & Quantile Aggregates
CREATE OR REPLACE FUNCTION _final_median(numeric[])
RETURNS numeric AS $$
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY x)
    FROM unnest($1) AS x;
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION _final_median_double(double precision[])
RETURNS double precision AS $$
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY x)
    FROM unnest($1) AS x;
$$ LANGUAGE sql IMMUTABLE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'median' AND prokind = 'a') THEN
        CREATE AGGREGATE median(numeric) (
            SFUNC = array_append,
            STYPE = numeric[],
            FINALFUNC = _final_median,
            INITCOND = '{}'
        );
        CREATE AGGREGATE median(double precision) (
            SFUNC = array_append,
            STYPE = double precision[],
            FINALFUNC = _final_median_double,
            INITCOND = '{}'
        );
    END IF;
END $$;

-- 7. Mathematical & Analytical Helpers
CREATE OR REPLACE FUNCTION round(val double precision, places integer)
RETURNS double precision AS $$
    SELECT round(val::numeric, places)::double precision;
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION array_inner_product(a anyarray, b anyarray)
RETURNS double precision AS $$
BEGIN
    RETURN ((a::text::vector <#> b::text::vector) * -1.0)::double precision;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION array_inner_product(a vector, b vector)
RETURNS double precision AS $$
    SELECT ((a <#> b) * -1.0)::double precision;
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE AGGREGATE list(anycompatible) (
    SFUNC = array_append,
    STYPE = anycompatiblearray,
    INITCOND = '{}'
);

CREATE OR REPLACE FUNCTION string_split(s text, delim text)
RETURNS text[] AS $$
    SELECT string_to_array(s, delim);
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION log2(x numeric)
RETURNS double precision AS $$
    SELECT (log(2.0, x))::double precision;
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION log2(x double precision)
RETURNS double precision AS $$
    SELECT (log(2.0, x::numeric))::double precision;
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION instr(str text, sub text)
RETURNS integer AS $$
    SELECT strpos(str, sub);
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION range(n integer)
RETURNS SETOF integer AS $$
    SELECT generate_series(0, n - 1);
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION range(start_n integer, stop_n integer)
RETURNS SETOF integer AS $$
    SELECT generate_series(start_n, stop_n - 1);
$$ LANGUAGE sql IMMUTABLE;
