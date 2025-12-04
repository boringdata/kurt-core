---
title: duckdb-book-summary-chapter3
content_type: tutorial
source_url: https://motherduck.com/duckdb-book-summary-chapter3
indexed_at: '2025-11-25T20:22:08.162242'
content_hash: 3b8b04c027af10a0
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

Read the ebook

[BACK TO TABLE OF CONTENTS](https://motherduck.com/duckdb-book-brief/#chapter-list)

Chapter 3

2 min read

# Executing SQL Queries

This is a summary of a book chapter from _DuckDB in Action_, published by Manning. [Download the complete book](https://motherduck.com/duckdb-book-brief) for free to read the complete chapter.

!['DuckDB In Action' book cover](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fduckdb-book-cover.622bc1e1.png&w=3840&q=75)

## 3.1 A Quick SQL Recap

SQL queries in DuckDB are constructed from statements and clauses, terminated with semicolons. DuckDB handles whitespace flexibly, allowing for both compact and formatted queries. Case-insensitivity simplifies keyword and identifier usage. DuckDB's SQL dialect incorporates clauses like WHERE, GROUP BY, and ORDER BY to refine query results. WHERE filters rows based on conditions, GROUP BY aggregates values into buckets defined by keys, and ORDER BY dictates the result sequence. These fundamental concepts are illustrated using a real-world example of analyzing energy production data.

## 3.2 Analyzing Energy Production

This chapter utilizes a real-world dataset of photovoltaic energy production from the US Department of Energy's Photovoltaic Data Acquisition (PVDAQ) project. The dataset, chosen for its accessibility and complexity, mirrors real-world analytical challenges, including data inconsistencies. The analysis focuses on practical applications like planning electricity usage and forecasting amortization, demonstrating DuckDB's capabilities for generating insightful reports from this data.

## 3.3 Data Definition Language (DDL) Queries

DuckDB, as a relational database management system (RDBMS), uses Data Definition Language (DDL) queries to define and manage the database schema. This involves using `CREATE TABLE` to define new tables with specified columns and data types, `ALTER TABLE` to modify existing table structures, and `DROP TABLE` to remove tables. Understanding these DDL commands is crucial for organizing and maintaining the database structure effectively.

## 3.4 Data Manipulation Language (DML) Queries

DML queries in DuckDB encompass actions that manipulate data within the database, including `INSERT`, `DELETE`, and `SELECT`.

### INSERT statement

The `INSERT` statement adds new data to a table.

### DELETE statement

The `DELETE` statement removes existing data from a table based on conditions.

### SELECT statement

The `SELECT` statement retrieves specific data specified which matches criteria in a `WHERE` statement and aggregates data according to a `GROUP BY` statement.

These DML queries are fundamental for interacting with the data stored within the defined database schema.

## 3.5 DuckDB-Specific SQL Extensions

DuckDB enhances SQL's usability with extensions that streamline common tasks. `SELECT * EXCLUDE()` refines queries by specifying columns to omit, while `SELECT * REPLACE()` modifies column output without altering the original query structure. DuckDB also simplifies column selection and filtering using regular expressions within the COLUMNS expression, enhancing query flexibility and readability.

!['DuckDB In Action' book cover](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fduckdb-book-cover.622bc1e1.png&w=3840&q=75)

Get your free book!

E-mail

Subscribe to MotherDuck news

Subscribe to DuckDB ecosystem newsletter

Download Book

Authorization Response