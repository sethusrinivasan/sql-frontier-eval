# Domain 5: Advanced Warehouse Analytics & Statistical Patterns (Queries 89 - 102)

WAREHOUSE_QUERIES = [
    {
        "id": "Q89_chasm_trap_fanout_resolution",
        "title": "Chasm Trap Resolution: Multi-Table 1:N Aggregation without Fan-Out Inflation",
        "domain": "Warehouse & Statistical",
        "human_context": "When an order has multiple discounts AND multiple shipment records, joining both child tables directly to the order creates a cross product that multiplies sales figures by 4x. Pre-aggregating each child table in CTEs before joining preserves financial integrity.",
        "hidden_trap": "Frontier models routinely join all tables before GROUP BY, causing catastrophic silent metric corruption.",
        "duckdb_advantage": "DuckDB can evaluate pre-aggregated CTEs in parallel vector pipelines with zero temp-table writes.",
        "setup_sql": """
            CREATE TABLE orders (order_id INT, customer_id INT, base_amount DECIMAL(10,2));
            CREATE TABLE order_discounts (discount_id INT, order_id INT, amount DECIMAL(10,2));
            CREATE TABLE order_shipments (shipment_id INT, order_id INT, fee DECIMAL(10,2));
            INSERT INTO orders VALUES (101, 1, 100.00);
            INSERT INTO order_discounts VALUES (1, 101, 10.00), (2, 101, 5.00);
            INSERT INTO order_shipments VALUES (1, 101, 4.00),  (2, 101, 6.00);
        """,
        "sql": """
            -- Correctly aggregate discounts and shipments without fan-out inflation
            WITH agg_discounts AS (
                SELECT order_id, SUM(amount) AS total_discount
                FROM order_discounts
                GROUP BY order_id
            ),
            agg_shipments AS (
                SELECT order_id, SUM(fee) AS total_shipping
                FROM order_shipments
                GROUP BY order_id
            )
            SELECT 
                o.customer_id,
                SUM(o.base_amount) AS total_gross_sales,
                COALESCE(SUM(d.total_discount), 0.00) AS total_discount_amount,
                COALESCE(SUM(s.total_shipping), 0.00) AS total_shipping_fees,
                ROUND(SUM(o.base_amount) - COALESCE(SUM(d.total_discount), 0.00) + COALESCE(SUM(s.total_shipping), 0.00), 2) AS net_revenue
            FROM orders o
            LEFT JOIN agg_discounts d ON o.order_id = d.order_id
            LEFT JOIN agg_shipments s ON o.order_id = s.order_id
            GROUP BY o.customer_id;
        """
    },
    {
        "id": "Q90_three_valued_logic_safe_anti_join",
        "title": "Three-Valued Logic Safe Anti-Join (Eliminating the NOT IN NULL Trap)",
        "domain": "Warehouse & Statistical",
        "human_context": "Marketing queries to find active customers who have not churned often use `WHERE id NOT IN (SELECT customer_id FROM churned_users)`. If a single `NULL` exists in `churned_users`, SQL three-valued logic causes the entire query to return ZERO rows.",
        "hidden_trap": "In SQL, `val NOT IN (1, NULL)` evaluates to `UNKNOWN`, which evaluates to `FALSE` in WHERE clauses, silently discarding every single record.",
        "duckdb_advantage": "Using `NOT EXISTS` or `ANTI JOIN` avoids three-valued logic traps and compiles to optimal hash anti-joins.",
        "setup_sql": """
            CREATE TABLE all_customers (customer_id INT, name VARCHAR);
            CREATE TABLE churned_customers (customer_id INT);
            INSERT INTO all_customers VALUES (1, 'Alice'), (2, 'Bob'), (3, 'Charlie');
            -- Note the presence of a NULL record in the churned table!
            INSERT INTO churned_customers VALUES (2), (NULL);
        """,
        "sql": """
            -- Robust anti-join that is immune to NULL records in the subquery
            SELECT 
                c.customer_id,
                c.name
            FROM all_customers c
            WHERE NOT EXISTS (
                SELECT 1 
                FROM churned_customers ch 
                WHERE ch.customer_id = c.customer_id
            )
            ORDER BY c.customer_id;
        """
    },
    {
        "id": "Q91_dynamic_pivot_monthly_revenue",
        "title": "Dynamic PIVOT of Monthly Revenue by Product Category",
        "domain": "Warehouse & Statistical",
        "human_context": "Financial reporting requires transforming normalized long-form transaction rows into cross-tabulated wide financial matrices (Months along the top, Categories down the side).",
        "hidden_trap": "Writing dozens of manual `CASE WHEN month = '2026-01' THEN amount ELSE 0 END` expressions is brittle and verbose.",
        "duckdb_advantage": "DuckDB has first-class native `PIVOT` syntax.",
        "setup_sql": """
            CREATE TABLE sales_facts (
                category VARCHAR,
                sale_month VARCHAR,
                revenue DECIMAL(10,2)
            );
            INSERT INTO sales_facts VALUES
                ('Electronics', '2026-01', 50000.00),
                ('Electronics', '2026-02', 65000.00),
                ('Apparel',     '2026-01', 30000.00),
                ('Apparel',     '2026-02', 32000.00);
        """,
        "sql": """
            -- Reshape monthly revenue into wide cross-tabulation using DuckDB PIVOT
            PIVOT sales_facts
            ON sale_month
            USING SUM(revenue)
            GROUP BY category
            ORDER BY category;
        """
    },
    {
        "id": "Q92_dynamic_unpivot_wide_metrics",
        "title": "Dynamic UNPIVOT of Wide Tabular Sensor / Survey Metrics",
        "domain": "Warehouse & Statistical",
        "human_context": "Legacy data or spreadsheet exports often arrive with metric names as column headers (cpu, memory, disk). Normalizing them into key-value pairs is necessary for time-series modeling.",
        "hidden_trap": "Chaining 10 UNION ALL queries multiplies read passes over the source data.",
        "duckdb_advantage": "DuckDB native `UNPIVOT` performs unpivoting in a single streaming pass.",
        "setup_sql": """
            CREATE TABLE wide_telemetry (
                host_id VARCHAR,
                captured_date DATE,
                cpu_metric DOUBLE,
                mem_metric DOUBLE,
                disk_metric DOUBLE
            );
            INSERT INTO wide_telemetry VALUES
                ('srv-01', '2026-03-01', 45.2, 78.5, 92.1);
        """,
        "sql": """
            -- Transform wide metric columns into normalized key-value rows
            UNPIVOT wide_telemetry
            ON cpu_metric, mem_metric, disk_metric
            INTO
                NAME metric_name
                VALUE metric_value;
        """
    },
    {
        "id": "Q93_list_lambdas_nested_json_arrays",
        "title": "List Lambdas for High-Performance Nested Array Transformations",
        "domain": "Warehouse & Statistical",
        "human_context": "Modern analytical warehouses store nested array payloads (e.g. array of discount percentages). Transforming or filtering elements directly inside the array without unnesting and re-aggregating saves massive compute.",
        "hidden_trap": "Unnesting arrays to flat rows and re-aggregating with LIST() triggers expensive hash shuffles.",
        "duckdb_advantage": "DuckDB list lambdas (`list_transform`, `list_filter`) execute in-place vectorized functions directly on array vectors.",
        "setup_sql": """
            CREATE TABLE shopping_carts (
                cart_id INT,
                discounts_applied INT[],
                item_prices DOUBLE[]
            );
            INSERT INTO shopping_carts VALUES
                (1, [5, 15, 25], [100.0, 50.0, 20.0]),
                (2, [0, 10],     [200.0, 80.0]);
        """,
        "sql": """
            -- Filter out discounts <= 5% and double remaining discount percentages using list lambdas
            SELECT 
                cart_id,
                discounts_applied AS raw_discounts,
                list_filter(discounts_applied, lambda x: x > 5) AS qualifying_discounts,
                list_transform(
                    list_filter(discounts_applied, lambda x: x > 5), 
                    lambda x: x * 2
                ) AS doubled_qualifying_discounts
            FROM shopping_carts
            ORDER BY cart_id;
        """
    },
    {
        "id": "Q94_median_absolute_deviation_mad",
        "title": "Median Absolute Deviation (MAD) Robust Statistical Outlier Detection",
        "domain": "Warehouse & Statistical",
        "human_context": "Traditional standard deviation Z-scores fail in the presence of extreme outliers because the outliers themselves distort the mean and standard deviation. MAD is a robust statistical scale estimator.",
        "hidden_trap": "Mean and standard deviation break down completely on fat-tailed or skewed data distributions.",
        "duckdb_advantage": "DuckDB can compute medians of deviations in standard analytical CTEs.",
        "setup_sql": """
            CREATE TABLE payment_volumes (
                tx_id INT,
                amount DOUBLE
            );
            INSERT INTO payment_volumes VALUES
                (1, 10.0), (2, 12.0), (3, 11.0), (4, 13.0), (5, 12.0),
                (6, 1000.0); -- Massive outlier
        """,
        "sql": """
            -- Compute Median Absolute Deviation (MAD) and flag robust outliers
            -- MAD = MEDIAN( |x - MEDIAN(x)| )
            WITH med AS (
                SELECT MEDIAN(amount) AS overall_median
                FROM payment_volumes
            ),
            deviations AS (
                SELECT 
                    p.tx_id,
                    p.amount,
                    m.overall_median,
                    ABS(p.amount - m.overall_median) AS abs_deviation
                FROM payment_volumes p
                CROSS JOIN med m
            ),
            mad_val AS (
                SELECT MEDIAN(abs_deviation) AS mad_score
                FROM deviations
            )
            SELECT 
                d.tx_id,
                d.amount,
                d.overall_median,
                ROUND(d.abs_deviation / NULLIF(v.mad_score, 0), 2) AS robust_mad_score,
                CASE 
                    WHEN (d.abs_deviation / NULLIF(v.mad_score, 0)) > 3.0 
                    THEN 'ROBUST_OUTLIER' 
                    ELSE 'NORMAL' 
                END AS anomaly_flag
            FROM deviations d
            CROSS JOIN mad_val v
            ORDER BY robust_mad_score DESC;
        """
    },
    {
        "id": "Q95_robust_z_score_iqr_normalization",
        "title": "Robust Z-Score Normalization using Median and Interquartile Range (IQR)",
        "domain": "Warehouse & Statistical",
        "human_context": "Standardizing skewed metrics (like API response latency) for machine learning feature pipelines requires scaling by IQR (Q3 - Q1) rather than standard deviation.",
        "hidden_trap": "Standard Z-score produces biased features when distributions have heavy tails.",
        "duckdb_advantage": "DuckDB percentile functions (`QUANTILE_CONT`) compute exact quartiles in a single scan.",
        "setup_sql": """
            CREATE TABLE response_times (
                request_id INT,
                latency_ms DOUBLE
            );
            INSERT INTO response_times VALUES
                (1, 45.0), (2, 50.0), (3, 52.0), (4, 48.0), (5, 300.0);
        """,
        "sql": """
            -- Compute robust IQR-normalized score: (x - Q2) / (Q3 - Q1)
            WITH quartiles AS (
                SELECT 
                    QUANTILE_CONT(latency_ms, 0.25) AS q1,
                    QUANTILE_CONT(latency_ms, 0.50) AS median_val,
                    QUANTILE_CONT(latency_ms, 0.75) AS q3
                FROM response_times
            )
            SELECT 
                r.request_id,
                r.latency_ms,
                ROUND((r.latency_ms - q.median_val) / NULLIF(q.q3 - q.q1, 0), 3) AS robust_iqr_z_score
            FROM response_times r
            CROSS JOIN quartiles q
            ORDER BY robust_iqr_z_score DESC;
        """
    },
    {
        "id": "Q96_window_frame_range_vs_rows_ties",
        "title": "Financial Ledger Running Total: ROWS vs. RANGE Semantic Contrast",
        "domain": "Warehouse & Statistical",
        "human_context": "In financial auditing, understanding the exact behavioral difference between `ROWS BETWEEN` and `RANGE BETWEEN` prevents duplicate-timestamp errors from failing regulatory ledger reconciliations.",
        "hidden_trap": "The ANSI SQL default for window frames with ORDER BY is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, which aggregates identical peers together into one lump sum.",
        "duckdb_advantage": "DuckDB provides explicit window execution options and deterministic ordering.",
        "setup_sql": """
            CREATE TABLE audit_ledger (
                tx_id INT,
                val_date DATE,
                amount DECIMAL(10,2)
            );
            INSERT INTO audit_ledger VALUES
                (1, '2026-03-01', 100.00),
                (2, '2026-03-01', 50.00),  -- Same date!
                (3, '2026-03-02', 20.00);
        """,
        "sql": """
            -- Compare the difference between default RANGE (peer bunching) vs ROWS (strict sequential)
            SELECT 
                tx_id,
                val_date,
                amount,
                -- Default RANGE behavior: bunches tied dates together ($150 on row 1 and 2)
                SUM(amount) OVER (
                    ORDER BY val_date
                    RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS bunched_range_total,
                -- Explicit ROWS behavior: increments strictly row by row ($100 then $150)
                SUM(amount) OVER (
                    ORDER BY val_date, tx_id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS strict_rows_total
            FROM audit_ledger
            ORDER BY val_date, tx_id;
        """
    },
    {
        "id": "Q97_sargable_date_boundary_pruning",
        "title": "SARGable Partition Pruning: Exact Half-Open Date Boundary Ranges",
        "domain": "Warehouse & Statistical",
        "human_context": "When filtering analytical partitions for a calendar month, `BETWEEN '2026-01-01' AND '2026-01-31'` leaks into February 1st if timestamps contain hours/minutes, while `strftime('%m', ts) = '01'` disables partition pruning entirely.",
        "hidden_trap": "Subtle boundary leakage or full table scans caused by non-SARGable WHERE predicates.",
        "duckdb_advantage": "Half-open `>= '2026-01-01' AND < '2026-02-01'` ensures exact month boundaries and 100% metadata partition pruning.",
        "setup_sql": """
            CREATE TABLE audit_events (
                event_id INT,
                created_at TIMESTAMP
            );
            INSERT INTO audit_events VALUES
                (1, '2026-01-31 23:59:59'),
                (2, '2026-02-01 00:00:00'), -- Should NOT be in January
                (3, '2026-01-15 12:00:00');
        """,
        "sql": """
            -- Exact SARGable half-open January 2026 boundary query
            SELECT 
                event_id,
                created_at
            FROM audit_events
            WHERE created_at >= TIMESTAMP '2026-01-01 00:00:00'
              AND created_at <  TIMESTAMP '2026-02-01 00:00:00'
            ORDER BY created_at;
        """
    },
    {
        "id": "Q98_window_exclude_group_moving_peer",
        "title": "Window Peer Frame Exclusion: EXCLUDE GROUP for Clean Cross-Group Contrast",
        "domain": "Warehouse & Statistical",
        "human_context": "When comparing sales across product categories or dates, analysts want to compute the average of all other groups, strictly excluding the entire current group.",
        "hidden_trap": "Computing group baselines without excluding the current group dilutes contrast in small sample sizes.",
        "duckdb_advantage": "DuckDB fully supports SQL:2011 `EXCLUDE GROUP` window syntax.",
        "setup_sql": """
            CREATE TABLE regional_orders (
                region VARCHAR,
                order_id INT,
                sale_amount DOUBLE
            );
            INSERT INTO regional_orders VALUES
                ('North', 1, 100.0),
                ('North', 2, 120.0),
                ('South', 3, 200.0),
                ('East',  4, 150.0);
        """,
        "sql": """
            -- Compute baseline average across other regions strictly excluding current region group
            SELECT 
                region,
                order_id,
                sale_amount,
                ROUND(AVG(sale_amount) OVER (
                    ORDER BY region
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
                    EXCLUDE GROUP
                ), 2) AS other_regions_baseline_avg
            FROM regional_orders
            ORDER BY region, order_id;
        """
    },
    {
        "id": "Q99_window_exclude_ties_duplicate_handling",
        "title": "Window Frame Ties Exclusion: EXCLUDE TIES for Unbiased Cumulative Totals",
        "domain": "Warehouse & Statistical",
        "human_context": "In financial ranking, when multiple entities have the exact same score, evaluating cumulative rank metrics without self-reinforcing duplicate ties prevents tied participants from skewing percentiles.",
        "hidden_trap": "Tied participants mutually inflate each other's cumulative metrics.",
        "duckdb_advantage": "DuckDB supports `EXCLUDE TIES` in window frames.",
        "setup_sql": """
            CREATE TABLE gaming_scores (
                player_id INT,
                score INT
            );
            INSERT INTO gaming_scores VALUES
                (1, 500),
                (2, 450),
                (3, 450), -- Tie
                (4, 300);
        """,
        "sql": """
            -- Calculate cumulative score excluding tied peers at the current rank
            SELECT 
                player_id,
                score,
                SUM(score) OVER (
                    ORDER BY score DESC
                    RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    EXCLUDE TIES
                ) AS cumulative_score_excluding_tied_peers
            FROM gaming_scores
            ORDER BY score DESC, player_id;
        """
    },
    {
        "id": "Q100_market_basket_association_rules",
        "title": "Market Basket Association Rules: Support, Confidence, and Lift in Pure SQL",
        "domain": "Warehouse & Statistical",
        "human_context": "Data miners discover product affinities ('Customers who buy Item A also buy Item B') using Support, Confidence, and Lift metrics computed directly from transaction tables.",
        "hidden_trap": "Generating cross-products across all transactions creates memory spills on large catalogs.",
        "duckdb_advantage": "DuckDB can evaluate pair frequency matrices and marginal probabilities in memory.",
        "setup_sql": """
            CREATE TABLE order_baskets (
                order_id INT,
                item VARCHAR
            );
            INSERT INTO order_baskets VALUES
                (1, 'Bread'), (1, 'Butter'), (1, 'Milk'),
                (2, 'Bread'), (2, 'Butter'),
                (3, 'Bread'), (3, 'Milk'),
                (4, 'Beer'),  (4, 'Diapers');
        """,
        "sql": """
            -- Compute Support, Confidence, and Lift for Item A -> Item B
            WITH basket_totals AS (
                SELECT COUNT(DISTINCT order_id) AS total_baskets FROM order_baskets
            ),
            item_counts AS (
                SELECT item, COUNT(DISTINCT order_id) AS item_baskets
                FROM order_baskets
                GROUP BY item
            ),
            pair_counts AS (
                SELECT 
                    a.item AS item_a,
                    b.item AS item_b,
                    COUNT(DISTINCT a.order_id) AS pair_baskets
                FROM order_baskets a
                JOIN order_baskets b 
                  ON a.order_id = b.order_id 
                 AND a.item != b.item
                GROUP BY a.item, b.item
            )
            SELECT 
                p.item_a,
                p.item_b,
                p.pair_baskets,
                -- Support: P(A and B)
                ROUND(p.pair_baskets * 1.0 / t.total_baskets, 3) AS support,
                -- Confidence: P(B | A) = pair / count_a
                ROUND(p.pair_baskets * 1.0 / ca.item_baskets, 3) AS confidence,
                -- Lift: Confidence / P(B) = (pair * total) / (count_a * count_b)
                ROUND((p.pair_baskets * 1.0 * t.total_baskets) / (ca.item_baskets * cb.item_baskets), 3) AS lift
            FROM pair_counts p
            JOIN item_counts ca ON p.item_a = ca.item
            JOIN item_counts cb ON p.item_b = cb.item
            CROSS JOIN basket_totals t
            WHERE p.pair_baskets >= 2
            ORDER BY lift DESC, p.item_a, p.item_b;
        """
    },
    {
        "id": "Q101_kaplan_meier_churn_survival",
        "title": "Kaplan-Meier Non-Parametric Customer Survival Analysis in SQL",
        "domain": "Warehouse & Statistical",
        "human_context": "Actuarial and SaaS subscription models estimate the probability of customer survival past Day T, accounting for right-censored users who haven't churned yet.",
        "hidden_trap": "Naively dividing churned users by total signups underestimates customer lifetime value.",
        "duckdb_advantage": "DuckDB window functions compute step-down survival curves using cumulative products.",
        "setup_sql": """
            CREATE TABLE subscription_cohort (
                user_id INT,
                tenure_months INT,
                has_churned BOOLEAN
            );
            INSERT INTO subscription_cohort VALUES
                (1, 1, true),  -- Churned at month 1
                (2, 1, false), -- Still active at month 1
                (3, 2, true),  -- Churned at month 2
                (4, 2, false),
                (5, 3, false);
        """,
        "sql": """
            -- Kaplan-Meier survival probability estimation by tenure month
            WITH monthly_risk AS (
                SELECT 
                    tenure_months,
                    COUNT(*) AS cohort_events,
                    SUM(CASE WHEN has_churned THEN 1 ELSE 0 END) AS churn_count,
                    COUNT(*) OVER (ORDER BY tenure_months DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS number_at_risk
                FROM subscription_cohort
                GROUP BY tenure_months
            )
            SELECT 
                tenure_months,
                number_at_risk,
                churn_count,
                ROUND(1.0 - (churn_count * 1.0 / number_at_risk), 4) AS interval_survival_rate
            FROM monthly_risk
            ORDER BY tenure_months;
        """
    },
    {
        "id": "Q102_equi_depth_dynamic_binning_ntile",
        "title": "Dynamic Equi-Depth Histogram Binning via NTILE in Pure SQL",
        "domain": "Warehouse & Statistical",
        "human_context": "Creating balanced feature histograms for ML requires equal-depth binning (each bucket contains an equal number of records) rather than equal-width binning.",
        "hidden_trap": "Equal-width bins leave high-value tail bins completely empty on skewed power-law distributions.",
        "duckdb_advantage": "DuckDB `NTILE()` computes equi-depth quantile bins with zero pre-scanning.",
        "setup_sql": """
            CREATE TABLE customer_spend (
                customer_id INT,
                annual_spend DECIMAL(10,2)
            );
            INSERT INTO customer_spend VALUES
                (1, 20.00), (2, 35.00), (3, 50.00), (4, 150.00),
                (5, 300.00), (6, 500.00), (7, 1200.00), (8, 5000.00);
        """,
        "sql": """
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
        """
    }
]
