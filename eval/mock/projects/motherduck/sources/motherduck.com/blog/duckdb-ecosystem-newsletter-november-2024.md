---
title: duckdb-ecosystem-newsletter-november-2024
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2024
indexed_at: '2025-11-25T19:56:40.055477'
content_hash: 1c8fd4f02d971f52
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: November 2024

2024/11/04 - 8 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

Hello. I'm [Simon](https://www.ssp.sh/), and I am excited to share another monthly newsletter with highlights and the latest updates about DuckDB, delivered straight to your inbox.

In this November issue, I gathered twelve exciting links, ranging from using DuckDB as an HTTP OLAP server to integrating it with the OSS Unity catalog to exciting applications such as DuckDB as a DrugDB. Others are building high-performance and cost-efficient data pipelines with DuckDB and Python and lazy loading data frames with Hex. Notable features include Excel-style pivoting, enhanced [ACID compliance](https://motherduck.com/learn-more/acid-transactions-sql), and MotherDuck's new LLM integration with SQL. Please enjoy.

As always, if you have feedback, news, or any insights, they are always welcome. 👉🏻 [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2F1667998175220.jpeg&w=3840&q=75)

### Lorenzo Mangani

[Lorenzo](https://www.linkedin.com/in/lmangani/) is CEO and Co-Founder at QXIP BV, Leaders in Open-Source Telecom Observability. But he's also recently contributed to the DuckDB community by creating [some community DuckDB extensions](https://github.com/quackscience)(more on that below!). Thanks Lorenzo, for your creativity within the DuckDB community!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [Building Cost-Efficient Data Pipelines with Python & DuckDB](https://www.startdataengineering.com/post/cost-effective-pipelines/)

Joseph writes about cost-efficient data pipelines and categorizes data pipelines with Python and DuckDB into three parts, helping visualize when best to use DuckDB. He also offers a [GitHub repo](https://github.com/josephmachado/cost_effective_data_pipelines/tree/main?tab=readme-ov-file) with the code.

### [Ducklake: Integrate DuckDB with Unity Catalog](https://xebia.com/blog/ducklake-a-journey-to-integrate-duckdb-with-unity-catalog/)

In this article, the team of Xebia integrated DuckDB using dbt and Jupyter notebooks with the open-source Unity Catalog and uses the advantages of both worlds. The integration provides real-time updates in the Unity Catalog UI, confirming that DuckDB and Unity Catalog are fully integrated.

### [Community Extensions: DuckDB HTTP GET/POST Client // HTTP Server](https://github.com/quackscience/duckdb-extension-httpclient)

A new HTTP DuckDB Community Extension is out. With it, you can make HTTP requests directly from within DuckDB. For example, with your SQL query, you can create a GET request using http\_get(url) and a POST request using http\_post(url, headers, params). This can be useful for fetching data from REST APIs, extracting data from JSON payloads, and processing API responses using DuckDB's SQL capabilities. The extension is available in the community extension repository, but its status is still experimental.

Quackscience also released another extension, the HTTP Server Extension, which transforms any DuckDB instance into an HTTP OLAP API server. With just a few commands, you get a queryable HTTP API with authentication support, a built-in query UI, and the ability to work with local and MotherDuck datasets. This makes it perfect for spinning up quick data services or creating distributed query networks while maintaining DuckDB's simplicity and performance.

### [DuckDB User Survey Analysis](https://duckdb.org/2024/10/04/duckdb-user-survey-analysis.html)

DuckDB Labs surveyed 500+ DuckDB users and shared their findings.

It's no surprise that DuckDB is often used on a laptop, but servers were also popular. The most popular clients are the Python API and the standalone CLI client. Most users don't have giant data sets but appreciate the high performance. Users would like performance optimizations related to time series and partitioned data. DuckDB is popular among data engineers, analysts, scientists, and software engineers. The survey includes many more findings, including some nice graphs.

### [Excel-Style Pivoting, read\_excel() function and duckdb-gsheets](https://duckdb.org/2024/09/27/sql-only-extensions.html)

Excel never dies, and with it, the Pivot Tables 😉. This year, in the year of the return of Pivot Tables (I have seen them in Rill and Cube), DuckDB supports these now, too, with:

`INSTALL pivot_table FROM community;
LOAD pivot_table;`

The extension supports well-known SQL features, such as PIVOT, UNNEST, MACRO, GROUPING SETS, ROLLUP, UNION ALL BY NAME, COLUMNS, and many more.

On the same note, Thomas wrote, "Where’s the read Excel() function in DuckDB?". Surprisingly, there is no read\_excel() function yet, but you can (mis)use DuckDB's Spatial extension. But what does spatial have to do with Excel? Nothing, but it's rooted in the fact that historically and even now, many geospatial files were — and still are — shared in Excel data files. Archie took it further with duckdb-gsheets, reading, and writing to Google Sheets.

### [DuckDB as a DrugDB: a Free and Simple Multi-Model Drug and Trial Database](https://dgg32.medium.com/duckdb-as-a-drugdb-a-free-and-simple-multi-model-drug-and-trial-database-83c222d1e9dd)

This is the fourth case study for clinical trials Sixing has made. He tried Google Spanner, Postgres, SurrealDB, and now DuckDB. He uses a combined dataset containing over 5000 drugs, 2000 disorders, and 2000 clinical trials, as well as Superset, for visualization. He uses extensions for full-text search (fits) and vector similarity search (vss) as well as DuckPGQ and uses the PGQ (Property Graph Query Language) for graph-related operations.

Sixing concluded that DuckDB's extension system successfully handles SQL, graph queries, vector searches, and full-text searches, making it suitable for complex healthcare data analysis. While the ecosystem needs development in areas like visualization tools, DuckDB's columnar storage and SQL/GQL compatibility make it an attractive alternative to traditional databases.

### [Building a High-Performance Data Pipeline Using DuckDB](https://practicaldataengineering.substack.com/p/building-data-pipeline-using-duckdb)

Alireza showcases how to build an efficient data pipeline using DuckDB as a compute engine for data lakes, implementing a Medallion architecture (Bronze → Silver → Gold) with GitHub Archive data. His detailed guide shows how DuckDB's in-memory processing and SQL capabilities can handle JSON ingestion, Parquet serialization, and data aggregation with impressive performance—processing nearly six million records in under a minute, with complete [sample code](https://github.com/pracdata/duckdb-pipeline) available.

### [Changing Data with Confidence and ACID](https://duckdb.org/2024/09/25/changing-data-with-confidence-and-acid.html)

Hannes and Mark explain the ACID principles behind DuckDB and how you can confidently change data with full ACID guarantees by default without additional configuration. Everything started with transactions, and eventually, the well-known ACID came with the principles that describe a set of guarantees that a data management system must provide to be considered safe. ACID is an acronym that stands for Atomicity, Consistency, Isolation, and Durability. Every one of these is explained in greater detail.

It's pretty novel for an OLAP database to have ACID. The article goes on to explain why ACID in OLAP makes sense. It summarizes that DuckDB has passed the specific ACID Transaction tests from the TPC-H Benchmark tests. Check the tests out at [GitHub](https://github.com/hannes/duckdb-tpch-power-test).

### [Optimizing Multi-Modal Analysis by Lazy Loading Dataframes](https://hex.tech/blog/lazy-dataframes/)

Hex, a notebook-based solution, has improved its performance by migrating to a DuckDB-based architecture that directly queries Arrow data from S3. This has enabled 5-10x speedups in execution times. Moving data processing from Python to DuckDB and Arrow in their backend service enabled lazy loading and more efficient data handling, eliminating pandas format limitations and reducing memory usage.

### [Introducing the prompt() Function: Use the Power of LLMs with SQL](https://motherduck.com/blog/sql-llm-prompt-function-gpt-models/)

MotherDuck released LLMs within SQL. Instead of a context switch, we can ask the LLM to summarize text into a short poem with :

```vbnet
Copy code

SELECT
  prompt('summarize the comment in a Haiku: ' || text)
AS summary FROM sample_data.hn.hacker_news
limit 20;
```

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [PyData NYC: A Duck in the hand is worth two in the Cloud: Data preparation and analytics on your laptop with DuckDB](https://pydata.org/nyc2024/tickets/)

**08 November, 11 Times Square, New York City, NY 🗽 - 2:30 PM US, Eastern**

Guen Prawiroatmodjo & Jacob Matson will showcase how DuckDB replaces Spark for 10GB-1TB tasks on laptops with fast, seamless Python integration, enabling efficient analytics and easy Cloud deployment via MotherDuck’s serverless support.

### [Small Data NYC: Watch Party Wednesday with Altana, Jamsocket and MotherDuck](https://lu.ma/small-data-nyc)

**13 November, 25 Kent, Williamsburg, Brooklyn 🗽 - 6:00 PM America, New York**

Join the Small Data community for Watch Party Wednesday to get a sneak peek of Small Data SF talks from Benn Stancil and MotherDuck CEO and Co-founder Jordan Tigani.

### [DataGalaxy Tech Summit NYC: How to put DuckDB to work today?](https://www.datagalaxy.com/en/events/datagalaxy-tech-summit/)

**13 November New York City 🗽 - 3:30 PM US, Eastern**

Nick Ursa of MotherDuck will present a talk on DuckDB. DataGalaxy brings together industry experts to share their insights on optimizing data models, choosing the best data storage formats, and insights on streamlining data ingestion processes.

### [AI Native Summit 2024](https://events.zettavp.com/zetta/rsvp/register?e=ai-native-summit-2024)

**21 November, Computer History Museum, Mountain View, CA 🌉 - 12:00 PM America, Los Angeles**

Join MotherDuck CEO Jordan Tigani and AI leaders across research, startups and global companies for a day of discussion about the state of enterprise AI.

### [Data Rock N' Roll at AWS re:Invent](http://events.montecarlodata.com/datarocknroll/motherduck)

**3 December, Brooklyn Bowl Las Vegas 🤘 - 6:00 PM America, Los Angeles**

Attendees will enjoy a fun-filled atmosphere where they can network with fellow AWS enthusiasts, industry leaders, and innovators while competing in friendly bowling matches.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2024/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2024/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2024/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2024/#upcoming-events)

Subscribe to DuckDB Newsletter

E-mail

Subscribe to other MotherDuck news

Submit

Subscribe

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[![The Data Warehouse powered by DuckDB SQL](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FData_Warehouse_82fcb17ea8.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-data-warehouse/)

[2024/11/01 - Jacob Matson](https://motherduck.com/blog/motherduck-data-warehouse/)

### [The Data Warehouse powered by DuckDB SQL](https://motherduck.com/blog/motherduck-data-warehouse)

Learn how DuckDB and MotherDuck transform data into business insights. DuckDB’s fast SQL processing meets MotherDuck’s cloud integration, creating a flexible, powerful data warehouse solution to solve complex business challenges and drive impact.

[View all](https://motherduck.com/blog/)

Authorization Response