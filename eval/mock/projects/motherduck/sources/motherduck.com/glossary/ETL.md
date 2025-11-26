---
title: ETL
content_type: tutorial
source_url: https://motherduck.com/glossary/ETL
indexed_at: '2025-11-25T20:02:50.054800'
content_hash: ee9b9b81d61b1709
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# ETL

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

## Overview

ETL (Extract, Transform, Load) is a data integration process that combines data from multiple sources into a single destination, typically a data warehouse or database. The process has been a cornerstone of data engineering since the 1970s and remains fundamental to modern data pipelines.

## Process Components

During the Extract phase, data is copied from source systems like databases, APIs, files, or applications. This raw data might come from [Salesforce](https://www.salesforce.com/), [PostgreSQL](https://www.postgresql.org/) databases, CSV files, or countless other sources.

The Transform phase cleanses and restructures the extracted data to fit the target system's requirements. Common transformations include:

- Converting data types (like changing dates from strings to proper date formats)
- Aggregating or summarizing data
- Joining data from multiple sources
- Filtering out unwanted records
- Standardizing values (like converting all state codes to uppercase)

Finally, the Load phase writes the transformed data into the destination system, which could be a data warehouse like [Snowflake](https://www.snowflake.com/) or a database like DuckDB.

## Modern Context

While traditional ETL tools like [Informatica](https://www.informatica.com/) required data to be transformed before loading, modern data platforms often use ELT (Extract, Load, Transform) instead, where data is loaded into the destination before transformation. This approach, enabled by powerful cloud data warehouses, provides more flexibility and allows for easier debugging and data lineage tracking.

Tools like [dbt](https://www.getdbt.com/) have popularized the ELT approach by making it easier for data teams to transform data using SQL after it's been loaded into their data warehouse.

## DuckDB Example

Here's a simple ETL process using DuckDB:

```sql
Copy code

-- Extract: Read from CSV file
CREATE TABLE raw_sales AS
SELECT * FROM read_csv_auto('sales.csv');

-- Transform: Clean and aggregate data
CREATE TABLE transformed_sales AS
SELECT
    date_trunc('month', sale_date) as month,
    region,
    SUM(amount) as total_sales,
    COUNT(*) as transaction_count
FROM raw_sales
WHERE amount > 0
GROUP BY 1, 2;

-- Load: Write to Parquet file for downstream use
COPY transformed_sales TO 'monthly_sales.parquet' (FORMAT PARQUET);
```

Authorization Response