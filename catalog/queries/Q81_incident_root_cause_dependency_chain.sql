/*
 ==============================================================================
 Query ID:         Q81_incident_root_cause_dependency_chain
 Title:            Causal Microservice Incident Root-Cause Dependency Chain
 Domain:           Graph & Hierarchy
 ------------------------------------------------------------------------------
 Human Context:
 When a user checkout fails, it could be caused by payments, auth, database, or network. Tracing dependencies upwards from the affected user service identifies the underlying root-cause service failure.

 The Hidden Trap:
 Diagnosing downstream symptoms rather than the root upstream failed dependency.

 The DuckDB Advantage:
 DuckDB traces dependency DAGs and joins failure logs in a single query.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
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
