---
title: streaming-data-to-motherduck
content_type: tutorial
source_url: https://motherduck.com/blog/streaming-data-to-motherduck
indexed_at: '2025-11-25T19:58:31.769978'
content_hash: 63037563a157d229
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Streaming Data To MotherDuck With Estuary

2024/01/24 - 6 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

Moving data from an operational OLTP database is a necessary step in any analytics journey. Operations is where most of the data you need to drive business-critical insights.
In this blog post, we'll understand why this matters, what change data capture (CDC) can bring in this context, and how [Estuary](https://estuary.dev/) and MotherDuck provide a fully managed off-the-shelf solution. So, if you are overloading your PostgreSQL/MySQL database with analytics, this article is for you!

## Why would I even need an OLAP database?

Companies often start to do analytics by running simple queries on their operational databases for their applications. These databases are typically OLTP (Online Transaction Processing) databases optimized for transactional processing involving low-latency, high-concurrency read/write operations.

Getting insights on this through analytical queries is the best way to get started.
But as your data and business grow, you quickly start to overload and OLTP database that is not designed for analytical queries.

OLAP (Online Analytical Processing) databases, on the other hand, are optimized for analytical processing and support complex queries over large datasets. MotherDuck, Snowflake, and BigQuery are examples of such databases. OLAP databases are the most common types of databases that you use to support your BI tools (dashboards, catalogs, etc).

Now, enter the first challenge of any data engineer: how should I move data into the OLAP database?

## CDC to the rescue, but not so fast

CDC pipelines replicate data changes from one database or system to another in real-time. In our case, it's typically moving from an OLTP database (e.g., PostgreSQL) to an OLAP system (e.g., MotherDuck) to offload analytics queries.

CDC has a couple of challenges :

- Schema mapping: The schema of the source database should be accurately mapped to the target system, especially if they use different data models or types.
- Schema evolution: Data evolves. Handling changes in schema (like adding new tables/columns or modifying data types) without interrupting the CDC process is not a piece of cake.
- Performance and scalability: CDC pipelines need to handle large volumes of data changes in real-time while ensuring minimal impact on the performance of the source system. Scaling up the pipeline to handle increasing data volumes can also be challenging.

Besides all of this, you also have different ways to handle CDC. For instance, with PostgreSQL you will see:

- Log-based CDC: PostgreSQL's write-ahead log (WAL) contains all inserts/updates/deletes and can be monitored to capture changes as they occur. Log-based CDC provides low overhead and high throughput, making it suitable for high-volume data environments.
- Trigger-based CDC: PostgreSQL triggers can capture changes in the source tables as they occur. Triggers can be defined to fire on specific events such as INSERT, UPDATE, or DELETE and execute custom code to transform or enrich the data before it is replicated to the target system. However, the downside is that trigger-based CDC can add overhead to the source system.

Multiple solutions exist, including open source, but they often take work to set up and maintain.

Fortunately, there are some tools that manage all the above for you. Let's get hands-on and try a CDC pipeline from a PostgreSQL database to MotherDuck using Estuary.

## Building CDC Pipelines

For the below demo, you would need :

- A MotherDuck account ( [sign up for free](https://app.motherduck.com/?auth_flow=signup)) with your service token.
- An Estuary account ( [sign up for free](https://dashboard.estuary.dev/))
- A PostgreSQL database with some data and settings setup (more on this below if you don't have an existing one)
- An AWS S3 bucket and IAM user that have R/W to this one (for staging files)

While this demo uses PostgreSQL as a source, feel free to try any [other available connectors](https://estuary.dev/integrations/) from Estuary.

### Setting up the PostgreSQL database

To quickly get started with a cloud PostgreSQL database, we'll use [Neon](https://neon.tech/). You can sign up for free as part of their free tier.
First, head over to `Dashboard` to create a dedicated database.
To load some sample data, the easy way is to use the online SQL editor from Neon.
![editor](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsql_editor_77fffc72e7.png&w=3840&q=75)
First, we'll create a `customer` table. Run the following in the online SQL editor

```scss
Copy code

CREATE TABLE customer (
  id SERIAL,
  first_name VARCHAR(50),
  last_name VARCHAR(50),
  email VARCHAR(255),
  PRIMARY KEY (id)
);
```

Now, let's ingest some sample data.

```sql
Copy code

INSERT INTO public.customer (id, first_name, last_name, email)
VALUES
(1, 'Casey', 'Smith', 'casey.smith@example.com'),
(2, 'Sally', 'Jones', 'sally.jones@example.com');
```

For Estuary's access, we will create a dedicated role, head over `Roles`->`New Role`![new_role](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fcreate_role_62bf281300.png&w=3840&q=75)
We'll also need to enable log replica in the `Settings` -\> `Beta`.
![logical_replica](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Flogical_replica_3e7615289f.png&w=3840&q=75)

Finally, go to the dashboard and grab the information from the connection string. Be sure to untick the pooled connection parameter. The connection string contains the hostname, user, and password that would be used in the Estuary connector.
![get_creds](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fget_creds_38e82c1925.png&w=3840&q=75)

## Setting up Estuary pipeline

Creating an Estuary pipeline consists of 3 things :

- Sources
- Collection(s) (the captured data)
- Destinations

Go to the Estuary dashdboard and click on `NEW CAPTURE` in the `Sources` menu.
![capture](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fcapture_8d3829c259.png&w=3840&q=75)
Search for the `PostgreSQL` connector, click and fill in the information from the connection string we picked from the Neon dashboard.
![ostgres](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpostgres_config_70029b5cd7.png&w=3840&q=75)

In the `Advanced` section, be sure to use `verify-full` on the SSL Mode. You can leave the other fields as default as the connector will create both [publication](https://www.postgresql.org/docs/current/logical-replication-publication.html) and [slot](https://www.postgresql.org/docs/9.4/catalog-pg-replication-slots.html) automatically.

If the connection to the source is successful, you will now be able to select collections (e.g., tables). Here we have only one table (collection). You have also a few options regarding schema evolutions.

![estuary](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2024_01_24_at_01_10_03_151a188eb0.png&w=3840&q=75)
Now on to the `Destination`, click on Destinations on the left hand side, then search for `Motherduck`. Select `MotherDuck` as the connector, and start to fill the required fields :

- [MotherDuck Service token](https://motherduck.com/docs/key-tasks/authenticating-to-motherduck/)
- Database/Schema
- AWS S3 bucket name and credentials for staging data loads.
- The collection to materialize (here `customer`)

![estuary2](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2024_01_24_at_01_12_56_1b1c471d4f.png&w=3840&q=75)

And that's it! Estuary will have backfilled Motherduck and started to load the incremental changes as well. You should now have data in [MotherDuck](https://app.motherduck.com/).

![estuary3](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Festuary_01_21_05_d1eca48df9.png&w=3840&q=75)

Feel free to play around with the PostgreSQL INSERT query we used above to generate more data and confirm that the data is correctly replicated directly into Motherduck!

## Streaming further to the pond

In this blog, we've explored the challenges involved in moving data through CDC pipelines, highlighting the complexities of managing these systems.
We demonstrated how fast and easy it is to up a CDC pipeline from PostgreSQL (Neon) to MotherDuck using Estuary.
Streaming is a big topic. Dive into [Estuary's documentation](https://docs.estuary.dev/)) if you want to learn more about all the options you have for implementing real-time CDC and streaming ETL.

Keep coding, and keep quacking.

### TABLE OF CONTENTS

[Why would I even need an OLAP database?](https://motherduck.com/blog/streaming-data-to-motherduck/#why-would-i-even-need-an-olap-database)

[CDC to the rescue, but not so fast](https://motherduck.com/blog/streaming-data-to-motherduck/#cdc-to-the-rescue-but-not-so-fast)

[Building CDC Pipelines](https://motherduck.com/blog/streaming-data-to-motherduck/#building-cdc-pipelines)

[Setting up Estuary pipeline](https://motherduck.com/blog/streaming-data-to-motherduck/#setting-up-estuary-pipeline)

[Streaming further to the pond](https://motherduck.com/blog/streaming-data-to-motherduck/#streaming-further-to-the-pond)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![AI That Quacks: Introducing DuckDB-NSQL, a LLM for DuckDB SQL](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FThumbnail_text2sql_2_5891621850.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-text2sql-llm/)

[2024/01/25 - Till Döhmen, Jordan Tigani](https://motherduck.com/blog/duckdb-text2sql-llm/)

### [AI That Quacks: Introducing DuckDB-NSQL, a LLM for DuckDB SQL](https://motherduck.com/blog/duckdb-text2sql-llm)

Our first Text2SQL model release!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response