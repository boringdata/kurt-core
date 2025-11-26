---
title: analyze-json-data-using-sql
content_type: tutorial
source_url: https://motherduck.com/blog/analyze-json-data-using-sql
indexed_at: '2025-11-25T19:56:20.007742'
content_hash: f6b3e80e1a28155a
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Analyze JSON Data Using SQL and DuckDB

2024/01/10 - 12 min read

BY
David Neal

You have a deadline flying in fast and a boatload of data to dive through. You extract the data archive to discover all the files have a “.json” extension. Oh, no. JSON is for programmers, right? What do you do now?

No need to get your feathers in a fluff! DuckDB to the rescue!

DuckDB is a featherlight yet powerful database that supports querying lots of data formats directly using SQL. It can query data locally on disk, in memory, in the cloud, or combine data from multiple sources in a single query!

In this post, we'll guide you through querying JSON data using DuckDB. You'll learn how to target the data you need with the precision of a duck snatching its favorite bread. Let’s get quacking on how to query JSON data with DuckDB!

## Prerequisites

- Install DuckDB (instructions below).
- Optional: View or download the [sample JSON data](https://github.com/reverentgeek/duckdb-json-tutorial) used in this tutorial.

## What is JSON?

JSON, which stands for JavaScript Object Notation, is a lightweight data format. It is designed to be fairly easy for humans to read and write, and easy for machines to parse and generate, making it a great way to share data. It was originally created for Web applications to share data between the browser and server and has become a standard for storing and sharing data in many other types of applications. Outside of the browser, JSON is typically stored in a text file with a `.json` extension.

Let’s waddle through some of the basics of JSON! JSON is built on two basic structures:

- A collection of one or more name/value pairs surrounded by curly braces {}, each pair separated by commas.
- A list of one or more values surrounded by brackets \[\], each value separated by commas.

Here’s an example:

```json
Copy code

{
  "ducks": [\
    {\
      "name": "Quackmire",\
      "color": "green",\
      "actions": [\
        "swimming",\
        "waddling",\
        "quacking"\
      ]\
    },\
    {\
      "name": "Feather Locklear",\
      "color": "yellow",\
      "actions": [\
        "sunbathing"\
      ]\
    },\
    {\
      "name": "Duck Norris",\
      "color": "brown",\
      "actions": [\
        "karate chopping bread"\
      ]\
    }\
  ],
  "totalDucks": 3
}
```

- All of the data is wrapped in curly braces {}, like a cozy nest.
- Each duck is part of a "ducks" array (like a flock of ducks in a row), wrapped by square brackets \[\].
- Each duck in the array is a set of "name/value" pairs. For example, "name": "Duck Norris" tells us one duck's name is Duck Norris.

Curly braces {} are used to represent an object. You might also think of an object as a record, thing, or entity. The name/value pairs are sometimes called properties. The value associated with the name can represent text (a string), a number, true/false (a boolean), a collection of values (an array), or a nested object. An array is represented by square brackets \[\] and can be an ordered list of strings, numbers, booleans, or objects.

The JSON format can represent data structures ranging from simple to complex with nested objects and arrays! This makes it a great way to express and exchange data.

## Install and execute DuckDB

If you don’t already have DuckDB installed, flap on over to [duckdb.org](https://duckdb.org/#quickinstall) and follow the instructions for your operating system. In this tutorial, you’ll be using DuckDB from the command line.

- _Mac:_ Follow the Homebrew (`brew`) install instructions.
- _Windows:_ Follow the `winget` install instructions.
- _Linux:_ Download the appropriate archive for your OS and processor. Extract the `duckdb` executable binary from the archive to a folder where you easily execute it from your terminal.

### Launch DuckDB from the command line

After installing DuckDB, open (or reopen) your terminal or command prompt and enter the following to start an in-memory session of DuckDB.

```sh
Copy code

duckdb
```

_Note: If you are running Linux, you’ll want to change the current directory to where you extracted the binary and use `./duckdb` to execute the binary_

If all goes to plan, you should see a new `D` prompt ready for a command or SQL query, similar to the following.

```sh
Copy code

Enter ".help" for usage hints.
Connected to a transient in-memory database.
Use ".open FILENAME" to reopen on a persistent database.
D
```

### Run your first DuckDB SQL query

From the `D` prompt on the command line, type in the following SQL query and press enter. Don’t forget to include the semicolon at the end! SQL queries can span multiple lines, and the semicolon lets DuckDB know you are finished writing the query and it’s ready to execute.

```sql
Copy code

SELECT current_date - 7;
```

The result returned should be the date from seven days ago. `current_date` is one of many SQL functions available, and can be useful for including in query results or filtering data.

## Query JSON files with DuckDB

This ability to query raw files directly is the foundation of a modern [No-ETL approach](https://motherduck.com/learn-more/no-etl-query-raw-files/), which helps startups and lean teams avoid costly data engineering. In many cases, you can query data directly from a JSON file by specifying a path to the file.

- Create a new text file named `ducks.json` and open it in a text editor.
- Paste the following JSON data into the file and save it.

```js
Copy code

[\
  {\
    "id": "kA0KgL",\
    "color": "red",\
    "firstName": "Marty",\
    "lastName": "McFly",\
    "gender": "male"\
  },\
  {\
    "id": "dx3ngL",\
    "color": "teal",\
    "firstName": "Duckota",\
    "lastName": "Fanning",\
    "gender": "female"\
  },\
  {\
    "id": "FQ4dU1",\
    "color": "yellow",\
    "firstName": "Duck",\
    "lastName": "Norris",\
    "gender": "male"\
  },\
  {\
    "id": "JqS7ZZ",\
    "color": "red",\
    "firstName": "James",\
    "lastName": "Pond",\
    "gender": "male"\
  },\
  {\
    "id": "ZM5uJL",\
    "color": "black",\
    "firstName": "Darth",\
    "lastName": "Wader",\
    "gender": "male"\
  }\
]
```

With DuckDB running at the command line, paste the following query and press ENTER.

```sql
Copy code

SELECT * FROM './ducks.json';
```

The results should look similar to the following.

```sh
Copy code

D SELECT * FROM './ducks.json';
┌─────────┬─────────┬───────────┬──────────┬─────────┐
│   id    │  color  │ firstName │ lastName │ gender  │
│ varchar │ varchar │  varchar  │ varchar  │ varchar │
├─────────┼─────────┼───────────┼──────────┼─────────┤
│ kA0KgL  │ red     │ Marty     │ McFly    │ male    │
│ dx3ngL  │ teal    │ Duckota   │ Fanning  │ female  │
│ FQ4dU1  │ yellow  │ Duck      │ Norris   │ male    │
│ JqS7ZZ  │ red     │ James     │ Pond     │ male    │
│ ZM5uJL  │ yellow  │ Darth     │ Wader    │ male    │
├─────────┴─────────┴───────────┴──────────┴─────────┤
│ 5 rows                                   5 columns │
└────────────────────────────────────────────────────┘
```

### Change DuckDB’s output display

If you’re not 100% satisfied with DuckDB’s output to the console, there are lots of choices to customize the output. Type the following command to list the available output modes.

```sh
Copy code

.help .mode
```

Try switching the output mode to column display and rerun the last query to see the difference.

```sh
Copy code

.mode column
```

```sql
Copy code

D SELECT * FROM './ducks.json';
id      color   firstName  lastName  gender
------  ------  ---------  --------  ------
kA0KgL  red     Marty      McFly     male
dx3ngL  teal    Duckota    Fanning   female
FQ4dU1  yellow  Duck       Norris    male
JqS7ZZ  red     James      Pond      male
ZM5uJL  black   Darth      Wader     male
```

Experiment with other output modes until you find the one you like the most! If you want to switch back to the default DuckDB output mode, use the following command.

```sh
Copy code

.mode duckbox
```

### Query multiple JSON files at once

You can query across multiple files at once using path wildcards. For example, to query all files that end with `.json`:

```sh
Copy code

SELECT * FROM './*.json';
```

You can query from specific files, too, such as:

```sh
Copy code

SELECT * FROM './monthly-sales-2023*.json';
```

### Join JSON files together

Just like joining tables together, if there is a common key in one or more different data files, you can join on that key.

In this example, we have one JSON file that contains a list of ducks in a sanctuary, including ID, name, and color. In another JSON file there is a log of all the the things the ducks were observed doing, surveyed every 10 minutes for a month. This second file has the date and time of the log, the action, and only the ID of the duck. To create a report that summarizes the ducks' activities, you would want to join them together.

```sql
Copy code

SELECT ducks.firstName || ' ' || ducks.lastName AS duck_name,
    samples.action,
    COUNT(*) AS observations
FROM    './samples.json' AS samples
JOIN    './ducks.json' AS ducks ON ducks.id = samples.id
GROUP BY ALL
ORDER BY 1, 3 DESC;
```

```sh
Copy code

┌────────────────┬─────────────────────────┬──────────────┐
│   duck_name    │         action          │ observations │
│    varchar     │         varchar         │    int64     │
├────────────────┼─────────────────────────┼──────────────┤
│ Captain Quack  │ sleeping                │          890 │
│ Captain Quack  │ quacking                │          632 │
│ Captain Quack  │ eating                  │          623 │
│ Captain Quack  │ annoying                │          594 │
│ Captain Quack  │ swimming                │          356 │
│ Captain Quack  │ waddling                │          351 │
│ Captain Quack  │ sunbathing              │          348 │
│ Captain Quack  │ twitching               │          125 │
│ Captain Quack  │ flying                  │          121 │
│ Captain Quack  │ dancing                 │          117 │
│ Captain Quack  │ diving                  │          106 │
│ Captain Quack  │ posting on social media │           57 │
...
```

### Import JSON data into DuckDB for further analysis

If you have a lot of different JSON files, it might make sense to import the data into tables in your local DuckDB database. In the following example, you'll import the `ducks.json` file and `samples.json` together into one table.

```sql
Copy code

CREATE OR REPLACE TABLE duck_samples AS
SELECT CAST(samples.sampleTime AS date) AS sample_date,
    ducks.firstName || ' ' || ducks.lastName AS duck_name,
    samples.action,
    COUNT(*) AS observations
FROM    read_json('./samples.json', columns = { id: 'varchar', sampleTime: 'datetime', action: 'varchar' }) AS samples
JOIN    './ducks.json' AS ducks ON ducks.id = samples.id
GROUP BY ALL;
```

This example uses the `read_json` function to customize the schema of the imported data, which can be useful for converting dates and times as the data is read and parsed from the JSON data.

With the `duck_samples` table populated, we can now use it to analyze the data in new ways, such as number of actions performed by all ducks on a given day.

```sql
Copy code

SELECT ds.sample_date,
    ds.action,
    ds.observations,
    round(( ds.observations / totals.total_obs ) * 100, 1) AS percent_total
FROM ( SELECT sample_date, action, SUM(observations) AS observations FROM duck_samples GROUP BY ALL ) AS ds
    JOIN ( SELECT sample_date, SUM(observations) AS total_obs FROM duck_samples GROUP BY ALL ) AS totals
    ON ds.sample_date = totals.sample_date
WHERE ds.sample_date = '2024-01-01'
GROUP BY ALL
ORDER BY 3 DESC;

┌─────────────┬─────────────────────────┬──────────────┬───────────────┐
│ sample_date │         action          │ observations │ percent_total │
│    date     │         varchar         │    int128    │    double     │
├─────────────┼─────────────────────────┼──────────────┼───────────────┤
│ 2024-01-01  │ sleeping                │         1551 │          21.5 │
│ 2024-01-01  │ quacking                │          978 │          13.6 │
│ 2024-01-01  │ eating                  │          977 │          13.6 │
│ 2024-01-01  │ annoying                │          947 │          13.2 │
│ 2024-01-01  │ swimming                │          612 │           8.5 │
│ 2024-01-01  │ waddling                │          600 │           8.3 │
│ 2024-01-01  │ sunbathing              │          598 │           8.3 │
│ 2024-01-01  │ flying                  │          231 │           3.2 │
│ 2024-01-01  │ diving                  │          220 │           3.1 │
│ 2024-01-01  │ twitching               │          208 │           2.9 │
│ 2024-01-01  │ dancing                 │          193 │           2.7 │
│ 2024-01-01  │ posting on social media │           85 │           1.2 │
├─────────────┴─────────────────────────┴──────────────┴───────────────┤
│ 12 rows                                                    4 columns │
└──────────────────────────────────────────────────────────────────────┘
```

## Query complex JSON data

Depending on the structure of the JSON data you are working with it may be necessary to extract values from nested objects or arrays. Nested objects are referred to in DuckDB as a `struct` data type. In some cases, it's possible to access data directly in a struct using syntax that resembles schema or table namespaces. For example, imagine you have JSON file named `ducks-nested-name.json` with the following data.

```json
Copy code

[\
  {\
    "color": "red",\
    "name": {\
      "firstName": "Marty",\
      "lastName": "McFly"\
    },\
    "gender": "male"\
  },\
  {\
    "color": "teal",\
    "name": {\
      "firstName": "Duckota",\
      "lastName": "Fanning"\
    },\
    "gender": "female"\
  },\
  {\
    "color": "yellow",\
    "name": {\
      "firstName": "Duck",\
      "lastName": "Norris"\
    },\
    "gender": "male"\
  }\
]
```

If you query the file directly, the results would like the following.

```sql
Copy code

D SELECT * FROM './ducks-nested-name.json';

┌─────────┬─────────────────────────────────────────────┬─────────┐
│  color  │                    name                     │ gender  │
│ varchar │ struct(firstname varchar, lastname varchar) │ varchar │
├─────────┼─────────────────────────────────────────────┼─────────┤
│ red     │ {'firstName': Marty, 'lastName': McFly}     │ male    │
│ teal    │ {'firstName': Duckota, 'lastName': Fanning} │ female  │
│ yellow  │ {'firstName': Duck, 'lastName': Norris}     │ male    │
└─────────┴─────────────────────────────────────────────┴─────────┘
```

You can access the nested values under `name` using the following syntax.

```sql
Copy code

D SELECT color, name.firstName FROM './ducks-nested-name.json';

┌─────────┬───────────┐
│  color  │ firstName │
│ varchar │  varchar  │
├─────────┼───────────┤
│ red     │ Marty     │
│ teal    │ Duckota   │
│ yellow  │ Duck      │
└─────────┴───────────┘
```

DuckDB provides the `unnest` function to help when dealing with nested data. Taking the first example with Quackmire, Feather Locklear, and Duck Norris, if you query this JSON data without using `unnest`, you'll see the following results.

```sh
Copy code

┌─────────────────────────────────────────────────────────────────┬────────────┐
│                              ducks                              │ totalDucks │
│   struct("name" varchar, color varchar, actions varchar[])[]    │   int64    │
├─────────────────────────────────────────────────────────────────┼────────────┤
│ [{'name': Quackmire, 'color': green, 'actions': [swimming, wa…  │          3 │\
└─────────────────────────────────────────────────────────────────┴────────────┘\
```\
\
To make better use of the data in the `ducks` column, use the `unnest` function to destructure and flatten the data into their own columns.\
\
```sql\
Copy code\
\
D SELECT unnest(ducks, recursive:= true) AS ducks\
FROM './ducks-example.json';\
\
┌──────────────────┬─────────┬────────────────────────────────┐\
│       name       │  color  │            actions             │\
│     varchar      │ varchar │           varchar[]            │\
├──────────────────┼─────────┼────────────────────────────────┤\
│ Quackmire        │ green   │ [swimming, waddling, quacking] │\
│ Feather Locklear │ yellow  │ [sunbathing]                   │\
│ Duck Norris      │ brown   │ [karate chopping bread]        │\
└──────────────────┴─────────┴────────────────────────────────┘\
```\
\
## Query JSON data from an API\
\
DuckDB can also parse data directly from APIs that return JSON. The following example uses the [TVmaze API](https://www.tvmaze.com/api), a public API for TV shows.\
\
```sql\
Copy code\
\
D SELECT show.name, show.type, show.summary\
FROM read_json('https://api.tvmaze.com/search/shows?q=duck',\
       auto_detect=true);\
\
┌──────────────────────┬──────────────┬────────────────────────────────────────────────────────────────┐\
│      show_name       │  show_type   │                            summary                             │\
│         json         │     json     │                              json                              │\
├──────────────────────┼──────────────┼────────────────────────────────────────────────────────────────┤\
│ "Duck Dynasty"       │ "Reality"    │ "<p>In <b>Duck Dynasty</b>, A&amp;E Network introduces the R…  │\
│ "Darkwing Duck"      │ "Animation"  │ "<p>In the city of St. Canard, the people are plagued by the…  │\
│ "Duck Dodgers"       │ "Animation"  │ "<p>Animated sci-fi series based on the alter ego of Looney …  │\
│ "Duck Patrol"        │ "Scripted"   │ "<p><b>Duck Patrol</b> deals with the activities of the offi…  │\
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘\
```\
\
## Learn more about DuckDB\
\
To learn more about what you can do with DuckDB, check out the [DuckDB Snippets Library](https://duckdbsnippets.com/) or download a free copy of [DuckDB in Action](https://motherduck.com/duckdb-book-brief).\
\
### TABLE OF CONTENTS\
\
[Prerequisites](https://motherduck.com/blog/analyze-json-data-using-sql/#prerequisites)\
\
[What is JSON?](https://motherduck.com/blog/analyze-json-data-using-sql/#what-is-json)\
\
[Install and execute DuckDB](https://motherduck.com/blog/analyze-json-data-using-sql/#install-and-execute-duckdb)\
\
[Query JSON files with DuckDB](https://motherduck.com/blog/analyze-json-data-using-sql/#query-json-files-with-duckdb)\
\
[Query complex JSON data](https://motherduck.com/blog/analyze-json-data-using-sql/#query-complex-json-data)\
\
[Query JSON data from an API](https://motherduck.com/blog/analyze-json-data-using-sql/#query-json-data-from-an-api)\
\
[Learn more about DuckDB](https://motherduck.com/blog/analyze-json-data-using-sql/#learn-more-about-duckdb)\
\
Start using MotherDuck now!\
\
[Try 21 Days Free](https://motherduck.com/get-started/)\
\
Get Started\
\
![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)\
\
### Subscribe to motherduck blog\
\
E-mail\
\
Subscribe to other MotherDuck Updates\
\
Submit\
\
## PREVIOUS POSTS\
\
[![Why Python Developers Need DuckDB (And Not Just Another DataFrame Library)](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fwhy_pythondev_1_22167e31bf.png&w=3840&q=75)](https://motherduck.com/blog/python-duckdb-vs-dataframe-libraries/)\
\
[2025/10/08 - Mehdi Ouazza](https://motherduck.com/blog/python-duckdb-vs-dataframe-libraries/)\
\
### [Why Python Developers Need DuckDB (And Not Just Another DataFrame Library)](https://motherduck.com/blog/python-duckdb-vs-dataframe-libraries)\
\
Understand why a database is much more than just a dataframe library\
\
[![DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_1_4_1_b6209aca06.png&w=3840&q=75)](https://motherduck.com/blog/announcing-duckdb-141-motherduck/)\
\
[2025/10/09 - Alex Monahan, Garrett O'Brien](https://motherduck.com/blog/announcing-duckdb-141-motherduck/)\
\
### [DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains](https://motherduck.com/blog/announcing-duckdb-141-motherduck)\
\
MotherDuck now supports DuckDB 1.4.1 and DuckLake 0.3, with new SQL syntax, faster sorting, Iceberg interoperability, and more. Read on for the highlights from these major releases.\
\
[View all](https://motherduck.com/blog/)\
\
Authorization Response