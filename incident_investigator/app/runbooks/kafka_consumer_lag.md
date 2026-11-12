# Runbook: Kafka Consumer Lag & Poison Pill Rebalance Loop

**Service:** billing-consumer  
**Severity:** P1  
**Category:** CONSUMER_REBALANCE_LOOP  

## Symptoms
- Alert: `KafkaConsumerLagCritical` (> 1,000,000 unread messages).
- Billing events processing throughput drops to 0 events/sec.
- Frequent consumer group rebalances logged continuously.

## Diagnostic Steps
1. Query `kafka_consumergroup_lag` metric per partition for topic `billing-events`.
2. Search consumer logs for `CommitFailedException` and `max.poll.interval.ms exceeded`.
3. Look for poison pill message errors where payload parsing hangs or throws unhandled format exception.
4. Check consumer heartbeat and rebalance frequency metrics.

## Root Cause Patterns
- Single malformed message triggers continuous processing timeout (> 300s), causing broker to evict consumer.
- Repeated eviction triggers infinite rebalance loop across all consumer group instances.

## Mitigation
1. Seek consumer offset past poison pill message or route malformed offset to Dead Letter Queue (DLQ).
2. Increase `max.poll.interval.ms` from 300000 to 600000.
3. Deploy consumer hotfix with defensive JSON schema validation and try-catch around message deserialization.
