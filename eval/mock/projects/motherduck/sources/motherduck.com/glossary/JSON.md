---
title: JSON
content_type: tutorial
source_url: https://motherduck.com/glossary/JSON
indexed_at: '2025-11-25T20:02:26.371471'
content_hash: ceab348702709c79
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# JSON

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

[JSON](https://www.json.org/json-en.html) (JavaScript Object Notation) is a lightweight, text-based data interchange format that's easy for humans to read and write, and simple for machines to parse and generate. It consists of two primary structures: objects (enclosed in curly braces) containing key-value pairs, and arrays (enclosed in square brackets) of values. JSON supports basic data types like strings, numbers, booleans, and null, making it versatile for representing structured data. While originally derived from JavaScript, JSON is language-independent and widely used for data exchange in web applications, APIs, and configuration files. In the context of data engineering, JSON is often used for storing semi-structured data in databases or as an intermediate format in data pipelines.

DuckDB provides built-in support for working with JSON data. Here's an example of querying JSON data in DuckDB:

```sql
Copy code

-- Create a table with a JSON column
CREATE TABLE users (id INTEGER, data JSON);

-- Insert some JSON data
INSERT INTO users VALUES
  (1, '{"name": "Alice", "age": 30, "hobbies": ["reading", "hiking"]}'),
  (2, '{"name": "Bob", "age": 25, "hobbies": ["gaming", "cooking"]}');

-- Query JSON data
SELECT id, data->>'name' AS name, data->>'age' AS age
FROM users
WHERE CAST(data->>'age' AS INTEGER) > 25;
```

This example demonstrates creating a table with a JSON column, inserting JSON data, and then querying specific fields from the JSON structure.

Authorization Response