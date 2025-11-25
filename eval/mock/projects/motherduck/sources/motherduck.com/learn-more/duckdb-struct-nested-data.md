---
title: 'DuckDB STRUCT: A Practical Guide for Handling Nested Data'
content_type: tutorial
description: Struggling with JSON or nested data in DuckDB? Learn how to use the STRUCT
  data type to group, access, and flatten complex data structures. This guide provides
  practical SQL examples to simplify your queries and make your schemas more readable.
published_date: '2025-11-23T00:00:00'
source_url: https://motherduck.com/learn-more/duckdb-struct-nested-data
indexed_at: '2025-11-25T10:52:49.327375'
content_hash: afd046744ee96fe9
has_code_examples: true
has_step_by_step: true
---

Okay, let's dive into the world of nested data in DuckDB, specifically the `STRUCT`

type. As a data engineer, you've certainly had your fair share of quacking with data that doesn't fit neatly into flat, rectangular tables. You know the drill: you get a JSON payload, maybe some event data from a system, or even just a set of related columns that really belong together conceptually, but smashing them into separate columns feels… well, clunky.

Dealing with this kind of semi-structured data in traditional relational databases can be a real headache. You either parse it out into a gazillion columns (hello, schema sprawl!) or stash it as a big text blob and deal with messy string manipulation later. Neither feels quite right.

This is where DuckDB's `STRUCT`

data type comes in, and frankly, it's a pretty neat tool to have in your belt. This article will walk you through what a `STRUCT`

is in DuckDB, why it's particularly useful for data folks, and how you can actually use it. You'll look at creating, accessing, and even "flattening" these nested structures with some practical examples. By the end of this, you should have a solid understanding of how `STRUCT`

s can help you manage and query complex data more effectively in DuckDB.

## So, What Exactly is a DuckDB STRUCT?

At its core, a `STRUCT`

in DuckDB is a way to group multiple related pieces of data, potentially of different data types, into a single column. Think of it like a mini-row or a record embedded within your main table row. It's a collection of named fields, called "entries" or "keys," each holding a value.

Conceptually, it's similar to the [ ROW](https://www.postgresql.org/docs/current/rowtypes.html) type you might find in PostgreSQL, but DuckDB's implementation has a key difference: every row in a

`STRUCT`

column must have the exact same keys with the same names and data types. This strict schema might seem limiting at first, but it's actually a deliberate design choice tied to [DuckDB's performance optimizations](https://duckdb.org/why_duckdb.html), allowing it to leverage its vectorized engine effectively. It ensures type consistency, which is always a good thing for correctness.

Using `STRUCT`

s can significantly improve the usability of wide tables, making column names easier to manage and understand by grouping related attributes.

Imagine you're tracking football match events. Instead of having separate columns for `event_type`

, `player_id`

, `event_timestamp`

, `coordinates_x`

, and `coordinates_y`

for every single event (a pass, a shot, a foul, etc.), you could have a single `event_details`

column of type `STRUCT`

that contains all of these as named fields.

It's also worth remembering that, like the schema of your table, the schema of a `STRUCT`

column is fixed once created. You cannot change the schema of a `STRUCT`

column in a table using `UPDATE`

operations directly by adding or removing keys. This is a design constraint to be aware of when you model your data.

## Creating STRUCTs: Packing the Data In

Alright, time to get your hands dirty. How do you actually create these `STRUCT`

s in DuckDB? There are a few ways.

The most explicit way is using the `struct_pack`

function. You specify the key names and the values you want to pack into the struct using the `:=`

operator. Notice that the key names don’t need single quotes here.

Copy code

```
SELECT struct_pack(
event_type := 'Pass',
player_id := 10,
event_timestamp := '2023-10-27 14:30:00'::TIMESTAMP,
coordinates := struct_pack(x := 85.5, y := 30.2) -- Yes, you can nest them!
) AS event_details;
```


Notice how you can even nest `STRUCT`

s within other `STRUCT`

s. The `coordinates`

field here is itself a `STRUCT`

with `x`

and `y`

keys.

A more concise way, and one you'll find yourself using often for quick ad-hoc queries or testing, is the curly brace `{}`

notation. You provide key-value pairs directly. Remember that key names here are strings, so they need single quotes.

Copy code

```
SELECT {
'event_type': 'Pass',
'player_id': 10,
'event_timestamp': '2023-10-27 14:30:00'::TIMESTAMP,
'coordinates': {'x': 85.5, 'y': 30.2} -- see the nesting again in the play
} AS event_details;
```


You can also create a `STRUCT`

from an existing row or subquery result:

Copy code

```
SELECT data AS my_struct
FROM (SELECT 'Penalty' AS event_type, 10 AS player_id) data;
```


DuckDB also provides a `row`

function, which is a special way to produce a `STRUCT`

. When you use `row()`

, it creates an unnamed `STRUCT`

(sometimes called a tuple), where the fields are accessed by their position (1-based index) rather than a name. However, when defining a table schema with a `STRUCT`

column, you'll typically define the named keys and their types explicitly, and the `row`

function can then be used to insert values into that defined structure.

Copy code

```
-- Defining a table with a STRUCT column
CREATE TABLE match_events (
match_id INTEGER,
event_details STRUCT(
event_type VARCHAR,
player_id INTEGER,
event_timestamp TIMESTAMP,
coordinates STRUCT(x DOUBLE, y DOUBLE)
)
);
-- Inserting data using the row function for the STRUCT
INSERT INTO match_events VALUES (
123,
row('Goal', 9, '2023-10-27 14:40:05'::TIMESTAMP, row(98.0, 50.0))
);
SELECT * FROM match_events;
```


This table now has a column `event_details`

where each entry holds a nested `STRUCT`

containing all the juicy details about an event in a match.

The `row`

function itself returns an unnamed struct, which you can see if you just select it directly:

Copy code

```
SELECT row(1, 'a'); -- Result: (1, a)
```


Interestingly, if you're selecting multiple expressions, the `row`

function is actually optional; the parentheses alone will pack them into an unnamed struct:

Copy code

```
SELECT (1, 'a') AS my_tuple; -- Result: (1, a)
```


## Accessing Data Within a STRUCT: Peeking Inside

Once you have data packed into a `STRUCT`

, you'll naturally want to get it back out. DuckDB offers a couple of intuitive ways to do this.

The most common method, and probably the easiest to read, is **dot notation**. Just use the name of the `STRUCT`

column, followed by a dot `.`

, and then the name of the key you want to access. If you have nested `STRUCT`

s, just keep adding dots!

Copy code

```
SELECT
match_id,
event_details.event_type AS event_type,
event_details.player_id AS player_id,
event_details.coordinates.x AS x_coordinate
FROM match_events
WHERE event_details.event_type = 'Goal';
```


This query directly accesses the `event_type`

and `player_id`

keys within the `event_details`

struct, and even drills down to the `x`

key within the nested `coordinates`

struct.

You can also use **bracket notation** `['key_name']`

. This is particularly useful if your key name contains spaces or special characters, though it's generally good practice to avoid those in key names if possible.

Copy code

```
-- Example with bracket notation
SELECT
match_id,
event_details['event_type'] AS event_type
FROM match_events;
```


Finally, there's the `struct_extract`

function, which is functionally equivalent to the dot and bracket notation for named structs.

Copy code

```
SELECT
match_id,
struct_extract(event_details, 'player_id') AS player_id
FROM match_events;
```


While `struct_extract`

works, the dot notation is usually preferred for readability unless you have a specific reason to use the function, like dynamically determining the key name, though that's a more advanced scenario.

For unnamed `STRUCT`

s (the tuples created by `row`

or simple parenthesized expressions), you access elements by their **1-based index** using bracket notation or `struct_extract`

:

Copy code

```
SELECT my_tuple[2]
FROM (SELECT row('a', 42, TRUE) AS my_tuple); -- Result: 42
SELECT struct_extract(my_tuple, 3)
FROM (SELECT ('a', 42, TRUE) AS my_tuple); -- Result: TRUE
```


## Working with STRUCTs: Adding and Modifying (Carefully!)

You might find yourself needing to add a new field to an existing `STRUCT`

value or modify a value within it. DuckDB provides the `struct_insert`

function for adding fields.

Copy code

```
SELECT struct_insert(
event_details,
expected_goals := 0.15 -- Adding an 'expected_goals' field
) AS event_details_with_xg
FROM match_events
LIMIT 1;
```


This creates a new `STRUCT`

value with the added field. It's important to note that `STRUCT`

s in DuckDB have a fixed schema defined when the column is created. As mentioned earlier, you **cannot change the schema of a STRUCT column in a table using UPDATE operations directly**. If you need to permanently add a new field to the


`event_details`

column for all rows, you'd typically need to recreate the table or migrate the data, defining the new `STRUCT`

schema with the added field. The `struct_insert`

function is more for ad-hoc transformations within a query.## Flattening STRUCTs: Spreading Out for Analysis

One of the most powerful things you can do with `STRUCT`

s, especially when dealing with semi-structured data loaded from sources like JSON or Parquet, is to "flatten" them. Flattening means taking the fields within a `STRUCT`

and turning them into individual columns in your result set. This is super handy for traditional analytical queries where you want to filter, group, and aggregate based on these nested values.

DuckDB gives you a couple of elegant ways to flatten `STRUCT`

s. The `unnest`

function is one option. While `unnest`

is perhaps more commonly associated with `LIST`

types, it works on `STRUCT`

s too, expanding their top-level keys into columns:

Copy code

```
SELECT unnest(event_details) FROM match_events;
/*
Result:
event_type player_id event_timestamp coordinates
Goal 9 2023-10-27 14:40:05 {'x': 98.0, 'y': 50.0}
*/
```


However, the most common and often cleanest way to flatten a `STRUCT`

into columns is using the [ star notation ](https://duckdb.org/docs/stable/sql/expressions/star.html). When you have a column that is a

`.*`

`STRUCT`

, you can select `column_name.*`

and DuckDB will automatically expand all the top-level keys of that `STRUCT`

into separate columns in your result.Let's say you want to analyze all the event details directly without constantly using dot notation.

Copy code

```
SELECT
match_id,
event_details.* -- Expands event_details struct into columns
FROM match_events;
```


This query would return columns like `match_id`

, `event_type`

, `player_id`

, `event_timestamp`

, and `coordinates`

(where `coordinates`

is still the nested `STRUCT`

). You could then, for example, select `event_details.coordinates.*`

to flatten the nested coordinates as well.

You can also use `.*`

with [ EXCLUDE](https://duckdb.org/docs/sql/query_syntax/select#exclude-clause) to flatten most fields but leave some nested or omit them entirely:

Copy code

```
SELECT event_details.* EXCLUDE (coordinates)
FROM match_events;
/*
Result (columns for event_type, player_id, event_timestamp, etc., but not coordinates):
event_type player_id event_timestamp
Goal 9 2023-10-27 14:40:05
*/
```


Or, more likely, you'd use `.*`

in a subquery or CTE to flatten and then select the individual columns you need for your analysis:

Copy code

```
WITH FlatEvents AS (
SELECT
match_id,
event_details.* -- Flatten the main event_details struct
FROM match_events
)
SELECT
match_id,
event_type,
player_id,
coordinates.x AS x, -- Access nested coordinate directly from the now-flattened struct
coordinates.y AS y
FROM FlatEvents
WHERE event_type = 'Goal';
```


This approach makes your subsequent SQL much cleaner and easier to read, allowing you to treat the struct's fields like regular columns. It's a really practical pattern when you're pulling data from a source that naturally produces nested structures.

## Comparing STRUCTs

While not as common as accessing or flattening, you can also compare `STRUCT`

s in DuckDB using standard comparison operators (`=`

, `<`

, `>`

, `<=`

, `>=`

). Comparisons work by comparing the fields **positionally from left to right based on the defined schema order** of the keys. It's similar to how row comparisons work.

When comparing two `STRUCT`

s, DuckDB looks at the values of the keys in their defined order. It compares the first key in both `STRUCT`

s. If they are different, the comparison result is determined there. If they are the same, it moves to the second key, and so on.

Copy code

```
-- Example comparison
SELECT {'k1': 2, 'k2': 3} < {'k1': 2, 'k2': 4} AS result; -- Result: true
SELECT {'k1': 'hello'} < {'k1': 'world'} AS result; -- Result: true
SELECT {'k2': 4, 'k1': 3} < {'k2': 2, 'k1': 4} AS result; -- Result: false (k2 compared first based on schema order)
```


This comparison behavior is quite useful for **sorting STRUCT columns or using them in WHERE or HAVING clauses**, allowing you to filter or order based on the nested values.

## A Practical Scenario

Imagine a project where you're pulling in logs from a microservice. The logs are JSON, and they have a nested `context`

field with all sorts of varying details depending on the log type. In a traditional database, you would have had to write some pretty gnarly ETL code to parse that JSON into a wide table, dealing with all the possible permutations of fields. It would feel like playing whack-a-mole with schemas.

When you start working with DuckDB and its nested types, particularly `STRUCT`

s (and [ MAPs](https://duckdb.org/docs/stable/sql/data_types/map.html) for truly dynamic keys, but that's another story!), you'll find it's a pleasant surprise. Being able to just load the JSON and then use dot notation or

`.*`

to explore and query the nested `context`

field will feel incredibly... natural. You won't need a complex ETL pipeline just to look at the data. It can significantly simplify your data ingestion and exploration phases. It's a lesser-known superpower for those used to rigid schemas.## Conclusion: Quacking Up Your Data Handling

Whether you're working with local files or connecting to [data in the cloud](https://motherduck.com/docs/key-tasks/authenticating-and-connecting-to-motherduck/connecting-to-motherduck/), perhaps even via something like [MotherDuck](https://motherduck.com/) for scale, understanding and leveraging `STRUCT`

s in DuckDB offers a powerful way to handle complex and hierarchical data directly within your SQL queries. It provides a clean way to group related information, **improves schema readability**, and **integrates well with DuckDB's performance-oriented architecture**. By understanding how to create, access, and manipulate `STRUCT`

s, you can write more expressive and efficient SQL queries, tackling data complexities head-on without resorting to awkward workarounds.

You've walked through the core concepts, seen how to build and deconstruct `STRUCT`

s, how to flatten them into standard columns, and touched on how they behave in **comparisons**. So the next time you see a chance to group some related columns or structure some semi-structured data, give the `STRUCT`

type a shot. You might be pleasantly surprised at how much quack-tastic it makes your queries!

Start using MotherDuck now!

## FAQS

### How can I use DuckDB's STRUCTs for large-scale, production data?

While DuckDB is excellent for local and in-process analytics, handling production-scale data, sharing results, and managing concurrent access requires a more robust solution. This is where MotherDuck comes in. MotherDuck is a serverless data warehouse built on DuckDB's powerful engine. You can develop your queries—including complex logic on STRUCT data—locally with DuckDB, and then seamlessly run them at scale on MotherDuck. It provides the separation of storage and compute, collaboration features, and reliability you need for a production data warehouse, all while keeping the DuckDB SQL you love.

### How can I query my local nested files (like Parquet or JSON) and join them with a larger, shared dataset in the cloud?

This is a common challenge where DuckDB's local power meets the need for collaboration and scale, and it's a perfect use case for MotherDuck. MotherDuck enables a unique hybrid execution model, allowing you to write a single SQL query that seamlessly joins data on your local machine with data stored centrally in your MotherDuck data warehouse. For example, you could analyze a new batch of log files (with complex STRUCT data) locally on your laptop and join them against a massive historical log table stored in MotherDuck to find trends. This gives you the best of both worlds: the speed of local processing for immediate analysis and the scale and collaborative power of a cloud data warehouse, all without needing to run a complex ETL process just to ask a question.