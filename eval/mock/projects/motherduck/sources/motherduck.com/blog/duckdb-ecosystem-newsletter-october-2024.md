---
title: duckdb-ecosystem-newsletter-october-2024
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-october-2024
indexed_at: '2025-11-25T19:56:21.795654'
content_hash: 4f6efe306750175f
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: October 2024

2024/10/04 - 10 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

Hello, I'm Simon, and I have the honor of writing my second monthly newsletter and bringing the highlights and latest updates around DuckDB to your inbox. One line about me: I'm a data engineer and technical author of the [Data Engineering Blog](https://ssp.sh/), [DE Vault](https://vault.ssp.sh/), and a living book about [Data Engineering Design Patterns](https://www.dedp.online/). I'm a big fan of DuckDB and how MotherDuck simplifies distribution and adds features.

This issue features DuckDB's latest developments, from the insights of DuckCon #5 to exciting new features in version 1.1.0. Discover how DuckDB is revolutionizing data processing with a Tutorial on RAG integration, Spark API compatibility, and community extensions as we explore its growing impact across various industries and applications. I hope you enjoy it.

If you have feedback, news, or any insight, they are always welcome. 👉🏻 [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F1518890010831_d1b140a631.jpeg&w=3840&q=75)

### Quentin Lhoest

[Quentin](https://www.linkedin.com/in/quentin-lhoest/?utm_campaign=DuckDB%20Ecosystem%20Newsletters&utm_medium=email&_hsmi=2&utm_content=2&utm_source=hs_email) is an Open Source ML Engineer at Hugging Face and a maintainer of Datasets. Back in March, he presented at a DuckDB meetup in Paris how Hugging Face uses DuckDB behind the scenes to provide direct insights into over 200,000 datasets. Furthermore, with the help of DuckDB Labs, you can now query Hugging Face datasets directly from DuckDB using `hf://`. Recently, he has been pushing the boundaries of the latest features of DuckDB by [showing an entire LLM pipeline using pure SQL](https://www.linkedin.com/posts/quentin-lhoest_apis-sql-gliner-activity-7246556906524217344-u-0F/?utm_medium=member_desktop&_hsmi=2&utm_source=share). Thanks, Quentin, for your energy in the DuckDB community!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [DuckCon \#5 Videos (Seattle, August 2024)](https://www.youtube.com/playlist?list=PLzIMXBizEZjhbacz4PWGuCUSxizmLei8Y)

The fifth DuckCon took place in Seattle in August; the videos are online now. I want to highlight some of the key insights from the talks. They are all worth watching.

The latest development with Hannes is where he shows the staggering numbers of DuckDB. Just the Python client has 6 million downloads per month. The extensions went from January this year with 2 million to 17 million per month. The website hits 600k unique web visitors per month, among other numbers growing fast.

Frances talks, among other things, about zero-copy clone and [embedded analytical processing](https://youtu.be/zl3G7TiI0Q4?si=NoXq7Ipjmza12Clm&t=1065), with a new extension that sits on top of Postgres called pg\_duckdb (announced in the last newsletter).

Mark also talks about the [future of DuckDB](https://youtu.be/xX6qnP2H5wk?si=JDNC_SwjaKr_J4k9&t=1679) and the direction in which it is going. For example, the extension ecosystem should be open to other languages, such as Rust. Besides support for Apache Iceberg and Delta Lake table format, it is adding support for lakehouse data formats and writing support. Other future improvements are in the Optimiser improvements, such as partition/sorting awareness and cardinality estimation, and some work on the parser extensibility; a research paper is also coming out.

Junaid at Atlan [built DuckDB pipelines with ArgoCD](https://youtu.be/rveaJWvD_zk?si=nPHbBZVoM9OB4tAT) and replaced Spark with a ~2.3x performance improvement. Brian from Rill shows how to have declarative, sub-second dashboards on top of DuckDB. There are many more we can't go into now, but I highly recommend checking them out; the complete list of DuckCon you'll find [here](https://duckdb.org/2024/08/15/duckcon5.html).

### [Building an AI Project with DuckDB (Tutorial)](https://www.datacamp.com/tutorial/building-ai-projects-with-duckdb)

Abid from Datacamp guides us through building tables, performing data analysis, building an RAG application, and using an SQL query engine with LLM primarily in two steps:

1. For that, we will work on two projects. First, we'll build a Retrieval-Augmented Generation (RAG) application using DuckDB as a vector database.

2. Then, we'll use DuckDB as an AI query engine to analyze data using natural language instead of SQL.


The tutorial explores the DuckDB Python API and showcases how easy it can be to create a chatbot with with an LLM such as the GPT4o model, the OpenAI API with text-embedding-3-small model, LlamaIndex and DuckDB—embedding an LLM model with a DuckDB database using the duckdb engine. This is an excellent example of how to build a great solution with minimal effort.

### [DuckDB Working with Spark API](https://duckdb.org/docs/api/python/spark_api)

Ryan [demonstrated](https://www.linkedin.com/posts/ryan-eakman-65469988_dataengineering-spark-activity-7233659465382649857-UCSx?utm_source=share&utm_medium=member_desktop) how he uses a SparkSession that is actually an SQLFrame DuckDBSession:

```python
Copy code

from sqlframe import activate
activate ("duckdb")

from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate() # spark is a SQLFrame DuckDBSession!
```

This allows us to run any pipeline transformation with the Pyspark DataFrame API without needing a Spark cluster or dependencies 🤯. [SQLFrame](https://github.com/eakmanrq/sqlframe) also supports BigQuery, Postgres, and Snowflake.

This is mostly possible with the new official [DuckDB Spark API](https://duckdb.org/docs/api/python/spark_api) implemented by DuckDB. The DuckDB PySpark API allows you to use the familiar Spark API to interact with DuckDB. All statements are translated to DuckDB's internal plans and executed using DuckDB's query engine. This code equivalent looks like this:

```javascript
Copy code

from duckdb.experimental.spark.sql import SparkSession as session
from duckdb.experimental.spark.sql.functions import lit, col
import pandas as pd

spark = session.builder.getOrCreate()
```

### [Ibis: because SQL is everywhere, and so is Python](https://www.youtube.com/watch?v=cCHME7eXAhk)

Gil teaches us about the beautiful world of Ibis and how it integrates with DuckDB. He showcases how Ibis can be used as an interface to interact with DuckDB, allowing users to write Python code that gets translated to efficient DuckDB queries. In addition, you can easily switch between engines like DuckDB and Polars using the same code, navigating different SQL dialects.

He mentions how processing 1.1 billion rows of PyPI package data using DuckDB through Ibis in about 38 seconds on a laptop, using only about 1GB of RAM.

### [tarfs – a DuckDB Community Extension](https://community-extensions.duckdb.org/extensions/tarfs.html)

This new community extension lets you read and globalize files within uncompressed tar archives. tarfs can be combined with DuckDB's httpfs to read tar archives over http by chaining the tar:// and http:// prefixes. Some examples:

```sql
Copy code

#Glob into a tar archive:

SELECT filename
FROM read_blob('tar://data/csv/tar/ab.tar/*') ORDER BY ALL;

#Open a specific file inside of a tar archive:

SELECT *
FROM read_csv('tar://data/csv/tar/ab.tar/a.csv') ORDER BY ALL;
```

> What is Glob?
> Glob is a pattern-matching technique used in file systems and programming to search for and identify multiple files that match a specific pattern. Globbing allows you to use wildcard characters to match multiple filenames or paths.

### [New Release DuckDB 1.1.0/1.1.1 is Out](https://duckdb.org/2024/09/09/announcing-duckdb-110)

With its latest release, DuckDB version 1.1.0, "Eatoni", brings many new features and improvements. This update makes the database better at handling different types of data and faster at running queries. Some of the new things include better math handling, new ways to work with SQL, and tools to help the community build add-ons for DuckDB.

DuckDB is now much performant with smarter about filtering data when combining tables, which makes joins faster and works now on multiple tasks simultaneously, both when streaming query results and combining data from different sources. Naming two here only. It can run complex queries more quickly, especially when dealing with large amounts of data or complicated calculations. The database is also better at handling geographical data; e.g., GeoParquet extends the Parquet format with geographic data. Please check [Spatial Extension](https://duckdb.org/docs/stable/core_extensions/spatial/overview).

Find all changes on [Release DuckDB 1.1.0](https://github.com/duckdb/duckdb/releases/tag/v1.1.0). Besides that release, 1.1.1 has been released with [fixing minor bugs](https://github.com/duckdb/duckdb/releases/tag/v1.1.1) that has been discovered since 1.1.0. MotherDuck also published [a blog to highlight some hidden gems](https://motherduck.com/blog/duckdb-110-hidden-gems/) from 1.1.

### [DuckDB for the Impatient: From Novice to Practitioner in Record Time](https://medium.com/@raphael.mansuy/duckdb-for-the-impatient-from-novice-to-practitioner-in-record-time-a813584e9381)

A great article summarizing the benefits of DuckDB. Raphael highlights DuckDB's seamless integration with popular data tools like Python, R, and Pandas, showcasing practical examples of leveraging DuckDB in data pipelines.

It delves into advanced querying techniques, demonstrating complex operations involving joins, aggregations, and window functions. The article also addresses performance optimization, providing insights into DuckDB's query execution process and offering tips for troubleshooting common issues. It explores real-world applications, illustrating how DuckDB has been successfully implemented in various industries for tasks such as real-time analytics and embedded data processing.

### ​​ [Querying IP addresses and CIDR ranges with DuckDB](https://tobilg.com/querying-ip-addresses-and-cidr-ranges-with-duckdb)

Tobias created three functions (called Macros in DuckDB) to determine if IPs from CIDRs are in a certain range. This is an excellent idea if you quickly need to process the same logic on your dataset and make the SQL as simple as possible. He had to start (network) and end (broadcast) IP addresses of a CIDR range that needed to be cast to integers to be able to determine if a given IP address (also cast to an integer) lies within the derived integer value boundaries.

### [Dynamic Column Selection COLUMNS() gets even better with 1.1](https://www.markhneedham.com/blog/2024/09/22/duckdb-dynamic-column-selection/)

Mark uses a wide dataset from Kaggle's FIFA 2022 in this article and applies the new features.

He demonstrates how you can do regular expressions on your column search with the added column search function: `select COLUMNS('gk_.*|.*_pass|.*shot.*|[^mark]ing') FROM players`.

Mark also shows how to exclude columns with variables that can be used if they return a single value or an array. You can also search for specific types, e.g., numeric fields with \`select player, COLUMNS(c -> list\_contains(getvariable('numeric\_fields'), c)) from players.

This is interesting and a more efficient way than the traditional select \* from information\_schema.tables with all metadata about every table, which DuckDB also supports. If you prefer [video](https://www.youtube.com/watch?v=ekUvkhD2OlQ) format, Mark made one, too.

### [Analyzing Multiple Google Sheets with MotherDuck](https://motherduck.com/blog/google-sheets-motherduck/)

This article showcases an exciting use case for combining multiple Excel sheets, or in this case, Google Sheets, and using SQL to join and extract analytical insights. In this article, Jacob shows how to do just that with MotherDuck. You can use private (with authentication) or publicly shared Google Sheets. Try it out at [MotherDuck](https://app.motherduck.com/).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [MotherDuck @ dbt Coalesce 2024](https://coalesce.getdbt.com/)

**7 October, Las Vegas, NV, USA**

Join MotherDuck at dbt Coalesce in Las Vegas! Explore how we’re revolutionizing data pipelines, enjoy cool swag & interactive booth activities, and mingle with your data peers.

**Location:** Resorts World, Las Vegas, NV 🌆 - 5:00 PM America, Los Angeles

**Type:** In Person

* * *

### [Introduction to DuckDB SQL](https://www.datacamp.com/webinars/introduction-to-duckdb-sql?utm_source=linkedin&utm_medium=organic_social&utm_campaign=231001_1-webinar_2-all_3-na_4-na_5-na_6-duckdb-sql_7-li_8-ogsl-li_9-oct01_10-bau_11-na)

**8 October - online**

Online webinar introduction to DuckDB SQL.

**Location:** online - 7:00 PM Mauritius Standard Time

**Type:** Online

* * *

### [Simplify your dbt Data Pipelines with Serverless DuckDB](https://coalesce-widgets.getdbt.com/agenda/session/1354859)

**8 October, Las Vegas, NV, USA**

Learn how to streamline data flow complexity and expenses while reaping the benefits of an ergonomic and frictionless workflow with MotherDuck, the serverless DuckDB-backed cloud data warehouse.

**Location:** Resorts World, Las Vegas, NV 🌆 - 12:00 PM America, Los Angeles

**Type:** In Person

* * *

### [Gatsby's Golden Happy Hour @ dbt Coalesce!](https://coalescehh.splashthat.com/)

**9 October, Las Vegas, NV, USA**

Felicis, Metaplane and MotherDuck invite you to unwind with cocktails, conversations, and good vibes at the ultimate analytics engineering conference in Las Vegas after a day of diving into the data with your fellow data people!

**Location:** Gatsby's Lounge, Las Vegas, NV 🌆 - 5:00 PM US, Pacific

**Type:** In Person

* * *

### [Harnessing AI for Relational Data: Industry and Research Perspectives](https://lu.ma/9vfh57p8)

**10 October - online**

Join MotherDuck, Numbers Station and WeWork at #SFTechWeek for insightful talks and a panel with leading academics and industry professionals!

**Location:** Online - 5:30 PM US, Eastern

**Type:** Online

* * *

### [DuckDB Amsterdam Meetup \#1](https://www.meetup.com/duckdb/events/303482464/)

**17 October, Amsterdam, NH, Netherlands**

Join us for the first DuckDB Amsterdam meetup! Hear from experts about real-world applications of DuckDB related to analytics engineering at Miro and how MotherDuck uses AI and machine learning.

**Location:** Miro, Stadhouderskade 1, Amsterdam, NH 🌷 - 6:00 PM Europe, Amsterdam

**Type:** In Person

* * *

### [The Postmodern Data Stack](https://techcrunch.com/events/tc-disrupt-2024/)

**28 October, San Francisco, CA, USA**

Tomasz Tunguz hosts a panel at TechCrunch Disrupt on the Postmodern Data Stack with Jordan Tigani of MotherDuck, Colin Zima of Omni, and Tyson Mao of Tobiko Data.

**Location:** Moscone Center West, San Francisco, CA 🌉 - 9:30 AM America, Los Angeles

**Type:** In Person

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-october-2024/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-october-2024/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-october-2024/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-october-2024/#upcoming-events)

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

[![DuckDB Ecosystem: September 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_3_72ab709f58.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

[2025/09/09 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

### [DuckDB Ecosystem: September 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025)

DuckDB Monthly #33: DuckDB 58× faster spatial joins, pg\_duckdb 1.0, and 79% Snowflake cost savings

[![MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Feu_launch_blog_b165ff2751.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-in-europe/)

[2025/09/24 - Garrett O'Brien, Sheila Sitaram](https://motherduck.com/blog/motherduck-in-europe/)

### [MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/blog/motherduck-in-europe)

Serverless analytics built on DuckDB, running entirely in the EU.

[View all](https://motherduck.com/blog/)

Authorization Response