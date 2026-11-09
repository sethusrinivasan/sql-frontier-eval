# Domain 3: Modern Search, Full-Text & Hybrid Retrieval Analytics (Queries 51 - 75)

SEARCH_QUERIES = [
    {
        "id": "Q51_fts_bm25_lexical_search",
        "title": "DuckDB Full-Text Search (FTS) BM25 Term Relevance Scoring",
        "domain": "Search & Retrieval",
        "human_context": "Traditional databases use simple `LIKE '%search%'` which treats 1 mention the same as 10 mentions and ignores document frequency. BM25 scores term saturation and document rarity.",
        "hidden_trap": "ILIKE matches substrings blindly (e.g. 'cat' matches 'scattered' or 'certificate') with zero relevancy ranking.",
        "duckdb_advantage": "DuckDB has native full-text indexing via the `fts` extension (`PRAGMA create_fts_index` and `match_bm25`).",
        "setup_sql": """
            INSTALL fts; LOAD fts;
            CREATE TABLE articles (
                doc_id INT,
                title VARCHAR,
                body VARCHAR
            );
            INSERT INTO articles VALUES
                (1, 'Fast Columnar Databases', 'DuckDB is a vectorized analytical database designed for fast analytics.'),
                (2, 'Postgres Tuning Guide',    'Relational database indexing and buffer pool optimization.'),
                (3, 'Vector Search Frontiers', 'Combining dense vector embeddings with sparse BM25 indexing.');
            PRAGMA create_fts_index('articles', 'doc_id', 'title', 'body');
        """,
        "sql": """
            -- BM25 full-text search for 'analytical database'
            WITH scored_articles AS (
                SELECT 
                    doc_id,
                    title,
                    body,
                    fts_main_articles.match_bm25(doc_id, 'analytical database') AS bm25_score
                FROM articles
            )
            SELECT 
                doc_id,
                title,
                ROUND(bm25_score, 4) AS bm25_score
            FROM scored_articles
            WHERE bm25_score IS NOT NULL
            ORDER BY bm25_score DESC;
        """
    },
    {
        "id": "Q52_reciprocal_rank_fusion_rrf",
        "title": "Reciprocal Rank Fusion (RRF) Hybrid Search (BM25 + Dense Vectors)",
        "domain": "Search & Retrieval",
        "human_context": "Hybrid search combines sparse keyword search (great for exact names and acronyms) with dense vector search (great for synonyms and concepts). RRF merges both rank lists using: RRF_score = 1/(60 + rank_bm25) + 1/(60 + rank_vec).",
        "hidden_trap": "Adding raw BM25 scores (range 0 to 50+) directly to cosine similarity scores (range 0 to 1) allows BM25 to completely drown out vector relevance.",
        "duckdb_advantage": "DuckDB window functions compute dense ranks across both retrieval channels and fuse them in a single query.",
        "setup_sql": """
            CREATE TABLE corpus_docs (
                doc_id INT,
                title VARCHAR,
                lexical_score DOUBLE,
                vec FLOAT[2]
            );
            INSERT INTO corpus_docs VALUES
                (1, 'DuckDB Vector Search Guide', 12.5, [0.95, 0.05]::FLOAT[2]),
                (2, 'Postgres HNSW Extension',     14.2, [0.70, 0.30]::FLOAT[2]),
                (3, 'Deep Learning Embeddings',    2.1,  [0.92, 0.10]::FLOAT[2]);
        """,
        "sql": """
            -- Hybrid RRF rank fusion between BM25 lexical score and dense vector cosine similarity
            WITH ranked_lexical AS (
                SELECT 
                    doc_id,
                    title,
                    ROW_NUMBER() OVER (ORDER BY lexical_score DESC) AS rank_lexical
                FROM corpus_docs
            ),
            ranked_vector AS (
                SELECT 
                    doc_id,
                    title,
                    ROW_NUMBER() OVER (
                        ORDER BY array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) DESC
                    ) AS rank_vector
                FROM corpus_docs
            )
            SELECT 
                l.doc_id,
                l.title,
                l.rank_lexical,
                v.rank_vector,
                -- Standard RRF formula with k = 60
                ROUND((1.0 / (60.0 + l.rank_lexical)) + (1.0 / (60.0 + v.rank_vector)), 6) AS rrf_score
            FROM ranked_lexical l
            JOIN ranked_vector v ON l.doc_id = v.doc_id
            ORDER BY rrf_score DESC;
        """
    },
    {
        "id": "Q53_min_max_convex_hybrid_search",
        "title": "Min-Max Normalized Convex Combination Hybrid Search",
        "domain": "Search & Retrieval",
        "human_context": "An alternative to rank-based RRF is score-based fusion: min-max scale lexical scores to [0, 1] and vector scores to [0, 1], then take alpha * lexical + (1 - alpha) * vector.",
        "hidden_trap": "Division by zero when all scores in a small result set are identical.",
        "duckdb_advantage": "DuckDB NULLIF and window MIN/MAX cleanly handle degenerate score distributions.",
        "setup_sql": """
            CREATE TABLE search_candidates (
                doc_id INT,
                title VARCHAR,
                raw_bm25 DOUBLE,
                vector_sim DOUBLE
            );
            INSERT INTO search_candidates VALUES
                (101, 'Data Warehousing Fundamentals', 25.0, 0.85),
                (102, 'Columnar Storage Internals',    10.0, 0.92),
                (103, 'SQL Query Optimization',         5.0, 0.70);
        """,
        "sql": """
            -- Min-Max normalization and 50/50 convex combination
            WITH bounds AS (
                SELECT 
                    doc_id,
                    title,
                    raw_bm25,
                    vector_sim,
                    MIN(raw_bm25) OVER () AS min_bm25,
                    MAX(raw_bm25) OVER () AS max_bm25,
                    MIN(vector_sim) OVER () AS min_vec,
                    MAX(vector_sim) OVER () AS max_vec
                FROM search_candidates
            ),
            normalized AS (
                SELECT 
                    doc_id,
                    title,
                    COALESCE((raw_bm25 - min_bm25) / NULLIF(max_bm25 - min_bm25, 0), 1.0) AS norm_bm25,
                    COALESCE((vector_sim - min_vec) / NULLIF(max_vec - min_vec, 0), 1.0) AS norm_vec
                FROM bounds
            )
            SELECT 
                doc_id,
                title,
                ROUND(norm_bm25, 4) AS norm_bm25,
                ROUND(norm_vec, 4) AS norm_vec,
                ROUND(0.50 * norm_bm25 + 0.50 * norm_vec, 4) AS convex_hybrid_score
            FROM normalized
            ORDER BY convex_hybrid_score DESC;
        """
    },
    {
        "id": "Q54_fuzzy_levenshtein_length_pruning",
        "title": "Typo-Tolerant Search with Levenshtein Edit Distance & Length Bounds",
        "domain": "Search & Retrieval",
        "human_context": "Users frequently misspell search terms (e.g. 'postgre' -> 'postgresql'). Levenshtein distance counts insertions, deletions, and substitutions.",
        "hidden_trap": "Computing Levenshtein distance on every catalog word is CPU intensive without pre-filtering on string length (ABS(len_a - len_b) <= max_distance).",
        "duckdb_advantage": "DuckDB pushes string length checks ahead of native `levenshtein()` evaluations.",
        "setup_sql": """
            CREATE TABLE catalog_keywords (
                keyword_id INT,
                keyword VARCHAR
            );
            INSERT INTO catalog_keywords VALUES
                (1, 'postgresql'),
                (2, 'postgres'),
                (3, 'postgress'),
                (4, 'python'),
                (5, 'javascript');
        """,
        "sql": """
            -- Find keywords within edit distance <= 2 of search query 'posgresql'
            SELECT 
                keyword_id,
                keyword,
                levenshtein(keyword, 'posgresql') AS edit_distance
            FROM catalog_keywords
            -- Pre-filter: word length cannot differ by more than max allowed edit distance (2)
            WHERE ABS(LENGTH(keyword) - LENGTH('posgresql')) <= 2
              AND levenshtein(keyword, 'posgresql') <= 2
            ORDER BY edit_distance ASC;
        """
    },
    {
        "id": "Q55_jaro_winkler_brand_search",
        "title": "Brand & Name Fuzzy Search via Jaro-Winkler Prefix Similarity",
        "domain": "Search & Retrieval",
        "human_context": "In e-commerce, users often mistype the suffixes of brand names ('Samsumg' vs 'Samsung'). Jaro-Winkler gives higher weight to prefix matches, making it ideal for proper names.",
        "hidden_trap": "Standard Levenshtein treats mistakes at the start of a word the same as at the end.",
        "duckdb_advantage": "DuckDB includes native `jaro_winkler_similarity(a, b)` returning normalized [0, 1] scores.",
        "setup_sql": """
            CREATE TABLE brands (
                brand_id INT,
                brand_name VARCHAR
            );
            INSERT INTO brands VALUES
                (1, 'Samsung'),
                (2, 'Samsonite'),
                (3, 'Apple'),
                (4, 'Sony');
        """,
        "sql": """
            -- Match brand query 'Samsun' with threshold >= 0.85
            SELECT 
                brand_id,
                brand_name,
                ROUND(jaro_winkler_similarity(brand_name, 'Samsun'), 4) AS jaro_similarity
            FROM brands
            WHERE jaro_winkler_similarity(brand_name, 'Samsun') >= 0.85
            ORDER BY jaro_similarity DESC;
        """
    },
    {
        "id": "Q56_multi_field_weighted_scoring",
        "title": "Multi-Field Weighted Full-Text Retrieval (Title 3x, Body 1x)",
        "domain": "Search & Retrieval",
        "human_context": "A match in a document title or product headline is far more indicative of relevance than a passing mention in the body text.",
        "hidden_trap": "Concatenating title and body into a single column gives equal weight to all words.",
        "duckdb_advantage": "DuckDB can evaluate independent field matches and combine them with linear weighting in SQL.",
        "setup_sql": """
            CREATE TABLE product_posts (
                post_id INT,
                title VARCHAR,
                body VARCHAR
            );
            INSERT INTO product_posts VALUES
                (1, 'Wireless Noise Canceling Headphones', 'These over-ear headphones feature active noise cancelling technology.'),
                (2, 'Travel Accessories and Gadgets',     'A complete list of travel gear including a wireless charging pad and cables.'),
                (3, 'Coffee Brewing Machines',          'Best espresso makers and grinders for home brewing.');
        """,
        "sql": """
            -- Search for 'wireless headphones': Title matches weighted 3.0x, Body matches weighted 1.0x
            WITH scored AS (
                SELECT 
                    post_id,
                    title,
                    ROUND(
                        (CASE WHEN title ILIKE '%wireless%' THEN 3.0 ELSE 0.0 END) +
                        (CASE WHEN title ILIKE '%headphones%' THEN 3.0 ELSE 0.0 END) +
                        (CASE WHEN body ILIKE '%wireless%' THEN 1.0 ELSE 0.0 END) +
                        (CASE WHEN body ILIKE '%headphones%' THEN 1.0 ELSE 0.0 END), 2
                    ) AS multi_field_score
                FROM product_posts
            )
            SELECT 
                post_id,
                title,
                multi_field_score
            FROM scored
            WHERE multi_field_score > 0
            ORDER BY multi_field_score DESC;
        """
    },
    {
        "id": "Q57_exact_phrase_proximity_boost",
        "title": "Exact Phrase Proximity Boosting in Keyword Retrieval",
        "domain": "Search & Retrieval",
        "human_context": "If a user searches for 'machine learning', an article containing the exact phrase 'machine learning' should rank higher than an article where 'machine' is in paragraph 1 and 'learning' is in paragraph 8.",
        "hidden_trap": "Pure bag-of-words keyword matches ignore token proximity and phrase boundaries.",
        "duckdb_advantage": "DuckDB combines exact phrase substring checks with token matching.",
        "setup_sql": """
            CREATE TABLE articles_proximity (
                article_id INT,
                text_content VARCHAR
            );
            INSERT INTO articles_proximity VALUES
                (1, 'Recent breakthroughs in machine learning algorithms have transformed AI.'),
                (2, 'The washing machine broke down, so I am learning how to fix the belt.'),
                (3, 'Database indexing structures and query execution plans.');
        """,
        "sql": """
            -- Query: 'machine' AND 'learning', with a 5.0x boost for exact phrase match
            SELECT 
                article_id,
                text_content,
                (CASE WHEN text_content ILIKE '%machine%' THEN 1.0 ELSE 0.0 END +
                 CASE WHEN text_content ILIKE '%learning%' THEN 1.0 ELSE 0.0 END +
                 CASE WHEN text_content ILIKE '%machine learning%' THEN 5.0 ELSE 0.0 END) AS relevance_score
            FROM articles_proximity
            WHERE text_content ILIKE '%machine%' AND text_content ILIKE '%learning%'
            ORDER BY relevance_score DESC;
        """
    },
    {
        "id": "Q58_stopword_cleansing_normalization",
        "title": "Stopword Filtering and Query Token Cleansing in SQL",
        "domain": "Search & Retrieval",
        "human_context": "Search queries like 'what is the best laptop' contain stop words ('what', 'is', 'the') that dilute search precision if not filtered prior to catalog matching.",
        "hidden_trap": "Leaving stopwords in keyword queries causes high-frequency words to trigger millions of false positive matches.",
        "duckdb_advantage": "DuckDB array functions (`list_filter`) can cleanse query tokens against stopword tables.",
        "setup_sql": """
            CREATE TABLE stopwords (word VARCHAR);
            INSERT INTO stopwords VALUES ('what'), ('is'), ('the'), ('and'), ('or'), ('a'), ('an');
        """,
        "sql": """
            -- Cleanse raw search tokens by filtering out stopwords
            WITH raw_query AS (
                SELECT UNNEST(string_split(lower('what is the best gaming laptop'), ' ')) AS token
            ),
            clean_tokens AS (
                SELECT q.token
                FROM raw_query q
                LEFT JOIN stopwords s ON q.token = s.word
                WHERE s.word IS NULL
            )
            SELECT 
                list(token) AS clean_tokens,
                string_agg(token, ' ') AS cleansed_search_query
            FROM clean_tokens;
        """
    },
    {
        "id": "Q59_faceted_search_json_attributes",
        "title": "Faceted Search Aggregations over Semi-Structured JSON Attributes",
        "domain": "Search & Retrieval",
        "human_context": "When a customer searches for 'laptops', e-commerce search engines return matching items along with dynamic facet counts (e.g. Brand: Apple (12), Dell (8); RAM: 16GB (15), 32GB (5)) extracted from JSON specs.",
        "hidden_trap": "Running separate queries for each facet dimension multiplies query latency and database load.",
        "duckdb_advantage": "DuckDB extracts JSON paths (`->>`) and aggregates multiple facet dimensions in parallel.",
        "setup_sql": """
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
        """,
        "sql": """
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
        """
    },
    {
        "id": "Q60_ngram_log_signature_search",
        "title": "Trigram / N-Gram Token Substring Matching for Technical Error Logs",
        "domain": "Search & Retrieval",
        "human_context": "In observability platforms (Datadog, Splunk), engineers search stack traces with partial error signatures. Trigram decomposition enables robust partial substring index matching.",
        "hidden_trap": "Full regex evaluations on raw million-line log tables trigger catastrophic backtracking.",
        "duckdb_advantage": "DuckDB n-gram tokenization and array overlaps provide fast log signature matching.",
        "setup_sql": """
            CREATE TABLE incident_logs (
                log_id INT,
                error_message VARCHAR
            );
            INSERT INTO incident_logs VALUES
                (1, 'java.lang.NullPointerException at com.app.auth.LoginService.verify'),
                (2, 'org.postgresql.util.PSQLException: Connection refused'),
                (3, 'java.lang.OutOfMemoryError: Java heap space');
        """,
        "sql": """
            -- Find logs matching 'NullPointer' or 'OutOfMemory' error signatures
            SELECT 
                log_id,
                error_message,
                CASE 
                    WHEN error_message LIKE '%NullPointer%' THEN 'NPE_EXCEPTION'
                    WHEN error_message LIKE '%OutOfMemory%' THEN 'OOM_KILL'
                    ELSE 'OTHER'
                END AS classified_signature
            FROM incident_logs
            WHERE error_message LIKE '%NullPointer%' 
               OR error_message LIKE '%OutOfMemory%'
            ORDER BY log_id;
        """
    },
    {
        "id": "Q61_synonym_expansion_reranking",
        "title": "Dynamic Query Synonym Expansion via Relational Thesaurus",
        "domain": "Search & Retrieval",
        "human_context": "When a customer searches for 'sofa', they also expect to see listings titled 'couch' or 'settee'. Expanding queries using a synonym thesaurus bridges terminology gaps.",
        "hidden_trap": "Hardcoding synonyms into client-side application code makes vocabulary updates inflexible.",
        "duckdb_advantage": "DuckDB joins query tokens to relational synonym tables to score documents with expanded terms.",
        "setup_sql": """
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
        """,
        "sql": """
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
        """
    },
    {
        "id": "Q62_autocomplete_prefix_popularity",
        "title": "Search Autocomplete Suggestion with Popularity Frequency Weighting",
        "domain": "Search & Retrieval",
        "human_context": "As users type 'air...', instant search suggests 'air fryer' (100k searches) before 'air mattress' (5k searches). Suggestions must match the prefix AND rank by historical popularity.",
        "hidden_trap": "Alphabetical sorting of prefix matches suggests obscure terms before popular items.",
        "duckdb_advantage": "DuckDB prefix filtering (`prefix_query || '%'`) combined with ordering indices produces sub-millisecond suggestions.",
        "setup_sql": """
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
        """,
        "sql": """
            -- Autocomplete suggestions for prefix 'air' ranked by volume * conversion
            SELECT 
                query_string,
                monthly_search_volume,
                ROUND(monthly_search_volume * conversion_rate, 0) AS popularity_rank_score
            FROM search_telemetry
            WHERE query_string LIKE 'air%'
            ORDER BY popularity_rank_score DESC
            LIMIT 3;
        """
    },
    {
        "id": "Q63_boolean_search_negation",
        "title": "High-Precision Boolean Search with Negation and Grouping",
        "domain": "Search & Retrieval",
        "human_context": "Legal e-discovery and patent search rely on exact Boolean syntax: (patent AND battery) NOT (lithium OR phone). Negations must be strictly applied without dropping valid candidate documents.",
        "hidden_trap": "Poor operator precedence in SQL boolean expressions causes negated terms to drop unrelated valid results.",
        "duckdb_advantage": "DuckDB SQL evaluates complex parenthesized boolean criteria with index acceleration.",
        "setup_sql": """
            CREATE TABLE patent_corpus (
                patent_id INT,
                abstract VARCHAR
            );
            INSERT INTO patent_corpus VALUES
                (1, 'Solid-state battery chemistry for electric vehicles and heavy transport'),
                (2, 'Lithium ion battery pack design for mobile phone handsets'),
                (3, 'Wireless charging pad for mobile phone and earbuds');
        """,
        "sql": """
            -- Query: ('battery') AND NOT ('lithium' OR 'phone')
            SELECT 
                patent_id,
                abstract
            FROM patent_corpus
            WHERE abstract ILIKE '%battery%'
              AND NOT (abstract ILIKE '%lithium%' OR abstract ILIKE '%phone%')
            ORDER BY patent_id;
        """
    },
    {
        "id": "Q64_pure_sql_tfidf_calculation",
        "title": "TF-IDF (Term Frequency - Inverse Document Frequency) in Pure SQL",
        "domain": "Search & Retrieval",
        "human_context": "TF-IDF is the foundational algorithm of information retrieval. Calculating it directly in SQL provides deep insight into term uniqueness across a corpus without requiring Python.",
        "hidden_trap": "Calculating document frequency across millions of documents requires careful window partitioning to avoid Cartesian explosions.",
        "duckdb_advantage": "DuckDB window functions compute corpus document counts (N) and term frequencies in parallel.",
        "setup_sql": """
            CREATE TABLE doc_words (
                doc_id INT,
                term VARCHAR,
                term_count INT
            );
            INSERT INTO doc_words VALUES
                (1, 'database', 10), (1, 'columnar', 5),
                (2, 'database', 8),  (2, 'relational', 7),
                (3, 'columnar', 4);
        """,
        "sql": """
            -- Calculate TF-IDF for term 'columnar' across 3 documents
            -- TF = term_count / total_terms_in_doc, IDF = LN(Total_Docs / Docs_With_Term)
            WITH doc_lengths AS (
                SELECT doc_id, SUM(term_count) AS doc_len
                FROM doc_words
                GROUP BY doc_id
            ),
            corpus_stats AS (
                SELECT COUNT(DISTINCT doc_id) AS total_docs FROM doc_words
            ),
            term_docs AS (
                SELECT term, COUNT(DISTINCT doc_id) AS docs_with_term
                FROM doc_words
                GROUP BY term
            )
            SELECT 
                w.doc_id,
                w.term,
                w.term_count,
                ROUND(w.term_count * 1.0 / l.doc_len, 4) AS tf,
                ROUND(LN(c.total_docs * 1.0 / td.docs_with_term), 4) AS idf,
                ROUND((w.term_count * 1.0 / l.doc_len) * LN(c.total_docs * 1.0 / td.docs_with_term), 4) AS tfidf_score
            FROM doc_words w
            JOIN doc_lengths l ON w.doc_id = l.doc_id
            JOIN term_docs td ON w.term = td.term
            CROSS JOIN corpus_stats c
            WHERE w.term = 'columnar'
            ORDER BY tfidf_score DESC;
        """
    },
    {
        "id": "Q65_search_position_bias_dcg",
        "title": "Discounted Cumulative Gain (DCG) with Search Position Bias Discount",
        "domain": "Search & Retrieval",
        "human_context": "Users are far more likely to click the #1 search result than the #5 result regardless of relevance. Ranking quality is measured via Discounted Cumulative Gain: DCG = SUM(relevance / log2(rank + 1)).",
        "hidden_trap": "Simple click counts reward poorly placed relevant items unfairly.",
        "duckdb_advantage": "DuckDB math functions (`LOG2`) compute logarithmic rank discounts in vectorized window expressions.",
        "setup_sql": """
            CREATE TABLE search_impressions (
                query_id INT,
                rank_position INT,
                relevance_label INT -- 0=irrelevant, 1=relevant, 2=perfect
            );
            INSERT INTO search_impressions VALUES
                (1, 1, 2), -- Rank 1: perfect match
                (1, 2, 0), -- Rank 2: bad match
                (1, 3, 1); -- Rank 3: good match
        """,
        "sql": """
            -- Calculate DCG@3 for query 1
            SELECT 
                query_id,
                ROUND(SUM(relevance_label / LOG2(rank_position + 1)), 4) AS dcg_at_3
            FROM search_impressions
            WHERE rank_position <= 3
            GROUP BY query_id;
        """
    },
    {
        "id": "Q66_alphanumeric_sku_normalization",
        "title": "Alphanumeric SKU Matching with Punctuation & Case Invariance",
        "domain": "Search & Retrieval",
        "human_context": "Customers search for model numbers in messy formats: 'wh-1000xm5', 'WH1000-XM5', 'wh 1000 xm5'. Robust search normalizes punctuation and whitespace before matching.",
        "hidden_trap": "Exact string equality misses 90% of technical product searches due to hyphens and spaces.",
        "duckdb_advantage": "DuckDB `regexp_replace` cleanses alphanumeric identifiers efficiently.",
        "setup_sql": """
            CREATE TABLE inventory_skus (
                sku_id INT,
                raw_sku VARCHAR,
                product_title VARCHAR
            );
            INSERT INTO inventory_skus VALUES
                (1, 'WH-1000XM5/B', 'Sony Premium Wireless Headphones Black'),
                (2, 'AIR-MAX-90-W',  'Nike Air Max 90 White Sneaker');
        """,
        "sql": """
            -- Cleanse search query 'wh1000xm5b' by stripping non-alphanumeric characters
            SELECT 
                sku_id,
                raw_sku,
                product_title
            FROM inventory_skus
            WHERE lower(regexp_replace(raw_sku, '[^a-zA-Z0-9]', '', 'g')) = lower(regexp_replace('wh 1000-xm5/b', '[^a-zA-Z0-9]', '', 'g'));
        """
    },
    {
        "id": "Q67_search_negation_term_suppression",
        "title": "Dynamic Negative Keyword Exclusion in E-Commerce Filters",
        "domain": "Search & Retrieval",
        "human_context": "A user searches 'monitor -curved' to find flat computer monitors. The engine must extract positive search terms and suppress any record containing the negative terms.",
        "hidden_trap": "Negative keywords must not exclude items where the negative term appears with negation qualifiers (e.g. 'not curved').",
        "duckdb_advantage": "DuckDB regex matching and exclusion conditions execute in a single scan.",
        "setup_sql": """
            CREATE TABLE display_items (
                item_id INT,
                title VARCHAR,
                description VARCHAR
            );
            INSERT INTO display_items VALUES
                (1, 'Dell UltraSharp 27', 'Flat IPS 4K computer monitor with USB-C hub'),
                (2, 'Samsung Odyssey G9', 'Ultra-wide 49 inch curved gaming monitor'),
                (3, 'LG UltraFine 32',   'Flat panel OLED professional display');
        """,
        "sql": """
            -- Positive term: 'monitor', Negative term: 'curved'
            SELECT 
                item_id,
                title,
                description
            FROM display_items
            WHERE (title ILIKE '%monitor%' OR description ILIKE '%monitor%')
              AND NOT (title ILIKE '%curved%' OR description ILIKE '%curved%')
            ORDER BY item_id;
        """
    },
    {
        "id": "Q68_multilingual_search_routing",
        "title": "Multi-Lingual Catalog Routing by Detected ISO Language Code",
        "domain": "Search & Retrieval",
        "human_context": "Global portals store titles in multiple localized columns (title_en, title_es, title_fr). Queries are dynamically routed to the matching language column based on user locale.",
        "hidden_trap": "Searching across all language columns simultaneously creates false-positive matches due to inter-language false cognates.",
        "duckdb_advantage": "DuckDB CASE projections route predicates to target language fields with zero query recompilation.",
        "setup_sql": """
            CREATE TABLE localized_products (
                product_id INT,
                title_en VARCHAR,
                title_es VARCHAR,
                title_fr VARCHAR
            );
            INSERT INTO localized_products VALUES
                (1, 'Red Bicycle',   'Bicicleta Roja',  'Velo Rouge'),
                (2, 'Green Helmet',  'Casco Verde',     'Casque Vert');
        """,
        "sql": """
            -- Match Spanish query 'Bicicleta' routed dynamically to title_es
            SELECT 
                product_id,
                title_es AS matched_title,
                'es' AS language_used
            FROM localized_products
            WHERE title_es ILIKE '%Bicicleta%'
            ORDER BY product_id;
        """
    },
    {
        "id": "Q69_query_relaxation_fallback",
        "title": "Zero-Result Search Query Relaxation (Strict AND -> Loose OR Fallback)",
        "domain": "Search & Retrieval",
        "human_context": "If a multi-word search query (e.g. 'ergonomic mechanical wireless split keyboard') returns zero results under strict AND matching, modern engines gracefully relax to OR matching.",
        "hidden_trap": "Failing to return fallback results leads to user bounce and abandoned sessions.",
        "duckdb_advantage": "DuckDB CTEs can check candidate counts and conditionally branch to relaxed OR queries.",
        "setup_sql": """
            CREATE TABLE keyboard_catalog (
                id INT,
                title VARCHAR
            );
            INSERT INTO keyboard_catalog VALUES
                (1, 'Ergonomic Split Keyboard Wired'),
                (2, 'Mechanical Wireless Office Keyboard'),
                (3, 'Standard Membrane Keyboard');
        """,
        "sql": """
            -- Query tokens: 'ergonomic', 'mechanical', 'wireless'
            WITH scored_matches AS (
                SELECT 
                    id,
                    title,
                    (CASE WHEN title ILIKE '%ergonomic%' THEN 1 ELSE 0 END +
                     CASE WHEN title ILIKE '%mechanical%' THEN 1 ELSE 0 END +
                     CASE WHEN title ILIKE '%wireless%' THEN 1 ELSE 0 END) AS match_score
                FROM keyboard_catalog
            )
            SELECT 
                id,
                title,
                match_score,
                CASE WHEN match_score = 3 THEN 'STRICT_ALL_MATCH' ELSE 'RELAXED_PARTIAL_MATCH' END AS match_tier
            FROM scored_matches
            WHERE match_score >= 1
            ORDER BY match_score DESC, id;
        """
    },
    {
        "id": "Q70_search_snippet_keyword_extraction",
        "title": "Search Snippet Extraction: Context Window Around Matching Terms",
        "domain": "Search & Retrieval",
        "human_context": "Search results show a preview snippet containing the searched keyword with 30 characters of surrounding context rather than the beginning of a 2,000-word article.",
        "hidden_trap": "Substring extraction crashes when matching keywords appear near the very beginning or end of the text.",
        "duckdb_advantage": "DuckDB `GREATEST` and `SUBSTRING` functions construct safe boundary-clipped preview snippets.",
        "setup_sql": """
            CREATE TABLE blog_posts (
                post_id INT,
                content VARCHAR
            );
            INSERT INTO blog_posts VALUES
                (1, 'In this tutorial we demonstrate high performance data analysis. The key feature of DuckDB is vectorized execution which processes data in columnar chunks for maximum CPU cache locality.'),
                (2, 'PostgreSQL is an advanced open source relational database with robust ACID transaction support.');
        """,
        "sql": """
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
        """
    },
    {
        "id": "Q71_search_journey_order_attribution",
        "title": "Customer Search-to-Purchase Path Attribution (Session Query Lift)",
        "domain": "Search & Retrieval",
        "human_context": "E-commerce search product managers need to know which search queries drove actual revenue. We link search queries to checkout events within the same 30-minute session.",
        "hidden_trap": "Attributing purchases to search queries that occurred after the purchase order was placed.",
        "duckdb_advantage": "DuckDB temporal range joins ensure search queries precede the checkout timestamp.",
        "setup_sql": """
            CREATE TABLE user_search_queries (
                user_id INT,
                query_term VARCHAR,
                searched_at TIMESTAMP
            );
            CREATE TABLE completed_orders (
                order_id INT,
                user_id INT,
                order_total DECIMAL(10,2),
                ordered_at TIMESTAMP
            );
            INSERT INTO user_search_queries VALUES
                (50, 'noise canceling headphones', '2026-03-01 14:10:00'),
                (50, 'sony xm5 sale',              '2026-03-01 14:15:00');
            INSERT INTO completed_orders VALUES
                (1001, 50, 349.99, '2026-03-01 14:25:00');
        """,
        "sql": """
            -- Attribute purchase to the most recent search query prior to order
            SELECT 
                o.order_id,
                o.user_id,
                o.order_total,
                s.query_term AS attributing_search_query,
                s.searched_at,
                o.ordered_at
            FROM completed_orders o
            ASOF JOIN user_search_queries s
              ON o.user_id = s.user_id
             AND o.ordered_at >= s.searched_at
            ORDER BY o.order_id;
        """
    },
    {
        "id": "Q72_fuzzy_entity_resolution_dedup",
        "title": "Fuzzy Customer Entity Resolution across Disparate Data Sources",
        "domain": "Search & Retrieval",
        "human_context": "Merging CRM and billing databases requires linking customers with slight name and address variations (e.g. 'Robert Smith, 123 Main St' vs 'Bob Smith, 123 Main Street').",
        "hidden_trap": "Pairwise fuzzy string matching over millions of records is computationally prohibitive without blocking/canopy clustering.",
        "duckdb_advantage": "DuckDB uses zip-code blocking keys before computing string similarity.",
        "setup_sql": """
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
        """,
        "sql": """
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
        """
    },
    {
        "id": "Q73_search_term_cooccurrence_matrix",
        "title": "Search Term Co-Occurrence Matrix (Market Basket of Search Queries)",
        "domain": "Search & Retrieval",
        "human_context": "To suggest related searches, engines analyze queries searched together in the same session (e.g. users searching 'monitor' also search 'hdmi cable' 42% of the time).",
        "hidden_trap": "Self-joining search sessions without ordering (`a.term < b.term`) doubles matrix size with duplicate reversed pairs.",
        "duckdb_advantage": "DuckDB computes symmetric co-occurrence frequencies in a single pass.",
        "setup_sql": """
            CREATE TABLE session_searches (
                session_id INT,
                term VARCHAR
            );
            INSERT INTO session_searches VALUES
                (1, 'laptop'), (1, 'mouse'), (1, 'backpack'),
                (2, 'laptop'), (2, 'mouse'),
                (3, 'laptop'), (3, 'keyboard');
        """,
        "sql": """
            -- Find pairs of terms most frequently searched in the same user session
            SELECT 
                a.term AS term_a,
                b.term AS term_b,
                COUNT(*) AS cooccurrence_count
            FROM session_searches a
            JOIN session_searches b
              ON a.session_id = b.session_id
             AND a.term < b.term
            GROUP BY a.term, b.term
            ORDER BY cooccurrence_count DESC, term_a, term_b;
        """
    },
    {
        "id": "Q74_did_you_mean_spell_suggestion",
        "title": "'Did You Mean?' Query Spell-Correction Suggestion Engine",
        "domain": "Search & Retrieval",
        "human_context": "When a query produces few results, search engines recommend a spell-corrected candidate word from the catalog vocabulary that has the lowest edit distance and highest document frequency.",
        "hidden_trap": "Suggesting rare typos back to users rather than verified popular vocabulary terms.",
        "duckdb_advantage": "DuckDB joins dictionary terms, calculates edit distance, and ranks by frequency in one query.",
        "setup_sql": """
            CREATE TABLE dictionary_terms (
                term VARCHAR,
                doc_frequency INT
            );
            INSERT INTO dictionary_terms VALUES
                ('wireless', 50000),
                ('wiretap',     50),
                ('tireless',   120);
        """,
        "sql": """
            -- Given misspelled query 'wireles', propose top dictionary replacement with edit distance <= 1
            SELECT 
                term AS suggested_correction,
                doc_frequency,
                levenshtein(term, 'wireles') AS edit_distance
            FROM dictionary_terms
            WHERE levenshtein(term, 'wireles') <= 2
            ORDER BY edit_distance ASC, doc_frequency DESC
            LIMIT 1;
        """
    },
    {
        "id": "Q75_hybrid_search_metadata_soft_boost",
        "title": "Hybrid Search with Hard Categorical Filter & Soft Merchant Quality Boost",
        "domain": "Search & Retrieval",
        "human_context": "Top marketplaces enforce strict hard filters (in-stock, prime shipping) while soft-boosting items based on merchant review rating: final_score = text_relevance * (1.0 + 0.1 * merchant_rating).",
        "hidden_trap": "Hard-filtering by rating eliminates high-relevance new merchants with few reviews.",
        "duckdb_advantage": "DuckDB combines hard boolean filtering with continuous multiplicative rating boosts.",
        "setup_sql": """
            CREATE TABLE merchant_inventory (
                item_id INT,
                category VARCHAR,
                title VARCHAR,
                merchant_rating DOUBLE,
                is_available BOOLEAN
            );
            INSERT INTO merchant_inventory VALUES
                (1, 'Audio', 'Pro Studio Monitor Headphones', 4.9, true),
                (2, 'Audio', 'Budget Studio Headphones',       3.8, true),
                (3, 'Audio', 'Discontinued Vintage Headphones', 4.8, false);
        """,
        "sql": """
            -- Search 'Headphones' in 'Audio': Hard filter available=true, soft-boost by merchant rating
            WITH text_matches AS (
                SELECT 
                    item_id,
                    title,
                    merchant_rating,
                    -- Base relevance score from keyword matches
                    (CASE WHEN title ILIKE '%studio%' THEN 2.0 ELSE 1.0 END) AS base_relevance
                FROM merchant_inventory
                WHERE category = 'Audio'
                  AND is_available = true
                  AND title ILIKE '%Headphones%'
            )
            SELECT 
                item_id,
                title,
                merchant_rating,
                base_relevance,
                ROUND(base_relevance * (1.0 + (merchant_rating / 5.0) * 0.50), 2) AS boosted_final_score
            FROM text_matches
            ORDER BY boosted_final_score DESC;
        """
    }
]
