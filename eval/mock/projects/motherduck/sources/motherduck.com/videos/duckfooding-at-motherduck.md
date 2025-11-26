---
title: duckfooding-at-motherduck
content_type: event
source_url: https://motherduck.com/videos/duckfooding-at-motherduck
indexed_at: '2025-11-25T20:45:02.848161'
content_hash: 83fa33d7aa0c8ab6
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

Duckfooding at MotherDuck - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Duckfooding at MotherDuck](https://www.youtube.com/watch?v=z5P6Qa2OP6Y)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=z5P6Qa2OP6Y&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 40:09

•Live

•

YouTubeData PipelinesMeetupTalk

# Duckfooding at MotherDuck

2024/10/14

## **Lessons from Building MotherDuck with MotherDuck**

When I joined MotherDuck as a Founding Engineer, I took on an unusual role: becoming the company's first internal customer. "Dogfooding" – the practice of using your own product extensively before releasing it to customers – has long been a staple of software development. For us at MotherDuck, a company building a cloud service based on the popular DuckDB analytical database, this approach has proved invaluable in uncovering real-world issues and accelerating product development.

## **38 Seconds of Nothing**

My journey with data systems began around 2010 when I inherited the management of what was then the largest east coast Hadoop cluster, a 300-terabyte behemoth. This early experience revealed a fundamental inefficiency in distributed systems that would later influence MotherDuck's design philosophy.

I ran a MapReduce job that took 42 seconds. But when I ran the same computation locally on my machine, it completed in just 4 seconds. I wondered: where were the other 38 seconds going?

The answer lies in the overhead of distributed computing. When data is processed across multiple machines, it must be serialized, sent over the network, deserialized, and reassembled – a process called "shuffling." This creates significant latency that doesn't exist when processing data on a single machine.

In distributed systems, every shuffle operation causes this network storm where each node must communicate with every other node. You're exposed to long tail latency because the second part of your query plan cannot proceed until all partitions have been received.

Meanwhile, hardware advancements have dramatically increased the processing capabilities of individual machines. Modern servers can have dozens of cores, hundreds of gigabytes of RAM, and terabytes of fast SSD storage. A single Graviton3 instance at $1.30 per hour delivers 300 gigabytes per second of aggregate memory bandwidth – comparable to an entire mid-sized Hadoop cluster from a decade ago.

We built these distributed systems to handle the top 1% of workloads, but we pay this distribution overhead for everything, even when it's unnecessary.

## **No Overkill, No Lag**

The inefficiencies of traditional big data systems created an opportunity for a different approach. DuckDB emerged as a response to the need for efficient local analytical processing, particularly for data scientists working with tools like pandas.

DuckDB takes a fundamentally different approach from cloud data warehouses. As an embedded analytical database, it runs in-process, eliminating network overhead entirely. It offers columnar storage, vectorized execution, and aggressive pipelining – essentially implementing state-of-the-art analytical processing techniques in a library that can run anywhere.

DuckDB became relevant because it addressed the inefficiency of traditional approaches. It applies cutting-edge research on pipelining data and parallelizing operators to a market segment that larger companies had ignored – local analytics on your own machine.

Unlike traditional data warehouses, DuckDB has no authentication system, no network interface, and no user management. It's designed for single-user, local processing. While this makes it incredibly efficient, it also limits its usefulness for collaborative work and larger datasets.

## **Tiny Queries Everywhere**

Our hypothesis at MotherDuck that most analytical workloads don't require massive distributed systems was supported by real-world data. Amazon published a paper with aggregated statistics from Redshift users, revealing that approximately 95% of queries scan less than 10GB of data, and 90% scan less than 1GB.

Even more surprisingly, 30% of queries in production data warehouses scan just 1-100MB of data, and about 10% of Redshift customers are running entire warehouses on datasets between 1-10MB – data that would fit comfortably in a laptop's memory.

People are over-provisioning relative to what one big machine could handle. There are benefits to having a shared, cloud-based system, but clearly many organizations are paying for more distributed processing power than they actually need.

## **We are Our Own First Customer**

From day one, I positioned myself as MotherDuck's first customer, implementing our internal analytics infrastructure using our own product. It would be hypocritical not to use the product we recommend to others ourselves.

Our internal analytics stack at MotherDuck is relatively straightforward – using Airflow as a scheduler, mostly Python for data processing, and growing to employ partners for specific needs. The system now handles about 6,000 queries daily across 40 scheduled jobs, making it a substantial enough workload to thoroughly test the product.

By being deliberate about data types and optimizing for the vector execution engine, I keep our datasets efficiently sized – about 1 terabyte in total. This allows us to run the entire analytics operation at remarkably low cost, demonstrating the efficiency that careful engineering can achieve with DuckDB.

Our billing is ridiculously tight. We only charge for when queries are actively working on something, not even billing for time when they're blocked on I/O. Following good practices with DuckDB results in a really cost-effective solution.

## **Real World Discoveries**

The real value of dogfooding emerged when I began encountering issues that might not have been caught through conventional testing:

**File Descriptor Limits**: We discovered a slow leak of connections when using `SELECT FROM s3://` commands that would eventually hit the 1024 file descriptor limit after about a week of running. This would never appear in short unit tests but became apparent during continuous operation of our analytics stack. Without dogfooding, customers might have hit this in production before we caught it.

**Concurrent Schema Change Issues**: We found that when schema changes occurred, our system would pessimistically abort running queries due to out-of-sync local catalogs. This seemed reasonable in theory, but with tools like dbt where every materialization is a DDL statement (CREATE TABLE AS), it made the system practically unusable for real data engineering work. We had to revise this approach for better usability.

**Long SQL in UI vs Error Location**: Our initial UI design placed SQL error messages below the query. This worked fine for simple examples, but I work with 1300+ line SQL queries that require scrolling back and forth between errors and the code that caused them. We shifted to inline error highlighting, similar to what dbt does, making it much more practical for real-world complex queries.

**Validating Differential Storage**: We implemented a feature called differential storage, essentially writing our own file system layer. This was an extremely risky change that affects the core of data persistence. By enabling it for my production workloads for a month and a half before rolling it out to customers, we were able to catch edge cases and ensure stability for this critical component.

**Bind Timeout During Slow Source Scans**: When connecting to external systems like Postgres, we initially expected at least one row of data every 15 seconds to keep connections fresh. But I had queries that scanned billions of rows yet returned only 40 rows after 10 minutes due to high selectivity. These timed out unnecessarily, teaching us that timeouts need to account for query selectivity, not just overall duration.

**Deeply Nested JSON Memory Usage**: While typical JSON test data might be 30 fields with one nesting level, I showed up with real documents from MongoDB that were 80 levels deep per record. DuckDB wasn't prepared for this and used about 500 times the memory of the string just to parse it. Real-world data is far messier than test data, and dogfooding helped us identify and fix these memory issues.

**Slow Extension Load Times**: As our binary grew over time, we weren't closely monitoring its size. The security checksumming process (which is crucial and can't be skipped) was taking 7+ seconds on each extension load. This delay became very noticeable in my daily workflow and prompted us to optimize our binary size and loading performance.

## **Continuous Learning by Running Stuff**

Our dogfooding approach created a tight feedback loop between product development and real-world usage. Over time, my role evolved from primarily testing basic functionality to actually using MotherDuck as the company's data engineer.

When we first started, I was just making sure that basic operations like loading data and running aggregations worked properly. Now, about two-thirds of my time is actually doing data work for the company because the product is no longer giving me trouble.

This transition happened because issues were identified and fixed early. By the time MotherDuck reached general availability, the product had already been battle-tested through months of internal use.

We also gained valuable insights about scalability and resource management on a single node. While distributed systems spread workloads across multiple machines, a scale-up approach requires careful attention to memory allocation, core utilization, and I/O management. These learnings informed improvements to DuckDB's resource handling capabilities.

Looking ahead, we continue to enhance our hybrid execution model, which intelligently processes queries partly on the client and partly in the cloud based on data location. This architecture provides the best of both worlds – local processing speed with cloud scalability when needed.

## **If You Don’t Use It, Nobody Should**

For us at MotherDuck, dogfooding has proven essential in building a product that truly meets user needs. By using our own service for actual data engineering work, we uncovered issues that synthetic testing would have missed and gained firsthand experience with the product's strengths and limitations.

This approach has yielded three main benefits: identifying bugs earlier in the development cycle, ensuring feature designs match real-world workflows, and building empathy for the customer experience. It has also reinforced our core thesis that most analytical workloads can be handled efficiently on a single node with modern hardware.

For engineers and data teams considering new analytical solutions, my experience suggests a few key takeaways. First, many workloads don't need the complexity of distributed systems. Second, the efficiency gains from eliminating network overhead and intermediate data materialization can be substantial. Finally, a product built by a team that uses it daily is likely to evolve in ways that address real pain points rather than theoretical concerns.

Whether you're building or buying a data solution, the principle remains the same: the best way to understand if something works in practice is to make it part of your daily workflow. I've essentially been the sacrificial data engineer, running into issues before our customers do, which has made the product better for everyone.

...SHOW MORE

## Related Videos

[!["DuckLake: Making BIG DATA feel small (Coalesce 2025)" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fmaxresdefault_1_7f1e9ebbca.jpg&w=3840&q=75)](https://motherduck.com/videos/ducklake-big-data-small-coalesce-2025/)

[2025-10-14](https://motherduck.com/videos/ducklake-big-data-small-coalesce-2025/)

### [DuckLake: Making BIG DATA feel small (Coalesce 2025)](https://motherduck.com/videos/ducklake-big-data-small-coalesce-2025)

MotherDuck’s managed DuckLake data lakehouse blends the cost efficiency, scale, and openness of a lakehouse with the speed of a warehouse for truly joyful dbt pipelines. They will show you how!

Talk

[!["What can Postgres learn from DuckDB? (PGConf.dev 2025)" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2025_06_13_at_3_52_19_PM_470b0f71b1.png&w=3840&q=75)\\
\\
20:44](https://motherduck.com/videos/what-can-postgres-learn-from-duckdb-pgconfdev-2025/)

[2025-06-13](https://motherduck.com/videos/what-can-postgres-learn-from-duckdb-pgconfdev-2025/)

### [What can Postgres learn from DuckDB? (PGConf.dev 2025)](https://motherduck.com/videos/what-can-postgres-learn-from-duckdb-pgconfdev-2025)

DuckDB an open source SQL analytics engine that is quickly growing in popularity. This begs the question: What can Postgres learn from DuckDB?

YouTube

Ecosystem

Talk

[![" pg_duckdb: Ducking awesome analytics in Postgres" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F0kc_W5o0tcg_HD_03880f61fb.jpg&w=3840&q=75)](https://motherduck.com/videos/pg_duckdb-ducking-awesome-analytics-in-postgres/)

[2025-06-12](https://motherduck.com/videos/pg_duckdb-ducking-awesome-analytics-in-postgres/)

### [pg\_duckdb: Ducking awesome analytics in Postgres](https://motherduck.com/videos/pg_duckdb-ducking-awesome-analytics-in-postgres)

Supercharge your Postgres analytics! This talk shows how the pg\_duckdb extension accelerates your slowest queries instantly, often with zero code changes. Learn practical tips and how to use remote columnar storage for even more speed.

Talk

Sources

[View all](https://motherduck.com/videos/)

Authorization Response