---
name: churn_analysis
display_name: Churn Risk Analysis
description: Identifies clients at risk of churning based on activity patterns and relationship signals.
category: analytics
tags: [churn, risk, clients]
---

# Churn Risk Analysis

Identify clients at risk of churning:

1. Get schema: Call `get_schema()` to understand available data

2. Find inactive clients:
   - Call `run_cypher("MATCH (c:Customer) WHERE NOT (c)-[]-() OR NOT exists(c.last_activity) RETURN c.name, c.external_id, c.created_at LIMIT 20")`

3. Look for negative signals:
   - Call `run_cypher("MATCH (c:Customer)-[r:HAS_TICKET|HAS_COMPLAINT]->(t) RETURN c.name, count(t) as issues ORDER BY issues DESC LIMIT 10")`

4. Synthesize a churn risk report with:
   - High risk clients (immediate attention needed)
   - Medium risk clients (monitor closely)
   - Recommended interventions per client
