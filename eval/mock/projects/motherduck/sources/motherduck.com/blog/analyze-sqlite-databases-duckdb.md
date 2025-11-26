---
title: analyze-sqlite-databases-duckdb
content_type: tutorial
source_url: https://motherduck.com/blog/analyze-sqlite-databases-duckdb
indexed_at: '2025-11-25T19:58:31.781836'
content_hash: 436490c0b2da5ec8
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# How to analyze SQLite databases in DuckDB

2023/01/24 - 6 min read

BY

[Ryan Boyd](https://motherduck.com/authors/ryan-boyd/)

![duckdb_sqlite_notext_transparent.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fweb-assets-prod.motherduck.com%2Fassets%2Fimg%2Fduckdb_sqlite_notext_transparent_4c8efbf5f1.png&w=3840&q=75)

DuckDB is often referred to as the 'SQLite for analytics.' This analogy helps us understand several key properties of DuckDB: it's for analytics (OLAP), it's embeddable, it's lightweight, it's self-contained and it's widely deployed. Okay, the latter may not be a given yet for DuckDB, but SQLite says it's [likely the most widely used and deployed database engine](https://www.sqlite.org/mostdeployed.html) and, with the rising popularity of analytics, it's quite possible DuckDB will eventually be competitive.

![DB Engines SQLite ranking](https://motherduck.com/_next/image/?url=https%3A%2F%2Fweb-assets-prod.motherduck.com%2Fassets%2Fimg%2Fdb_engines_ranking_sqlite_e48226e623.jpg&w=3840&q=75)

It should be noted that while the original row-based architecture of SQLite lends itself well to transactional workloads (heavy reads and writes, few aggregations), there has been some work being done to make SQLite better for analytics workloads. Simon Willison [summarizes the work](https://simonwillison.net/2022/Sep/1/sqlite-duckdb-paper/) in a blog post from last fall based on a [VLDB paper](https://vldb.org/pvldb/volumes/15/paper/SQLite%3A%20Past%2C%20Present%2C%20and%20Future) and [CIDR presentation](https://www.youtube.com/watch?v=c9bQyzm6JRU) from the SQLite team.

## Working with SQLite databases in DuckDB

The DuckDB team added support to query SQLite databases directly from DuckDB using the [sqlitescanner extension](https://github.com/duckdblabs/sqlite_scanner). This extension makes a SQLite database available as read-only views within DuckDB.

For this blog post, we'll use the [SQLite Sakila Sample Database](https://www.kaggle.com/datasets/atanaskanev/sqlite-sakila-sample-database) to show you how SQLite in DuckDB works. This database is a SQLite port of the original MySQL sample database representing a ficticious [DVD rental store](https://en.wikipedia.org/wiki/Video_rental_shop).

If you prefer watching videos to learn, Mark Needham has a [short video tutorial](https://www.youtube.com/watch?v=ogge3kmm_2g) on this topic that's worth a watch.

### Loading the database

In order to load the database inside DuckDB, you'll need to install and load the extension.

```plaintext
Copy code

$ duckdb
D INSTALL sqlite;
D LOAD sqlite;
```

Next, you'll want to attach the SQLite database. If you downloaded the database from Kaggle above and have it in your current directory, you'll call the `sqlite_attach` procedure as follows.

```sql
Copy code

CALL sqlite_attach('sqlite-sakila.db');
```

### Exploring the data and running analytics queries

```plaintext
Copy code

D SHOW tables;
┌────────────────────────┐
│          name          │
│        varchar         │
├────────────────────────┤
│ actor                  │
│ address                │
│ category               │
│ city                   │
│ country                │
│ customer               │
│ customer_list          │
│ film                   │
│ film_actor             │
│ film_category          │
│ film_list              │
│ film_text              │
│ inventory              │
│ language               │
│ payment                │
│ rental                 │
│ sales_by_film_category │
│ sales_by_store         │
│ staff                  │
│ staff_list             │
│ store                  │
├────────────────────────┤
│        21 rows         │
└────────────────────────┘
```

Now let's try to get the top film categories based on the number of rentals. Note that each film is only in one category.

**Query:**

```sql
Copy code

SELECT c.name, count(*) cs
FROM rental r
LEFT JOIN inventory i USING (inventory_id)
LEFT JOIN film_category fc USING (film_id)
LEFT JOIN category c USING (category_id)
GROUP BY c.name
ORDER BY cs DESC;
```

**Result:**

```plaintext
Copy code

┌─────────────┬───────┐
│    name     │  cs   │
│   varchar   │ int64 │
├─────────────┼───────┤
│ Sports      │  1179 │
│ Animation   │  1166 │
│ Action      │  1112 │
│ Sci-Fi      │  1101 │
│ Family      │  1096 │
│ Drama       │  1060 │
│ Documentary │  1050 │
│ Foreign     │  1033 │
│ Games       │   969 │
│ Children    │   945 │
│ Comedy      │   941 │
│ New         │   940 │
│ Classics    │   939 │
│ Horror      │   846 │
│ Travel      │   837 │
│ Music       │   830 │
├─────────────┴───────┤
│ 16 rows   2 columns │
└─────────────────────┘
```

It looks like Sports movies are the most popular. Sigh, sportsball.

## Differences between SQLite and DuckDB

There are some noticeable differences between SQLite and DuckDB in how data is stored. SQLite, as a data store focused on transactions, stores data row-by-row while DuckDB, as a database engine for analytics, stores data by columns. Additionally, SQLite doesn't strictly enforce types in the data -- this is known as being weakly typed (or [flexibly typed](https://www.sqlite.org/flextypegood.html)).

Let's look at the customer table.

```plaintext
Copy code

D DESCRIBE customer;
┌─────────────┬─────────────┬─────────┬───────┬─────────┬───────┐
│ column_name │ column_type │  null   │  key  │ default │ extra │
│   varchar   │   varchar   │ varchar │ int32 │ varchar │ int32 │
├─────────────┼─────────────┼─────────┼───────┼─────────┼───────┤
│ customer_id │ BIGINT      │ YES     │       │         │       │
│ store_id    │ BIGINT      │ YES     │       │         │       │
│ first_name  │ VARCHAR     │ YES     │       │         │       │
│ last_name   │ VARCHAR     │ YES     │       │         │       │
│ email       │ VARCHAR     │ YES     │       │         │       │
│ address_id  │ BIGINT      │ YES     │       │         │       │
│ active      │ VARCHAR     │ YES     │       │         │       │
│ create_date │ TIMESTAMP   │ YES     │       │         │       │
│ last_update │ TIMESTAMP   │ YES     │       │         │       │
└─────────────┴─────────────┴─────────┴───────┴─────────┴───────┘
```

You'll notice that the store\_id is a `BIGINT`, which makes sense. The data in the example SQLite database we're using abides by that typing, but it's not guaranteed since it's not strongly-typed.

```plaintext
Copy code

D SELECT * FROM customer;
┌─────────────┬──────────┬────────────┬───────────┬───┬────────────┬─────────┬─────────────────────┬─────────────────────┐
│ customer_id │ store_id │ first_name │ last_name │ … │ address_id │ active  │     create_date     │     last_update     │
│    int64    │  int64   │  varchar   │  varchar  │   │   int64    │ varchar │      timestamp      │      timestamp      │
├─────────────┼──────────┼────────────┼───────────┼───┼────────────┼─────────┼─────────────────────┼─────────────────────┤
│           1 │        1 │ MARY       │ SMITH     │ … │          5 │ 1       │ 2006-02-14 22:04:36 │ 2021-03-06 15:53:36 │
```

Let's show you how a user might take advantage of the "flexible typing" in SQLite.

**Queries:**

```sql
Copy code

sqlite> UPDATE customer SET store_id='first' WHERE first_name='MARY';
sqlite> SELECT * from customer WHERE first_name='MARY'
```

**Result:**

```plaintext
Copy code

1|first|MARY|SMITH|MARY.SMITH@sakilacustomer.org|5|1|2006-02-14 22:04:36.000|2023-01-22 22:06:20
```

Oops! We now have a `store_id` that's a string instead of an integer! Because it's weakly typed, this will have little effect on SQLite, but if we pop over into the strongly-typed DuckDB and try to query this table, we'll get an error.

```plaintext
Copy code

D SELECT * FROM customer;
Error: Invalid Error: Mismatch Type Error: Invalid type in column "store_id": column was declared as integer, found "first" of type "text" instead.
```

To avoid this error, we can set the `sqlite_all_varchar` option to ignore the data types specified in SQLite and interpret all data in the DuckDB views as being of the `VARCHAR` type.

```sql
Copy code

SET GLOBAL sqlite_all_varchar=true;
```

Note that this option has to be set before we attach the SQLite database, or we will receive a different error:

```plaintext
Copy code

D SELECT * FROM customer;
Error: Binder Error: Contents of view were altered: types don't match!
```

## Loading data into DuckDB from SQLite

In order to take advantage of all the performance optimizations of DuckDB's columnar-vectorized query engine, you might wish to load the SQLite data into native DuckDB tables. You can do this very easily if you don't have any type matching problems as discussed above.

For example, to create the `customer` table in DuckDB as `customerf`, you can do:

```sql
Copy code

CREATE TABLE customerf AS SELECT * FROM customer
```

If this doesn't work because of mismatched types, you can set the `sqlite_all_varchar` option discussed earlier and load the data into DuckDB, taking advantage of DuckDB's implicit type casting.

```sql
Copy code

CREATE TABLE customerf(customer_id bigint, store_id bigint, first_name varchar, last_name varchar, email varchar, address_id bigint, active varchar, create_date timestamp, last_update timestamp);

INSERT INTO customerf SELECT * FROM customer WHERE TRY_CAST(store_id AS BIGINT) IS NOT NULL;
```

You'll notice that `customer` had 599 rows, while the new `customerf` has 598. You can now correct the unclean row of data and insert it again manually.

## What about other databases?

Although this post discussed using SQLite databases within DuckDB, you can now also [query PostgreSQL databases](https://duckdb.org/2022/09/30/postgres-scanner.html) from within DuckDB.

What other databases would you like to see supported?

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![How We're Making Analytics Ducking Awesome](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFrame_8539_3c342bd81f.png&w=3840&q=75)](https://motherduck.com/blog/in-the-news-podcasts-conferences/)

[2023/01/02 - Ryan Boyd](https://motherduck.com/blog/in-the-news-podcasts-conferences/)

### [How We're Making Analytics Ducking Awesome](https://motherduck.com/blog/in-the-news-podcasts-conferences)

MotherDuck on Podcasts, in the News and at conferences.

[![This Month in the DuckDB Ecosystem: January 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFrame_8538_1_19a9e51746.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-two/)

[2023/01/12 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-two/)

### [This Month in the DuckDB Ecosystem: January 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-two)

DuckDB community member Marcos Ortiz shares his favorite links and upcoming events across the community. Includes featured community member Jacob Matson who wrote about the Modern Data Stack in a Box with DuckDB.

[View all](https://motherduck.com/blog/)

Authorization Response