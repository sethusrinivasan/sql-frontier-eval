/*
 ==============================================================================
 Query ID:         Q10_peer_exclusion_moving_average
 Title:            Window Frame Exclusion: Peer Period Average via EXCLUDE CURRENT ROW
 Domain:           Temporal & Time-Series
 ------------------------------------------------------------------------------
 Human Context:
 To detect anomalous spikes, analysts compare a metric against the average of neighboring days, strictly excluding the current day's value to avoid skewing the baseline.

 The Hidden Trap:
 Computing rolling averages without excluding the current row inflates the baseline during the spike itself, hiding the anomaly.

 The DuckDB Advantage:
 DuckDB supports standard SQL:2011 window frame exclusion clauses: `EXCLUDE CURRENT ROW`.
 ==============================================================================
*/

-- ----------------------------------------------------------------------------
-- 1. SETUP DDL & FIXTURES
-- ----------------------------------------------------------------------------
CREATE TABLE daily_api_calls (
                service_id VARCHAR,
                call_date DATE,
                total_calls INT
            );
            INSERT INTO daily_api_calls VALUES
                ('auth-svc', '2026-03-01', 1000),
                ('auth-svc', '2026-03-02', 1050),
                ('auth-svc', '2026-03-03', 9500), -- Major spike
                ('auth-svc', '2026-03-04', 1020),
                ('auth-svc', '2026-03-05', 1010);

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION ANALYTICAL QUERY
-- ----------------------------------------------------------------------------
-- Calculate 5-day baseline average strictly excluding current row
            SELECT 
                service_id,
                call_date,
                total_calls,
                -- 2 days before and 2 days after, excluding current day
                ROUND(AVG(total_calls) OVER (
                    PARTITION BY service_id
                    ORDER BY call_date
                    ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING
                    EXCLUDE CURRENT ROW
                ), 2) AS peer_baseline_avg,
                -- Spikiness ratio
                ROUND(total_calls / AVG(total_calls) OVER (
                    PARTITION BY service_id
                    ORDER BY call_date
                    ROWS BETWEEN 2 PRECEDING AND 2 FOLLOWING
                    EXCLUDE CURRENT ROW
                ), 2) AS spike_factor
            FROM daily_api_calls
            ORDER BY call_date;
