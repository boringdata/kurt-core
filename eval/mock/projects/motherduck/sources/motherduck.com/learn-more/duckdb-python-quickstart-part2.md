---
title: 'DuckDB Python Quickstart (Part 2): Pandas, Arrow, Polars & Python UDFs'
content_type: tutorial
description: Take your DuckDB and Python skills further by learning how to query Pandas
  DataFrames directly with SQL. This guide shows you how to integrate with Arrow and
  Polars and extend DuckDB by writing your own custom Python UDFs.
published_date: '2025-11-21T00:00:00'
source_url: https://motherduck.com/learn-more/duckdb-python-quickstart-part2
indexed_at: '2025-11-25T10:52:39.097304'
content_hash: 92a22a3264093f33
has_code_examples: true
has_step_by_step: true
---

# DuckDB Python Quickstart (Part 2): Pandas, Arrow, Polars & Python UDFs

15 min readBYWelcome back to your DuckDB Python quickstart series! In [Part 1](https://motherduck.com/learn-more/duckdb-python-quickstart-part1/), you covered the essentials: getting DuckDB installed, making connections, executing basic SQL queries using the `.sql()`

and `.execute()`

methods, ingesting data directly from files, and leveraging the powerful Relational API for programmatic query building, including set operations and joins.

In this second part, you'll explore the features that truly make DuckDB a first-class citizen in the Python data ecosystem. You'll see how DuckDB seamlessly integrates with popular libraries like Pandas, Apache Arrow, and Polars, and how you can extend DuckDB's functionality by writing your own functions in Python.

Now you can pick up where you left off and see how DuckDB interacts with your existing Python data structures! And like last time, you can follow this tutorial through [this notebook](https://github.com/adisomani/duckdb-notebooks/blob/main/duckdb_python_quickstart-part2.ipynb) also.

## Integrating with the Python Data Ecosystem: Pandas, Arrow, Polars

This is where DuckDB really shines for data professionals living in the Python world. DuckDB is designed to work *with* your existing data structures, not just separate from them.

### Querying Pandas DataFrames

Got a Pandas DataFrame loaded in memory? You can query it directly as if it were a table.

Copy code

```
import pandas as pd
import duckdb
# Create a sample Pandas DataFrame
data = {'col1': [1, 2, 3, 4],
'col2': ['A', 'B', 'C', 'A']}
df = pd.DataFrame(data)
# Connect to DuckDB (in-memory for this example)
con = duckdb.connect(database=':memory:')
# Query the DataFrame using duckdb.sql() via the connection
result_relation = con.sql("SELECT * FROM df WHERE col2 = 'A'")
result_relation.show()
```


Copy code

```
┌───────┬─────────┐
│ col1 │ col2 │
│ int64 │ varchar │
├───────┼─────────┤
│ 1 │ A │
│ 4 │ A │
└───────┴─────────┘
```


That's it! DuckDB automatically recognizes the DataFrame variable `df`

in your Python environment (when using a connection or the default global connection) and makes it available as if it were a table in the `FROM`

clause. This is incredibly powerful for quickly querying, filtering, joining, or aggregating DataFrames using familiar SQL syntax, which can often be much faster than equivalent Pandas operations for certain types of queries, especially aggregates and complex joins on larger DataFrames.

You can also query the DataFrame using the relational API:

Copy code

```
# Query the DataFrame using the relational API via the connection
(con.sql("FROM df") # Start with the DataFrame as a relation
.filter("col2 = 'A'")
.show()
)
```


Copy code

```
┌───────┬─────────┐
│ col1 │ col2 │
│ int64 │ varchar │
├───────┼─────────┤
│ 1 │ A │
│ 4 │ A │
└───────┴─────────┘
```


INFO: SQLAlchemy Integration
For more complex applications requiring an Object-Relational Mapper (ORM) or a standard database interface like SQLAlchemy, you can use the `duckdb-engine` package (`pip install duckdb-engine`). This provides a SQLAlchemy dialect that allows you to interact with DuckDB using the full power of SQLAlchemy, including querying DataFrames registered with the engine.
### Getting Results as Pandas DataFrames

Going the other way is just as easy. Any `DuckDBPyRelation`

can be converted into a Pandas DataFrame using `.df()`

or `.fetchdf()`

.

Copy code

```
import duckdb
import pandas as pd
# Connect to DuckDB (or reuse connection)
con = duckdb.connect(database=':memory:')
con.sql("INSTALL httpfs")
con.sql("LOAD httpfs")
# Query a file or table to get a relation
population_relation = con.sql("SELECT Country, Population FROM read_csv_auto('https://bit.ly/3KoiZR0')")
# Convert the result relation to a Pandas DataFrame
population_df = population_relation.df()
print(type(population_df))
print(population_df.head())
```


Copy code

```
<class 'pandas.core.frame.DataFrame'>
Country Population
0 Afghanistan 31056997
1 Albania 3581655
2 Algeria 32930091
3 American Samoa 57794
4 Andorra 71201
```


This seamless back-and-forth between DuckDB relations and Pandas DataFrames removes a lot of the impedance mismatch you might face with other databases.

### Working with Apache Arrow and Polars

DuckDB also has deep integration with Apache Arrow, the standard for in-memory columnar data. Arrow enables zero-copy data transfer between DuckDB and other libraries that support Arrow, like Pandas (under the hood with newer versions), PyArrow itself, and the rapidly growing Polars library.

You can convert a DuckDB relation to an Arrow Table using `.arrow()`

or `.fetcharrow()`

, or the equivalent `.to_arrow_table()`

:

Copy code

```
import duckdb
import pyarrow as pa
# Make sure you have pyarrow installed: pip install pyarrow
# Connect to DuckDB (or reuse connection)
con = duckdb.connect(database=':memory:')
con.sql("INSTALL httpfs")
con.sql("LOAD httpfs")
# Get a relation (from a file, table, or query)
countries_relation = con.sql("SELECT Country, Region FROM read_csv_auto('https://bit.ly/3KoiZR0') LIMIT 10")
# Convert to an Apache Arrow Table
arrow_table = countries_relation.arrow() # Or countries_relation.to_arrow_table()
print(type(arrow_table))
print(arrow_table)
```


Copy code

```
<class 'pyarrow.lib.RecordBatchReader'>
<pyarrow.lib.RecordBatchReader object at 0x123a7b630>
```


Similarly, converting to a Polars DataFrame is just as easy with `.pl()`

(requires the `polars`

library installed: `pip install polars`

):

Copy code

```
import duckdb
import polars as pl
# Connect to DuckDB (or reuse connection)
con = duckdb.connect(database=':memory:')
con.sql("INSTALL httpfs")
con.sql("LOAD httpfs")
# Get a relation
countries_relation = con.sql("SELECT Country, Region FROM read_csv_auto('https://bit.ly/3KoiZR0') LIMIT 10")
# Convert to a Polars DataFrame
polars_df = countries_relation.pl()
print(type(polars_df))
print(polars_df)
```


Copy code

```
<class 'polars.dataframe.frame.DataFrame'>
shape: (10, 2)
┌────────────────────┬─────────────────────────────────┐
│ Country ┆ Region │
│ --- ┆ --- │
│ str ┆ str │
╞════════════════════╪═════════════════════════════════╡
│ Afghanistan ┆ ASIA (EX. NEAR EAST) │
│ Albania ┆ EASTERN EUROPE … │
│ Algeria ┆ NORTHERN AFRICA … │
│ American Samoa ┆ OCEANIA … │
│ Andorra ┆ WESTERN EUROPE … │
│ Angola ┆ SUB-SAHARAN AFRICA … │
│ Anguilla ┆ LATIN AMER. & CARIB │
│ Antigua & Barbuda ┆ LATIN AMER. & CARIB │
│ Argentina ┆ LATIN AMER. & CARIB │
│ Armenia ┆ C.W. OF IND. STATES │
└────────────────────┴─────────────────────────────────┘
```


INFO: Deferring Materialization
Converting a DuckDB relation to a Python DataFrame/Table (`.df()`, `.arrow()`, `.pl()`) materializes the entire result set in Python memory. For performance, it's generally recommended that you perform as many filtering, projection, aggregation, and joining steps as possible using DuckDB's SQL or Relational API *before* converting to a Python object. This allows DuckDB's optimized query engine to process the data efficiently, often without bringing everything into Python memory until the final result is needed.
Once you have data as an Arrow table, you can use `pyarrow.compute`

for further operations directly within Arrow if needed, though DuckDB often remains faster for many analytical queries:

Copy code

```
import pyarrow.compute as pc
import pyarrow as pa
# Convert RecordBatchReader to Table
arrow_table = arrow_table.read_all()
# Now you can use filter and select
filtered_arrow = arrow_table.filter(pc.match_substring(arrow_table['Country'], 'America'))
selected_arrow = filtered_arrow.select(['Country', 'Region'])
print("Filtered and Selected Arrow Table:")
print(selected_arrow)
```


Copy code

```
Filtered and Selected Arrow Table:
pyarrow.Table
Country: string
Region: string
----
Country: [["American Samoa "]]
Region: [["OCEANIA "]]
```


This interoperability makes DuckDB a fantastic glue layer for data pipelines involving various Python libraries.

## Extending DuckDB with Python: User-Defined Functions (UDFs)

WARNING: UDFs and MotherDuck Please note that User-Defined Functions (UDFs), as described in this section, are a feature of the local, embedded DuckDB Python library and**do not work on MotherDuck**. The reason is that UDFs require a Python runtime to execute the function's code. MotherDuck is a serverless platform that provides SQL execution but does not run user-provided Python code on its servers. The examples below are for local DuckDB usage within a Python environment.

Sometimes you need to perform an operation within your SQL query that's simply not available in standard SQL or DuckDB's built-in functions, but it's easy to do in Python. This is where User-Defined Functions (UDFs) come in. DuckDB lets you define Python functions and call them directly from your SQL queries.

Let's revisit the population data. Looking at the `Region`

column, there seem to be some extra spaces (padding) that make grouping or filtering tricky.

Copy code

```
import duckdb
# Connect to DuckDB and load population data
con = duckdb.connect(database=':memory:') # Or use the persistent DB file
con.sql("INSTALL httpfs")
con.sql("LOAD httpfs")
# Load the data into a table if it doesn't exist in this session
try:
con.sql("SELECT COUNT(*) FROM population")
except duckdb.CatalogException:
print("Loading population data from URL...")
con.sql("SELECT * FROM read_csv_auto('https://bit.ly/3KoiZR0')").to_table("population")
print("Population data loaded.")
con.sql("""
SELECT DISTINCT Region, length(Region) AS numChars
FROM population
""").show()
```


Copy code

```
Loading population data from URL...
Population data loaded.
┌─────────────────────────────────────┬──────────┐
│ Region │ numChars │
│ varchar │ int64 │
├─────────────────────────────────────┼──────────┤
│ WESTERN EUROPE │ 35 │
│ SUB-SAHARAN AFRICA │ 35 │
│ NEAR EAST │ 35 │
│ C.W. OF IND. STATES │ 20 │
│ BALTICS │ 35 │
│ ASIA (EX. NEAR EAST) │ 29 │
│ OCEANIA │ 35 │
│ NORTHERN AMERICA │ 35 │
│ NORTHERN AFRICA │ 35 │
│ EASTERN EUROPE │ 35 │
│ LATIN AMER. & CARIB │ 23 │
├─────────────────────────────────────┴──────────┤
│ 11 rows 2 columns │
└────────────────────────────────────────────────┘
```


See those character counts? 23 for "LATIN AMER. & CARIB" looks about right, but 35 for "BALTICS" (which is 7 characters long)? Definitely trailing spaces.

DuckDB has a built-in `trim()`

function, but for the sake of demonstration, you can write a Python UDF to remove leading/trailing spaces.

Copy code

```
def remove_spaces_py(field: str) -> str:
"""Removes leading/trailing spaces from a string."""
if field is not None:
# Use Python's strip()
return field.strip() # Python's strip() removes both leading/trailing
# Or use lstrip() and rstrip() specifically
# return field.lstrip().rstrip()
return field
# Register the Python function as a SQL function in DuckDB
con.create_function('remove_spaces_py', remove_spaces_py)
```


You defined a simple Python function `remove_spaces_py`

. You used type hints (`str`

for input and output), which helps DuckDB infer the SQL types (VARCHAR). Then, `con.create_function()`

registers this Python function under a name you can use in SQL (`remove_spaces_py`

).

### Introspecting Registered Functions

After registering a UDF, you can query DuckDB's built-in `duckdb_functions()`

table function to see information about all available functions, including your new one:

Copy code

```
con.sql("""
SELECT function_name, function_type, parameters, parameter_types, return_type
FROM duckdb_functions()
WHERE function_name = 'remove_spaces_py'
""").show()
```


Copy code

```
┌──────────────────┬───────────────┬────────────┬─────────────────┬─────────────┐
│ function_name │ function_type │ parameters │ parameter_types │ return_type │
│ varchar │ varchar │ varchar[] │ varchar[] │ varchar │
├──────────────────┼───────────────┼────────────┼─────────────────┼─────────────┤
│ remove_spaces_py │ scalar │ [col0] │ [VARCHAR] │ VARCHAR │
└──────────────────┴───────────────┴────────────┴─────────────────┴─────────────┘```
This introspection confirms your function is registered correctly with the inferred types.
Now, try using it in a query:
```python
con.sql("""
SELECT
Region AS original_region,
length(Region) AS len1,
remove_spaces_py(Region) AS cleaned_region,
length(remove_spaces_py(Region)) AS len2
FROM population
WHERE length(Region) > length(remove_spaces_py(Region)) -- Only show rows where trimming actually happened
LIMIT 3
""").show()
```


Copy code

```
┌─────────────────────────────────────┬───────┬──────────────────────┬───────┐
│ original_region │ len1 │ cleaned_region │ len2 │
│ varchar │ int64 │ varchar │ int64 │
├─────────────────────────────────────┼───────┼──────────────────────┼───────┤
│ ASIA (EX. NEAR EAST) │ 29 │ ASIA (EX. NEAR EAST) │ 20 │
│ EASTERN EUROPE │ 35 │ EASTERN EUROPE │ 14 │
│ NORTHERN AFRICA │ 35 │ NORTHERN AFRICA │ 15 │
└─────────────────────────────────────┴───────┴──────────────────────┴───────┘
```


Success! Your Python UDF `remove_spaces_py`

is correctly callable from SQL and does its job.

DuckDB usually does a good job inferring types from Python type hints. However, for clarity or if type hints are missing, you can explicitly specify the input and return types when registering the function:

Copy code

```
from duckdb.sqltypes import VARCHAR
# Remove the old function first (optional, but good practice if redefining)
try:
con.remove_function('remove_spaces_py')
except duckdb.InvalidInputException: # Function might not exist yet
pass
# Register again, explicitly specifying types
con.create_function(
'remove_spaces_py',
remove_spaces_py, # Use the Python function object
[VARCHAR], # List of input types (a single VARCHAR parameter)
VARCHAR # Return type (VARCHAR)
)
# Now you can use it just as before
```


### Real-World Data Cleaning: Handling Locale-Specific Decimals

A common data cleaning task is handling numbers formatted according to different regional conventions, such as using a comma (`,`

) as a decimal separator instead of a period (`.`

). If ingested without proper handling, these numbers might be treated as strings.

The population dataset you are using includes columns like `"Coastline (coast/area ratio)"`

and `"Pop. Density (per sq. mi.)"`

which appear to use the European comma format. You can define a Python UDF using the `locale`

module to convert these strings to numeric types.

First, make sure the `locale`

module is available and you have a locale installed that uses comma as a decimal separator (like 'de_DE' for German). You might need to configure your operating system's locales if they aren't available by default.

Copy code

```
import locale
from duckdb.sqltypes import DOUBLE, VARCHAR
# Define the Python function to convert locale-specific strings to float
def convert_locale_py(field: str) -> float:
"""Converts a locale-specific string (e.g., using comma decimal) to a float."""
if field is None:
return None
try:
# Set locale temporarily (consider thread safety in multi-threaded apps)
# You might need to adjust the locale string based on your system setup
original_locale = locale.getlocale(locale.LC_NUMERIC)
# The locale string can vary. 'de_DE.UTF-8' is common on Linux.
# On Windows, it might be 'German_Germany.1252' or just 'de'.
# On MacOS, it might be 'de_DE.UTF-8'.
# We'll try a few common ones.
locales_to_try = ['de_DE.UTF-8', 'de_DE', 'de', 'German']
for loc in locales_to_try:
try:
locale.setlocale(locale.LC_NUMERIC, loc)
break
except locale.Error:
continue
else:
# If no locale worked, we can't do the conversion this way.
# A more robust solution might be a simple string replace.
return float(field.replace(',', '.'))
# Use locale.atof to convert string to float based on locale settings
result = locale.atof(field)
# Restore original locale
locale.setlocale(locale.LC_NUMERIC, original_locale)
return result
except (ValueError, TypeError):
return None # Return None for conversion errors
# Register the function with DuckDB, specifying input and output types
con.create_function(
'convert_locale_py',
convert_locale_py,
[VARCHAR], # Expecting a VARCHAR input
DOUBLE # Returning a DOUBLE
)
```


*(Note: Handling locales can be system-dependent. The locale string 'de_DE.UTF-8' might need adjustment. Setting and restoring the locale is important in applications to avoid side effects. The code above includes fallback logic for robustness.)*

Now, use your `convert_locale_py`

function in a query to see how it transforms the data:

Copy code

```
con.sql("""
SELECT
"Coastline (coast/area ratio)" AS original_coastline,
convert_locale_py("Coastline (coast/area ratio)") AS cleaned_coastline_double,
"Pop. Density (per sq. mi.)" AS original_pop_density,
convert_locale_py("Pop. Density (per sq. mi.)") AS cleaned_pop_density_double
FROM population
LIMIT 5
""").show()
```


Copy code

```
┌────────────────────┬──────────────────────────┬──────────────────────┬────────────────────────────┐
│ original_coastline │ cleaned_coastline_double │ original_pop_density │ cleaned_pop_density_double │
│ varchar │ double │ varchar │ double │
├────────────────────┼──────────────────────────┼──────────────────────┼────────────────────────────┤
│ 0,00 │ 0.0 │ 48,0 │ 48.0 │
│ 1,26 │ 1.26 │ 124,6 │ 124.6 │
│ 0,04 │ 0.04 │ 13,8 │ 13.8 │
│ 58,29 │ 58.29 │ 290,4 │ 290.4 │
│ 0,00 │ 0.0 │ 152,1 │ 152.1 │
└────────────────────┴──────────────────────────┴──────────────────────┴────────────────────────────┘
```


Excellent! The UDF successfully converted the comma-separated strings to standard double-precision floating-point numbers.

This UDF capability opens the door to using any Python library within your SQL queries, from complex string manipulations with `re`

to mathematical functions with `numpy`

or `scipy`

, or even calling external APIs (though be mindful of performance implications for row-by-row processing).

Once you've verified the conversion, you can use `ALTER TABLE`

to change the column's data type permanently and apply the UDF to update the values in place:

Copy code

```
con.sql("""
ALTER TABLE population
ALTER "Coastline (coast/area ratio)"
SET DATA TYPE DOUBLE
USING convert_locale_py("Coastline (coast/area ratio)")
""")
con.sql("""
ALTER TABLE population
ALTER "Pop. Density (per sq. mi.)"
SET DATA TYPE DOUBLE
USING convert_locale_py("Pop. Density (per sq. mi.)")
""")
# You would repeat this for other columns needing locale conversion like
# "Birthrate", "Deathrate" etc.
# Verify the column type change
con.sql("DESCRIBE population").show()
```


Copy code

```
┌────────────────────────────────────┬─────────────┬─────────┬─────────┬─────────┬─────────┐
│ column_name │ column_type │ null │ key │ default │ extra │
│ varchar │ varchar │ varchar │ varchar │ varchar │ varchar │
├────────────────────────────────────┼─────────────┼─────────┼─────────┼─────────┼─────────┤
│ Country │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Region │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Population │ BIGINT │ YES │ NULL │ NULL │ NULL │
│ Area (sq. mi.) │ BIGINT │ YES │ NULL │ NULL │ NULL │
│ Pop. Density (per sq. mi.) │ DOUBLE │ YES │ NULL │ NULL │ NULL │
│ Coastline (coast/area ratio) │ DOUBLE │ YES │ NULL │ NULL │ NULL │
│ Net migration │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Infant mortality (per 1000 births) │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ GDP ($ per capita) │ BIGINT │ YES │ NULL │ NULL │ NULL │
│ Literacy (%) │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Phones (per 1000) │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Arable (%) │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Crops (%) │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Other (%) │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Climate │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Birthrate │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Deathrate │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Agriculture │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Industry │ VARCHAR │ YES │ NULL │ NULL │ NULL │
│ Service │ VARCHAR │ YES │ NULL │ NULL │ NULL │
├────────────────────────────────────┴─────────────┴─────────┴─────────┴─────────┴─────────┤
│ 20 rows 6 columns │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```


INFO: UDF Performance Considerations
While Python UDFs are incredibly flexible, they typically execute row-by-row and involve context switching between DuckDB's C++ execution engine and the Python interpreter. This can be slower than DuckDB's highly optimized vectorized native functions. You should use UDFs when a necessary operation *cannot* be done efficiently or at all in SQL, but prefer native SQL functions (`trim()`, `replace()`, etc.) for common tasks when available. For the locale conversion, using a UDF might be necessary if a suitable built-in function or reader option isn't available.
## Closing Time

When you're finished with a persistent database connection, it's good practice to close it:

Copy code

`con.close()`


This ensures any pending writes are flushed and resources are released. For in-memory databases created with `:memory:`

or the default `duckdb.sql()`

connection, this isn't strictly necessary as they live and die with the Python process or script execution, but it doesn't hurt.

## Wrapping Up

This two-part DuckDB Python quickstart has covered the essential features that make DuckDB such a powerful tool for data engineers, analysts, and scientists. Its embedded nature eliminates the overhead of managing a separate database server for local work. Its columnar architecture and vectorized execution make analytical queries on large datasets surprisingly fast.

But perhaps its biggest win is the deep integration with the Python data ecosystem. The ability to query Pandas DataFrames directly, seamlessly convert results to and from DataFrames, and leverage Arrow for efficient data transfer makes DuckDB feel like a natural extension of your Python data stack. The Relational API provides a robust, programmatic way to build queries, complementing standard SQL and enabling safer, more maintainable code. Add in the flexibility of Python UDFs for tackling custom cleaning and transformation tasks, and you have a powerful, high-performance tool that fits snugly into modern data workflows.

So next time you're faced with a pile of data files or a large DataFrame and need to slice and dice it with SQL or relational operations, don't groan about setting up a server. Just remember this DuckDB Python quickstart guide, and get quacking on your analysis!

Start using MotherDuck now!