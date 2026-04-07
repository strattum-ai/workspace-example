---
name: portfolio_insights
display_name: Portfolio Insights
description: Analyzes the complete client portfolio, identifying top clients, growth patterns, and anomalies.
category: analytics
tags: [portfolio, clients, analytics]
---

# Portfolio Insights

You are analyzing the client portfolio. Follow these steps:

1. First, get the data schema to understand what entity types are available:
   - Call `get_schema()` to see graph nodes, edges and available tables

2. Query the graph for top clients:
   - Call `run_cypher("MATCH (c:Customer) RETURN c.name, c.external_id, c.created_at ORDER BY c.created_at DESC LIMIT 20")`

3. Look for clients with recent activity:
   - Call `run_cypher("MATCH (c:Customer)-[r]->() WHERE r.timestamp > datetime() - duration('P30D') RETURN c.name, type(r), count(r) as activity ORDER BY activity DESC LIMIT 10")`

4. Synthesize findings into a concise report with:
   - Total client count
   - Top 5 most active clients
   - Notable patterns or anomalies
   - Recommended next actions
