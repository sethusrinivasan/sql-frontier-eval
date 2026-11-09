# Domain 4: Graph, Hierarchy & Event Sequence Analytics (Queries 76 - 88)

GRAPH_QUERIES = [
    {
        "id": "Q76_bill_of_materials_recursive_rollup",
        "title": "Hierarchical Bill of Materials (BOM) Cost Rollup via Recursive CTE",
        "domain": "Graph & Hierarchy",
        "human_context": "Manufacturing an electric vehicle requires thousands of nested parts (Car -> Battery Pack -> Cell Module -> Lithium Cathode). Calculating unit cost requires rolling up quantities across arbitrary depth levels.",
        "hidden_trap": "Fixed joins only support fixed depth hierarchies (e.g. 3 levels max). If an assembly has 6 levels, fixed joins miss the lowest-tier parts entirely.",
        "duckdb_advantage": "DuckDB executes `WITH RECURSIVE` queries in memory with zero row-materialization overhead.",
        "setup_sql": """
            CREATE TABLE bom_parts (
                parent_part VARCHAR,
                child_part VARCHAR,
                quantity_needed INT,
                unit_cost DECIMAL(10,2)
            );
            INSERT INTO bom_parts VALUES
                ('EV_CAR', 'CHASSIS', 1, 5000.00),
                ('EV_CAR', 'BATTERY_PACK', 1, 0.00),
                ('BATTERY_PACK', 'BATTERY_MODULE', 4, 0.00),
                ('BATTERY_MODULE', 'LITHIUM_CELL', 100, 15.00);
        """,
        "sql": """
            -- Recursively expand BOM tree to compute total quantity of base components
            WITH RECURSIVE bom_tree AS (
                -- Anchor: Top-level components of EV_CAR
                SELECT 
                    parent_part,
                    child_part,
                    quantity_needed AS total_qty,
                    1 AS depth
                FROM bom_parts
                WHERE parent_part = 'EV_CAR'
                
                UNION ALL
                
                -- Recursive: Multiply quantity down the hierarchy tree
                SELECT 
                    t.child_part AS parent_part,
                    b.child_part,
                    t.total_qty * b.quantity_needed AS total_qty,
                    t.depth + 1 AS depth
                FROM bom_tree t
                JOIN bom_parts b ON t.child_part = b.parent_part
            )
            SELECT 
                child_part,
                total_qty,
                depth
            FROM bom_tree
            ORDER BY depth, child_part;
        """
    },
    {
        "id": "Q77_org_hierarchy_span_of_control",
        "title": "Organizational Reporting Depth & Management Span of Control",
        "domain": "Graph & Hierarchy",
        "human_context": "HR analytics measures how deep the management chain is from the CEO to individual contributors and calculates direct vs indirect headcounts for each manager.",
        "hidden_trap": "Unbounded recursive queries crash if there is an accidental circular reporting loop (e.g. A reports to B, B reports to A).",
        "duckdb_advantage": "DuckDB recursion tracks path depth to prevent infinite loops.",
        "setup_sql": """
            CREATE TABLE employees (
                emp_id INT,
                emp_name VARCHAR,
                manager_id INT
            );
            INSERT INTO employees VALUES
                (1, 'Alice (CEO)', NULL),
                (2, 'Bob (VP Eng)', 1),
                (3, 'Charlie (VP Sales)', 1),
                (4, 'David (Staff Eng)', 2),
                (5, 'Eve (Senior Eng)', 4);
        """,
        "sql": """
            -- Traverse management tree from CEO downward, tracking reporting depth
            WITH RECURSIVE org_hierarchy AS (
                SELECT 
                    emp_id,
                    emp_name,
                    manager_id,
                    1 AS hierarchy_level,
                    emp_name AS reporting_path
                FROM employees
                WHERE manager_id IS NULL
                
                UNION ALL
                
                SELECT 
                    e.emp_id,
                    e.emp_name,
                    e.manager_id,
                    h.hierarchy_level + 1,
                    h.reporting_path || ' -> ' || e.emp_name
                FROM employees e
                JOIN org_hierarchy h ON e.manager_id = h.emp_id
            )
            SELECT 
                emp_id,
                emp_name,
                hierarchy_level,
                reporting_path
            FROM org_hierarchy
            ORDER BY hierarchy_level, emp_id;
        """
    },
    {
        "id": "Q78_transitive_fraud_sybil_ring",
        "title": "Transitive Fraud Ring & Sybil Account Detection via Device Links",
        "domain": "Graph & Hierarchy",
        "human_context": "Financial fraudsters create hundreds of fake accounts linked by shared credit cards, device fingerprints, or IP addresses. Finding all accounts transitively connected to a confirmed fraudster exposes the syndicate.",
        "hidden_trap": "Looking only 1 hop away misses fraudsters who funnel funds through mule intermediary accounts.",
        "duckdb_advantage": "DuckDB recursive CTEs trace transitive graph edges across multiple hops.",
        "setup_sql": """
            CREATE TABLE shared_identifiers (
                account_id INT,
                linked_account_id INT
            );
            INSERT INTO shared_identifiers VALUES
                (101, 102), -- 101 shares credit card with 102
                (102, 103), -- 102 shares device with 103
                (103, 104), -- 103 shares bank account with 104
                (201, 202); -- Separate cluster
        """,
        "sql": """
            -- Find all accounts transitively linked to known bad actor 101
            WITH RECURSIVE fraud_cluster AS (
                SELECT 
                    101 AS seed_account,
                    linked_account_id AS connected_account,
                    1 AS hop_distance
                FROM shared_identifiers
                WHERE account_id = 101
                
                UNION ALL
                
                SELECT 
                    c.seed_account,
                    s.linked_account_id,
                    c.hop_distance + 1
                FROM fraud_cluster c
                JOIN shared_identifiers s ON c.connected_account = s.account_id
                WHERE c.hop_distance < 5
            )
            SELECT DISTINCT 
                seed_account,
                connected_account,
                MIN(hop_distance) AS shortest_hop_distance
            FROM fraud_cluster
            GROUP BY seed_account, connected_account
            ORDER BY shortest_hop_distance;
        """
    },
    {
        "id": "Q79_graph_cycle_detection_visited_array",
        "title": "Cycle Detection in Directed Dependency Graphs with Visited Array",
        "domain": "Graph & Hierarchy",
        "human_context": "In build systems (e.g. Webpack, Bazel) or task scheduling, circular dependencies (Task A -> Task B -> Task A) cause deadlocks. The engine must detect cycles and abort gracefully.",
        "hidden_trap": "Standard recursive CTEs without cycle tracking loop infinitely until the database crashes with out-of-memory errors.",
        "duckdb_advantage": "DuckDB array lists (`list_contains`) allow tracking visited paths directly inside recursive CTE state.",
        "setup_sql": """
            CREATE TABLE task_dependencies (
                task_id VARCHAR,
                depends_on VARCHAR
            );
            INSERT INTO task_dependencies VALUES
                ('compile', 'codegen'),
                ('codegen', 'lint'),
                ('lint', 'compile'); -- Circular cycle!
        """,
        "sql": """
            -- Detect circular loops using array path tracking
            WITH RECURSIVE path_finder AS (
                SELECT 
                    task_id,
                    depends_on,
                    [task_id] AS visited_path,
                    false AS has_cycle
                FROM task_dependencies
                
                UNION ALL
                
                SELECT 
                    p.task_id,
                    d.depends_on,
                    list_append(p.visited_path, d.task_id),
                    list_contains(p.visited_path, d.depends_on) AS has_cycle
                FROM path_finder p
                JOIN task_dependencies d ON p.depends_on = d.task_id
                WHERE NOT p.has_cycle AND array_length(p.visited_path) < 10
            )
            SELECT 
                task_id,
                depends_on,
                visited_path,
                has_cycle
            FROM path_finder
            WHERE has_cycle = true
            LIMIT 1;
        """
    },
    {
        "id": "Q80_logistics_shortest_path_routing",
        "title": "Lowest-Cost Routing across Logistics Hubs via Recursive Dijkstra",
        "domain": "Graph & Hierarchy",
        "human_context": "Supply chain networks ship containers through intermediary freight hubs. Finding the cheapest transit path from Source to Destination minimizes freight costs.",
        "hidden_trap": "Evaluating all combinations without cost bounding leads to exponential path explosion.",
        "duckdb_advantage": "DuckDB can evaluate path cost summations in recursive iterations.",
        "setup_sql": """
            CREATE TABLE shipping_lanes (
                origin VARCHAR,
                destination VARCHAR,
                cost DOUBLE
            );
            INSERT INTO shipping_lanes VALUES
                ('SEA', 'ORD', 400.0),
                ('ORD', 'JFK', 300.0),
                ('SEA', 'DEN', 200.0),
                ('DEN', 'JFK', 450.0);
        """,
        "sql": """
            -- Find lowest cost route from Seattle ('SEA') to New York ('JFK')
            WITH RECURSIVE routes AS (
                SELECT 
                    origin,
                    destination,
                    cost AS total_cost,
                    origin || ' -> ' || destination AS route_path,
                    1 AS hops
                FROM shipping_lanes
                WHERE origin = 'SEA'
                
                UNION ALL
                
                SELECT 
                    r.origin,
                    l.destination,
                    r.total_cost + l.cost AS total_cost,
                    r.route_path || ' -> ' || l.destination,
                    r.hops + 1
                FROM routes r
                JOIN shipping_lanes l ON r.destination = l.origin
                WHERE r.hops < 4
            )
            SELECT 
                origin,
                destination,
                total_cost,
                route_path,
                hops
            FROM routes
            WHERE destination = 'JFK'
            ORDER BY total_cost ASC
            LIMIT 1;
        """
    },
    {
        "id": "Q81_incident_root_cause_dependency_chain",
        "title": "Causal Microservice Incident Root-Cause Dependency Chain",
        "domain": "Graph & Hierarchy",
        "human_context": "When a user checkout fails, it could be caused by payments, auth, database, or network. Tracing dependencies upwards from the affected user service identifies the underlying root-cause service failure.",
        "hidden_trap": "Diagnosing downstream symptoms rather than the root upstream failed dependency.",
        "duckdb_advantage": "DuckDB traces dependency DAGs and joins failure logs in a single query.",
        "setup_sql": """
            CREATE TABLE service_mesh (
                service VARCHAR,
                depends_on VARCHAR
            );
            CREATE TABLE service_alerts (
                service VARCHAR,
                status VARCHAR,
                error_rate DOUBLE
            );
            INSERT INTO service_mesh VALUES
                ('checkout-api', 'payment-gateway'),
                ('payment-gateway', 'fraud-evaluator'),
                ('fraud-evaluator', 'redis-cache');
            INSERT INTO service_alerts VALUES
                ('checkout-api', 'DEGRADED', 0.15),
                ('payment-gateway', 'DEGRADED', 0.20),
                ('fraud-evaluator', 'DEGRADED', 0.85),
                ('redis-cache', 'CRITICAL_DOWN', 1.00);
        """,
        "sql": """
            -- Trace dependencies backwards from checkout-api to find root critical failure
            WITH RECURSIVE upstream_chain AS (
                SELECT 
                    service,
                    depends_on,
                    1 AS depth
                FROM service_mesh
                WHERE service = 'checkout-api'
                
                UNION ALL
                
                SELECT 
                    m.service,
                    m.depends_on,
                    c.depth + 1
                FROM upstream_chain c
                JOIN service_mesh m ON c.depends_on = m.service
            )
            SELECT 
                c.depth,
                c.service,
                c.depends_on AS upstream_service,
                a.status AS upstream_status,
                a.error_rate AS upstream_error_rate
            FROM upstream_chain c
            JOIN service_alerts a ON c.depends_on = a.service
            ORDER BY c.depth DESC
            LIMIT 1;
        """
    },
    {
        "id": "Q82_connected_components_community_labeling",
        "title": "Graph Connected Components Labeling via Min-ID Propagation",
        "domain": "Graph & Hierarchy",
        "human_context": "Graph connected components partition isolated clusters of customers or machines. Propagating the minimum account ID across edges assigns every node in the same component a shared group ID.",
        "hidden_trap": "Standard SQL engines lack graph primitives, forcing expensive external graph database licenses.",
        "duckdb_advantage": "DuckDB can evaluate recursive label propagation directly on relational tables.",
        "setup_sql": """
            CREATE TABLE graph_edges (
                node_a INT,
                node_b INT
            );
            -- Component 1: Nodes 1, 2, 3
            -- Component 2: Nodes 8, 9
            INSERT INTO graph_edges VALUES
                (1, 2), (2, 3),
                (8, 9);
        """,
        "sql": """
            -- Symmetric edges
            WITH RECURSIVE symmetric_edges AS (
                SELECT node_a AS src, node_b AS dst FROM graph_edges
                UNION
                SELECT node_b AS src, node_a AS dst FROM graph_edges
            ),
            components AS (
                -- Anchor: Initial component label is node itself
                SELECT src AS node_id, src AS component_id, 0 AS iteration
                FROM symmetric_edges
                
                UNION ALL
                
                -- Propagate smaller component ID across edges
                SELECT 
                    e.dst AS node_id,
                    c.component_id,
                    c.iteration + 1
                FROM components c
                JOIN symmetric_edges e ON c.node_id = e.src
                WHERE c.component_id < e.dst AND c.iteration < 5
            )
            SELECT 
                node_id,
                MIN(component_id) AS cluster_id
            FROM components
            GROUP BY node_id
            ORDER BY cluster_id, node_id;
        """
    },
    {
        "id": "Q83_degree_centrality_pagerank_step",
        "title": "Network Node In-Degree Centrality and Influence Ranking",
        "domain": "Graph & Hierarchy",
        "human_context": "Social network influence and API hub criticality are determined by node in-degree centrality (number of inbound links from distinct entities).",
        "hidden_trap": "Counting total edges without filtering distinct source nodes allows a single spammer to inflate influencer metrics.",
        "duckdb_advantage": "DuckDB aggregates high-volume graph degree metrics with high-speed hash grouping.",
        "setup_sql": """
            CREATE TABLE network_follows (
                follower_id INT,
                target_user_id INT
            );
            INSERT INTO network_follows VALUES
                (101, 1), (102, 1), (103, 1), (104, 1), -- Node 1 has 4 followers
                (101, 2), (102, 2),                     -- Node 2 has 2 followers
                (101, 3);                               -- Node 3 has 1 follower
        """,
        "sql": """
            -- Compute in-degree centrality and influence rank
            SELECT 
                target_user_id AS influencer_id,
                COUNT(DISTINCT follower_id) AS in_degree_centrality,
                DENSE_RANK() OVER (ORDER BY COUNT(DISTINCT follower_id) DESC) AS influence_rank
            FROM network_follows
            GROUP BY target_user_id
            ORDER BY influence_rank;
        """
    },
    {
        "id": "Q84_critical_path_method_scheduling",
        "title": "Task Scheduling Critical Path Method (CPM) Duration Analysis",
        "domain": "Graph & Hierarchy",
        "human_context": "Project managers identify the 'Critical Path'—the longest sequence of dependent tasks that dictates the minimum project completion time.",
        "hidden_trap": "Adding task durations without considering parallel execution branches yields an unrealistically inflated project timeline.",
        "duckdb_advantage": "DuckDB recursive CTEs trace parallel branch durations and calculate maximum path length.",
        "setup_sql": """
            CREATE TABLE project_tasks (
                task_code VARCHAR,
                prerequisite_code VARCHAR,
                duration_days INT
            );
            INSERT INTO project_tasks VALUES
                ('START', NULL, 0),
                ('DESIGN', 'START', 10),
                ('BUILD_FRONTEND', 'DESIGN', 15),
                ('BUILD_BACKEND',  'DESIGN', 25), -- Longest branch
                ('DEPLOY', 'BUILD_BACKEND', 5);
        """,
        "sql": """
            -- Find the longest path (Critical Path) from START to DEPLOY
            WITH RECURSIVE task_paths AS (
                SELECT 
                    task_code,
                    duration_days AS cumulative_days,
                    task_code AS path_str
                FROM project_tasks
                WHERE prerequisite_code IS NULL
                
                UNION ALL
                
                SELECT 
                    t.task_code,
                    p.cumulative_days + t.duration_days,
                    p.path_str || ' -> ' || t.task_code
                FROM task_paths p
                JOIN project_tasks t ON p.task_code = t.prerequisite_code
            )
            SELECT 
                task_code,
                cumulative_days AS critical_path_duration,
                path_str
            FROM task_paths
            ORDER BY cumulative_days DESC
            LIMIT 1;
        """
    },
    {
        "id": "Q85_multilevel_referral_commissions",
        "title": "Multi-Level Affiliate Referral Tree Commission Rollup (Tier 1-3)",
        "domain": "Graph & Hierarchy",
        "human_context": "Affiliate programs reward referrals up to 3 tiers deep (Direct referrer gets 10%, Tier 2 gets 5%, Tier 3 gets 2.5% of purchase amount).",
        "hidden_trap": "Hardcoded 3-way self-joins fail to handle users whose upline is only 1 or 2 tiers deep without complex coalesce logic.",
        "duckdb_advantage": "DuckDB recursive CTEs assign dynamic commission percentages based on recursion depth.",
        "setup_sql": """
            CREATE TABLE referral_links (
                user_id INT,
                referrer_id INT
            );
            CREATE TABLE user_purchases (
                purchase_id INT,
                user_id INT,
                amount DECIMAL(10,2)
            );
            INSERT INTO referral_links VALUES
                (4, 3), -- 4 referred by 3
                (3, 2), -- 3 referred by 2
                (2, 1); -- 2 referred by 1 (Grandparent)
            INSERT INTO user_purchases VALUES
                (101, 4, 1000.00); -- Purchase by user 4
        """,
        "sql": """
            -- Calculate multi-tier referral payout for purchase 101
            WITH RECURSIVE upline AS (
                -- Level 1: Direct referrer
                SELECT 
                    r.user_id AS buyer_id,
                    r.referrer_id AS beneficiary_id,
                    1 AS tier,
                    0.10 AS commission_rate
                FROM referral_links r
                WHERE r.user_id = 4
                
                UNION ALL
                
                -- Level 2 and 3 upline
                SELECT 
                    u.buyer_id,
                    r.referrer_id AS beneficiary_id,
                    u.tier + 1,
                    CASE WHEN u.tier + 1 = 2 THEN 0.05 ELSE 0.025 END AS commission_rate
                FROM upline u
                JOIN referral_links r ON u.beneficiary_id = r.user_id
                WHERE u.tier < 3
            )
            SELECT 
                u.buyer_id,
                u.beneficiary_id,
                u.tier,
                p.amount AS purchase_amount,
                ROUND(p.amount * u.commission_rate, 2) AS commission_earned
            FROM upline u
            JOIN user_purchases p ON u.buyer_id = p.user_id
            ORDER BY u.tier;
        """
    },
    {
        "id": "Q86_multiparent_allocation_cost_rollup",
        "title": "Multi-Parent Shared Infrastructure Cost Allocation Rollup",
        "domain": "Graph & Hierarchy",
        "human_context": "Cloud infrastructure (e.g. shared Kubernetes cluster) is co-owned by multiple products with fractional split percentages. Costs must cascade down to consumer business units.",
        "hidden_trap": "Failing to multiply split percentages down the DAG results in allocated costs exceeding 100% of actual spend.",
        "duckdb_advantage": "DuckDB calculates fractional cost propagation with exact decimal precision.",
        "setup_sql": """
            CREATE TABLE cost_nodes (
                node_id VARCHAR,
                monthly_cost DECIMAL(10,2)
            );
            CREATE TABLE cost_allocations (
                parent_node VARCHAR,
                child_node VARCHAR,
                allocation_pct DOUBLE
            );
            INSERT INTO cost_nodes VALUES ('K8S_SHARED', 10000.00);
            INSERT INTO cost_allocations VALUES
                ('K8S_SHARED', 'PRODUCT_SEARCH', 0.60),
                ('K8S_SHARED', 'PRODUCT_CHECKOUT', 0.40);
        """,
        "sql": """
            -- Allocate parent cost to child business units
            SELECT 
                a.parent_node,
                a.child_node,
                a.allocation_pct,
                n.monthly_cost AS raw_parent_cost,
                ROUND(n.monthly_cost * a.allocation_pct, 2) AS allocated_cost
            FROM cost_allocations a
            JOIN cost_nodes n ON a.parent_node = n.node_id
            ORDER BY allocated_cost DESC;
        """
    },
    {
        "id": "Q87_circular_fx_arbitrage_triangle",
        "title": "Triangular FX Currency Arbitrage Detection (Loop Profitability)",
        "domain": "Graph & Hierarchy",
        "human_context": "High-frequency FX trading bots scan for triangular arbitrage where converting USD -> EUR -> JPY -> USD yields more than 1.00 USD after exchange rates.",
        "hidden_trap": "Missing currency conversion bid-ask spreads causes false positive arbitrage signals that lose money in practice.",
        "duckdb_advantage": "DuckDB evaluates 3-hop currency cycles and product rates in sub-millisecond execution.",
        "setup_sql": """
            CREATE TABLE fx_pairs (
                from_curr VARCHAR,
                to_curr VARCHAR,
                exchange_rate DOUBLE
            );
            INSERT INTO fx_pairs VALUES
                ('USD', 'EUR', 0.92),
                ('EUR', 'JPY', 160.0),
                ('JPY', 'USD', 0.0069); -- Arbitrage loop: 0.92 * 160 * 0.0069 = 1.01568 (+1.5% profit)
        """,
        "sql": """
            -- Detect 3-hop triangular arbitrage opportunities where effective rate > 1.005
            SELECT 
                a.from_curr AS curr_start,
                a.to_curr AS curr_mid1,
                b.to_curr AS curr_mid2,
                c.to_curr AS curr_end,
                ROUND(a.exchange_rate * b.exchange_rate * c.exchange_rate, 4) AS loop_multiplier,
                ROUND((a.exchange_rate * b.exchange_rate * c.exchange_rate - 1.0) * 100, 2) AS profit_margin_pct
            FROM fx_pairs a
            JOIN fx_pairs b ON a.to_curr = b.from_curr
            JOIN fx_pairs c ON b.to_curr = c.from_curr AND c.to_curr = a.from_curr
            WHERE (a.exchange_rate * b.exchange_rate * c.exchange_rate) > 1.005;
        """
    },
    {
        "id": "Q88_state_machine_transition_verification",
        "title": "Transactional State Machine Transition Sequence Verification",
        "domain": "Graph & Hierarchy",
        "human_context": "Financial compliance requires payment transactions to strictly follow the state sequence: INITIATED -> AUTHORIZED -> CAPTURED -> SETTLED. Any transaction skipping steps is flagged as fraudulent.",
        "hidden_trap": "Verifying status counts without checking transition sequence allows out-of-order state transitions.",
        "duckdb_advantage": "DuckDB LEAD/LAG checks verify exact valid transition edges against a legal state graph.",
        "setup_sql": """
            CREATE TABLE payment_status_audit (
                tx_id INT,
                step_order INT,
                status VARCHAR
            );
            -- Valid tx 1
            INSERT INTO payment_status_audit VALUES
                (1, 1, 'INITIATED'), (1, 2, 'AUTHORIZED'), (1, 3, 'CAPTURED');
            -- Invalid tx 2: Jumped directly from INITIATED to CAPTURED!
            INSERT INTO payment_status_audit VALUES
                (2, 1, 'INITIATED'), (2, 2, 'CAPTURED');
        """,
        "sql": """
            -- Validate that every state transition matches the legal state machine rules
            WITH transitions AS (
                SELECT 
                    tx_id,
                    status AS current_state,
                    LEAD(status) OVER (PARTITION BY tx_id ORDER BY step_order) AS next_state
                FROM payment_status_audit
            )
            SELECT 
                tx_id,
                current_state,
                next_state,
                CASE 
                    WHEN next_state IS NULL THEN 'TERMINAL_STATE'
                    WHEN current_state = 'INITIATED' AND next_state = 'AUTHORIZED' THEN 'VALID'
                    WHEN current_state = 'AUTHORIZED' AND next_state = 'CAPTURED' THEN 'VALID'
                    WHEN current_state = 'CAPTURED' AND next_state = 'SETTLED' THEN 'VALID'
                    ELSE 'INVALID_ILLEGAL_STATE_JUMP'
                END AS audit_validation_result
            FROM transitions
            ORDER BY tx_id, current_state;
        """
    }
]
