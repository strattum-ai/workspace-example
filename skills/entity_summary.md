---
name: entity_summary
display_name: Entity Summary
description: Generates a comprehensive summary for any entity including relationships, timeline and key metrics.
category: context
tags: [entity, summary, context]
---

# Entity Summary

Generate a comprehensive entity summary:

1. Search for the entity: Call `search_entity(query="<entity name or id>")`

2. Get full context: Call `get_entity_context(entity_id="<id>", depth="immediate")`

3. Check for related knowledge: Call `search_knowledge(query="<entity name> policies procedures")`

4. Compile a structured summary with:
   - Entity profile (name, type, key attributes)
   - Recent timeline (last 10 events)
   - Key relationships (companies, contracts, contacts)
   - Relevant documentation found
   - Action items or open issues
