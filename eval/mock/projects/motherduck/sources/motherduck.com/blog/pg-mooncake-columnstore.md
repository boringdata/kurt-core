---
title: pg-mooncake-columnstore
content_type: tutorial
source_url: https://motherduck.com/blog/pg-mooncake-columnstore
indexed_at: '2025-11-25T19:56:53.507225'
content_hash: 123ac727980494ad
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# pg\_mooncake: Columnstore Tables with DuckDB Execution in Postgres

2024/10/30 - 4 min read

BY

[Pranav Aurora](https://motherduck.com/authors/pranav-aurora/)

_Editor's note: this post is by a guest author, Pranav Aurora, who is a co-founder of mooncake_

## Another system promising analytics in Postgres?

[pg\_duckdb is officially in beta](https://motherduck.com/blog/pgduckdb-beta-release-duckdb-postgres/) and has been positively received by the community. So, what’s the deal with pg\_mooncake?

Well, DuckDB-powered analytics in Postgres must look and feel like Postgres.

pg\_mooncake builds on this by introducing a native columnstore table to Postgres–supporting inserts, updates, joins, and soon, indexes. These tables are written as Iceberg or Delta tables (parquet files + metadata) in your object store. It leverages pg\_duckdb for its vectorized execution engine and deploys it as a part of the extension. You can try it using their docker image, and running:

```bash
Copy code

docker run --name mooncake-demo -e POSTGRES_HOST_AUTH_METHOD=trust -d ccqmpux/demo-arm64
docker run -it --rm --link mooncake-demo:postgres ccqmpux/demo-arm64 psql -h postgres -U postgres
```

The combination of a columnar storage format and DuckDB execution, means pg\_mooncake can deliver up to 1,000x faster analytics over regular Postgres tables. This performance is akin to running DuckDB on parquet files.

Here's now to create your columnstore table:

```sql
Copy code

CREATE extension pg_mooncake;
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    product_name TEXT,
    quantity INT,
    price DECIMAL(10, 2)
) USING columnstore;
```

pg\_mooncake is open source under a permissive MIT license. Mooncake Labs, the main contributors, are committed to keeping it that way and are grateful for the support from DuckDB Labs and the community. The extension is now available in preview on Neon.

## So, when should I use pg\_mooncake?

pg\_mooncake gives developers a native table experience for working with columnar format data in Postgres. This enables two key scenarios:

### 1\. Analytics on live datasets

You can run transactional and batch inserts, updates, and deletes directly on these columnstore tables.

```sql
Copy code

BEGIN;
INSERT INTO sales (id, product_name, quantity, price)
VALUES (3, 'Tablet', 30, 600);
UPDATE sales
SET quantity = 25
WHERE id = 3;
COMMIT;
```

Run your OLAP queries on these tables with up-to-date data:

```sql
Copy code

SELECT SUM(quantity * price) AS total_sales_amount
FROM sales;
```

### 2\. Writing Postgres data to Delta Lake and Iceberg Tables

Instead of backing your Postgres tables as ad-hoc Parquet files, you can write directly to open tables (Iceberg and Delta) in your object store. You can also query these tables using DuckDB outside of Postgres.

Soon, we’ll also provide a path to sync your existing Iceberg and Delta tables with your Postgres columnstore tables.

## How DuckDB enabled us to ship the extension in 60 days.

In just 60 days of hands-on keyboard, we were able to ship a clean and efficient system, thanks to the DuckDB execution engine. We didn’t have to modify the engine, and its performance is outstanding right out of the box. We're extremely grateful for the DuckDB community and foundation for making this possible.

DuckDB is the default execution engine for our columnstore tables, shipped as part of the pg\_mooncake extension. pg\_mooncake is modular and will seamlessly integrate future updates to pg\_duckdb, and performance is comparable to running pg\_duckdb on Parquet.

We initially set out to implement pg\_mooncake fully within Postgres but ultimately developed it as a DuckDB storage extension.This is how we shipped insert, update and deletes on columnstore tables.

> It was the duck that enabled the Mooncake.

## What's the MotherDuck connection?

Since Mooncake writes its columnstore tables in Delta or Iceberg format, you can query these tables outside of Postgres using MotherDuck or DuckDB without needing to stitch together files or wrangle with DataFrames –– just pass it the directory on your filesystem.

```sql
Copy code

SELECT *
FROM delta_scan('s3://some/delta/table');
```

For larger datasets, when running queries in your product Postgres database isn’t ideal, MotherDuck offloads the workload to the cloud—allowing users to run the same queries with improved performance, without any modifications.

pg\_mooncake will support this pattern more natively in the future – taking advantage of MotherDuck's “dual execution” capabilities to offload queries to the cloud.

Mooncake and MotherDuck form a powerful pair for online, user-facing analytics and offline warehousing-type analytics, all leveraging a single copy of data exposed as a table in Postgres. No CDC, ETL, or pipelines, just ship your roadmap.

## pg\_mooncake is officially in preview.

pg\_duckdb was officially announced in beta last week, and pg\_mooncake is now in preview today. The duck and the elephant are joining together nicely. Over a Mooncake to share.

Check the [extension repository](https://github.com/Mooncake-Labs/pg_mooncake) for more information, and start playing with it on your Neon and MotherDuck accounts

### TABLE OF CONTENTS

[Another system promising analytics in Postgres?](https://motherduck.com/blog/pg-mooncake-columnstore/#another-system-promising-analytics-in-postgres)

[So, when should I use pg\_mooncake?](https://motherduck.com/blog/pg-mooncake-columnstore/#so-when-should-i-use-pgmooncake)

[How DuckDB enabled us to ship the extension in 60 days.](https://motherduck.com/blog/pg-mooncake-columnstore/#how-duckdb-enabled-us-to-ship-the-extension-in-60-days)

[What's the MotherDuck connection?](https://motherduck.com/blog/pg-mooncake-columnstore/#whats-the-motherduck-connection)

[pg\_mooncake is officially in preview.](https://motherduck.com/blog/pg-mooncake-columnstore/#pgmooncake-is-officially-in-preview)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![ pg_duckdb beta release : Even faster analytics in Postgres](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpg_duckdb_beta_2_bc478870d8.png&w=3840&q=75)](https://motherduck.com/blog/pgduckdb-beta-release-duckdb-postgres/)

[2024/10/23 - Jelte Fennema-Nio, Mehdi Ouazza](https://motherduck.com/blog/pgduckdb-beta-release-duckdb-postgres/)

### [pg\_duckdb beta release : Even faster analytics in Postgres](https://motherduck.com/blog/pgduckdb-beta-release-duckdb-postgres)

pg\_duckdb makes elephants fly, marking its first release.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response