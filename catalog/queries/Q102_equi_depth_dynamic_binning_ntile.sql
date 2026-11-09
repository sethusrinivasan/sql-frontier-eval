/*
 ==============================================================================
 Query ID:         Q102_equi_depth_dynamic_binning_ntile
 Title:            Dynamic Equi-Depth Histogram Binning via NTILE in Pure SQL
 Domain:           Warehouse & Statistical
 ------------------------------------------------------------------------------
 Human Context:
 Creating balanced feature histograms for ML requires equal-depth binning (each bucket contains an equal number of records) rather than equal-width binning.

 The Hidden Trap:
 Equal-width bins leave high-value tail bins completely empty on skewed power-law distributions.

 The DuckDB Advantage:
 DuckDB `NTILE()` computes equi-depth quantile bins with zero pre-scanning.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE customer_spend (
                customer_id INT,
                annual_spend DECIMAL(10,2)
            );
            INSERT INTO customer_spend VALUES
                (1, 20.00), (2, 35.00), (3, 50.00), (4, 150.00),
                (5, 300.00), (6, 500.00), (7, 1200.00), (8, 5000.00);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Partition customers into 4 equal-depth spending quartiles (bins)
            WITH binned AS (
                SELECT 
                    customer_id,
                    annual_spend,
                    NTILE(4) OVER (ORDER BY annual_spend ASC) AS spend_quartile
                FROM customer_spend
            )
            SELECT 
                spend_quartile,
                COUNT(*) AS customer_count,
                MIN(annual_spend) AS min_spend_in_bin,
                MAX(annual_spend) AS max_spend_in_bin,
                ROUND(AVG(annual_spend), 2) AS avg_spend_in_bin
            FROM binned
            GROUP BY spend_quartile
            ORDER BY spend_quartile;
