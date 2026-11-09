/*
 ==============================================================================
 Query ID:         Q48_vector_quantization_distortion
 Title:            Vector Quantization Precision Distortion & Reconstruction Error
 Domain:           Vector & Embeddings
 ------------------------------------------------------------------------------
 Human Context:
 To compress embeddings from 32-bit floats to 8-bit integers, engineers evaluate the reconstruction error (distance between uncompressed and quantized vector) to measure fidelity loss.

 The Hidden Trap:
 Deploying quantized embeddings without evaluating distortion leads to silent degradation in search accuracy.

 The DuckDB Advantage:
 DuckDB can evaluate floating-point vector distances against quantized projections.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE vector_compression_test (
                vector_id INT,
                fp32_vec FLOAT[3],
                quantized_vec FLOAT[3]
            );
            INSERT INTO vector_compression_test VALUES
                (1, [0.12345, 0.67891, 0.44332]::FLOAT[3], [0.12, 0.68, 0.44]::FLOAT[3]),
                (2, [0.99123, 0.02111, 0.11005]::FLOAT[3], [0.99, 0.02, 0.11]::FLOAT[3]);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Evaluate Euclidean distortion and cosine fidelity loss per vector
            SELECT 
                vector_id,
                ROUND(array_distance(fp32_vec, quantized_vec), 6) AS l2_quantization_error,
                ROUND(1.0 - array_cosine_similarity(fp32_vec, quantized_vec), 6) AS cosine_distortion
            FROM vector_compression_test
            ORDER BY l2_quantization_error DESC;
