---
title: duckdb-tutorial-for-beginners
content_type: tutorial
source_url: https://motherduck.com/blog/duckdb-tutorial-for-beginners
indexed_at: '2025-11-25T19:57:39.343742'
content_hash: 9666dd2fd1ca1c68
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# DuckDB Tutorial For Beginners

2024/10/31 - 12 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)
,
[Ryan Boyd](https://motherduck.com/authors/ryan-boyd/)

If you haven't had the chance to get up to speed with DuckDB, this tutorial is for you! We'll go over the essentials, from installation to workflow, getting to know the command-line interface (CLI), and diving into your first analytics project. If are too lazy to read, I also made a video for this tutorial.

DuckDB Tutorial For Beginners In 12 min - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[DuckDB Tutorial For Beginners In 12 min](https://www.youtube.com/watch?v=ZX5FdqzGT1E)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

Full screen is unavailable. [Learn More](https://support.google.com/youtube/answer/6276924)

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Why am I seeing this?](https://support.google.com/youtube/answer/9004474?hl=en)

[Watch on](https://www.youtube.com/watch?v=ZX5FdqzGT1E&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 11:26

•Live

•

Let's start quacking some code!

Editor's note: this tutorial was originally published 2023-04-26 by Mehdi and has been updated by Ryan to reflect advancements in DuckDB.


## What is DuckDB?

DuckDB is an in-process SQL [OLAP](https://motherduck.com/learn-more/what-is-OLAP/) database, which means it is a database optimized for analytics and runs within the same process as the application using it. This unique feature allows DuckDB to offer the advantages of a database without the complexities of managing one. But, as with any software concept, the best way to learn is to dive in and get your hands dirty.

We’ll be showing examples using the DuckDB command-line client (CLI), but you can also use DuckDB from within Python, R, and other languages, or any tool supporting JDBC or ODBC drivers. There is a community-contributed selection of example queries and code for many of these languages on the [DuckDB Snippets](https://duckdbsnippets.com/) website.

_In the below snippets, any code example prefixed with `$` means that it’s a bash command. Otherwise we assume that these would run within a DuckDB process, which uses a `D` prompt._

## Installation

Installing DuckDB is a breeze. Visit the [DuckDB documentation](https://duckdb.org/docs/installation/index) and download the binary for your operating system.

For MacOS and Windows users, you can leverage package managers to make the DuckDB CLI directly available in your PATH, simplifying upgrades and installations.

To install DuckDB on MacOS using Homebrew, run the following command:

```bash
Copy code

$ brew install duckdb
```

To install DuckDB on Windows using winget, run the following command:

```bash
Copy code

C:\> winget install DuckDB.cli
```

You can now launch DuckDB by simply calling the `duckdb` CLI command.

```jsx
Copy code

$ duckdb
v1.0.0 1f98600c2c
Enter ".help" for usage hints.
Connected to a transient in-memory database.
Use ".open FILENAME" to reopen on a persistent database.
D
```

## Workflow with VSCode

To follow along with our exploration of DuckDB, check out this [GitHub repository](https://github.com/mehd-io/duckdb-playground-tutorial). I recommend working with an editor, a SQL file, and sending commands to the terminal for a lightweight setup. This approach offers visibility on all commands, enables you to safely version control them, and allows you to leverage formatting tools and AI friends like Copilot.

In our example, we'll use Visual Studio Code (VSCode). To configure a custom shortcut to send commands from the editor to the terminal, open the keyboard shortcuts JSON file and add a key binding to the following command :

```jsx
Copy code

{
    "key": "shift+enter",
    "command": "workbench.action.terminal.runSelectedText"
}
```

Of course, this workflow can be pretty easily replicated with any editor or IDE!

### Data Persistence with DuckDB: Overview

By default, DuckDB is an in-memory process and won't persist any data. To demonstrate this, let's create a simple table based on a query result:

```sql
Copy code

$ duckdb
D CREATE TABLE ducks AS SELECT 3 AS age, 'mandarin' AS breed;
FROM ducks;
┌───────┬──────────┐
│  age  │  breed   │
│ int32 │ varchar  │
├───────┼──────────┤
│     3 │ mandarin │
└───────┴──────────┘
```

This query creates and populates a "ducks" table. However, if we exit the CLI and reopen it, the table will be gone.

Unlike standard SQL, the query above uses the `FROM` statement without any `SELECT *` statement. This is a neat shortcut in DuckDB and there are plenty more [DuckDB SQL shortcuts](https://duckdb.org/2022/05/04/friendlier-sql.html)!


### Data Persistence with DuckDB: Creating a Database

To persist data, you have two options:

1. Provide a path to a database file when starting DuckDB. The file can have any extension, but common choices are `.db`, `.duckdb`, or `.ddb`. If no database exists at the specified path, DuckDB will create one.


```bash
Copy code


$ duckdb /data/myawesomedb.db
```


You can also launch DuckDB with a database in read-only mode to avoid modifying the database:


```bash
Copy code


$ duckdb -readonly /data/myawesomedb.db
```

2. If DuckDB is already running, use the `attach` command to connect to a database at the specified file path.


```arduino
Copy code


ATTACH DATABASE '/path/to/your/database.db' AS mydb;
```


The database file uses DuckDB's custom single-file format (all tables are included), which supports transactional ACID compliance and stores data in a compressed columnar format for optimal aggregation performance. DuckDB is [regularly adding](https://duckdb.org/2022/10/28/lightweight-compression.html) new compression algorithms to improve performance.

While the DuckDB team often improves the file format with new releases, it is [backward compatible](https://duckdb.org/docs/internals/storage.html) as of DuckDB 1.0, meaning that new releases are able to read files produced by early releases of DuckDB.

If you use MotherDuck as your cloud data warehouse, it automatically manages the DuckDB databases for you, so you create a MotherDuck database using the familiar [`CREATE DATABASE`](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/create-database/) SQL statement.

## Reading and Displaying Data

Next, let's explore reading and writing data in CSV and Parquet formats. We'll use a small dataset from Kaggle containing daily Netflix Top 10 Movie/TV Show data for the United States from 2020 to March 2022.

To load the CSV dataset, use the [read\_csv\_auto](https://duckdb.org/docs/data/csv/overview#read_csv_auto-function) command, which infers the schema and detects the delimiter. You can also use the `read_csv` command and pass the schema and delimiter as parameters.

```sql
Copy code

SELECT * FROM read_csv_auto('path/to/your/file.csv');
```

When you use this command, the dataset is read, but an actual table is not created in your DuckDB database. To create a table, use a `CREATE TABLE x AS` (CTAS) statement:

```sql
Copy code

CREATE TABLE netflix_top10 AS SELECT * FROM read_csv_auto('path/to/your/file.csv');
```

To write data to a CSV file, use the `COPY` command and specify the delimiter. For Parquet files, simply specify the file format:

```sql
Copy code

COPY ./data/netflix_top10.csv TO 'path/to/your/output/file.csv' WITH (FORMAT 'CSV', DELIMITER ',');
COPY ./data/netflix_top10.csv TO 'path/to/your/output/file.parquet' WITH (FORMAT 'PARQUET');
```

To read data from a Parquet file, use the `read_parquet` command:

```sql
Copy code

SELECT * FROM read_parquet('path/to/your/file.parquet');
```

DuckDB supports a wide variety of different file formats, including the native DuckDB database file used above, CSV, [JSON](https://motherduck.com/blog/analyze-json-data-using-sql/), Parquet, [Iceberg](https://motherduck.com/docs/integrations/file-formats/apache-iceberg/), [Delta Lake](https://motherduck.com/docs/integrations/file-formats/delta-lake/) and more. You can read these files from your local filesystem, a http endpoint or a cloud blob store like AWS S3, Cloudflare R2, Azure Blob Storage or Google Cloud Storage.

## Display Modes, Output Options

DuckDB CLI offers various ways to enhance your experience by customizing the data display and output options.

You can use the `.mode` command to change the appearance of tables returned in the terminal output. For instance, if you are dealing with long nested JSON, you can change the mode to `line` or `JSON` to have a better view of your data.

```jsx
Copy code

.mode line
SELECT * FROM './data/sales.json';
sales_data = [{'order_id': 1, 'customer': {'id': 101, 'name': John Doe, 'email': john.doe@example.com}, 'items': [{'product_id': 301, 'product_name': Laptop, 'quantity': 1, 'price': 1200}, {'product_id': 302, 'product_name': Mouse, 'quantity': 1, 'price': 25}], 'total_amount': 1225, 'date': 2023-03-24}, {'order_id': 2, 'customer': {'id': 102, 'name': Jane Smith, 'email': jane.smith@example.com}, 'items': [{'product_id': 303, 'product_name': Keyboard, 'quantity': 1, 'price': 50}, {'product_id': 304, 'product_name': Monitor, 'quantity': 1, 'price': 200}], 'total_amount': 250, 'date': 2023-03-25}]
```

Next to that, you can output elsewhere the data by redirecting the terminal output to a file.

Let’s say you would like to output the result to a Markdown file, you can set the display mode to Markdown with `.mode markdown`. Combine this with the `.output` or `.once` command to write the result directly to a specific file. The `.output` command writes all the output of the different results you run, while `.once` does it just once.

```lua
Copy code

.mode markdown
.output myfile.md
```

## Running Commands and Exiting

DuckDB CLI allows you to run a SQL statement and exit using the `-c` option parameter. For example, if you use a `SELECT` statement to read a Parquet file:

```jsx
Copy code

$ duckdb -c "SELECT * FROM read_parquet('path/to/your/file.parquet');"
```

This feature is lightweight, fast, and easy. You can even build your own [bash functions](https://duckdbsnippets.com/snippets/6/quickly-convert-a-csv-to-parquet-bash-function) using the DuckDB CLI for various operations on CSV/Parquet files, such as converting a CSV to Parquet.

DuckDB also offers flags for configuration that you can fine-tune, such as setting the thread count, memory limits, ordering of null values and more. You can find the full list of flag options and their current values from the `duckdb_settings()` table function.

```csharp
Copy code

FROM duckdb_settings();
```

## Working with Extensions

Extensions are like packages that you can install within DuckDB to enjoy specific feature. DuckDB supports a number of core extensions. Not all are included by default, but DuckDB has a mechanism for remote extension installation. To view the available core extensions, execute the following statement:

```csharp
Copy code

FROM duckdb_extensions();
```

To install an extension, such as the popular `httpfs` extension that allows reading/writing remote files over HTTPS and S3, use the `INSTALL` command followed by the extension name. Once installed, DuckDB downloads the extension to the `$HOME/.duckdb/` folder (modifiable by setting the `extension_directory` parameter).

Next, load the extension in the DuckDB process with the `LOAD` command.

```ini
Copy code

INSTALL httpfs;
LOAD httpfs;
```

DuckDB supports autoloading of the core extensions, so you often do not need to manually load these. As an example. if you read from a CSV file with a \`https://\` scheme, the \`httpfs\` extension will be autoloaded.


If you're using a third-party extension or your own extension not bundled by default, set the `allow_unsigned_extensions` flag to `True`, or use the `-unsigned` flag parameter when launching DuckDB.

```jsx
Copy code

$ duckdb -unsigned
```

Extensions are powerful and versatile. You can create your own using the [template](https://github.com/duckdb/extension-template) provided by the DuckDB Labs team to kickstart your extension development journey.

There is now a [Community Extensions repository](https://duckdb.org/docs/extensions/community_extensions.html) for you to share any custom extensions with the wider DuckDB community for easy installation.

## First analytics project

We have the mentioned Netflix dataset hosted on a public AWS S3 bucket. In this simple project, we will answer the most existential question : what were people in the US binge-watching during the COVID lockdown?

As the data is sitting on AWS S3, we’ll start by installing the extension httpfs.

```jsx
Copy code

-- Install extensions
INSTALL httpfs;
LOAD httpfs;
-- Minimum configuration for loading S3 dataset if the bucket is public
SET s3_region='us-east-1';
```

We can now read our dataset :

```jsx
Copy code

D CREATE TABLE netflix AS SELECT * FROM read_parquet('s3://us-prd-motherduck-open-datasets/netflix/netflix_daily_top_10.parquet');
FROM netflix;
┌────────────┬───────┬───────────────────┬───┬────────────────┬──────────────────┐
│   As of    │ Rank  │ Year to Date Rank │ … │ Days In Top 10 │ Viewership Score │
│    date    │ int64 │      varchar      │   │     int64      │      int64       │
├────────────┼───────┼───────────────────┼───┼────────────────┼──────────────────┤
│ 2020-04-01 │     1 │ 1                 │ … │              9 │               90 │
│ 2020-04-01 │     2 │ 2                 │ … │              5 │               45 │
│ 2020-04-01 │     3 │ 3                 │ … │              9 │               76 │
│ 2020-04-01 │     4 │ 4                 │ … │              5 │               30 │
│ 2020-04-01 │     5 │ 5                 │ … │              9 │               55 │
│ 2020-04-01 │     6 │ 6                 │ … │              4 │               14 │
```

Finally, getting the top watched movies as follow :

```jsx
Copy code

-- Display the most popular TV Shows
SELECT Title, max("Days In Top 10") from netflix
where Type='Movie'
GROUP BY Title
ORDER BY max("Days In Top 10") desc
limit 5;
┌────────────────────────────────┬───────────────────────┐
│             Title              │ max("Days In Top 10") │
│            varchar             │         int64         │
├────────────────────────────────┼───────────────────────┤
│ The Mitchells vs. The Machines │                    31 │
│ How the Grinch Stole Christmas │                    29 │
│ Vivo                           │                    29 │
│ 365 Days                       │                    28 │
│ Despicable Me 2                │                    27 │
└────────────────────────────────┴───────────────────────┘

-- Copy the result to CSV
COPY (
SELECT Title, max("Days In Top 10") from netflix
where Type='TV Show'
GROUP BY Title
ORDER BY max("Days In Top 10") desc
limit 5
) TO 'output.csv' (HEADER, DELIMITER ',');
```

What’s fun is that for both Movies and TV shows, the top 5 mostly include kids show. We all know that kids doesn’t bother to see multiple time the same thing…

DuckDB and MotherDuck also support accessing private S3 buckets by using [`CREATE SECRET`](https://motherduck.com/docs/integrations/cloud-storage/amazon-s3/) to specify and store your credentials.

## Exploring Beyond the Pond

That’s it for this tutorial! If you're interested in delving deeper into DuckDB, check out these resources:

- The official DuckDB docs : [https://duckdb.org/](https://duckdb.org/)
- The DuckDB discord : [https://discord.com/invite/tcvwpjfnZx](https://discord.com/invite/tcvwpjfnZx)

To elevate your experience with DuckDB and scale it with a cloud data warehouse, explore [MotherDuck](https://motherduck.com/product/)! Dive into our [end-to-end tutorial](https://motherduck.com/docs/getting-started/e2e-tutorial) to discover the user-friendly web interface, AI-based SQL query fixing, global and organization-wide data sharing capabilities, and more.

Additionally, stay tuned to our [monthly newsletter](https://motherduck.com/duckdb-news/) and [YouTube channel](https://youtube.com/@motherduckdb/), where we'll continue to share more DuckDB-related content!

Keep quacking, keep coding.

!['DuckDB In Action' book cover](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fduckdb-book-full-cover.68e4f598.png&w=3840&q=75)

Get your free book!

E-mail

Subscribe to other MotherDuck news

Submit

Free Book!

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: March 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_ecosystem_monthly_feb_2023_352e669717.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-four/)

[2023/03/23 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-four/)

### [This Month in the DuckDB Ecosystem: March 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-four)

This month in the DuckDB Ecosystem, by Marcos Ortiz. Includes featured community member Elliana May, Python ecosystem, top links, upcoming events and more.

[![This Month in the DuckDB Ecosystem: April 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_ecosystem_monthly_april_2023_bb2015c778.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-five/)

[2023/04/17 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-five/)

### [This Month in the DuckDB Ecosystem: April 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-five)

This month in the DuckDB Ecosystem, by Marcos Ortiz. Latest updates, including featured community member Josh Wills, upcoming events like webinars and top links.

[View all](https://motherduck.com/blog/)

Authorization Response