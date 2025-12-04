---
title: duckdb-python-quickstart-part1
content_type: tutorial
source_url: https://motherduck.com/learn-more/duckdb-python-quickstart-part1
indexed_at: '2025-11-25T09:57:03.972667'
content_hash: a093ddae571df028
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO LEARN](https://motherduck.com/learn-more/)

# DuckDB Python Quickstart (Part 1): Your Complete Guide to Fast Data Analytics

14 min readBY

[Aditya Somani](https://motherduck.com/authors/aditya-aomani/)

![DuckDB Python Quickstart (Part 1): Your Complete Guide to Fast Data Analytics](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Flearn_more_duck_db_df1112cb47_151aeeba16.png&w=3840&q=75)

Alright, let's talk data. How many times have you been handed a CSV file, a Parquet dump, or even just a hefty Pandas DataFrame and thought, "Okay, how do I query this _right now_ without spinning up a whole database server?" Maybe you just need to do some quick exploration, filter a few million rows, or calculate some aggregates, but setting up a proper database feels like overkill, and plain old Pandas is starting to chug on the larger datasets.

You've probably been there. That friction between having data in files or memory and needing database-level query power is a common one. This is where something like DuckDB comes in, and specifically, its fantastic Python integration.

Think of DuckDB as the analytical database that lives _inside_ your Python process. No separate server to manage, no complex setup – you just `pip install duckdb`, and you're ready to perform fast, analytical SQL queries directly on your data, wherever it lives. It's like having a pocket-sized data warehouse ready to _quack_ into action whenever you need it.

In this first part of your DuckDB Python quickstart, you're going to dive into the foundational API features. You'll cover everything you need to get up and running quickly:

- **Installation and Connection:** Getting DuckDB into your Python environment and making your first connection.
- **Basic Querying:** Executing simple SQL statements using both the relational API and DB-API styles.
- **Data Ingestion:** Reading data directly from common file formats like CSV and Parquet.
- **The Relational API:** A Pythonic way to build and compose queries, including set operations and joins.

By the end of this guide, you'll have a solid grasp of how to leverage DuckDB for basic querying and data handling directly within your Python environment. And, by the way, you could also follow this guide using [this notebook](https://github.com/adisomani/duckdb-notebooks/blob/main/duckdb_python_quickstart.ipynb). Let's get your ducks in a row!

## Getting Started: Installation and Connection

First things first, you need the DuckDB Python package. If you're using pip, a simple:

```bash
Copy code

pip install duckdb
```

will do the trick. If you're more of a Conda person, you can use:

```bash
Copy code

conda install python-duckdb -c conda-forge
```

Once installed, you can import the library and check the version to make sure everything is gravy:

```python
Copy code

import duckdb
print(duckdb.__version__)
# Should output something like: '1.3.0'
```

Now, how do you connect? This is delightfully simple with DuckDB. Since it's an embedded database, it runs directly within your Python process. You don't _have_ to create an explicit connection object right away if you just want to mess around in memory, but it's good practice and necessary if you want a persistent database or specific connection settings.

To start an **in-memory** database (data disappears when your session ends):

```python
Copy code

import duckdb

con = duckdb.connect(database=':memory:')
```

To connect to or create a **persistent database file**:

```python
Copy code

import duckdb

con = duckdb.connect(database='my_local_data.duckdb') # Creates if it doesn't exist
```

Here's something useful you'll discover: if you don't specify a database name in `duckdb.connect()`, it defaults to in-memory. Even better, the main `duckdb` module provides a default in-memory connection that you can use directly via `duckdb.sql()` without managing a connection object explicitly. This default connection is global to the `duckdb` Python module, which makes it perfect for quick exploratory work.

INFO: Serverless Option: MotherDuck
While DuckDB is embedded and runs locally, you can easily extend its capabilities for serverless, collaborative analytics by \[connecting to MotherDuck\](https://motherduck.com/). MotherDuck provides a managed service that works seamlessly with your DuckDB Python client, allowing you to store data persistently in the cloud and share access. Learn more about how to [Connect Python to MotherDuck](https://motherduck.com/docs/category/python/).

## Your First Queries: `sql()` and `execute()`

DuckDB's Python API offers two main approaches for executing SQL. The `sql()` method is typically more convenient for interactive work and integrating with Python objects.

Let's start with a simple query using the default connection:

```python
Copy code

import duckdb

# Use the default in-memory connection
result = duckdb.sql("SELECT 42 AS answer")
```

What do you get back? Let's check the type:

```python
Copy code

print(type(result))
# Output: <class 'duckdb.duckdb.DuckDBPyRelation'>
```

Ah, a `DuckDBPyRelation`. This is a key concept in DuckDB's relational API. It represents a query result _or_ a data source (like a table or a file), but it doesn't necessarily mean the data has been fully processed or brought into Python memory yet. It's a symbolic representation of a query.

To see the actual data, you need to _materialize_ the relation. You can do this in several ways:

- `.show()`: Prints a nice tabular representation (great for interactive exploration).
- `.fetchall()`: Returns all results as a list of tuples (the traditional DB-API way).
- `.fetchone()`: Returns the next single row as a tuple.
- `.df()` or `.fetchdf()`: Converts the result into a Pandas DataFrame.
- `.arrow()` or `.fetcharrow()`: Converts the result into an Apache Arrow Table.
- `.pl()`: Converts the result into a Polars DataFrame.

Let's try `show()`:

```python
Copy code

duckdb.sql("SELECT 42 AS answer").show()
```

```bash
Copy code

┌────────┐
│ answer │
│ int32  │
├────────┤
│     42 │
└────────┘
```

And using `fetchall()`:

```python
Copy code

result_list = duckdb.sql("SELECT 42 AS answer").fetchall()
print(result_list)
# Output: [(42,)]
```

The other primary way to execute SQL is using the `execute()` method, typically on a connection object (`con.execute(...)`). This aligns more closely with the Python DB-API 2.0 standard. It immediately executes the query and returns a cursor-like object that you then use with methods like `fetchone()` or `fetchall()` to retrieve data.

```python
Copy code

con = duckdb.connect(database=':memory:')
result_cursor = con.execute("SELECT 'hello' || ' ' || 'world' AS greeting")
print(result_cursor.fetchone())
# Output: ('hello world',)
```

For most quick analysis and integration with Python data structures, `sql()` is often preferred due to its flexibility and the `DuckDBPyRelation` object it returns, which you'll explore further. The `execute()` method is particularly useful when you need **parameterized queries** (passing values separately from the SQL string).

Here's how you pass parameters using the DB-API style `execute()`, which helps prevent SQL injection and can improve performance for repeated queries:

```python
Copy code

con = duckdb.connect(database=':memory:')
con.execute("CREATE TABLE items (name VARCHAR, value INTEGER)")
con.execute("INSERT INTO items VALUES ('apple', 1), ('banana', 2), ('cherry', 3)")

# Parameterized query using '$param_name' syntax and a dictionary
item_name = 'banana'
result = con.execute("SELECT value FROM items WHERE name = $item_name", {'item_name': item_name})
print(f"Value for {item_name}: {result.fetchone()}")

# Parameterized query using '?' syntax and a tuple/list
item_value = 1
result = con.execute("SELECT name FROM items WHERE value = ?", [item_value])
print(f"Name for value {item_value}: {result.fetchone()}")

con.close()
```

```bash
Copy code

Value for banana: (2,)
Name for value 1: ('apple',)
```

The `$param_name` syntax with a dictionary is often more readable than the `?` syntax with a list/tuple. Both are valid ways to pass parameters.

## Ingesting Data: From Files to Relations

One of the most common tasks is getting data _into_ your database or query environment. DuckDB shines here by allowing you to query files directly. No need for a `CREATE TABLE` followed by a bulk `INSERT`. You can treat files like tables from the get-go.

Let's say you have a CSV file. DuckDB provides functions like `read_csv`, `read_parquet`, `read_json`, etc., that you can call directly from Python or within SQL.

Using the Python API, you can read a file and get a `DuckDBPyRelation` back:

```python
Copy code

import duckdb

# You'll use a publicly available CSV file
# Connect to a persistent DB file or use ':memory:'
con = duckdb.connect(database='my_local_data.duckdb')
con.sql("INSTALL httpfs") # Need httpfs extension to read from URL
con.sql("LOAD httpfs")

population_relation = con.read_csv("https://bit.ly/3KoiZR0")

print(type(population_relation))
# Output: <class 'duckdb.duckdb.DuckDBPyRelation'>
```

Just like with your simple `SELECT 42` example, this `population_relation` object isn't the data itself, but a representation of the data in the CSV file, ready to be queried. You can then query this relation using either SQL or the Relational API methods.

Using SQL via `sql()`:

```python
Copy code

con.sql("SELECT Country, Population FROM population_relation LIMIT 5").show()
```

```bash
Copy code

┌─────────────────┬────────────┐
│     Country     │ Population │
│     varchar     │   int64    │
├─────────────────┼────────────┤
│ Afghanistan     │   31056997 │
│ Albania         │    3581655 │
│ Algeria         │   32930091 │
│ American Samoa  │      57794 │
│ Andorra         │      71201 │
└─────────────────┴────────────┘
```

This is incredibly convenient! You're querying the CSV file directly using SQL syntax, without defining a schema or loading it fully into a table first.

If you find yourself querying the same file repeatedly or need better performance than reading the file anew each time, you can easily persist the data into a DuckDB table using the `.to_table()` method on your relation:

```python
Copy code

# You should already have the 'con' connection open and httpfs loaded

population_relation = con.read_csv("https://bit.ly/3KoiZR0") # Read into a relation
population_relation.to_table("population") # Persist the relation as a table named 'population'

# Now you can query the 'population' table directly
con.sql("SELECT COUNT(*) FROM population").show()
```

```bash
Copy code

┌──────────────┐
│ count_star() │
│    int64     │
├──────────────┤
│          227 │
└──────────────┘
```

INFO: Querying Files Directly
DuckDB's ability to query file formats like CSV, Parquet, and JSON directly without a formal \`CREATE TABLE\` step is a massive productivity boost for data exploration and quick analysis. It leverages optimized readers under the hood. For larger files or repeated access, converting to a DuckDB table (.to\_table()) is generally recommended for better performance and persistence.

While `.to_table()` persists data locally, you might want to [persist data in the cloud with MotherDuck](https://motherduck.com/docs/key-tasks/loading-data-into-motherduck/) for collaboration, accessibility, and serverless scaling.

## The Relational API: Building Queries Programmatically

You've seen that `duckdb.sql()` and `con.read_csv()` return `DuckDBPyRelation` objects. These objects are not just passive query results; they are _query builders_ themselves. This is DuckDB's Relational API, offering a Pythonic, fluent interface to construct queries.

Instead of writing a single SQL string, you can chain methods on a `DuckDBPyRelation` object, with each method representing a relational operation like `filter`, `project` (select columns), `aggregate`, `order`, `limit`, `except_`, `intersect`, `union`, and `join`.

Here are some key methods you'll use:

- `.filter(condition)`: Adds a `WHERE` clause.
- `.project(columns)`: Adds a `SELECT` clause (specifies columns).
- `.limit(n)`: Adds a `LIMIT` clause.
- `.order(columns)`: Adds an `ORDER BY` clause.
- `.aggregate(expressions, group_by_columns=None)`: Adds an `AGGREGATE` and optional `GROUP BY`.
- `.except_(other_relation)`: Returns rows in the current relation that are not in `other_relation`.
- `.intersect(other_relation)`: Returns rows present in _both_ the current relation and `other_relation`.
- `.union(other_relation)`: Combines all rows from both relations (like `UNION ALL` in SQL; for `UNION DISTINCT`, you'd typically chain `.distinct()`).
- `.join(other_relation, on=None, how='inner')`: Performs a join with `other_relation`.

Let's find countries with a population over 10 million, select just the country and population, limit to the first 5, and display the result, all using the relational API methods on the `population_relation` you created earlier:

```python
Copy code

# You should already have the 'population_relation' relation from the CSV file
(population_relation
 .filter("Population > 10000000")
 .project("Country, Population")
 .limit(5)
 .show()
)
```

```bash
Copy code

┌──────────────┬────────────┐
│   Country    │ Population │
│   varchar    │   int64    │
├──────────────┼────────────┤
│ Afghanistan  │   31056997 │
│ Algeria      │   32930091 │
│ Angola       │   12127071 │
│ Argentina    │   39921833 │
│ Australia    │   20264082 │
└──────────────┴────────────┘
```

Notice how you can chain the methods. Each method call returns a _new_`DuckDBPyRelation` representing the result of applying that operation. The actual query execution doesn't happen until a materializing method like `.show()`, `.fetchall()`, or `.df()` is called. This lazy execution is powerful!

This programmatic approach has a significant advantage over building SQL strings manually:

INFO: Programmatic Query Building
Building queries using the Relational API methods (\`.filter()\`, \`.project()\`, etc.) is generally safer and more maintainable than constructing SQL queries via string formatting or concatenation, especially when dealing with dynamic conditions or column selections based on user input or program logic. It helps avoid potential SQL injection vulnerabilities (as column/table names cannot be parameterized in standard SQL) and makes your code more readable and composable by breaking down complex queries into smaller, named relational objects.

You can also save intermediate steps as variables:

```python
Copy code

over_10m_population = population_relation.filter("Population > 10000000")

# Now reuse 'over_10m_population' for different analyses
# Find average population per region for these large countries
# Also include the count of countries per region in the same aggregate
(over_10m_population
 .aggregate("""
    Region,
    count(*) AS country_count,
    CAST(avg(Population) AS int) AS avg_pop
    """) # Aggregates on Region and computes count and average
 .order("avg_pop DESC")
 .show()
)
```

```bash
Copy code

┌─────────────────────────────────────┬───────────────┬───────────┐
│               Region                │ country_count │  avg_pop  │
│               varchar               │     int64     │   int32   │
├─────────────────────────────────────┼───────────────┼───────────┤
│ ASIA (EX. NEAR EAST)                │            19 │ 192779730 │
│ NORTHERN AMERICA                    │             2 │ 165771574 │
│ LATIN AMER. & CARIB                 │            10 │  48643375 │
│ C.W. OF IND. STATES                 │             5 │  48487549 │
│ WESTERN EUROPE                      │             9 │  38955933 │
│ NORTHERN AFRICA                     │             4 │  38808343 │
│ NEAR EAST                           │             5 │  32910924 │
│ SUB-SAHARAN AFRICA                  │            21 │  30941436 │
│ EASTERN EUROPE                      │             3 │  23691959 │
│ OCEANIA                             │             1 │  20264082 │
├─────────────────────────────────────┴───────────────┴───────────┤
│ 10 rows                                               3 columns │
└─────────────────────────────────────────────────────────────────┘
```

### Relational Set Operations and Joins

The relational API also includes methods for set operations and joins, allowing you to combine or compare relations programmatically.

Let's find countries with _under_ 10 million population by using the `except_` method to subtract the `over_10m_population` relation from the original `population_relation`:

```python
Copy code

under_10m_population = population_relation.except_(over_10m_population)

# Now aggregate the under 10m countries by region
(under_10m_population
 .aggregate("""
    Region,
    count(*) AS country_count,
    CAST(avg(Population) AS int) AS avg_pop
    """)
 .order("avg_pop DESC")
 .show()
)
```

```bash
Copy code

┌─────────────────────────────────────┬───────────────┬─────────┐
│               Region                │ country_count │ avg_pop │
│               varchar               │     int64     │  int32  │
├─────────────────────────────────────┼───────────────┼─────────┤
│ EASTERN EUROPE                      │             9 │ 5426538 │
│ C.W. OF IND. STATES                 │             7 │ 5377686 │
│ SUB-SAHARAN AFRICA                  │            30 │ 3322228 │
│ NORTHERN AFRICA                     │             2 │ 3086881 │
│ ASIA (EX. NEAR EAST)                │             9 │ 2796374 │
│ NEAR EAST                           │            11 │ 2773978 │
│ WESTERN EUROPE                      │            19 │ 2407190 │
│ BALTICS                             │             3 │ 2394991 │
│ LATIN AMER. & CARIB                 │            35 │ 2154024 │
│ OCEANIA                             │            20 │  643379 │
│ NORTHERN AMERICA                    │             3 │   43053 │
├─────────────────────────────────────┴───────────────┴─────────┤
│ 11 rows                                             3 columns │
└───────────────────────────────────────────────────────────────┘
```

Now, let's find countries that are both in 'EASTERN EUROPE' _and_ have a population over 10 million using `intersect`:

```python
Copy code

# Filter for Eastern Europe
eastern_europe = population_relation.filter("Region ~ '.*EASTERN EUROPE.*'") # Using SIMILAR TO shorthand

# Find the intersection of Eastern Europe countries and those over 10m
(eastern_europe
 .intersect(over_10m_population)
 .project("Country, Population")
 .show()
)
```

```bash
Copy code

┌─────────────────┬────────────┐
│     Country     │ Population │
│     varchar     │   int64    │
├─────────────────┼────────────┤
│ Czech Republic  │   10235455 │
│ Romania         │   22303552 │
│ Poland          │   38536869 │
└─────────────────┴────────────┘
```

Finally, let's look at a simple `join` example. Suppose you had another relation, maybe containing region nicknames. You can simulate this by creating a relation from Python data (this requires Pandas/Arrow, you'll cover that more later, but the `from_arrow` or `from_df` methods can create relations):

```python
Copy code

import pandas as pd

# Create a simple DataFrame of region nicknames
region_nicknames_df = pd.DataFrame({
    'Region': [\
        'ASIA (EX. NEAR EAST)     ',\
        'NORTHERN AMERICA       ',\
        'LATIN AMER. & CARIB      ',\
        'C.W. OF IND. STATES      ',\
        'WESTERN EUROPE           '\
    ],
    'Nickname': [\
        'Asian Tigers',\
        'North America',\
        'Latin America',\
        'CIS States',\
        'Western Europe'\
    ]
})

# Convert DataFrame to a DuckDBPyRelation using the correct method
region_nicknames_rel = con.from_df(region_nicknames_df)

# Trim spaces in the region names for a clean join using the built-in trim() function.
population_trimmed = population_relation.project("Country, Population, trim(Region) as Region")
nicknames_trimmed = region_nicknames_rel.project("trim(Region) as Region, Nickname")

# Perform an inner join on the trimmed Region names
(population_trimmed
 .join(nicknames_trimmed, on="Region")
 .project("Country, Population, Nickname")
 .limit(5)
 .show()
)
```

```bash
Copy code

┌────────────────────┬────────────┬────────────────┐
│      Country       │ Population │    Nickname    │
│      varchar       │   int64    │    varchar     │
├────────────────────┼────────────┼────────────────┤
│ Afghanistan        │   31056997 │ Asian Tigers   │
│ Andorra            │      71201 │ Western Europe │
│ Anguilla           │      13477 │ Latin America  │
│ Antigua & Barbuda  │      69108 │ Latin America  │
│ Argentina          │   39921833 │ Latin America  │
└────────────────────┴────────────┴────────────────┘
```

You can even use these relation objects directly within standard SQL queries executed via `con.sql()`:

```python
Copy code

con.sql("""
-- Query the 'over_10m_population' relation directly in SQL
SELECT Country, "GDP ($ per capita)"
FROM over_10m_population
WHERE "GDP ($ per capita)" > 29000
LIMIT 5
""").show()
```

```bash
Copy code

┌────────────────┬────────────────────┐
│    Country     │ GDP ($ per capita) │
│    varchar     │       int64        │
├────────────────┼────────────────────┤
│ Belgium        │              29100 │
│ Canada         │              29800 │
│ United States  │              37800 │
└────────────────┴────────────────────┘
```

Ah, much better! Belgium, Canada, and the United States fit the bill. The point is, `over_10m_population`, which is a Python object representing a filtered relation, can be referenced directly in the `FROM` clause of a standard SQL query. Pretty slick! This demonstrates how the Relational API and standard SQL can complement each other.

## Wrapping Up

DuckDB's Python integration provides a practical middle ground between the simplicity of working with files and the power of SQL databases. The combination of direct file reading, in-memory processing, and both SQL and programmatic query interfaces makes it a solid tool for data analysis workflows.

The key concepts you've covered – connections, the `DuckDBPyRelation` object, direct file ingestion, and the relational API – form the foundation for most DuckDB operations. These features will streamline many of your data exploration tasks, particularly when working with files that are too large for comfortable Pandas operations but don't warrant setting up a full database server.

INFO: Extend with MotherDuck
While this guide focuses on local DuckDB, \*\*MotherDuck\*\* extends these capabilities to a serverless, collaborative environment. With Motherduck, you can query data stored in the cloud, share databases with colleagues, and leverage the convenience of a managed service. [Explore MotherDuck](https://motherduck.com/) to see how it complements your DuckDB workflows.

In the [next part](https://motherduck.com/learn-more/duckdb-python-quickstart-part2), you'll explore DuckDB's integrations with Pandas, Polars, and Arrow, along with Python user-defined functions for custom data transformations. These integrations are where DuckDB really starts to quack up the productivity gains in a typical Python data workflow.

### TABLE OF CONTENTS

[Getting Started: Installation and Connection](https://motherduck.com/learn-more/duckdb-python-quickstart-part1/#getting-started-installation-and-connection)

[Your First Queries: \`sql\`](https://motherduck.com/learn-more/duckdb-python-quickstart-part1/#your-first-queries-sql)

[Ingesting Data: From Files to Relations](https://motherduck.com/learn-more/duckdb-python-quickstart-part1/#ingesting-data-from-files-to-relations)

[The Relational API: Building Queries Programmatically](https://motherduck.com/learn-more/duckdb-python-quickstart-part1/#the-relational-api-building-queries-programmatically)

[Wrapping Up](https://motherduck.com/learn-more/duckdb-python-quickstart-part1/#wrapping-up)

Start using MotherDuck now!

[Try 21 Days Free](https://app.motherduck.com/?auth_flow=signup)

Start using MotherDuck now!

[Try 21 Days Free](https://app.motherduck.com/?auth_flow=signup)

Authorization Response