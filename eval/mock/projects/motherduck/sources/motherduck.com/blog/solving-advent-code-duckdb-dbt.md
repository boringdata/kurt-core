---
title: solving-advent-code-duckdb-dbt
content_type: blog
source_url: https://motherduck.com/blog/solving-advent-code-duckdb-dbt
indexed_at: '2025-11-25T19:58:13.168915'
content_hash: 63c55cd32a666a2b
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Solving Advent of Code with DuckDB and dbt

2023/02/09 - 9 min read

BY

[Graham Wetzler](https://motherduck.com/authors/graham-wetzler/)

## What is Advent of Code?

For the uninitiated, [Advent of Code](https://adventofcode.com/) (AoC) is an advent calendar in the form of coding problems that runs from December 1-25. It has run every year since 2015.

The [AoC about page](https://adventofcode.com/2022/about) describes it best:

> Advent of Code is an Advent calendar of small programming puzzles for a variety of skill sets and skill levels that can be solved in any programming language you like. People use them as interview prep, company training, university coursework, practice problems, a speed contest, or to challenge each other.

Each problem has two parts. Complete the solution for both parts and you get a gold star. Completing just part one earns you a silver star. The problems generally get tougher as the days go on. This is best illustrated by the [stats page](https://adventofcode.com/2022/stats) which clearly shows the tail off of the number of people completing the problems.

I've attempted AoC each year since 2020. In 2022 I used Python. In 2021, I decided to try to use Snowflake SQL but by day four it became too tedious for me and I returned to using Python.

The daily solution threads on [/r/adventofcode](https://www.reddit.com/r/adventofcode/) are full of people using any programming language you can imagine. This includes extremely odd choices such as [APL](https://en.wikipedia.org/wiki/APL_(programming_language)), [Rockstar](https://codewithrockstar.com/), and even Microsoft Excel. However, I was surprised to not find many SQL solutions posted. When I did find them they were often written in T-SQL for Microsoft SQL Server, and occasionally I'd find a PostgreSQL solution.

## Why DuckDB?

In November 2022 with AoC approaching I decided I would commit myself to using SQL for AoC, even if I didn't get very far. I like SQL because it's a very satisfying way to solve complex problems. The next question was which database I would use. I'd been familiar with DuckDB for years but never had a chance to use it in any practical sense. With its recent surge in popularity, DuckDB felt like an obvious choice. I could easily run it on my laptop, I didn't need to set up an account with a cloud data warehouse provider, and didn't need to mess with Docker to get PostgreSQL running.

While DuckDB could work perfectly fine on its own, I decided to pair it with [dbt-duckdb](https://github.com/jwills/dbt-duckdb), a DuckDB adapter for [dbt](https://www.getdbt.com/). I use dbt daily during my job as an analytics engineer so it felt like an obvious way to structure my project. By using dbt I was able to add tests to ensure my solution still worked after refactoring.

## Patterns

After doing several AoC problems you start to see patterns appear. You're provided your puzzle input for each day. The puzzle inputs are text files, often in the form of long lists of numbers or strings. DuckDB has excellent support for [reading CSV files](https://duckdb.org/docs/data/csv). Both `read_csv` and `read_csv_auto` worked incredibly well for parsing my puzzle input depending on how much flexibility I needed.

The data types provided by DuckDB are very comprehensive. While data types like lists are essential in procedural languages such as Python, I'd barely ever used them in SQL before. For many problems, I found a common pattern of using [`string_split`](https://duckdb.org/docs/sql/functions/char) to return rows of lists containing strings, then using the incredibly powerful [`unnest`](https://duckdb.org/docs/sql/query_syntax/unnest) function to turn the rows of lists into one row per list item. This worked especially well for grid problems that are often seen in AoC to format the structure into rows of `x`, `y`, and `value`.

Recursive CTEs are essential for many of the more challenging AoC problems, especially ones that require building and walking [graphs](https://en.wikipedia.org/wiki/Graph_theory), as well as ones that require iterating over rows with conditional branching logic.

Window functions are also very useful. DuckDB is kind enough to maintain the order of rows after reading in a CSV, but you'll often want to add an identifier to keep track of these rows through transformations. `row_number() over ()` will give you just that.

`string_agg` is a useful aggregate, window, and list function. However (at the time of writing) when using it as a list function it has an odd limitation; specifying the string separator does not work as expected. Thanks to the wonderful [DuckDB Discord](https://discord.com/invite/tcvwpjfnZx) I found a solution for this: `list_aggr(['a', 'b', 'c'], 'string_agg', '')` will join a list together. It looks odd but it does work.

## Walkthrough

Next, I'll walk through a couple of my solutions. Feel free to skip past if you plan on attempting these yourself and you don't want to be spoiled.

## Day Three

[Day three](https://adventofcode.com/2022/day/3) has you working with ”items“ (represented as letters) in a rucksack (a line of input). The puzzle input contains 300 lines of varying length random-looking text strings.

First, we start with reading in the puzzle input. Here we also add the `elf` identifier to each row to keep track of each elf's rucksack.

```sql
Copy code

with input(elf, items) as (
  select row_number() over () as elf
       , *
    from read_csv_auto('input/03.csv')
)
```

The first real step is to split each rucksack into equal halves. We can do this by counting how many items each rucksack contains and then using string slicing we can separate each half into a new column. Finally, we split the strings into lists.

```sql
Copy code

, compartments as (
  select *
       , length(items) as len
       , string_split(items[1 : len / 2], '') as compartment_1
       , string_split(items[len / 2 + 1 : len], '') as compartment_2
    from input
)
```

Part one asks us to find the one item type that appears in both compartments of each rucksack. With both compartments now `list` types we can use a `list_filter` to construct a lambda that uses the `contains` function to filter for the one item. Finally, we can use `[1]` which is a list slice to return a single value from the resulting lists.

```sql
Copy code

, common_by_compartment as (
  select elf
       , list_filter(compartment_1, x -> contains(compartment_2, x))[1] as item
    from compartments
)
```

The final step for part one (and part two) is to calculate the priority. If you're familiar with [ASCII character codes](https://en.wikipedia.org/wiki/ASCII) you'll probably notice the shortcut we can use. The `ord` function returns the ASCII character code for the character passed in. With the ASCII code, we just need to figure out the offset needed to match the instructions. Finally, we can sum the column to get the answer to part one.

```sql
Copy code

select sum(case
           when ord(item) between 65 and 90 then ord(item) - 38 /* A-Z */
           else ord(item) - 96 /* a-z */
       end) as answer
  from common_by_compartment
```

Part two ups the difficulty and asks us to find the common item between groups of three elves. The first step is to create the groups using a `row_number` window function with a window frame specifying `elf % 3`. `elf` is the identifier we created in the first step and `%` is the modulo operator which returns the remainder of dividing the two values.

```sql
Copy code

, elf_groups as (
  select row_number() over (partition by elf % 3 order by elf) as elf_group
       , *
    from input
)
```

Next, we split each rucksack into a list and `unnest` to fan out the results to a single item per row.

```sql
Copy code

, distinct_items_by_group as (
  select distinct
         elf_group
       , elf
       , unnest(string_split(items, '')) as item
    from elf_groups
)
```

Nearly finished, we can use a simple `group by` and `having` statement to find the common item for each group of elves.

```sql
Copy code

, common_by_group as (
  select elf_group
       , item
    from distinct_items_by_group
   group by 1, 2
  having count(*) = 3
)
```

The final step for part two is to calculate the priority the same way as in part one.

## Day Six

[Day six's](https://adventofcode.com/2022/day/6) problem asks you to help the elves decode signals from their communication system. The puzzle input is a single line of 4,096 lowercase letters. In part one, you're asked to find the first _start-of-packet_ marker which is defined as four sequential characters that are all different. Part two asks us to find the first _start-of-message_ marker which is the same as a _start-of-packet_ marker except it's 14 characters.

We start the same way as usual, by reading from our puzzle input. We also dive right in by splitting the characters into a list and unnesting to get each character onto their own row.

```sql
Copy code

with input as (
  select unnest(str_split(char, '')) as buffer
    from read_csv_auto('input/06.csv') as chars(char)
)
```

The next step simply adds an identifier column that we'll later use to sort by.

```sql
Copy code

, row_id as (
  select row_number() over () as id
       , buffer
    from input
)
```

Here is where the bulk of the work happens for both parts. First, we use `list` in a window function with a [frame](https://duckdb.org/docs/sql/window_functions#framing) that looks backward the required number of characters. Then `list_distinct` returns the unique items from the column of lists. Finally, `length` will give us the length of each list.

```sql
Copy code

, markers as (
  select id
       , length(list_distinct(list(buffer) over (order by id
                                                  rows between 3 preceding
                                                   and current row))) as packet_marker
       , length(list_distinct(list(buffer) over (order by id
                                                  rows between 13 preceding
                                                   and current row))) as message_marker
    from row_id
   order by id
```

To get the final answer for both parts we just figure out the minimum `id` that matches our criteria.

```sql
Copy code

select 1 as part
     , min(id) as answer
  from markers
 where packet_marker = 4
 union all
select 2 as part
     , min(id) as answer
  from markers
 where message_marker = 14
```

## Wrapping Up

I enjoyed attempting AoC with DuckDB. It required a completely different way of thinking compared to Python. While I didn't complete as many days as in prior years using Python, I learned a ton. I also felt like several of my solutions were much more readable and elegant compared to those done in procedural languages.

I managed to get gold stars for the first eight days. On [day nine](https://adventofcode.com/2022/day/9) I struggled to come up with a solution; I believe it's possible to solve this using a recursive CTE or even a lateral join (currently in DuckDB development builds) but I didn't get very far. I did find a solution for day 10, however, on days 11, 12, and 13, I worked for many hours but ultimately did not manage to find solutions. Day 12 involved building a graph which I did using a recursive CTE. While it could run successfully on the sample input, I could not get it to run quickly enough to solve using my provided input.

Go give it a try! You don't have to wait until December, you can attempt any day from any of the prior years. I recommend joining or creating a private leaderboard for some friendly competition among friends or those with similar interests. If you're able to come up with DuckDB solutions I'd love to hear about them!

You can find [my Github repo with my solutions here](https://github.com/grahamwetzler/advent-of-code-dbt-2022) and the best place to reach me is on [LinkedIn](https://www.linkedin.com/in/grahamwetzler/).

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![How to analyze SQLite databases in DuckDB](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_sqlite_ae3ed17fef.png&w=3840&q=75)](https://motherduck.com/blog/analyze-sqlite-databases-duckdb/)

[2023/01/24 - Ryan Boyd](https://motherduck.com/blog/analyze-sqlite-databases-duckdb/)

### [How to analyze SQLite databases in DuckDB](https://motherduck.com/blog/analyze-sqlite-databases-duckdb)

DuckDB is often referred to as the SQLite for analytics. This blog post talks about how to query SQLite transactional databases from within the DuckDB analytics database.

[![Python Faker for DuckDB Fake Data Generation](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpython_faker_duckdb_social_aa828ffa63.jpg&w=3840&q=75)](https://motherduck.com/blog/python-faker-duckdb-exploration/)

[2023/01/31 - Ryan Boyd](https://motherduck.com/blog/python-faker-duckdb-exploration/)

### [Python Faker for DuckDB Fake Data Generation](https://motherduck.com/blog/python-faker-duckdb-exploration)

Using the Python Faker library to generate data for exploring DuckDB

[View all](https://motherduck.com/blog/)

Authorization Response