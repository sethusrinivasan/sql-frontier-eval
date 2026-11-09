/*
 ==============================================================================
 Query ID:         Q70_search_snippet_keyword_extraction
 Title:            Search Snippet Extraction: Context Window Around Matching Terms
 Domain:           Search & Retrieval
 ------------------------------------------------------------------------------
 Human Context:
 Search results show a preview snippet containing the searched keyword with 30 characters of surrounding context rather than the beginning of a 2,000-word article.

 The Hidden Trap:
 Substring extraction crashes when matching keywords appear near the very beginning or end of the text.

 The DuckDB Advantage:
 DuckDB `GREATEST` and `SUBSTRING` functions construct safe boundary-clipped preview snippets.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE blog_posts (
                post_id INT,
                content VARCHAR
            );
            INSERT INTO blog_posts VALUES
                (1, 'In this tutorial we demonstrate high performance data analysis. The key feature of DuckDB is vectorized execution which processes data in columnar chunks for maximum CPU cache locality.'),
                (2, 'PostgreSQL is an advanced open source relational database with robust ACID transaction support.');

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Extract 25-character window surrounding the word 'vectorized'
            SELECT 
                post_id,
                '...' || SUBSTRING(
                    content,
                    GREATEST(1, INSTR(lower(content), 'vectorized') - 15),
                    LENGTH('vectorized') + 30
                ) || '...' AS snippet_preview
            FROM blog_posts
            WHERE content ILIKE '%vectorized%';
