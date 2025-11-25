---
title: CSV
content_type: tutorial
source_url: https://motherduck.com/glossary/CSV
indexed_at: '2025-11-25T20:03:02.497716'
content_hash: 02cb0de9e29275bf
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# CSV

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

[CSV](https://datatracker.ietf.org/doc/html/rfc4180) (Comma-Separated Values) is a simple, text-based file format used to store tabular data. Each line in a CSV file represents a row, with individual values separated by commas. This format is widely supported by spreadsheet applications, databases, and data processing tools, making it a popular choice for data exchange and storage. CSV files are human-readable and can be easily edited with a text editor.

In DuckDB, you can work with CSV files using the `read_csv` function. For example:

```sql
Copy code

SELECT * FROM read_csv('data.csv', auto_detect=true);
```

This command reads a CSV file named 'data.csv' and automatically detects the column types. CSV files are particularly useful for small to medium-sized datasets and are often used as an intermediate format in data pipelines or for data export and import operations.

Authorization Response