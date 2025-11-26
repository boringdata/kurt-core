---
title: result
content_type: tutorial
source_url: https://motherduck.com/glossary/result
indexed_at: '2025-11-25T20:02:31.543149'
content_hash: c63243956aacd86c
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# result

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

The `result` keyword in SQL is not commonly used across all database systems, but in DuckDB, it has a specific meaning within the context of recursive queries. When writing a recursive Common Table Expression (CTE), `result` is used to reference the output of the previous iteration of the recursive part. This allows you to build upon the results of each recursive step.

Here's an example using DuckDB to generate a sequence of numbers:

```sql
Copy code

WITH RECURSIVE countdown(n) AS (
    SELECT 5 AS n  -- Base case
    UNION ALL
    SELECT n - 1   -- Recursive case
    FROM result    -- 'result' refers to the previous iteration
    WHERE n > 0
)
SELECT * FROM countdown;
```

This query will produce:

```yaml
Copy code

 n
---
 5
 4
 3
 2
 1
```

The `result` keyword helps create powerful recursive queries for tasks like traversing hierarchical data structures or generating sequences. It's important to note that not all database systems use `result` in this way, so this usage is specific to DuckDB's implementation of recursive CTEs.

Authorization Response