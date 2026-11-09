/*
 ==============================================================================
 Query ID:         Q80_logistics_shortest_path_routing
 Title:            Lowest-Cost Routing across Logistics Hubs via Recursive Dijkstra
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 Supply chain networks ship containers through intermediary freight hubs. Finding the cheapest transit path from Source to Destination minimizes freight costs.

 The Hidden Trap:
 Evaluating all combinations without cost bounding leads to exponential path explosion.

 The DuckDB Advantage:
 DuckDB can evaluate path cost summations in recursive iterations.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
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
