---
title: duckdb-110-hidden-gems
content_type: blog
source_url: https://motherduck.com/blog/duckdb-110-hidden-gems
indexed_at: '2025-11-25T19:57:28.731175'
content_hash: e7a6b8378cd4ae3f
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# 5 Hidden gems in DuckDB 1.1

2024/09/27 - 4 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

DuckDB 1.1 was released on September 9, and we recently had a bug fix release, 1.1.1, out on September 23. MotherDuck supported `1.1.1` just two days after its release, and we continue to work closely with the DuckDB Labs team to bring a smooth upgrade experience for all users.

But as things are moving fast, what did you miss in the 1.1 features?
DuckDB Labs released their usual [blog](https://duckdb.org/2024/09/09/announcing-duckdb-110.html), but I have my own preferred picks that didn't make that list, so let's dive in.

## 1\. Custom HTTP headers: your database can do API call

The DuckDB extension mechanism is powerful. Most of them are pre-loaded in the background, and you can't see the magic happening.
In a previous [blog post](https://motherduck.com/blog/getting-started-gis-duckdb/), I show how we could query an API with a single line statement and return it as a DuckDB table :

```sql
Copy code

CREATE TABLE poi_france AS SELECT * FROM read_json_auto('https://my-endpoint/api')
```

What is happening here :

- The `httpfs` extension is loaded to get the data from an HTTP endpoint.
- `read_json_auto` will parse directly the JSON response in a table

But what if our API is not public and requires authentication and other headers?

This is where the new HTTP headers come into play. You can now create `http` secret.

```sql
Copy code

CREATE SECRET http (
    TYPE HTTP,
    EXTRA_HTTP_HEADERS MAP {
        'Authorization': 'Bearer YOUR_STRIPE_API_KEY'
    }
);

select unnest(data) as customers
from read_json('https://api.stripe.com/v1/customers');
```

Snippet courtesy of [Archie](https://x.com/archieemwood) on [duckdbsnippets.com](https://duckdbsnippets.com/users/327).

## 2\. More data types to optimize memory: VARINT

`VARINT` type refers to a **variable-length integer** data type. Unlike fixed-size integers (like `INT` or `BIGINT`), which allocate a fixed number of bytes regardless of the size of the value stored, `VARINT` optimizes the storage by using fewer bytes for smaller numbers and more bytes for larger numbers.

This is particularly useful when dealing with datasets that contain a wide range of integer values, including many small numbers and some large numbers.

Did you know? You can list all data types from the CLI using :

```sql
Copy code

D SELECT * FROM (DESCRIBE SELECT * FROM test_all_types()) ;
┌────────────────────────────┬─────────────────────────────────────┬─────────┬─────────┬─────────┬─────────┐
│        column_name         │             column_type             │  null   │   key   │ default │  extra  │
│          varchar           │               varchar               │ varchar │ varchar │ varchar │ varchar │
├────────────────────────────┼─────────────────────────────────────┼─────────┼─────────┼─────────┼─────────┤
│ bool                       │ BOOLEAN                             │ YES     │         │         │         │
│ tinyint                    │ TINYINT                             │ YES     │         │         │         │
│ smallint                   │ SMALLINT                            │ YES     │         │         │         │
│ int                        │ INTEGER                             │ YES     │         │         │         │
│ bigint                     │ BIGINT                              │ YES        │         │         │         │
│     ·                      │     ·                               │  ·      │    ·    │    ·    │    ·    │
│     ·                      │     ·                               │  ·      │    ·    │    ·    │    ·    │
│     ·                      │     ·                               │  ·      │    ·    │    ·    │    ·    │
```

## 3\. More DuckDB in the browser: Pyodide support

DuckDB is already heavily used in the browser through [Wasm](https://webassembly.org/). This runs entirely on the client side, enabling you to leverage your local computing and avoid network traffic.
[Pyodide](https://pyodide.org/en/stable/) is a port of CPython to WebAssembly.
In short, it enables a Python environment that runs in the browser, again on the client side. This is currently really useful for learning platforms like [Datacamp](https://datacamp.com/). It's a better experience for the user as things run on the client, and it reduces server-side cost 💸.

DuckDB now supports Pyodide, which means you can install the duckdb package directly there (through `micropip` \- meaning any import statement will install the package).
Check the demo using the [REPL of Pyodide](https://pyodide.org/en/stable/console.html) :

Your browser does not support the video tag.

Note : It doesn't support yet extensions - so pretty limited but a big path forward.

## 4\. ORDER BY + LIMIT get faster

Before this fix, DuckDB would not apply the Top-N optimization if the `ORDER BY` and `LIMIT` clauses were used in different parts of the query, such as within a CTE.
So typically, this will be faster on 1.1 release :

```sql
Copy code

WITH CTE AS (SELECT * FROM tbl ORDER BY col) SELECT * FROM cte LIMIT N
```

## 5\. More insights from EXPLAIN - easier debugging

The DuckDB team added a neat feature to export your [EXPLAIN as HTML](https://github.com/duckdb/duckdb/pull/13202).

Usage :

```css
Copy code

EXPLAIN (FORMAT HTML) SELECT ...
```

![explain_first](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F353390406_d0dc962f_ec7d_40f6_9a5a_bd9a739824a8_ed6df56ecf.png&w=3840&q=75)

You can easily navigate through complex plans as you can also collapse/expand children.
And that's not all, when using a Jupyter notebook, the `explain()` method of the `DuckDBPyRelation` will automatically use the HTML format and render the result using `IPython.display.HTML`.

![explain](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2024_09_27_at_12_17_44_ec552fe2d2.png&w=3840&q=75)

Note that the team also re-work the documentation around `EXPLAIN` and `EXPLAIN ANALYZE`. Make sure to [check this one](https://duckdb.org/docs/sql/statements/profiling.html); it's really helpful whenever you have an issue or performance slowdown to better understand what's going on.

That's it for the new feature on 1.1! In the meantime, keep coding and keep quacking.

☁️🦆 Start using DuckDB in the Cloud for FREE with MotherDuck : [https://hubs.la/Q02QnFR40](https://hubs.la/Q02QnFR40)

### TABLE OF CONTENTS

[1\. Custom HTTP headers: your database can do API call](https://motherduck.com/blog/duckdb-110-hidden-gems/#1-custom-http-headers-your-database-can-do-api-call)

[2\. More data types to optimize memory: VARINT](https://motherduck.com/blog/duckdb-110-hidden-gems/#2-more-data-types-to-optimize-memory-varint)

[3\. More DuckDB in the browser: Pyodide support](https://motherduck.com/blog/duckdb-110-hidden-gems/#3-more-duckdb-in-the-browser-pyodide-support)

[4\. ORDER BY + LIMIT get faster](https://motherduck.com/blog/duckdb-110-hidden-gems/#4-order-by-limit-get-faster)

[5\. More insights from EXPLAIN - easier debugging](https://motherduck.com/blog/duckdb-110-hidden-gems/#5-more-insights-from-explain-easier-debugging)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Generating a data app with your MotherDuck data](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdataapp_6bbeacb678.png&w=3840&q=75)](https://motherduck.com/blog/data-app-generator/)

[2024/09/06 - Till Döhmen](https://motherduck.com/blog/data-app-generator/)

### [Generating a data app with your MotherDuck data](https://motherduck.com/blog/data-app-generator)

How to generate a web app dashboard based on your data

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response