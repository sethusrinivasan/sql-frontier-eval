/*
 ==============================================================================
 Query ID:         Q38_multimodal_image_text_fusion
 Title:            Multi-Modal Joint Retrieval (Image + Text Query Embedding Fusion)
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 In e-commerce search, users submit a photo and a text clarification (e.g. photo of dress + 'in floral silk'). We compute a weighted combination of image-vector and text-vector similarity.

 The Hidden Trap:
 Treating text and image vectors as independent queries yields conflicting rank lists.

 The DuckDB Advantage:
 DuckDB can evaluate multiple vector distance functions in a single projection pass.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
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
