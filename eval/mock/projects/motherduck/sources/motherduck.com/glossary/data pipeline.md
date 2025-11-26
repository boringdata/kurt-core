---
title: data pipeline
content_type: tutorial
source_url: https://motherduck.com/glossary/data pipeline
indexed_at: '2025-11-25T20:02:27.790201'
content_hash: ae7b58007212a97b
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# data pipeline

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

A data pipeline is a series of interconnected processes that extract data from various sources, transform it into a usable format, and load it into a destination system for analysis or storage. It automates the flow of data through different stages, ensuring data is cleaned, validated, and prepared for consumption by downstream applications or users. Modern data pipelines often incorporate tools like [Apache Airflow](https://airflow.apache.org/) for orchestration, [dbt](https://www.getdbt.com/) for transformation, and [Fivetran](https://www.fivetran.com/) for data extraction. These pipelines can handle both batch and real-time data processing, enabling organizations to make data-driven decisions based on up-to-date information. In the context of DuckDB, you might create a simple data pipeline using SQL to extract data from a CSV file, transform it, and load it into a table:

```sql
Copy code

-- Extract data from CSV
CREATE TABLE raw_data AS SELECT * FROM read_csv_auto('data.csv');

-- Transform data
CREATE TABLE transformed_data AS
SELECT
    id,
    UPPER(name) AS name,
    CASE
        WHEN age < 18 THEN 'Minor'
        ELSE 'Adult'
    END AS age_category
FROM raw_data;

-- Load data into final table
CREATE TABLE final_table AS SELECT * FROM transformed_data;
```

This example demonstrates a basic Extract, Transform, Load (ETL) process within DuckDB.

Authorization Response