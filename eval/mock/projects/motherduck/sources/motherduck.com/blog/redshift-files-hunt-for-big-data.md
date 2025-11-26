---
title: redshift-files-hunt-for-big-data
content_type: blog
source_url: https://motherduck.com/blog/redshift-files-hunt-for-big-data
indexed_at: '2025-11-25T19:57:27.512364'
content_hash: 5b116bf283398973
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Redshift Files: The Hunt for Big Data

2024/08/07 - 26 min read

BY

[Jordan Tigani](https://motherduck.com/authors/jordan-tigani/)

The Redshift team at AWS recently published a [paper](https://assets.amazon.science/24/3b/04b31ef64c83acf98fe3fdca9107/why-tpc-is-not-enough-an-analysis-of-the-amazon-redshift-fleet.pdf), “Why TPC is not enough: An analysis of the Amazon Redshift Fleet”. As part of their research, they [released](https://github.com/amazon-science/redset?tab=readme-ov-file) a dataset containing data about half a billion queries on 32 million tables over a 3 month period. It is a massive treasure trove to help understand how people do analytics.

It is also a great opportunity to test, using a public dataset, how prevalent “Big Data” is in the real world. A year and a half ago, I published a blog post called “ [Big Data is Dead](https://motherduck.com/blog/big-data-is-dead/)”, which argued that big data was not relevant to most people in analytics. In the post, I made the assertions that:

- Most people don’t actually have big data
- Most people who do have big data query small tables anyway
- Most people who both have big data and query it still only read a small portion of that data
- You only need “big data” tools if you are in the Big Data 1%.

At the time I wrote the post, I wasn’t using measured data, just some remembered stats and anecdotes. Since then, a ton of people from around the industry, from Snowflake to AWS to Google, have privately confirmed to me that the numbers I hand-waved through in the piece were accurate; most of their users don’t actually have a ton of data. That said, there is nothing like actual data to test whether your hypotheses hold up in the real world. (Spoiler alert: They do!)

Armed with the Redshift data, we can test how prevalent Big Data is for Redshift users in the dataset. For the sake of argument, let’s call “Big Data” anything larger than 10 TB. At sizes smaller than that, databases like Clickhouse or DuckDB can do a pretty good job on a single machine, based on benchmarks. Note that in another [blog post](https://motherduck.com/blog/the-simple-joys-of-scaling-up/), I also argued that the boundary between small data and big data keeps moving further out every year; while we’re defining Big Data as 10TB now, in another few years, 50TB or 100TB datasets may be easy to work with using small data tools on a laptop.

The queries that are used in the analysis are in the [Appendix](https://motherduck.com/blog/redshift-files-hunt-for-big-data/#appendix) section in order to avoid cluttering up the post. You can run them yourself in [MotherDuck](https://motherduck.com/docs/getting-started/) or your favorite query engine; instructions are also included in the [Appendix](https://motherduck.com/blog/redshift-files-hunt-for-big-data/#appendix). The Appendix also includes a discussion of the assumptions that were made, such as assuming that the Redset approximates the overall Redshift fleet. Please check that section out to understand the strength of the assertions made in this post.

## Looking at Big Data Queries

To start, let’s figure out how much data queries actually use. The Redshift dataset reports the amount of data scanned on a per-query basis, which we can use to see the distribution of query sizes.Let’s also look at what percentage of time is spent querying data at each size:

| **query\_size** | **pct** | **elapsed\_pct** |
| --- | --- | --- |
| \[1PB - 10PB) | 0.00021% | 0.068% |\
| \[100TB - 1PB) | 0.00081% | 0.54% |\
| \[10TB - 100TB) | 0.029% | 5.1% |\
| \[1TB - 10TB) | 0.21% | 11% |\
| \[100GB - 1TB) | 1.1% | 18% |\
| \[10GB - 100GB) | 4.1% | 20% |\
| \[1GB - 10GB) | 19% | 14% |\
| < 1 GB | 75% | 31% |\
\
Only 0.03% of queries in the dataset, or 3 out of 10,000, query more than 10 TB of data. That means that by query volume, having to handle Big Data is very rare.\
\
You might point out that these are more expensive queries to run, so you might instead ask what percentage of the elapsed time is spent on those queries. It is still only around 5.6 % of overall query time. If we consider query cost to be proportional to query time, we’re spending 94% of query dollars on computation that doesn’t need big data compute.\
\
From a super simple analysis, we can see that more than 99.95% of queries don’t actually qualify as big data, although 6% of execution time is spent on big data queries.\
\
Who is doing the big data queries? How many users and user sessions query more than 10TB of data at a time? It turns out, almost no one.\
\
| **scan\_size** | **pct\_user** | **pct\_session** |\
| --- | --- | --- |\
| \[1PB - 10PB) | 0.0019% | 0.0275% |\
| \[100TB - 1PB) | 0.020% | 0.22% |\
| \[10TB - 100TB) | 0.15% | 3.3% |\
| \[1TB - 10TB) | 0.36% | 4.8% |\
| \[100GB - 1TB) | 0.91% | 12% |\
| \[10GB - 100GB) | 5.4% | 19% |\
| \[1GB - 10GB) | 26% | 24% |\
| < 1 GB | 67% | 38% |\
\
These are some pretty amazing numbers: only 1 user in 600 has ever scanned more than 10 TB in a query, and fewer than 4% of sessions use big data. This means that 99.8% of users would have been fine using tools that weren’t designed for big data. And 93% of users probably would have been fine processing their data on their laptop.\
\
## Who’s got Big Data?\
\
Now that we’ve seen that Big Data queries are pretty rare, it doesn’t mean that organizations don’t have Big Data lying around. How many organizations in the dataset actually have big data? To answer this, let’s first look at how many databases have big data.\
\
| **db\_size** | **pct** | **db\_count** |\
| --- | --- | --- |\
| \[1PB - 10PB) | 0.32% | 3 |\
| \[100TB - 1PB) | 1.1% | 10 |\
| \[10TB - 100TB) | 3.8% | 35 |\
| \[1TB - 10TB) | 6.7% | 62 |\
| \[100GB - 1TB) | 19% | 173 |\
| \[10GB - 100GB) | 11% | 102 |\
| \[1GB - 10GB) | 10% | 97 |\
\
In order to figure out whether a database is Big Data, we look at the largest amount of data scanned from any query run against the database. Note that we’re looking across all query types, which includes data creation operations. We bucket the max table size by order of magnitude. By our definition, barely 5% of databases have what we consider “Big Data”.\
\
The Redshift paper doesn’t talk about data sizes in bytes, but they do talk about the number of rows: “In fact, most tables have less than a million rows and the vast majority (98 %) has less than a billion rows. Much of this data is small enough such that it can be cached or replicated”\
\
## Ok, so, you’ve got Big Data. Do you actually use it?\
\
I talk to a lot of people at enterprises who assure me that while Big Data might be rare, they have tons and tons of data. But, just because you have a ton of data doesn’t mean that you typically use much of that data for your analytics. Let’s look at the query patterns of organizations that have Big Data.\
\
We will filter out our data to focus on cases where the organization (the Redshift Instance) has Big Data, meaning that they have some tables larger than 10 TB. How often are those tables used? We look at the breakdown of table size referenced by a query and the largest ever queried per user:\
\
| **total\_table\_size** | **query\_pct** | **user\_pct** |\
| --- | --- | --- |\
| \[1PB - 10PB) | 0.23% | 0.15% |\
| \[100TB - 1PB) | 0.12% | 3.0% |\
| \[10TB - 100TB) | 0.47% | 13% |\
| \[1TB - 10TB) | 1.2% | 31% |\
| \[100GB - 1TB) | 2.0% | 54% |\
| \[10GB - 100GB) | 4.7% | 64% |\
| \[1GB - 10GB) | 23% | 53% |\
| < 1 GB | 68% | 56% |\
\
In cases where people have big data, 99% of their queries are run solely against smaller tables that don’t actually have big data.\
\
This might seem surprising that the number is this low. Organizations tend to start with raw data and transform it until it gets to the shape that it can be used for serving reports. This is often called a “medallion” architecture, because the final transformed result is the “gold” data that is trusted by business users. A lot of reduction ends up happening in this process, and the serving layers tend to be a lot smaller than the original data sizes.\
\
The rationale for using a smaller serving tier is part cost and part performance. Querying a lot of data is expensive. In Google BigQuery or AWS Athena, it costs you at least $50 to scan 10 TB. If you do that a couple of million times, the cost get painful pretty quickly. So people will summarize data into trusted tables that can be used to run their business. It is an added bonus that these tables can generally be queried very quickly, which makes business users happy when they can get immediate results..\
\
When you look at the breakdown by user, the results are also fairly stark; In organizations with Big Data, 87% of users never run queries against “big” tables. Note that this column adds up to more than 100% because some users query against a range of data sizes.\
\
We should also point out that many organizations have multiple Redshift instances. While smaller organizations likely only have a single instance, larger organizations might have many of them. In cases where organizations have more than onstance, they tend to be broken down by department or team. For those organizations, the analysis above might be better applied to departments than overall organizations.\
\
## When you need Big Data, how much of it do you actually use?\
\
So you’ve got Big Data. Obviously, you want to query it sometimes. When you do, how much of it gets used? It turns out, not much:\
\
| **total\_table\_size** | **scan\_pct\_50** | **scan\_pct\_90** | **scan\_50** | **scan\_90** |\
| --- | --- | --- | --- | --- |\
| \[1PB - 10PB) | 0.0043% | 0.17% | 24 | 987 |\
| \[100TB - 1PB) | 0.064% | 0.37% | 36.4 | 1079 |\
| \[10TB - 100TB) | 0.045% | 7.7% | 3.2 | 1052 |\
| \[1TB - 10TB) | 1.2% | 14.0% | 6.00 | 73.5 |\
| \[100GB - 1TB) | 4.0% | 27.5% | 2.34 | 20.7 |\
| \[10GB - 100GB) | 2.5% | 28.0% | 0.56 | 2.7 |\
| \[1GB - 10GB) | 26% | 95.0% | 0.23 | 1.03 |\
\
Here we bucket tables similarly to the previous queries to take a look at how much data is scanned when querying tables of a certain size. For the 10-100 TB bucket, we can check out what percentage of the table is scanned at various percentiles (50% & 90%). We can also check out the absolute amount of data scanned.\
\
For our “big data” tables, where the table size in a query is more than 10 TB, the average query only queries half of a percent of the table, or 3 GB. 90% of queries that query big data tables query less than 8% of the table, or around 1 TB.\
\
Most database systems can do partition pruning, column projection, filter pushdown, segment selection, or other optimizations to be able to read a lot less than the full table size. So this shouldn’t be surprising.\
\
Let’s look at this another way: For queries that read from big data tables, how often do they actually query big data?\
\
| **scan\_size** | **query\_pct** | **query\_count** |\
| --- | --- | --- |\
| \[100TB - 1PB) | 0.001% | 1 |\
| \[10TB - 100TB) | 0.41% | 409 |\
| \[1TB - 10TB) | 36% | 35063 |\
| \[100GB - 1TB) | 5.0% | 4922 |\
| \[10GB - 100GB) | 47% | 45898 |\
| \[1GB - 10GB) | 13% | 12393 |\
\
Here we see that fewer than 0.5% of queries that read from giant tables scan more than 10TB.\
\
This fits with a common use case we see with people who have tons of data; they might collect a lot of data, but they tend to only look at the recent data. The rest sits around and is mostly quiescent.\
\
## Is Big Data Dead Yet?\
\
Let’s see how those assertions from before have held up:\
\
**Most people don’t actually have big data.**\
\
- 95% of databases don’t qualify as Big Data and 99.98% of users never run big data queries. ✅\
\
**Most people who do have big data query small tables anyway.**\
\
- When people have big data, 99% of their queries are against smaller tables. ✅\
\
**Most people who both have big data and query it still only read a small portion of that data:**\
\
- 99.5% of queries over “big data” tables, query “small data” amounts. ✅\
\
**You only need “big data” tools if you are in the “Big Data 1%”.**\
\
- From the above results, you need to use big data tools 0.5% of 1% of 5% of the time, which is something like the “big data 0.00025%”. ✅\
\
Some people have big data and make use of it. But analyzing a lot of data is rarer than most people think. And if the vast majority of your time is spent working with smaller amounts of data, you can probably get away with tools that were designed for simpler use cases.\
\
## Appendix\
\
### Assumptions\
\
In order to make sense of these queries, I needed to make a handful of assumptions.\
\
**The Redshift instances in the dataset are representative of the larger user base.**\
\
As is mentioned in the github repository: “Redset is not intended to be representative of Redshift as a whole. Instead, Redset provides biased sample data to support the development of new benchmarks for these specific workloads.“ While this reduces the strength of some of the conclusions in this post, this dataset remains one of the best sources for understanding data sizes and shapes in real world workloads.\
\
What’s more, it is unlikely that this data is biased towards the small size; the paper makes the case that the long tail is important to look at, and it would be surprising if they de-emphasized the long tail. What’s more, some of the conclusions in the paper would be weakened if the data is not representative of the broader fleet. For example, they have discussions about the shapes of data, growth of tables, and the number of rows that are typically found, and these wouldn’t hold up if the data wasn’t nearly representative.\
\
**Table Size estimation is hard.**\
\
If all you have are scan sizes, then it is hard to know the full size of the table. Most analysis doesn’t require this, but a couple of the queries do rely on being able to figure out which tables are “big” and which are not. To figure out what tables are “big”, I pick the largest scan of the table by itself. This may under-count the table size in some cases. However, it may also over-count the table size, since there seem to be cases where the same table gets read multiple times.\
\
Note that the technique we are using here, looking at the maximum query size ever run on a table, will often significantly under-count the size of a table. However, in a world with separation of storage and compute, if you don’t read parts of a table, it might as well not exist for the purposes of query execution. That is, if you have a partitioned table that sits on disk with 10 years of logs and you only ever scan the last 7 days, then the 9.9 years of logs that you don’t scan don’t impact things at all. The query engine you’re using doesn’t have to handle 10 years of logs.\
\
While it is true that at some point you might decide you need to look at the whole dataset (after all, that’s likely why you keep it around), do you want to design your data architecture and query engine around something you might want to do a couple of times a year, or what you do thousands of times a day? Virtually any system will be able to crunch through the giant data set eventually, it might just take a long time.\
\
**The Boundary between Small Data and Big Data is 10 TB**\
\
The definition of “Big Data” has always been a bit vague, but the one I find most instructive is that Big Data starts when you need to scale out to multiple machines in order to process the data in a reasonable amount of time.\
\
At MotherDuck, we have built a scale up hosted version of DuckDB, and we have a lot of happy customers running databases that are several terabytes when compressed. So 10 TB as a boundary point for “Big Data” seems reasonable from an “existence proof” perspective.\
\
If you wanted to draw a finer line, you might want to differentiate between scan size and storage size. A scan size of 1TB might be considered big data, but you wouldn’t consider your stored data to actually be “Big Data” until you had more than 10TB (or more). However, this still wouldn’t meaningfully change the results. More than 99% of users still never scan more than a Terabyte at once, and 98% of queries against instances that have big data scan less than 1TB. For the purposes of simplicity I drew the line at 1TB across the board.\
\
### Preparing Data\
\
To do this analysis, I used MotherDuck, but you can use any query engine you’d like. You can run all of these queries yourself in MotherDuck by following along.\
\
If you’d like to use the MotherDuck UI, you can navigate to [https://app.motherduck.com](https://app.motherduck.com/) and sign up. It is easy, and doesn’t require a credit card. You can also run from the DuckDB CLI. To do this on a Mac, you can run `brew install duckdb`.\
\
You can get the `redset` dataset by attaching the share that I created. Run the following command in either the MotherDuck UI, the DuckDB CLI, or your favorite DuckDB environment:\
\
```sql\
Copy code\
\
ATTACH 'md:_share/redset/dff07b51-2c00-48d5-9580-49cec3af39e4'\
```\
\
If you run the above command in MotherDuck or DuckDB, it will attach a MotherDuck share called `redset` that has the full `redset` dataset already loaded.\
\
Alternatively, you can load the data from S3 yourself with the following commands in MotherDuck or DuckDB:\
\
```sql\
Copy code\
\
--- Alternate setup, loading data directly ---\
CREATE TABLE serverless as\
SELECT * FROM 's3://redshift-downloads/redset/serverless/full.parquet';\
CREATE TABLE provisioned as\
SELECT * FROM 's3://redshift-downloads/redset/provisioned/full.parquet';\
```\
\
In order to make queries run faster and simplify some of the queries (so they are easier to share), I created a handful of temp tables that compute various statistics about the data. To create the scratch database, I ran:\
\
```sql\
Copy code\
\
CREATE OR REPLACE DATABASE scratch;\
```\
\
I also created a couple of useful helper functions. The first is `pow_floor`, which we use to create power-of-10 buckets by truncating a value to the nearest power of 10. So 59.3 would be 10, 5930 would be 1000. This is useful to enable us to see how things change with regard to order of magnitude changes in the data.The `gb_range` macro translates the output of `pow_floor` into something that describes the data range.\
\
```sql\
Copy code\
\
CREATE OR REPLACE MACRO pow_floor(x) AS pow(10,log(10,x+0.01)::bigint)::bigint;\
\
CREATE OR REPLACE MACRO gb_to_label(size_gb) AS CASE\
    WHEN size_gb < 1000 THEN CONCAT(size_gb, 'GB')\
    WHEN size_gb < 1000 * 1000 THEN CONCAT((size_gb / 1000) :: bigint, 'TB')\
    ELSE CONCAT((size_gb / 1000 / 1000) :: bigint, 'PB')\
END;\
\
CREATE OR REPLACE MACRO gb_range(size_gb) AS CASE\
    WHEN size_gb = 0 THEN '< 1 GB'\
    WHEN size_gb > 0 THEN CONCAT(\
        '[',\
        gb_to_label(size_gb),\
        ' - ',\
        gb_to_label(size_gb * 10),\
        ')'\
    )\
    ELSE 'N/A'\
END;\
```\
\
Now, let’s look at the data. We want to create a consistent view that we’ll use across all of our queries that filters out stuff we don’t care about, and makes sure we’re looking at the right things.\
\
```sql\
Copy code\
\
CREATE OR REPLACE VIEW scratch.all_queries as\
SELECT * FROM (SELECT * FROM provisioned UNION ALL\
  SELECT * REPLACE (instance_id + (SELECT max(instance_id) from provisioned) + 1 as instance_id) from serverless\
)\
WHERE query_type not in ('unload', 'other', 'vacuum') and was_aborted = 0 and mbytes_scanned is not null\
```\
\
The Redshift data comes in two different tables, `provisioned` and `serverless`. If we want to query all of the data, we need to query across both of them. Luckily, they have the same schema, but unluckily, they have overlapping instance IDs. So if we want to query across both of them, we need to remap the instance IDs so they don’t overlap.\
\
We also are going to skip over query types `unload`, `other` and `vacuum` because they aren’t useful for seeing what kinds of analytics people are doing.\
\
For our analysis, we want to understand how big the tables are, but unfortunately, that information isn’t directly available. We just know how much data was scanned per query, but some queries scan many tables, and some scan only parts of a table.\
\
To get an estimate, I use the largest single-table query done for each table and use that as the table size.\
\
This is not an exact method of computing query size; some tables that are created from a summary might be much smaller, or the user may never query the full table size. However, if the user never reads the full table size, then the full table size likely doesn’t matter; what matters is the proportion that is used.\
\
Here is the basic query for figuring out table size:\
\
```sql\
Copy code\
\
CREATE OR REPLACE TABLE scratch.table_sizes as\
SELECT try_cast(read_table_ids as bigint) as table_id,\
  instance_id, database_id,\
  max(if(num_scans > 0, mbytes_scanned / num_scans, mbytes_scanned)) / 1000 as table_gb\
FROM scratch.all_queries\
WHERE num_permanent_tables_accessed < 2 and num_external_tables_accessed = 0\
  and num_system_tables_accessed = 0\
  and table_id is not null\
GROUP BY ALL\
```\
\
This query is pretty straightforward. I look only at cases where a single table was queried (since it would be hard to attribute size to a different table) and skip anything that reads system tables or external tables, since that will affect the scan size.\
\
Note that we play a little bit of a trick to get the table ID; since we are only looking for queries that query one table, a comma separated list of tables. The `read_table_ids` field will be just a string representation of the single table. So we cast it to a `bigint`. If it fails the cast, it must not have been a single table query. We also divide by the number of scans done, since sometimes the same table gets scanned multiple times.\
\
Next, we want to compute the size of tables involved in a query. We already have the amount of data scanned, but we also want to learn what the full size of the relevant tables are. This query saves it in a temp table:\
\
```sql\
Copy code\
\
CREATE OR REPLACE TABLE scratch.queries_and_sizes as\
WITH queries as (\
SELECT\
  query_id, database_id, instance_id, user_id,\
  regexp_split_to_array(read_table_ids, ',') as table_id_array,\
  mbytes_scanned / 1024 as scanned_gb\
FROM scratch.all_queries\
WHERE num_external_tables_accessed = 0 and query_type = 'select'\
  and len(table_id_array) > 0\
),\
queries_and_scan_sizes as (\
SELECT query_id, instance_id, database_id, user_id, scanned_gb,\
  try_cast(tid.table_id_array as bigint) as table_id,\
FROM queries, UNNEST(table_id_array) tid\
WHERE table_id is not null\
)\
SELECT query_id, instance_id, database_id, user_id,\
  sum(table_gb) total_table_gb, any_value(scanned_gb) as scanned_gb,\
  count(*) as table_count\
FROM queries_and_scan_sizes q\
JOIN scratch.table_sizes using(table_id, database_id, instance_id)\
GROUP BY ALL\
```\
\
This query is a little bit complicated because the list of tables scanned is in a comma-separated varchar field. So we first split the list to an array, and then flatten by the table ID. We match the table ID up against our saved table size table, and compute the sum of all table sizes in the query. Also, we are only looking at `SELECT` queries for this one, since we generally care most about analytics queries, not queries that are transforming data.\
\
### Analysis Queries\
\
Now we’ve got the base tables set up, and we can move onto the queries to figure out how the data is being used.\
\
#### Query Sizes and Elapsed Time\
\
We want to figure out the size of queries bucketed by order of magnitude of the query size. The lowest bucket would be queries that read less than 1 GB, then 1-10 GB, then 10-100 GB, and so forth. We then figure out what percentage of queries are in each bucket. Furthermore, we compute the elapsed time running queries in each bucket.\
\
```sql\
Copy code\
\
SELECT pow_floor(mbytes_scanned/1000) as query_gb,\
  gb_range(query_gb) as query_size,\
  COUNT(1) / SUM(COUNT(1)) OVER () as pct,\
  SUM(execution_duration_ms) /  SUM(SUM(execution_duration_ms)) OVER () as elapsed_pct,\
FROM scratch.all_queries\
GROUP BY ALL\
ORDER BY 1 DESC\
```\
\
We play a couple of tricks in this query. First, you can see we use the pow\_floor macro that we’ve created to bucket the bytes scanned into powers-of-10 buckets. Then we use `COUNT(1) / SUM(COUNT(1)) OVER ()` to compute the percentage of the total. The numerator (`COUNT(1)`) counts the number of queries in that size bucket, and the denominator (`SUM(COUNT(1))`) counts the total number across the whole query. The sum of this column should add up to 100%. We then use the same trick again to compute the percentage of elapsed time at each bucket size.\
\
#### Database Sizes\
\
This query computes database sizes and divides them into order-of-magnitude size buckets. Then, like the previous query, we compute the percentage of databases in each bucket size. To compute the database size, we don’t bother trying to assign queries to tables, we just look at the largest query ever run in that database that didn’t access external tables.\
\
While it is possible that this under-counts the database size, it is more likely that it over-counts because many complex queries will scan the same table multiple times, and we don’t bother accounting for this. Even if it did under-count, you could argue that the rest of the database is not relevant if it never gets scanned.\
\
```sql\
Copy code\
\
WITH db_sizes as (\
  SELECT instance_id, database_id, max(mbytes_scanned/1000) as scanned_gb\
  FROM scratch.all_queries\
  WHERE  num_external_tables_accessed = 0 and num_permanent_tables_accessed > 0\
  GROUP BY ALL\
)\
SELECT\
  pow_floor(scanned_gb) as db_gb,\
  gb_range(db_gb) as db_size,\
  COUNT(1) / SUM(COUNT(1)) OVER() as pct,\
  COUNT(1) as db_count\
FROM db_sizes\
GROUP BY ALL\
ORDER BY db_gb DESC\
```\
\
This query is very simple. We first compute size per database in a common table expression (CTE), using our computed table size table. We then bucket the database sizes by power-of-10 size and report the\
\
percentage of tables in that bucket.\
\
#### User Scan Sizes and Sessions\
\
This query looks at the largest query ever run by a particular user and puts it into a query size bucket. It also looks at user sessions, as divided into unique hours that a user was querying. Note that ad-hoc query users will have far fewer sessions than automated systems that continually load data.\
\
```sql\
Copy code\
\
WITH user_sessions as (\
  SELECT user_id, instance_id,\
    DATE_TRUNC('HOUR', arrival_timestamp) as session_ts,\
    max(mbytes_scanned) / 1000 as max_scanned_gb\
  FROM scratch.all_queries\
  GROUP BY ALL\
)\
SELECT pow_floor(max_scanned_gb) as scanned_gb,\
  gb_range(scanned_gb) as scan_size,\
  COUNT(DISTINCT (user_id, instance_id))/\
    SUM(COUNT(DISTINCT (user_id, instance_id))) OVER() as pct_user,\
  COUNT(*)/SUM(COUNT(*)) OVER( ) as pct_session,\
from user_sessions\
where scanned_gb is not null\
GROUP BY ALL\
ORDER BY 1 DESC\
```\
\
User IDs are repeated across instances, so we need to look at distinct combinations of `<user_id><instance_id>` Then we use the `pow_floor` macro to bucket scan amounts into the order-of-magnitude buckets. We do two aggregations at once, first by distinct users, which lets us compute how many users are in a certain bucket, and then across all rows, which include sessions. Note that we’re only looking at select queries, since we’re interested in analytics rather than data preparation.\
\
#### Table Size Buckets\
\
This query looks at the distribution of table sizes. It uses the table size table that was computed in the setup section.\
\
```sql\
Copy code\
\
SELECT\
  pow_floor(table_gb) as total_table_gb,\
  gb_range(total_table_gb) as table_size,\
  COUNT(1) / SUM(COUNT(1)) OVER () as pct,\
  COUNT(1) as table_count\
FROM scratch.table_sizes\
GROUP BY ALL\
ORDER BY 1 DESC\
```\
\
To compute table size distribution across all tables, it is even easier than the database sizes, since we already have the table sizes computed individually in our scratch database.\
\
#### Size of tables queried when instances have “big data”\
\
Assuming we’re dealing with “Big Data”, how big are the queries that we’re looking at? To figure out when an instance has “big data” tables, we look at the query that scanned the most data. However, we need to modify it slightly, because sometimes a single query scans the same table multiple times. So if the number of tables accessed is less than the number of scans, we down-scale the scan size appropriately to take into account some tables being scanned multiple times.\
\
```sql\
Copy code\
\
WITH instance_sizes as (\
  SELECT instance_id, database_id,\
  max(mbytes_scanned/1000.0\
      * IF(num_scans > num_permanent_tables_accessed, num_permanent_tables_accessed/num_scans, 1)) as max_scanned_gb\
  FROM scratch.all_queries\
  WHERE num_external_tables_accessed = 0  and num_permanent_tables_accessed > 0\
  GROUP BY ALL\
),\
big_data_instances as (\
  SELECT instance_id\
  FROM instance_sizes\
  WHERE max_scanned_gb > 10 * 1000\
),\
big_data_users as (\
  SELECT COUNT(DISTINCT (user_id, instance_id)) as user_count\
  FROM scratch.queries_and_sizes\
  JOIN big_data_instances using (instance_id)\
)\
SELECT\
  pow_floor(total_table_gb) as total_table_gb_out,\
  gb_range(total_table_gb_out) as total_table_size,\
  count(*)/sum(count(*)) over () as query_pct,\
  COUNT(DISTINCT (user_id,instance_id))/(SELECT user_count from big_data_users) as user_pct,\
FROM scratch.queries_and_sizes\
JOIN big_data_instances using (instance_id)\
GROUP BY ALL\
ORDER BY 1 DESC\
```\
\
This query first finds the instances that have big data tables (greater than 10 TB) and then filters out to find only queries that are against those databases. The query also counts how many users are querying across the organizations that have these big data instances.\
\
Finally, the query buckets the size of the tables being scanned and computes the percentage of queries in each bucket and the percentage of the total users that are seen in each bucket. Note that user IDs are repeated across instances, so we need to use distinct user\_id+instance\_id pairs.\
\
#### Sizes of tables scanned by size of table\
\
This query computes per table size how much data is typically scanned. It computes the median size and the 90th percentile size.\
\
```sql\
Copy code\
\
SELECT\
  pow_floor(total_table_gb) as total_table_gb_out,\
  gb_range(total_table_gb_out) as total_table_size,\
  approx_quantile(scanned_gb / total_table_gb, 0.5) as scan_pct_50,\
  approx_quantile(scanned_gb / total_table_gb, 0.9) as scan_pct_90,\
  approx_quantile(scanned_gb, 0.5) as scan_50,\
  approx_quantile(scanned_gb, 0.9) as scan_90,\
FROM scratch.queries_and_sizes\
GROUP BY ALL\
ORDER BY 1 DESC\
```\
\
This query uses the same bucketing mechanism we use above to break up the total bytes referenced in the query into buckets, and then computes the median and 90th percentile of usage.\
\
#### A **mount of data queried when big data tables are queried**\
\
Now, assuming we are querying huge tables, how much data do we actually read?\
\
```sql\
Copy code\
\
SELECT\
  pow_floor(scanned_gb) as scanned_gb_out,\
  gb_range(scanned_gb_out) as scan_size,\
  COUNT(1)/SUM(COUNT(1)) OVER() as query_pct,\
  COUNT(1) as query_count\
FROM scratch.queries_and_sizes\
WHERE total_table_gb > 10 * 1000\
GROUP BY ALL\
ORDER BY 1 DESC\
```\
\
We compute for each scan size bucket the percentages of queries that are within that bucket, but we limit it to queries that are against tables we have already decided are “big data”\
\
We have the total\_gb filter on the query so we only see cases where the total size of tables that are in the query is greater than 10 GB. And then we break the results down by actual bytes scanned. We use the same tricks as earlier, the pow\_floor breaks the scanned bytes into order-of-magnitude buckets, and the `count(*)/sum(count(*)) OVER()` trick gets us the percentage in the bucket.\
\
That’s it! Nothing more to see. No more big data hiding anywhere.\
\
### TABLE OF CONTENTS\
\
[Looking at Big Data Queries](https://motherduck.com/blog/redshift-files-hunt-for-big-data/#looking-at-big-data-queries)\
\
[Who’s got Big Data?](https://motherduck.com/blog/redshift-files-hunt-for-big-data/#whos-got-big-data)\
\
[Ok, so, you’ve got Big Data. Do you actually use it?](https://motherduck.com/blog/redshift-files-hunt-for-big-data/#ok-so-youve-got-big-data-do-you-actually-use-it)\
\
[When you need Big Data, how much of it do you actually use?](https://motherduck.com/blog/redshift-files-hunt-for-big-data/#when-you-need-big-data-how-much-of-it-do-you-actually-use)\
\
[Is Big Data Dead Yet?](https://motherduck.com/blog/redshift-files-hunt-for-big-data/#is-big-data-dead-yet)\
\
[Appendix](https://motherduck.com/blog/redshift-files-hunt-for-big-data/#appendix)\
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
[![This Month in the DuckDB Ecosystem: August 2024](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Faugust_2024_03ffc9144f.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2024/)\
\
[2024/08/01 - Mehdi Ouazza](https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2024/)\
\
### [This Month in the DuckDB Ecosystem: August 2024](https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2024)\
\
DuckDB Monthly: Memory Management in DuckDB, Monitoring Python Package Usage, Community Extensions Launch, and more!\
\
[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)\
\
[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)\
\
### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)\
\
Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.\
\
[View all](https://motherduck.com/blog/)\
\
Authorization Response