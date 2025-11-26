---
title: duckdb-book-summary-chapter2
content_type: tutorial
source_url: https://motherduck.com/duckdb-book-summary-chapter2
indexed_at: '2025-11-25T20:22:14.105686'
content_hash: beababf601bf00c2
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

Read the ebook

[BACK TO TABLE OF CONTENTS](https://motherduck.com/duckdb-book-brief/#chapter-list)

Chapter 2

3 min read

# Getting Started with DuckDB

This is a summary of a book chapter from _DuckDB in Action_, published by Manning. [Download the complete book](https://motherduck.com/duckdb-book-brief) for free to read the complete chapter.

!['DuckDB In Action' book cover](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fduckdb-book-cover.622bc1e1.png&w=3840&q=75)

## 2.3 Using the DuckDB CLI

Launching the DuckDB CLI is incredibly simple, requiring just the execution of the 'duckdb' command. This initiates DuckDB and presents the user with the CLI prompt, ready to accept commands. By default, the database operates in transient mode, storing all data in memory, which is lost upon exiting the CLI using '.quit' or '.exit'.

![Post Image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fterminal3_9c945793cf.png&w=3840&q=75)

The CLI efficiently handles SQL statements, executing them upon encountering a semicolon and a newline. It provides flexibility by allowing multi-line input for longer statements and offers various output formats to suit different needs. Additionally, the CLI supports special dot commands for tasks like opening files, reading SQL scripts, listing tables, and controlling output settings.

## 2.4 DuckDB’s extension system

DuckDB's extension system expands its core functionality by providing modular packages that can be easily installed and managed. These extensions encompass features not included in the core database, allowing users to tailor DuckDB to their specific requirements. DuckDB comes bundled with several pre-loaded extensions, which may vary depending on the distribution.

The `duckdb_extensions` function provides a comprehensive list of available extensions, indicating their installation and loading status.

Installing an extension is as simple as using the `INSTALL` command followed by the extension name. Once installed, an extension can be loaded using the `LOAD` command. DuckDB's extension mechanism is designed to be idempotent, ensuring that repeated installation or loading attempts do not result in errors.

## 2.5 Analyzing a CSV file with the DuckDB CLI

DuckDB excels at handling common data engineering tasks, such as analyzing CSV files. Whether data resides on a local machine, a remote HTTP server, or cloud storage like S3, GCP, or HDFS, DuckDB can directly process it without requiring manual downloads or imports. Its parallel ingestion capabilities for formats like CSV and Parquet ensure rapid data loading. DuckDB automatically recognizes and processes files with specific extensions, such as '.csv'. For files without clear extensions, functions like `read_csv_auto` can be used to specify the format explicitly. DuckDB's ability to handle remote files and automatically infer formats streamlines data analysis workflows.

## 2.6 Summary

DuckDB's versatility is evident in its support for numerous programming languages, including Python, R, Java, Javascript, Julia, C/C++, ODBC, WASM, and Swift. Its CLI extends functionality through dot commands, enabling control over outputs, file reading, access to built-in help, and more. The CLI offers various display modes, such as 'duckbox', 'line', and 'ascii', to customize output presentation. DuckDB's ability to directly query CSV files from HTTP servers, facilitated by the 'httpfs' extension, simplifies data access and analysis. Furthermore, the CLI integrates seamlessly into data pipelines, allowing for efficient data processing without the need for table creation by querying external datasets and writing results to standard output or files.

!['DuckDB In Action' book cover](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fduckdb-book-cover.622bc1e1.png&w=3840&q=75)

Get your free book!

E-mail

Subscribe to MotherDuck news

Subscribe to DuckDB ecosystem newsletter

Download Book

Authorization Response