# Domain 2: Vector Embeddings & Similarity Search Analytics (Queries 26 - 50)

VECTOR_QUERIES = [
    {
        "id": "Q26_cosine_similarity_top_k",
        "title": "Dense Vector Cosine Similarity Nearest Neighbors (Top-K ANN)",
        "domain": "Vector & Embeddings",
        "human_context": "When a user asks a question in an AI assistant, the query is embedded into a dense vector (e.g. 4-dimensional here for illustration, or 384/1536 in prod). We retrieve the top most semantically relevant documentation chunks.",
        "hidden_trap": "Models frequently try to calculate cosine similarity manually using dot product divided by norms in SQL, which is slow, verbose, and numerically unstable with zero vectors.",
        "duckdb_advantage": "DuckDB has high-performance native SIMD-accelerated `array_cosine_similarity(a, b)` over fixed-size arrays `FLOAT[N]`.",
        "setup_sql": """
            CREATE TABLE doc_embeddings (
                doc_id INT,
                title VARCHAR,
                embedding FLOAT[4]
            );
            INSERT INTO doc_embeddings VALUES
                (1, 'DuckDB Architecture Overview', [0.9, 0.1, 0.2, 0.0]::FLOAT[4]),
                (2, 'PostgreSQL Vacuum Internals',  [0.1, 0.8, 0.3, 0.1]::FLOAT[4]),
                (3, 'Vector Search & Embeddings',   [0.85, 0.15, 0.3, 0.05]::FLOAT[4]),
                (4, 'Kafka Event Streaming Guide',  [0.0, 0.2, 0.9, 0.4]::FLOAT[4]);
        """,
        "sql": """
            -- Find the top 2 documents closest to the query embedding [0.9, 0.1, 0.25, 0.0]
            WITH scored_docs AS (
                SELECT 
                    doc_id,
                    title,
                    embedding,
                    -- Native SIMD cosine similarity
                    array_cosine_similarity(embedding, [0.9, 0.1, 0.25, 0.0]::FLOAT[4]) AS cosine_score
                FROM doc_embeddings
            )
            SELECT 
                doc_id,
                title,
                ROUND(cosine_score, 4) AS similarity_score
            FROM scored_docs
            ORDER BY cosine_score DESC
            LIMIT 2;
        """
    },
    {
        "id": "Q27_euclidean_l2_nearest_neighbors",
        "title": "L2 Euclidean Distance Nearest Neighbors Search via array_distance",
        "domain": "Vector & Embeddings",
        "human_context": "In computer vision feature retrieval (facial recognition, product image matching), feature vectors are compared using Euclidean (L2) distance where lower distance equals higher visual similarity.",
        "hidden_trap": "LLMs often try to write SQRT(SUM(POW(a - b, 2))) which prevents vectorized hardware acceleration.",
        "duckdb_advantage": "DuckDB provides native `array_distance(a, b)` for Euclidean L2 metric calculation.",
        "setup_sql": """
            CREATE TABLE image_features (
                image_id INT,
                label VARCHAR,
                vector FLOAT[3]
            );
            INSERT INTO image_features VALUES
                (101, 'Red Running Shoe',  [1.0, 2.0, 3.0]::FLOAT[3]),
                (102, 'Crimson Sneaker',   [1.1, 2.1, 2.9]::FLOAT[3]),
                (103, 'Blue Hiking Boot',  [5.0, 8.0, 9.0]::FLOAT[3]);
        """,
        "sql": """
            -- Find visual nearest neighbors to query image vector [1.05, 2.05, 3.0]
            SELECT 
                image_id,
                label,
                ROUND(array_distance(vector, [1.05, 2.05, 3.0]::FLOAT[3]), 4) AS l2_distance
            FROM image_features
            ORDER BY l2_distance ASC
            LIMIT 2;
        """
    },
    {
        "id": "Q28_inner_product_mips",
        "title": "Maximum Inner Product Search (MIPS) for Normalized Embeddings",
        "domain": "Vector & Embeddings",
        "human_context": "For unit-normalized vectors (e.g. OpenAI text-embedding-3 or Cohere embeddings), cosine similarity is identical to the inner product (dot product), which executes even faster.",
        "hidden_trap": "Re-normalizing vectors in every query wastes compute when embeddings are pre-normalized upon insertion.",
        "duckdb_advantage": "DuckDB native `array_inner_product(a, b)` provides the fastest dot-product vector scoring path.",
        "setup_sql": """
            CREATE TABLE product_catalog_vectors (
                product_id INT,
                product_name VARCHAR,
                norm_vector FLOAT[3]
            );
            INSERT INTO product_catalog_vectors VALUES
                (1, 'Ultra Laptop', [0.8, 0.6, 0.0]::FLOAT[3]),
                (2, 'Smart Phone',  [0.6, 0.8, 0.0]::FLOAT[3]),
                (3, 'Coffee Maker', [0.0, 0.0, 1.0]::FLOAT[3]);
        """,
        "sql": """
            -- MIPS search for normalized user query vector [0.85, 0.52, 0.0]
            SELECT 
                product_id,
                product_name,
                ROUND(array_inner_product(norm_vector, [0.85, 0.52, 0.0]::FLOAT[3]), 4) AS dot_product_score
            FROM product_catalog_vectors
            ORDER BY dot_product_score DESC
            LIMIT 2;
        """
    },
    {
        "id": "Q29_pre_filter_vs_post_filter_trap",
        "title": "The Pre-Filtering Trap: Relational Predicates with Vector Top-K",
        "domain": "Vector & Embeddings",
        "human_context": "A user searches for 'cheap mechanical keyboard under $50'. If you run vector search Top-K first and filter by price afterwards (post-filtering), you may return zero products because all top-5 matches were $150 keyboards.",
        "hidden_trap": "Post-filtering vector results breaks recall. Relational constraints (in-stock, price bounds, user tenant_id) must be evaluated as PRE-FILTERS before Top-K ranking.",
        "duckdb_advantage": "DuckDB seamlessly pushes relational filters directly into the scan before computing expensive vector distances.",
        "setup_sql": """
            CREATE TABLE inventory_items (
                item_id INT,
                name VARCHAR,
                price DECIMAL(10,2),
                in_stock BOOLEAN,
                vector FLOAT[3]
            );
            INSERT INTO inventory_items VALUES
                (1, 'Custom Mechanical Keyboard', 180.00, true,  [0.9, 0.1, 0.1]::FLOAT[3]),
                (2, 'Budget Gaming Keyboard',       45.00, true,  [0.85, 0.15, 0.1]::FLOAT[3]),
                (3, 'Cheap Office Keyboard',        25.00, true,  [0.8, 0.2, 0.1]::FLOAT[3]),
                (4, 'Out of Stock Keyboard',        35.00, false, [0.92, 0.1, 0.1]::FLOAT[3]);
        """,
        "sql": """
            -- Pre-filtered vector search: strictly in-stock and under $50 BEFORE ranking top 2
            SELECT 
                item_id,
                name,
                price,
                ROUND(array_cosine_similarity(vector, [0.9, 0.1, 0.1]::FLOAT[3]), 4) AS similarity
            FROM inventory_items
            WHERE in_stock = true
              AND price <= 50.00
            ORDER BY similarity DESC
            LIMIT 2;
        """
    },
    {
        "id": "Q30_adaptive_similarity_threshold",
        "title": "Adaptive Similarity Thresholding with Fallback Top-K Guarantee",
        "domain": "Vector & Embeddings",
        "human_context": "RAG systems want high-confidence matches (similarity > 0.85) to avoid hallucinations, but if no document exceeds 0.85, they need a guaranteed top-1 fallback to provide at least some context.",
        "hidden_trap": "A hard WHERE similarity > 0.85 yields empty sets, while a raw LIMIT 5 includes irrelevant noise.",
        "duckdb_advantage": "DuckDB window functions and conditional filtering allow hybrid thresholding in a single query.",
        "setup_sql": """
            CREATE TABLE knowledge_base (
                kb_id INT,
                content VARCHAR,
                vector FLOAT[3]
            );
            INSERT INTO knowledge_base VALUES
                (1, 'DuckDB uses columnar storage', [0.4, 0.4, 0.1]::FLOAT[3]),
                (2, 'DuckDB vector execution engine', [0.5, 0.3, 0.2]::FLOAT[3]),
                (3, 'French cuisine recipes',        [0.0, 0.1, 0.9]::FLOAT[3]);
        """,
        "sql": """
            -- Score items, guarantee top 1 fallback even if below 0.85 threshold
            WITH scored AS (
                SELECT 
                    kb_id,
                    content,
                    array_cosine_similarity(vector, [0.9, 0.2, 0.1]::FLOAT[3]) AS sim_score,
                    ROW_NUMBER() OVER (ORDER BY array_cosine_similarity(vector, [0.9, 0.2, 0.1]::FLOAT[3]) DESC) AS rank_pos
                FROM knowledge_base
            )
            SELECT 
                kb_id,
                content,
                ROUND(sim_score, 4) AS sim_score,
                rank_pos,
                CASE WHEN sim_score >= 0.85 THEN 'CONFIDENT_MATCH' ELSE 'FALLBACK_TOP_MATCH' END AS match_type
            FROM scored
            WHERE sim_score >= 0.85 OR rank_pos = 1
            ORDER BY rank_pos;
        """
    },
    {
        "id": "Q31_semantic_deduplication_support_tickets",
        "title": "Semantic Deduplication of IT Incident Tickets via Vector Cosine Threshold",
        "domain": "Vector & Embeddings",
        "human_context": "During service outages, hundreds of users submit identically phrased IT support tickets ('login down', 'cannot access account'). Clustering tickets with vector similarity > 0.88 consolidates duplicates into a single incident.",
        "hidden_trap": "Quadratic N x N self-joins without ordering check (`t1.id < t2.id`) double compute and compare tickets to themselves.",
        "duckdb_advantage": "Triangle inequality pruning and symmetric self-join filtering in DuckDB.",
        "setup_sql": """
            CREATE TABLE support_tickets (
                ticket_id INT,
                subject VARCHAR,
                vector FLOAT[3]
            );
            INSERT INTO support_tickets VALUES
                (1, 'Cannot log into customer portal',  [0.9, 0.1, 0.0]::FLOAT[3]),
                (2, 'Portal login failing with 500 error', [0.89, 0.12, 0.01]::FLOAT[3]),
                (3, 'Billing address invoice update',   [0.1, 0.8, 0.2]::FLOAT[3]),
                (4, 'Unable to authenticate on website', [0.91, 0.09, 0.02]::FLOAT[3]);
        """,
        "sql": """
            -- Detect duplicate ticket pairs with cosine similarity >= 0.88
            SELECT 
                t1.ticket_id AS primary_ticket_id,
                t1.subject AS primary_subject,
                t2.ticket_id AS duplicate_ticket_id,
                t2.subject AS duplicate_subject,
                ROUND(array_cosine_similarity(t1.vector, t2.vector), 4) AS similarity
            FROM support_tickets t1
            JOIN support_tickets t2 
              ON t1.ticket_id < t2.ticket_id -- strictly upper triangle to avoid duplicates and self-matching
             AND array_cosine_similarity(t1.vector, t2.vector) >= 0.88
            ORDER BY similarity DESC;
        """
    },
    {
        "id": "Q32_near_duplicate_product_catalog",
        "title": "Multi-Merchant Near-Duplicate Catalog Resolution with Price Consistency",
        "domain": "Vector & Embeddings",
        "human_context": "Marketplaces aggregate catalogs from thousands of sellers. Matching identical items requires high semantic vector similarity AND compatible price bounds (e.g. price within 20%).",
        "hidden_trap": "Vector similarity alone matches accessories to main products; price filtering alone matches unrelated items.",
        "duckdb_advantage": "DuckDB combines vector math and arithmetic bounds in a single joint execution predicate.",
        "setup_sql": """
            CREATE TABLE merchant_catalog (
                sku_id INT,
                merchant VARCHAR,
                title VARCHAR,
                price DECIMAL(10,2),
                vector FLOAT[3]
            );
            INSERT INTO merchant_catalog VALUES
                (1, 'Merchant A', 'Sony WH-1000XM5 Noise-Cancelling Headphones', 349.99, [0.95, 0.1, 0.05]::FLOAT[3]),
                (2, 'Merchant B', 'Sony WH1000XM5 Wireless Headset - Black',     339.00, [0.94, 0.12, 0.04]::FLOAT[3]),
                (3, 'Merchant C', 'Sony Headphone Replacement Ear Cushions',       29.99, [0.88, 0.2, 0.1]::FLOAT[3]);
        """,
        "sql": """
            -- Match identical product listings across merchants (high similarity + price within 20%)
            SELECT 
                a.sku_id AS sku_a,
                a.merchant AS merchant_a,
                a.title AS title_a,
                b.sku_id AS sku_b,
                b.merchant AS merchant_b,
                b.title AS title_b,
                ROUND(array_cosine_similarity(a.vector, b.vector), 4) AS similarity,
                ROUND(ABS(a.price - b.price) / a.price * 100, 1) AS price_difference_pct
            FROM merchant_catalog a
            JOIN merchant_catalog b
              ON a.sku_id < b.sku_id
             AND a.merchant != b.merchant
             AND array_cosine_similarity(a.vector, b.vector) >= 0.90
             AND ABS(a.price - b.price) <= (0.20 * a.price)
            ORDER BY similarity DESC;
        """
    },
    {
        "id": "Q33_colbert_late_interaction_maxsim",
        "title": "ColBERT Multi-Vector Late Interaction (MaxSim) in Pure SQL",
        "domain": "Vector & Embeddings",
        "human_context": "Advanced retrieval models (ColBERT / Sanity) represent queries and documents as collections of token vectors. Scoring computes MaxSim: for each query token, take the maximum cosine similarity across all document tokens, then sum.",
        "hidden_trap": "Implementing late interaction typically requires specialized Python tensor pipelines.",
        "duckdb_advantage": "DuckDB can compute multi-vector token interactions, grouping by query token and document ID in vectorized SQL.",
        "setup_sql": """
            CREATE TABLE query_tokens (
                q_token_id INT,
                token_text VARCHAR,
                vec FLOAT[2]
            );
            CREATE TABLE doc_token_embeddings (
                doc_id INT,
                d_token_id INT,
                token_text VARCHAR,
                vec FLOAT[2]
            );
            -- Query: "fast database"
            INSERT INTO query_tokens VALUES
                (1, 'fast',     [1.0, 0.0]::FLOAT[2]),
                (2, 'database', [0.0, 1.0]::FLOAT[2]);
            -- Document 10: "quick relational store"
            INSERT INTO doc_token_embeddings VALUES
                (10, 1, 'quick',      [0.9, 0.1]::FLOAT[2]),
                (10, 2, 'relational', [0.1, 0.85]::FLOAT[2]),
                (10, 3, 'store',      [0.2, 0.7]::FLOAT[2]);
        """,
        "sql": """
            -- ColBERT MaxSim calculation: SUM_q( MAX_d( sim(q, d) ) )
            WITH token_sims AS (
                SELECT 
                    q.q_token_id,
                    q.token_text AS q_token,
                    d.doc_id,
                    d.token_text AS d_token,
                    array_cosine_similarity(q.vec, d.vec) AS sim
                FROM query_tokens q
                CROSS JOIN doc_token_embeddings d
            ),
            max_sim_per_query_token AS (
                SELECT 
                    doc_id,
                    q_token_id,
                    MAX(sim) AS max_token_sim
                FROM token_sims
                GROUP BY doc_id, q_token_id
            )
            SELECT 
                doc_id,
                ROUND(SUM(max_token_sim), 4) AS colbert_maxsim_score
            FROM max_sim_per_query_token
            GROUP BY doc_id
            ORDER BY colbert_maxsim_score DESC;
        """
    },
    {
        "id": "Q34_user_profile_embedding_centroid",
        "title": "User Profile Preference Vector Centroid Aggregation",
        "domain": "Vector & Embeddings",
        "human_context": "To personalize feeds, recommendation engines compute a dynamic user preference vector by calculating the average centroid of the embeddings of products the user clicked in the last 7 days.",
        "hidden_trap": "SQL standard lacks native array averaging; unnesting arrays without proper positional indexes scrambles vector dimensions.",
        "duckdb_advantage": "DuckDB array indexing and UNNEST WITH ORDINALITY allow dimension-wise vector averaging.",
        "setup_sql": """
            CREATE TABLE user_clicks_vectors (
                user_id INT,
                item_id INT,
                item_vector FLOAT[3]
            );
            INSERT INTO user_clicks_vectors VALUES
                (42, 1, [0.8, 0.2, 0.1]::FLOAT[3]),
                (42, 2, [0.6, 0.4, 0.2]::FLOAT[3]),
                (42, 3, [0.7, 0.3, 0.3]::FLOAT[3]);
        """,
        "sql": """
            -- Calculate element-wise centroid vector for user 42
            WITH unnested_dims AS (
                SELECT 
                    user_id,
                    item_id,
                    UNNEST(item_vector) AS val,
                    GENERATE_SUBSCRIPTS(item_vector, 1) AS dim_idx
                FROM user_clicks_vectors
            ),
            avg_dims AS (
                SELECT 
                    user_id,
                    dim_idx,
                    ROUND(AVG(val), 4) AS avg_dim_val
                FROM unnested_dims
                GROUP BY user_id, dim_idx
                ORDER BY user_id, dim_idx
            )
            SELECT 
                user_id,
                LIST(avg_dim_val)::FLOAT[3] AS user_preference_centroid
            FROM avg_dims
            GROUP BY user_id;
        """
    },
    {
        "id": "Q35_kmeans_cluster_assignment_step",
        "title": "K-Means Clustering Assignment and Centroid Update in Pure SQL",
        "domain": "Vector & Embeddings",
        "human_context": "Unsupervised customer segmentation can be run directly inside DuckDB by assigning customer vectors to the nearest centroid and recomputing cluster means in a single query.",
        "hidden_trap": "Running ML clustering outside the warehouse requires exporting millions of vectors over the network.",
        "duckdb_advantage": "DuckDB computes distance matrices and partition centroids natively at memory bandwidth speeds.",
        "setup_sql": """
            CREATE TABLE cluster_centroids (
                cluster_id INT,
                center FLOAT[2]
            );
            CREATE TABLE data_points (
                point_id INT,
                coord FLOAT[2]
            );
            INSERT INTO cluster_centroids VALUES
                (1, [1.0, 1.0]::FLOAT[2]),
                (2, [8.0, 8.0]::FLOAT[2]);
            INSERT INTO data_points VALUES
                (101, [1.2, 0.9]::FLOAT[2]),
                (102, [1.5, 1.1]::FLOAT[2]),
                (103, [7.8, 8.2]::FLOAT[2]);
        """,
        "sql": """
            -- Step 1: Assign each point to the closest cluster centroid via array_distance
            WITH point_distances AS (
                SELECT 
                    p.point_id,
                    p.coord,
                    c.cluster_id,
                    array_distance(p.coord, c.center) AS dist,
                    ROW_NUMBER() OVER (PARTITION BY p.point_id ORDER BY array_distance(p.coord, c.center) ASC) AS rank_closest
                FROM data_points p
                CROSS JOIN cluster_centroids c
            )
            SELECT 
                point_id,
                cluster_id AS assigned_cluster,
                ROUND(dist, 4) AS distance_to_center
            FROM point_distances
            WHERE rank_closest = 1
            ORDER BY point_id;
        """
    },
    {
        "id": "Q36_knn_vector_anomaly_detection",
        "title": "Vector Anomaly Detection via Average K-Nearest Neighbor Distance",
        "domain": "Vector & Embeddings",
        "human_context": "Anomalous sensor readings or fraudulent transaction vectors reside in sparse regions of the embedding space. Measuring the average distance to a vector's 3 nearest neighbors flags outliers.",
        "hidden_trap": "Setting a global static distance threshold fails when data clusters have variable local densities.",
        "duckdb_advantage": "DuckDB window functions compute localized k-NN distances per entity without external libraries.",
        "setup_sql": """
            CREATE TABLE transaction_embeddings (
                tx_id INT,
                vec FLOAT[2]
            );
            -- Normal cluster around (0,0); tx_id 4 is an outlier at (10, 10)
            INSERT INTO transaction_embeddings VALUES
                (1, [0.05, 0.02]::FLOAT[2]),
                (2, [0.01, 0.04]::FLOAT[2]),
                (3, [0.03, 0.01]::FLOAT[2]),
                (4, [10.0, 10.0]::FLOAT[2]);
        """,
        "sql": """
            -- Calculate average distance to 2 nearest neighbors to score anomaly level
            WITH pairwise_distances AS (
                SELECT 
                    a.tx_id,
                    b.tx_id AS neighbor_id,
                    array_distance(a.vec, b.vec) AS dist,
                    ROW_NUMBER() OVER (PARTITION BY a.tx_id ORDER BY array_distance(a.vec, b.vec) ASC) AS k_rank
                FROM transaction_embeddings a
                JOIN transaction_embeddings b ON a.tx_id != b.tx_id
            ),
            knn_avg AS (
                SELECT 
                    tx_id,
                    AVG(dist) AS mean_2nn_distance
                FROM pairwise_distances
                WHERE k_rank <= 2
                GROUP BY tx_id
            )
            SELECT 
                tx_id,
                ROUND(mean_2nn_distance, 4) AS outlier_score,
                CASE WHEN mean_2nn_distance > 5.0 THEN 'ANOMALOUS_OUTLIER' ELSE 'NORMAL' END AS classification
            FROM knn_avg
            ORDER BY outlier_score DESC;
        """
    },
    {
        "id": "Q37_hybrid_relational_vector_cohort_join",
        "title": "Cohort-Constrained Vector Match with Geographical Regionality",
        "domain": "Vector & Embeddings",
        "human_context": "Real-world matchmaking (dating apps, gig-economy driver matching) requires vector personality/skill compatibility joined with strict relational geographic and category boundaries.",
        "hidden_trap": "Matching vectors globally without partitioning by region produces candidates located 3,000 miles away.",
        "duckdb_advantage": "DuckDB joins relational partitions (region = 'NA-WEST') directly with vector distance.",
        "setup_sql": """
            CREATE TABLE candidates (
                candidate_id INT,
                region VARCHAR,
                skills_vec FLOAT[3]
            );
            CREATE TABLE job_openings (
                job_id INT,
                region VARCHAR,
                required_vec FLOAT[3]
            );
            INSERT INTO candidates VALUES
                (1, 'US-WEST', [0.8, 0.5, 0.2]::FLOAT[3]),
                (2, 'EU-CENTRAL', [0.85, 0.5, 0.2]::FLOAT[3]);
            INSERT INTO job_openings VALUES
                (101, 'US-WEST', [0.82, 0.48, 0.18]::FLOAT[3]);
        """,
        "sql": """
            -- Match jobs to candidates strictly within matching geographical region ordered by skill compatibility
            SELECT 
                j.job_id,
                j.region,
                c.candidate_id,
                ROUND(array_cosine_similarity(c.skills_vec, j.required_vec), 4) AS skill_fit_score
            FROM job_openings j
            JOIN candidates c
              ON j.region = c.region
            ORDER BY skill_fit_score DESC;
        """
    },
    {
        "id": "Q38_multimodal_image_text_fusion",
        "title": "Multi-Modal Joint Retrieval (Image + Text Query Embedding Fusion)",
        "domain": "Vector & Embeddings",
        "human_context": "In e-commerce search, users submit a photo and a text clarification (e.g. photo of dress + 'in floral silk'). We compute a weighted combination of image-vector and text-vector similarity.",
        "hidden_trap": "Treating text and image vectors as independent queries yields conflicting rank lists.",
        "duckdb_advantage": "DuckDB can evaluate multiple vector distance functions in a single projection pass.",
        "setup_sql": """
            CREATE TABLE fashion_items (
                item_id INT,
                title VARCHAR,
                img_vec FLOAT[2],
                txt_vec FLOAT[2]
            );
            INSERT INTO fashion_items VALUES
                (1, 'Silk Floral Summer Dress', [0.8, 0.2]::FLOAT[2], [0.9, 0.1]::FLOAT[2]),
                (2, 'Cotton Floral Blouse',    [0.75, 0.25]::FLOAT[2], [0.6, 0.4]::FLOAT[2]),
                (3, 'Leather Biker Jacket',    [0.1, 0.9]::FLOAT[2], [0.0, 1.0]::FLOAT[2]);
        """,
        "sql": """
            -- Joint multi-modal score: 60% image vector similarity + 40% text vector similarity
            SELECT 
                item_id,
                title,
                ROUND(array_cosine_similarity(img_vec, [0.82, 0.18]::FLOAT[2]), 4) AS img_sim,
                ROUND(array_cosine_similarity(txt_vec, [0.92, 0.08]::FLOAT[2]), 4) AS txt_sim,
                ROUND(
                    0.60 * array_cosine_similarity(img_vec, [0.82, 0.18]::FLOAT[2]) +
                    0.40 * array_cosine_similarity(txt_vec, [0.92, 0.08]::FLOAT[2]), 4
                ) AS joint_multimodal_score
            FROM fashion_items
            ORDER BY joint_multimodal_score DESC;
        """
    },
    {
        "id": "Q39_maximal_marginal_relevance_mmr",
        "title": "Maximal Marginal Relevance (MMR) Diversity Reranking in SQL",
        "domain": "Vector & Embeddings",
        "human_context": "Standard vector retrieval often returns 5 virtually identical articles. MMR penalizes redundancy by selecting documents that are similar to the query but dissimilar to already-selected documents.",
        "hidden_trap": "Pure relevance search creates echo-chamber search results with zero content diversity.",
        "duckdb_advantage": "DuckDB can compute inter-candidate similarity matrix in memory to penalize redundancy.",
        "setup_sql": """
            CREATE TABLE news_articles (
                article_id INT,
                headline VARCHAR,
                vec FLOAT[2]
            );
            INSERT INTO news_articles VALUES
                (1, 'Fed cuts interest rates by 25 bps',      [0.99, 0.05]::FLOAT[2]),
                (2, 'Central bank lowers benchmark 25 bps',   [0.98, 0.06]::FLOAT[2]), -- Redundant clone
                (3, 'Tech stock rally follows monetary shift', [0.80, 0.45]::FLOAT[2]); -- Diverse relevant
        """,
        "sql": """
            -- First candidate is highest query similarity; score subsequent candidates by query sim minus similarity to article 1
            WITH ranked_candidates AS (
                SELECT 
                    article_id,
                    headline,
                    vec,
                    array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) AS query_sim
                FROM news_articles
            )
            SELECT 
                c.article_id,
                c.headline,
                ROUND(c.query_sim, 4) AS query_relevance,
                ROUND(array_cosine_similarity(c.vec, top1.vec), 4) AS redundancy_with_top1,
                -- MMR formula: 0.7 * Sim(doc, query) - 0.3 * Sim(doc, top1)
                ROUND(0.7 * c.query_sim - 0.3 * array_cosine_similarity(c.vec, top1.vec), 4) AS mmr_score
            FROM ranked_candidates c
            CROSS JOIN (SELECT vec FROM ranked_candidates ORDER BY query_sim DESC LIMIT 1) top1
            ORDER BY mmr_score DESC;
        """
    },
    {
        "id": "Q40_cosine_matrix_cluster_pruning",
        "title": "Pairwise Vector Similarity Self-Join with Coarse Cluster Pruning",
        "domain": "Vector & Embeddings",
        "human_context": "Finding all similar document pairs across 100,000 docs is O(N^2) (10 billion checks). Partitioning into coarse category buckets first reduces search to O(N * (N/K)).",
        "hidden_trap": "Unpartitioned cross joins cause out-of-memory crashes on analytical engines.",
        "duckdb_advantage": "DuckDB evaluates equi-join partition keys before computing array_cosine_similarity.",
        "setup_sql": """
            CREATE TABLE corpus (
                doc_id INT,
                bucket_id INT,
                vector FLOAT[2]
            );
            INSERT INTO corpus VALUES
                (1, 10, [0.9, 0.1]::FLOAT[2]),
                (2, 10, [0.88, 0.12]::FLOAT[2]),
                (3, 20, [0.1, 0.9]::FLOAT[2]),
                (4, 20, [0.12, 0.88]::FLOAT[2]);
        """,
        "sql": """
            -- Pairwise similarity evaluated ONLY within shared bucket partitions
            SELECT 
                a.doc_id AS doc_a,
                b.doc_id AS doc_b,
                a.bucket_id,
                ROUND(array_cosine_similarity(a.vector, b.vector), 4) AS similarity
            FROM corpus a
            JOIN corpus b
              ON a.bucket_id = b.bucket_id
             AND a.doc_id < b.doc_id
            WHERE array_cosine_similarity(a.vector, b.vector) >= 0.85
            ORDER BY similarity DESC;
        """
    },
    {
        "id": "Q41_collaborative_filtering_latent_dot",
        "title": "Latent Factor Matrix Factorization Dot Product Recommendation",
        "domain": "Vector & Embeddings",
        "human_context": "Matrix factorization (SVD / ALS) maps users and movies to latent factor vectors. Predicted rating is dot product of user vector and movie vector plus user and movie bias terms.",
        "hidden_trap": "Omitting bias terms causes popular movies to be underrated and niche items to be overrated.",
        "duckdb_advantage": "DuckDB can evaluate latent factor dot products combined with additive scalar bias terms.",
        "setup_sql": """
            CREATE TABLE user_latent (
                user_id INT,
                user_bias DOUBLE,
                u_vec FLOAT[3]
            );
            CREATE TABLE item_latent (
                movie_id INT,
                title VARCHAR,
                movie_bias DOUBLE,
                m_vec FLOAT[3]
            );
            INSERT INTO user_latent VALUES
                (1, 0.2, [0.5, 0.3, 0.1]::FLOAT[3]);
            INSERT INTO item_latent VALUES
                (101, 'Sci-Fi Odyssey', 0.5, [0.6, 0.2, 0.1]::FLOAT[3]),
                (102, 'Romantic Comedy', -0.1, [0.1, 0.7, 0.2]::FLOAT[3]);
        """,
        "sql": """
            -- Predict user rating: baseline (3.5) + u_bias + m_bias + (u_vec . m_vec)
            SELECT 
                u.user_id,
                m.movie_id,
                m.title,
                ROUND(
                    3.5 + u.user_bias + m.movie_bias + array_inner_product(u.u_vec, m.m_vec), 2
                ) AS predicted_rating
            FROM user_latent u
            CROSS JOIN item_latent m
            WHERE u.user_id = 1
            ORDER BY predicted_rating DESC;
        """
    },
    {
        "id": "Q42_negative_prompting_vector_repulsion",
        "title": "Vector Repulsion Scoring (Positive vs Negative Query Guidance)",
        "domain": "Vector & Embeddings",
        "human_context": "In image generation and semantic search, users supply positive and negative prompts (e.g. 'cyberpunk city' NOT 'blurry / low quality'). The score boosts positive similarity and penalizes negative similarity.",
        "hidden_trap": "Filtering out negatives with boolean NOT drops items that have even slight overlap with negative words.",
        "duckdb_advantage": "DuckDB computes continuous vector repulsion formulas in standard SQL expressions.",
        "setup_sql": """
            CREATE TABLE generative_assets (
                asset_id INT,
                name VARCHAR,
                vec FLOAT[2]
            );
            INSERT INTO generative_assets VALUES
                (1, 'Sharp Neon Skyline',      [0.9, 0.1]::FLOAT[2]),
                (2, 'Blurry Neon Streetscape', [0.8, 0.7]::FLOAT[2]),
                (3, 'Rustic Wooden Cabin',     [0.0, 0.9]::FLOAT[2]);
        """,
        "sql": """
            -- Positive query: [1.0, 0.0] (cyberpunk neon), Negative query: [0.0, 1.0] (blurry/rustic)
            -- Net Score = Cosine(vec, pos) - (0.5 * Cosine(vec, neg))
            SELECT 
                asset_id,
                name,
                ROUND(array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]), 4) AS pos_sim,
                ROUND(array_cosine_similarity(vec, [0.0, 1.0]::FLOAT[2]), 4) AS neg_sim,
                ROUND(
                    array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) - 
                    (0.50 * array_cosine_similarity(vec, [0.0, 1.0]::FLOAT[2])), 4
                ) AS net_guided_score
            FROM generative_assets
            ORDER BY net_guided_score DESC;
        """
    },
    {
        "id": "Q43_best_chunk_pooling_retrieval",
        "title": "Document-Level Aggregation with Best-Chunk Pooling in RAG",
        "domain": "Vector & Embeddings",
        "human_context": "Long PDF manuals are split into 50 chunks each. To avoid returning 5 chunks from the exact same PDF manual, we retrieve the best chunk per document and aggregate at the document level.",
        "hidden_trap": "Returning raw chunk Top-K dominates the context window with duplicates from a single document.",
        "duckdb_advantage": "DuckDB QUALIFY clause filters for the top chunk per document without nested CTEs.",
        "setup_sql": """
            CREATE TABLE document_chunks (
                chunk_id INT,
                doc_id INT,
                doc_title VARCHAR,
                chunk_text VARCHAR,
                vec FLOAT[2]
            );
            INSERT INTO document_chunks VALUES
                (101, 1, 'Manual A', 'Setup guide section 1', [0.95, 0.1]::FLOAT[2]),
                (102, 1, 'Manual A', 'Setup guide section 2', [0.92, 0.15]::FLOAT[2]),
                (103, 2, 'Manual B', 'Troubleshooting section 1', [0.88, 0.2]::FLOAT[2]);
        """,
        "sql": """
            -- Retrieve the single highest-scoring chunk per document using QUALIFY
            SELECT 
                doc_id,
                doc_title,
                chunk_id,
                chunk_text,
                ROUND(array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]), 4) AS chunk_score
            FROM document_chunks
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY doc_id 
                ORDER BY array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) DESC
            ) = 1
            ORDER BY chunk_score DESC;
        """
    },
    {
        "id": "Q44_token_budget_context_truncation",
        "title": "Dynamic Context Window Token Budget Packing for LLM RAG",
        "domain": "Vector & Embeddings",
        "human_context": "When assembling retrieved chunks for an LLM prompt, you have a strict token limit (e.g. 1,000 tokens). You must greedily pick highest-similarity chunks until the cumulative token sum would exceed the budget.",
        "hidden_trap": "Picking a fixed LIMIT 10 can overflow LLM token limits or waste available prompt capacity.",
        "duckdb_advantage": "DuckDB cumulative window sums (`SUM(token_count) OVER (...)`) cleanly enforce strict budgets.",
        "setup_sql": """
            CREATE TABLE rag_candidate_chunks (
                chunk_id INT,
                token_count INT,
                vec FLOAT[2]
            );
            INSERT INTO rag_candidate_chunks VALUES
                (1, 400, [0.95, 0.05]::FLOAT[2]),
                (2, 350, [0.90, 0.10]::FLOAT[2]),
                (3, 400, [0.85, 0.15]::FLOAT[2]); -- Exceeds 1000 total budget
        """,
        "sql": """
            -- Greedily pack chunks ordered by similarity up to strict 1,000 token budget
            WITH ranked_chunks AS (
                SELECT 
                    chunk_id,
                    token_count,
                    array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) AS score,
                    SUM(token_count) OVER (
                        ORDER BY array_cosine_similarity(vec, [1.0, 0.0]::FLOAT[2]) DESC
                    ) AS cumulative_tokens
                FROM rag_candidate_chunks
            )
            SELECT 
                chunk_id,
                token_count,
                cumulative_tokens,
                ROUND(score, 4) AS similarity_score
            FROM ranked_chunks
            WHERE cumulative_tokens <= 1000
            ORDER BY similarity_score DESC;
        """
    },
    {
        "id": "Q45_cross_encoder_candidate_generation",
        "title": "Two-Stage Retrieval: Bi-Encoder Candidate Generation for Re-ranking",
        "domain": "Vector & Embeddings",
        "human_context": "Modern enterprise search uses a 2-stage pipeline: Fast bi-encoder vector search retrieves Top-50 candidates, which are then passed to a computationally heavy cross-encoder for final scoring.",
        "hidden_trap": "Running heavy cross-encoder models across entire datasets is computationally impossible.",
        "duckdb_advantage": "DuckDB can quickly filter millions of rows down to 50 candidates in milliseconds.",
        "setup_sql": """
            CREATE TABLE knowledge_articles (
                article_id INT,
                category VARCHAR,
                vec FLOAT[2]
            );
            INSERT INTO knowledge_articles VALUES
                (1, 'tech', [0.9, 0.1]::FLOAT[2]),
                (2, 'tech', [0.8, 0.2]::FLOAT[2]),
                (3, 'hr',   [0.1, 0.9]::FLOAT[2]);
        """,
        "sql": """
            -- First-stage candidate extraction: Top candidates in relevant category
            SELECT 
                article_id,
                category,
                ROUND(array_cosine_similarity(vec, [0.95, 0.05]::FLOAT[2]), 4) AS stage1_biencoder_score
            FROM knowledge_articles
            WHERE category = 'tech'
            ORDER BY stage1_biencoder_score DESC
            LIMIT 50;
        """
    },
    {
        "id": "Q46_temporal_embedding_drift",
        "title": "Temporal Semantic Drift Tracking across Document Embedding Centroids",
        "domain": "Vector & Embeddings",
        "human_context": "As companies evolve, the meaning of terms like 'security' or 'remote work' shifts. Tracking the cosine distance between monthly embedding centroids reveals semantic concept drift.",
        "hidden_trap": "Ignoring semantic drift causes older documentation to silently diverge from current employee search queries.",
        "duckdb_advantage": "DuckDB calculates monthly vector centroids and inter-month drift using LAG.",
        "setup_sql": """
            CREATE TABLE monthly_centroids (
                month_date DATE,
                centroid FLOAT[2]
            );
            INSERT INTO monthly_centroids VALUES
                ('2026-01-01', [0.90, 0.10]::FLOAT[2]),
                ('2026-02-01', [0.88, 0.12]::FLOAT[2]),
                ('2026-03-01', [0.70, 0.35]::FLOAT[2]); -- Significant semantic drift
        """,
        "sql": """
            -- Track month-over-month semantic drift in concept centroids
            SELECT 
                month_date,
                centroid,
                LAG(centroid) OVER (ORDER BY month_date) AS prev_month_centroid,
                ROUND(
                    1.0 - array_cosine_similarity(
                        centroid, 
                        LAG(centroid) OVER (ORDER BY month_date)
                    ), 4
                ) AS drift_distance_from_prev_month
            FROM monthly_centroids
            ORDER BY month_date;
        """
    },
    {
        "id": "Q47_hierarchical_vector_coarse_fine",
        "title": "Hierarchical Coarse-to-Fine Multi-Level Vector Filtering",
        "domain": "Vector & Embeddings",
        "human_context": "In massive enterprise catalogs, searching 100 million items is accelerated by first matching high-level department embedding centroids, then searching specific item vectors inside matching departments.",
        "hidden_trap": "Flat brute-force vector search over hundreds of millions of items consumes excessive compute.",
        "duckdb_advantage": "DuckDB joins coarse department vectors directly to fine item vectors in a single query.",
        "setup_sql": """
            CREATE TABLE departments (
                dept_id INT,
                dept_name VARCHAR,
                dept_centroid FLOAT[2]
            );
            CREATE TABLE items (
                item_id INT,
                dept_id INT,
                item_name VARCHAR,
                item_vector FLOAT[2]
            );
            INSERT INTO departments VALUES
                (1, 'Electronics', [0.9, 0.1]::FLOAT[2]),
                (2, 'Gardening',   [0.1, 0.9]::FLOAT[2]);
            INSERT INTO items VALUES
                (101, 1, 'Noise-canceling earphones', [0.92, 0.08]::FLOAT[2]),
                (102, 1, 'USB-C Cable',               [0.85, 0.15]::FLOAT[2]),
                (201, 2, 'Lawn Mower',                [0.12, 0.88]::FLOAT[2]);
        """,
        "sql": """
            -- Find best matching department, then retrieve top items strictly within that department
            WITH top_dept AS (
                SELECT dept_id
                FROM departments
                ORDER BY array_cosine_similarity(dept_centroid, [0.95, 0.05]::FLOAT[2]) DESC
                LIMIT 1
            )
            SELECT 
                i.item_id,
                i.item_name,
                ROUND(array_cosine_similarity(i.item_vector, [0.95, 0.05]::FLOAT[2]), 4) AS fine_sim_score
            FROM items i
            JOIN top_dept d ON i.dept_id = d.dept_id
            ORDER BY fine_sim_score DESC;
        """
    },
    {
        "id": "Q48_vector_quantization_distortion",
        "title": "Vector Quantization Precision Distortion & Reconstruction Error",
        "domain": "Vector & Embeddings",
        "human_context": "To compress embeddings from 32-bit floats to 8-bit integers, engineers evaluate the reconstruction error (distance between uncompressed and quantized vector) to measure fidelity loss.",
        "hidden_trap": "Deploying quantized embeddings without evaluating distortion leads to silent degradation in search accuracy.",
        "duckdb_advantage": "DuckDB can evaluate floating-point vector distances against quantized projections.",
        "setup_sql": """
            CREATE TABLE vector_compression_test (
                vector_id INT,
                fp32_vec FLOAT[3],
                quantized_vec FLOAT[3]
            );
            INSERT INTO vector_compression_test VALUES
                (1, [0.12345, 0.67891, 0.44332]::FLOAT[3], [0.12, 0.68, 0.44]::FLOAT[3]),
                (2, [0.99123, 0.02111, 0.11005]::FLOAT[3], [0.99, 0.02, 0.11]::FLOAT[3]);
        """,
        "sql": """
            -- Evaluate Euclidean distortion and cosine fidelity loss per vector
            SELECT 
                vector_id,
                ROUND(array_distance(fp32_vec, quantized_vec), 6) AS l2_quantization_error,
                ROUND(1.0 - array_cosine_similarity(fp32_vec, quantized_vec), 6) AS cosine_distortion
            FROM vector_compression_test
            ORDER BY l2_quantization_error DESC;
        """
    },
    {
        "id": "Q49_prototype_intent_classification",
        "title": "Zero-Shot Query Intent Classification via Prototype Vector Distance",
        "domain": "Vector & Embeddings",
        "human_context": "Instead of training a BERT classifier, user query vectors are compared against pre-computed 'intent prototype vectors' (e.g. Navigational, Transactional, Informational). The closest prototype labels the query intent.",
        "hidden_trap": "Maintaining external classifier microservices adds 50ms latency to query planning.",
        "duckdb_advantage": "DuckDB classifies intent in pure SQL with sub-millisecond execution.",
        "setup_sql": """
            CREATE TABLE intent_prototypes (
                intent_name VARCHAR,
                prototype_vector FLOAT[2]
            );
            CREATE TABLE inbound_queries (
                query_id INT,
                query_text VARCHAR,
                query_vector FLOAT[2]
            );
            INSERT INTO intent_prototypes VALUES
                ('TRANSACTIONAL_BUY', [0.9, 0.1]::FLOAT[2]),
                ('INFORMATIONAL_FAQ', [0.1, 0.9]::FLOAT[2]);
            INSERT INTO inbound_queries VALUES
                (1, 'where to purchase macbook pro', [0.88, 0.15]::FLOAT[2]),
                (2, 'how does duckdb storage work',   [0.15, 0.85]::FLOAT[2]);
        """,
        "sql": """
            -- Classify each query to its closest intent prototype
            WITH ranked_intents AS (
                SELECT 
                    q.query_id,
                    q.query_text,
                    p.intent_name,
                    array_cosine_similarity(q.query_vector, p.prototype_vector) AS intent_similarity,
                    ROW_NUMBER() OVER (
                        PARTITION BY q.query_id 
                        ORDER BY array_cosine_similarity(q.query_vector, p.prototype_vector) DESC
                    ) AS rank_match
                FROM inbound_queries q
                CROSS JOIN intent_prototypes p
            )
            SELECT 
                query_id,
                query_text,
                intent_name AS predicted_intent,
                ROUND(intent_similarity, 4) AS confidence
            FROM ranked_intents
            WHERE rank_match = 1
            ORDER BY query_id;
        """
    },
    {
        "id": "Q50_contrastive_triplet_loss_evaluation",
        "title": "Contrastive Triplet Evaluation: Anchor-Positive-Negative Separation",
        "domain": "Vector & Embeddings",
        "human_context": "In embedding model evaluation, high-quality models satisfy the triplet condition: distance(anchor, positive) + margin < distance(anchor, negative). We evaluate model margin violations directly in SQL.",
        "hidden_trap": "Validating embedding models often requires ad-hoc PyTorch scripts; SQL evaluation enables continuous monitoring in production.",
        "duckdb_advantage": "DuckDB computes margin violations across millions of triplets in seconds.",
        "setup_sql": """
            CREATE TABLE eval_triplets (
                triplet_id INT,
                anchor_vec FLOAT[2],
                positive_vec FLOAT[2],
                negative_vec FLOAT[2]
            );
            INSERT INTO eval_triplets VALUES
                -- Good triplet: pos is close, neg is far
                (1, [1.0, 0.0]::FLOAT[2], [0.95, 0.05]::FLOAT[2], [0.1, 0.9]::FLOAT[2]),
                -- Violated triplet: neg is closer than pos!
                (2, [1.0, 0.0]::FLOAT[2], [0.5, 0.5]::FLOAT[2],   [0.9, 0.1]::FLOAT[2]);
        """,
        "sql": """
            -- Compute triplet margin violation with margin = 0.2
            -- Violation = GREATEST(0, dist(a, p) - dist(a, n) + margin)
            SELECT 
                triplet_id,
                ROUND(array_distance(anchor_vec, positive_vec), 4) AS dist_pos,
                ROUND(array_distance(anchor_vec, negative_vec), 4) AS dist_neg,
                ROUND(
                    GREATEST(0.0, array_distance(anchor_vec, positive_vec) - array_distance(anchor_vec, negative_vec) + 0.20), 4
                ) AS triplet_margin_loss,
                CASE 
                    WHEN (array_distance(anchor_vec, positive_vec) - array_distance(anchor_vec, negative_vec) + 0.20) > 0 
                    THEN 'VIOLATION' 
                    ELSE 'SATISFIED' 
                END AS evaluation_status
            FROM eval_triplets
            ORDER BY triplet_id;
        """
    }
]
