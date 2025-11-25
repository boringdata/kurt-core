---
title: just-enough-sql-for-ai
content_type: tutorial
source_url: https://motherduck.com/blog/just-enough-sql-for-ai
indexed_at: '2025-11-25T19:56:41.774519'
content_hash: 1d155bf9faf9e77d
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Just Enough SQL to be Dangerous with AI

2025/08/04 - 13 min read

BY

[Jacob Matson](https://motherduck.com/authors/jacob-matson/)
,
[Alex Monahan](https://motherduck.com/authors/alex-monahan/)

There's a massive amount of excitement around using Large Language Models (LLMs) for data analysis, and for good reason. The dream of simply "asking your data questions" in plain English is rapidly becoming a reality.

But while LLMs are incredibly powerful at writing code, they aren't magic. To use them effectively and, more importantly, safely, you need to be a good "pilot." You need to know how to ask the right questions, how to structure your data, and crucially, how to verify that the SQL the AI generates is actually correct and doing what you think it is. You wouldn't fly a plane without knowing how the controls work, and you shouldn't query your database with an AI without understanding the language it's speaking.

This guide will walk you through the absolute essentials of SQL. We're not trying to make you a database administrator; we're giving you just enough SQL to be effective, confident, and safe when using AI to analyze your data.

NOTE: Why DuckDB?
If you're an analyst using an LLM, your ideal database is a local, high-performance analytical engine, not a remote server. DuckDB is that engine. Its design was built for modern hardware with fast disks, many cores, and plentiful RAM. It runs in-process, creating a safe sandbox to test LLM-generated queries on local Parquet, CSV, or JSON files without touching a production system. Its 'single-node' architecture provides a zero-configuration environment that runs exceptionally fast on any machine. This approach quacks just right for its one true purpose: running complex analytical queries with maximum speed and minimum friction. And since it's fully ACID-compliant, you can even run transactions in a pinch. Ultimately, DuckDB is the fastest way to connect an AI to your data and start solving real problems.

## **Part 1: The Fundamentals - Asking Questions of Your Data**

Let's dive in and learn how to load data, grab a whole table, pick specific columns, add a calculated column, and filter rows.

#### **Getting Your Data into the Game**

First things first, you need data. DuckDB makes it incredibly easy to load data directly from a CSV file (or even a file sitting on a website). There's no complex import process; you just point DuckDB at the file.

NOTE: Installing DuckDB?
You will need to install the DuckDB CLI for this tutorial - head over to the \[installer page\](https://duckdb.org/docs/installation/) to get it.

With a single line of SQL, we can create a new table called weather from a CSV file containing weather data from Washington.

```sql
Copy code

CREATE TABLE weather AS
SELECT * FROM read_csv('https://raw.githubusercontent.com/motherduckdb/sql-tutorial/main/data/washington_weather.csv');
```

That's it! The `CREATE TABLE weather AS` command tells DuckDB to create a new table named weather, and the `SELECT * FROM read_csv(...)` part reads the data from the URL and puts it into our new table.

### **The Two Most Important Words in SQL: `SELECT` and `FROM`**

The foundation of every single query you'll ever write rests on two words: `SELECT` and `FROM`.

- `SELECT` specifies the columns you want to see.
- `FROM` specifies the table where those columns live.

To see all the data in our new weather table, you can use `SELECT *`, where the asterisk (\*) is a wildcard for "all columns."

```sql
Copy code

SELECT * FROM weather;
```

If you only want to see specific columns, you can list them out. This is great for focusing on just the data you need.

```sql
Copy code

SELECT name, date, temperature_min, temperature_max FROM weather;
```

### **Filtering for What You Need with `WHERE`**

Getting all your data is a good start, but usually, you're looking for something specific. The `WHERE` clause is your tool for filtering rows based on a condition.

For example, if you only want to see dates where the temperature was higher than 82°F, you can add a `WHERE` clause:

```sql
Copy code

SELECT * FROM weather WHERE temperature_obs > 82;
```

You can also combine conditions using AND or OR. Let's find the days where precipitation was over 2.5 inches _or_ the elevation was above 600 feet.

```sql
Copy code

SELECT * FROM weather WHERE precipitation > 2.5 OR elevation > 600;
```

NOTE: Quoting String vs Columns
In SQL, strings are indicated with single quotes, like so: 'my string value', and column names with double quotes, like so: "my column name". You'll only need to use double quotes for your column names if they contain spaces or special characters.

### **Making New Information with Calculated Columns**

Sometimes the most interesting insights come from data you create yourself. SQL lets you add new, "calculated" columns to your results on the fly. For instance, we can calculate the average daily temperature from the min and max temperatures.

```sql
Copy code

SELECT name, date, (temperature_max + temperature_min) / 2 AS mean_temperature FROM weather;
```

Here, we created a new column called `mean_temperature` that didn't exist in our original table. The AS keyword is how we give our new column a name.

### **Sorting Your Results with `ORDER BY`**

To make sense of your results, you'll often want to sort them. The `ORDER BY` clause lets you sort your rows based on a specific column. By default, it sorts in ascending order (ASC), but you can specify descending order with `DESC`.

Let's find the rainiest days by ordering our results by precipitation in descending order.

```sql
Copy code

SELECT name, date, precipitation
FROM weather
ORDER BY precipitation DESC;
```

## **Part 2: Shaping and Summarizing Data**

Now that you can select and filter data, let's move on to one of the most powerful features of SQL: summarizing and combining data.

### **Summarizing Thousands of Rows into One with `GROUP BY`**

Aggregate functions like `AVG()`, `MIN()`, `MAX()`, and `COUNT()` let you perform a calculation across many rows. When combined with a `GROUP BY` clause, you can perform these calculations on specific subsets of your data. This is the key to unlocking high-level insights.

Let's switch to a dataset of bird measurements. If we want to find the average beak dimensions _for each species_, we can `GROUP BY` the species name.

```sql
Copy code

-- First, let's create our tables for this section
CREATE TABLE birds AS SELECT * FROM read_csv('https://raw.githubusercontent.com/motherduckdb/sql-tutorial/main/data/birds.csv');

CREATE TABLE ducks AS SELECT * FROM read_csv('https://raw.githubusercontent.com/motherduckdb/sql-tutorial/main/data/ducks.csv');

-- Now, let's find the average beak measurements by species
SELECT
    Species_Common_Name,
    AVG(Beak_Width) AS Avg_Beak_Width,
    AVG(Beak_Depth) AS Avg_Beak_Depth,
    AVG(Beak_Length_Culmen) AS Avg_Beak_Length_Culmen
FROM birds
GROUP BY Species_Common_Name;
```

This query groups all the individual bird measurements by their common name and then calculates the average beak width, depth, and length for each of those groups.

### **Combining Datasets with `JOIN`**

Your data won't always live in a single table. A `JOIN` is how you combine rows from two or more tables based on a related column.

Let's say we want to analyze the measurements of only the birds that are ducks. We have a birds table with measurements and a ducks table with a list of duck species. We can join them on the species name.

An `INNER JOIN` (the default, so you can just write `JOIN`) combines rows only when there is a match in both tables.

```sql
Copy code

SELECT
    birds.Species_Common_Name,
    birds.Beak_Length_Culmen,
    ducks.author
FROM birds
    INNER JOIN ducks ON birds.Species_Common_Name = ducks.name;
```

Notice we prefixed the column names with the table name (e.g., `birds.Species_Common_Name`). This is a good practice for clarity, especially when tables have columns with the same name.

What if you want to keep all the rows from the first (or "left") table, even if there's no match in the second table? For that, you use a `LEFT JOIN`. This is useful for adding optional details. In our case, all birds will be listed, but only the ducks will have a value in the author column; for all other birds, it will be `NULL` (SQL's indicator for a missing value).

```sql
Copy code

SELECT
    birds.Species_Common_Name,
    birds.Beak_Length_Culmen,
    ducks.author
FROM birds
    LEFT JOIN ducks ON birds.Species_Common_Name = ducks.name;
```

## **Part 3: Writing Clean Queries for Complex Questions**

### **Organizing Your Logic with `WITH` (Common Table Expressions)**

As your questions get more complex, your queries can become long and hard to read. A subquery (a query inside another query) can quickly turn into a tangled mess.

This is where the `WITH` clause comes in. Think of it as a pro-tip for readability. A `WITH` clause, also known as a Common Table Expression (CTE), lets you break a complex query into logical, named steps. Each step creates a temporary, named result set that you can refer to in later steps.

This is absolutely critical for debugging what an LLM gives you. Instead of one giant, monolithic query, you get a readable, step-by-step recipe that's much easier to follow and verify.

### **Why CTEs Matter: A Before and After Example**

Let's see exactly why CTEs are so crucial when working with AI-generated SQL. Imagine you ask an AI: "Find all birds with above-average wing length for their species, but only for species where we have more than 10 samples."

An AI might generate this hard-to-verify subquery approach:

```sql
Copy code

-- This works but is harder to debug!
SELECT * FROM birds b1
WHERE wing_length > (
    SELECT AVG(wing_length)
    FROM birds b2
    WHERE b2.Species_Common_Name = b1.Species_Common_Name
)
AND Species_Common_Name IN (
    SELECT Species_Common_Name
    FROM birds
    GROUP BY Species_Common_Name
    HAVING COUNT(*) > 10
);
```

Can you quickly verify if this is correct? It's tough! The logic is buried in nested subqueries. Now look at the same query written with CTEs:

```sql
Copy code

WITH
    duck_beaks AS (
        SELECT
            column00 as id,
            Species_Common_Name,
            Beak_Length_Culmen
        FROM birds
            INNER JOIN ducks ON name = Species_Common_Name
        ),
    pc99_beak_len AS (
        SELECT QUANTILE_CONT(Beak_Length_Culmen, 0.99) AS Top_Beak_Length
        FROM duck_beaks
    )
SELECT
    duck_beaks.id,
    duck_beaks.Species_Common_Name,
    duck_beaks.Beak_Length_Culmen
FROM duck_beaks
    INNER JOIN pc99_beak_len ON duck_beaks.Beak_Length_Culmen > pc99_beak_len.Top_Beak_Length
ORDER BY duck_beaks.Beak_Length_Culmen DESC;
```

See how readable that is?

1. First, we create a temporary table duck\_beaks that contains only the measurements for ducks.
2. Second, we create pc99\_beak\_len to calculate the 99th percentile beak length from our duck\_beaks table.
3. Finally, we select the ducks from duck\_beaks whose beak length is greater than the value we calculated in our second step.

## **Part 3.5: Red Flags in AI-Generated SQL**

Before you start asking AI to write SQL for you, let's talk about the most common ways AI-generated queries can go wrong. Knowing these patterns will help you spot problems before they cause issues.

### **The Accidental Data Explosion**

**The Problem:** AI forgets to specify how tables should be joined, creating a "Cartesian product" where every row is matched with every other row.

```sql
Copy code

-- DANGER: This might return millions of rows!
SELECT * FROM orders
INNER JOIN customers ON 1=1

-- CORRECT: Always specify the join condition
SELECT * FROM orders
JOIN customers ON orders.customer_id = customers.id;
```

**Red Flag**: Look for `JOIN` conditions in the `FROM` clause with a condition that is always true!

### **The Silent Type Confusion**

**The Problem**: AI might compare numbers to strings or dates to text, leading to unexpected results.

```sql
Copy code

-- DANGER: Comparing string to number
SELECT * FROM sales WHERE amount > '1000';
-- This might work but could miss $999.99 vs $1000.00

-- CORRECT: Ensure consistent types
SELECT * FROM sales WHERE amount > 1000;
```

**Red Flag**: Watch for quotes around numbers or missing quotes around dates.

### **The Performance Trap**

**The Problem**: AI generates queries that technically work but are incredibly slow on large datasets.

```sql
Copy code

-- SLOW: Function on every row prevents index or statistic usage
SELECT * FROM events
WHERE YEAR(event_date) = 2024;

-- FAST: Allow database to use indexes & statistics
SELECT * FROM events
WHERE event_date >= '2024-01-01'
  AND event_date < '2025-01-01';
```

**Red Flag**: Functions applied to columns in WHERE clauses often prevent efficient filtering.

### **The Golden Rule: Start Small**

When testing AI-generated SQL, consider adding `LIMIT 10` first to verify the logic works correctly before running on your entire dataset. Once verified, remove the limit.

```sql
Copy code

-- Always test with a small sample first
SELECT * FROM complex_query_here
LIMIT 10;
```

_A side-note for those of you who have made this far_: MotherDuck’s [Instant SQL with Cmd + K](https://motherduck.com/blog/motherduck-ai-sql-fixit-inline-editing-features/) feature will do this for you and works brilliantly with AI.

## **Part 4: The Payoff - Putting Your SQL Skills to Work with AI**

Now for the fun part. Let's see how the SQL you've just learned empowers you to work with AI.

### **From English to SQL with MotherDuck**

MotherDuck has built-in AI functions that can translate your natural language questions directly into SQL. To use them, you first need to make sure your data is in MotherDuck. Let's load our birds table.

```sql
Copy code

-- This assumes you have signed up for MotherDuck and are connected.
CREATE OR REPLACE TABLE birds AS FROM 'https://raw.githubusercontent.com/motherduckdb/sql-tutorial/main/data/birds.csv';
```

Now, you can ask a question in plain English using `PRAGMA prompt_query()`.

```sql
Copy code

PRAGMA prompt_query('which bird has the largest wing length?');
```

MotherDuck's AI will analyze your question, look at the schema of the birds table, and run the SQL to get you the answer.

### **Trust, but Verify: Reading the AI's Mind**

This is the key takeaway of this entire post. The AI gave you an answer, but how do you know it's right? How did it interpret your question? Now that you know SQL, you're not just blindly trusting the AI. You can read its mind.

The `CALL prompt_sql()` function shows you the _exact_ SQL query the AI generated to answer your question.

```sql
Copy code

CALL prompt_sql('which bird has the largest wing length?');
```

This might return something like:

```sql
Copy code

SELECT * FROM birds ORDER BY wing_length DESC LIMIT 1;
```

Look at that! It's a query you can now completely understand. You see the `SELECT * FROM birds` to get all the data. You see the `ORDER BY wing_length DESC` to find the largest wing length first, and you see `LIMIT 1` to get only the top row. Because you learned the fundamentals, you can now verify the AI's logic and trust its answer.

## **Conclusion**

You've just learned the core concepts of `SQL`: `SELECT...FROM`, `WHERE`, `GROUP BY`, `JOIN`, and `WITH`. You've seen how to load, filter, aggregate, and combine data.

You don't need to be a SQL expert to leverage AI, but a foundational understanding is your superpower. It transforms you from a passive user who hopes the AI gets it right into an active, effective analyst who can confidently guide and verify these powerful new tools. You now have just enough SQL to be truly dangerous.

Ready to try it yourself? [Sign up for a free MotherDuck account](https://www.google.com/search?q=https://app.motherduck.com/login), load your own data, and start asking questions. Join our [Slack community](https://www.google.com/search?q=https://motherduck.com/slack) to share what you discover!

## **SQL Quick Reference Guide**

### **Essential SQL Commands**

#### **Basic Data Retrieval**

```sql
Copy code

-- Get all data from a table
SELECT * FROM table_name;

-- Get specific columns
SELECT column1, column2 FROM table_name;

-- Filter rows with conditions
SELECT * FROM table_name WHERE condition;

-- Sort results
SELECT * FROM table_name ORDER BY column_name DESC;
```

### **Creating Calculated Columns**

```sql
Copy code

-- Add a new calculated column
SELECT column1,
       (column2 + column3) / 2 AS new_column_name
FROM table_name;
```

### **Aggregating Data**

```sql
Copy code

-- Common aggregate functions
SELECT COUNT(*), AVG(column), MIN(column), MAX(column), SUM(column)
FROM table_name;

-- Group data and aggregate
SELECT group_column, AVG(value_column) AS avg_value
FROM table_name
GROUP BY group_column;
```

### **Combining Tables**

```sql
Copy code

-- Inner Join (only matching rows)
SELECT * FROM table1
JOIN table2 ON table1.id = table2.id;

-- Left Join (all rows from left table)
SELECT * FROM table1
LEFT JOIN table2 ON table1.id = table2.id;
```

### **Writing Clean Complex Queries**

```sql
Copy code

-- Use WITH for readable, step-by-step queries
WITH
    step1 AS (
        SELECT ... FROM ...
    ),
    step2 AS (
        SELECT ... FROM step1 ...
    )
SELECT ... FROM step2;
```

### **Remember**

| Keyword | Function |
| --- | --- |
| **SELECT** | chooses columns |
| **FROM** | specifies tables |
| **JOIN** | combines data from multiple tables |
| **WHERE** | filters rows |
| **GROUP BY** | creates groups for aggregation |
| **ORDER BY** | sorts results |
| **WITH** | breaks complex queries into readable steps |

_Always verify AI-generated SQL before trusting the results!_

### TABLE OF CONTENTS

[Part 1: The Fundamentals - Asking Questions of Your Data](https://motherduck.com/blog/just-enough-sql-for-ai/#part-1-the-fundamentals-asking-questions-of-your-data)

[Part 2: Shaping and Summarizing Data](https://motherduck.com/blog/just-enough-sql-for-ai/#part-2-shaping-and-summarizing-data)

[Part 3: Writing Clean Queries for Complex Questions](https://motherduck.com/blog/just-enough-sql-for-ai/#part-3-writing-clean-queries-for-complex-questions)

[Part 3.5: Red Flags in AI-Generated SQL](https://motherduck.com/blog/just-enough-sql-for-ai/#part-35-red-flags-in-ai-generated-sql)

[Part 4: The Payoff - Putting Your SQL Skills to Work with AI](https://motherduck.com/blog/just-enough-sql-for-ai/#part-4-the-payoff-putting-your-sql-skills-to-work-with-ai)

[Conclusion](https://motherduck.com/blog/just-enough-sql-for-ai/#conclusion)

[SQL Quick Reference Guide](https://motherduck.com/blog/just-enough-sql-for-ai/#sql-quick-reference-guide)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Introducing Mega and Giga Ducklings: Scaling Up, Way Up](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckling_sizes_social_cards_3c29d6c212.png&w=3840&q=75)](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/)

[2025/07/17 - Ryan Boyd](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale/)

### [Introducing Mega and Giga Ducklings: Scaling Up, Way Up](https://motherduck.com/blog/announcing-mega-giga-instance-sizes-huge-scale)

New MotherDuck instance sizes allow data warehousing users more flexibility for complex queries and transformations. Need more compute to scale up? Megas and Gigas will help!

[![MotherDuck's Latest AI Features: Smarter SQL Error Fixes and Natural Language Editing](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsql_flowstate_2_9bf9503dc8.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-ai-sql-fixit-inline-editing-features/)

[2025/07/25 - Hamilton Ulmer, Jacob Matson](https://motherduck.com/blog/motherduck-ai-sql-fixit-inline-editing-features/)

### [MotherDuck's Latest AI Features: Smarter SQL Error Fixes and Natural Language Editing](https://motherduck.com/blog/motherduck-ai-sql-fixit-inline-editing-features)

Stay in flow with MotherDuck's latest features. Real-time SQL feedback and natural language editing.

[View all](https://motherduck.com/blog/)

Authorization Response