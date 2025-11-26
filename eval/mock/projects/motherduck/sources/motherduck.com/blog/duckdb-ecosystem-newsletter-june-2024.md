---
title: duckdb-ecosystem-newsletter-june-2024
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2024
indexed_at: '2025-11-25T19:57:41.879898'
content_hash: b50e4e6d4acee35b
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: June 2024

2024/06/08 - 5 min read

BY

[Ryan Boyd](https://motherduck.com/authors/ryan-boyd/)

## Hey, friend 👋

This week represented a pivotal moment for DuckDB: the [release of DuckDB 1.0.0](https://duckdb.org/2024/06/03/announcing-duckdb-100.html).  With this “Snow Duck” release, DuckDB is now production-ready, with guaranteed backwards-compatibility, improved performance and stability.  Our team at MotherDuck [congratulates our friends](https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release) at DuckDB Foundation and DuckDB Labs on this huge milestone.

I don’t think any of us could have imagined the success DuckDB has had in redefining the conversation around efficient data analytics and the viability of embedded database engines for data big and small.  The movement is underway and accelerating in no small part due to the amazing community around DuckDB which has contributed to the core library, built the extension ecosystem, helped other data people use DuckDB and shared their experiences.

Heres to you, the amazing DuckDB community: 🍻

Our Featured Community Member this month is a duplicate of the [very first person featured](https://motherduck.com/blog/duckdb-ecosystem-newsletter-one/#featured-community-members) in this newsletter because of how pivotal he’s been in the march towards 1.0: DuckDB co-creator Mark Raasveldt.

Cheers,

Ryan

co-founder @ MotherDuck

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2FImported%2520sitepage%2520images%2Fmark_raasveldt.jpg&w=3840&q=75)

### Mark Raasveldt

[Mark Raasveldt (mytherin)](https://mytherin.github.io/) is the co-creator and one of the driving forces behind DuckDB. He was pivotal in getting DuckDB to 1.0.0.

During his studies at CWI in the Netherlands, he recognized the need for a database tailored to analytical workloads, leading him to co-found DuckDB with Hannes Mühleisen. As the CTO of DuckDB Labs, Mark's expertise in database internals and performance optimization has been pivotal in shaping DuckDB's architecture, from efficient data ingestion to advanced query processing techniques.

With a vision for further enhancements and expanded capabilities, Mark continues to lead DuckDB's development, fostering a vibrant community of contributors.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [How We Fused DuckDB into Postgres with Crunchy Bridge for Analytics](https://www.crunchydata.com/blog/how-we-fused-duckdb-into-postgres-with-crunchy-bridge-for-analytics)

The team at Crunchy Data has integrated DuckDB into Postgres using Crunchy Bridge, enabling powerful analytics capabilities. This fusion leverages DuckDB's speed and efficiency for in-database analytics without the need for data transfers.

### [Accessing 150k Hugging Face Datasets with DuckDB, query using GPT-4o](https://huggingface.co/blog/chilijung/access-150k-hugging-face-datasets-with-duckdb)

Explore how DuckDB is being utilized to access and analyze a vast array of datasets available on Hugging Face. With over 150,000 datasets, DuckDB's seamless integration enhances data accessibility and analysis workflows.

### [Enhancing DuckDB UNIX Pipe Integration with shellfs](https://www.linkedin.com/pulse/enhancing-duckdb-unix-pipe-integration-introducing-shellfs-conover-f0jwe?utm_source=share&utm_medium=member_android&utm_campaign=share_via)

Discover how shellfs is improving DuckDB's integration with UNIX pipes, making it easier to handle data streams efficiently. This enhancement significantly streamlines data processing tasks, particularly in UNIX environments.

### [DuckDB In-Process Python Analytics for Not-Quite-Big Data](https://thenewstack.io/duckdb-in-process-python-analytics-for-not-quite-big-data/)

Learn how DuckDB facilitates in-process analytics in Python, offering an efficient solution for medium-sized data. This tutorial covers the practical implementation and benefits of using DuckDB for Python-based data analysis.

### [Working with Cron Expressions in DuckDB](https://www.linkedin.com/pulse/cron-expressions-duckdb-rusty-conover-6bole/?trackingId=Xhp0IvC0IjmDaMNH3CEF1Q%3D%3D)

Rusty Conover is featured twice this month!  In this article, Rusty provides a comprehensive guide on utilizing cron expressions within DuckDB for scheduling tasks. This article delves into the syntax and use cases of cron expressions to automate repetitive tasks.

### [My First Billion Rows in DuckDB](https://towardsdatascience.com/my-first-billion-of-rows-in-duckdb-11873e5edbb5)

A detailed tutorial on handling large datasets efficiently with DuckDB, showcasing its performance and scalability. This article highlights practical tips and techniques for working with billion-row datasets in DuckDB.

### [A Way to Production-Ready AI Analytics with RAG](https://medium.com/gooddata-developers/a-way-to-production-ready-ai-analytics-with-rag-0c71fc3b23e8)

GoodData Developers discuss leveraging DuckDB for robust AI analytics in production environments. This article explores the practical applications and benefits of using DuckDB in AI-driven analytics workflows.

### [Quack Quack Ka-Ching: Cut Costs by Querying Snowflake from DuckDB](https://medium.com/datamindedbe/quack-quack-ka-ching-cut-costs-by-querying-snowflake-from-duckdb-f19eff2fdf9d)

Learn how querying Snowflake from DuckDB can help you reduce costs significantly. This article provides insights into cost-saving strategies and performance optimization techniques for data querying.

### [Search Using DuckDB - Part 2](https://motherduck.com/blog/search-using-duckdb-part-2/)

MotherDuck continues their series on using DuckDB for efficient search functionalities. This part delves deeper into advanced search techniques and practical implementations using DuckDB.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [Data & AI Summit](https://www.databricks.com/dataaisummit)

**10-13 June, San Francisco, USA**

There are a number of DuckDB related happenings this week at Databricks’ Data & AI Summit. Hannes will be featured in the [keynote session on Thursday](https://www.databricks.com/dataaisummit/session/data-ai-summit-keynote-thursday). There is also a breakout session by the Databricks team on [Delta Lake and DuckDB](https://www.databricks.com/dataaisummit/session/delta-lake-meets-duckdb-delta-kernel). Lastly, MotherDuck is hosting a [party for the DuckDB community on Tuesday evening.](https://www.eventbrite.com/e/motherducking-party-after-dataai-summit-san-francisco-tickets-901904038257?aff=oddtdtcreator&_gl=1%2A39c7c7%2A_gcl_au%2AMjAxODE0ODM1MC4xNzEwMjY5OTI5LjEwNTM5MTI4NC4xNzEwNzk4NTU3LjE3MTA3OTg1NTY.%2A_ga%2AMTU4MTg2MDQxOC4xNzEwMjY5OTI5%2A_ga_L80NDGFJTP%2AMTcxNzg3NTU3Mi4xOTUuMS4xNzE3ODc3MjY5LjU2LjAuMjMyNjE2Mzkz)

### [DuckCon \#5 in Seattle](https://duckdb.org/2024/08/15/duckcon5.html)

**15 August, Seattle, WA, USA**

DuckDB Labs is excited to hold the next “DuckCon” DuckDB user group meeting in Seattle, WA, sponsored by MotherDuck. The meeting will take place on August 15, 2024 (Thursday) in the SIFF Cinema Egyptian.

As is traditional in DuckCons, it will start with a talk from DuckDB’s creators [Hannes Mühleisen](https://hannes.muehleisen.org/) and [Mark Raasveldt](https://mytherin.github.io/) about the state of DuckDB. This will be followed by presentations by DuckDB users. In addition, they will have several lightning talks from the DuckDB community.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2024/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2024/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2024/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2024/#upcoming-events)

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

[![Congratulations to DuckDB Labs On Reaching 1.0!](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_1_0_blog_thumbnail_d494b36705.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release)

[2024/06/03 - MotherDuck team](https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release)

### [Congratulations to DuckDB Labs On Reaching 1.0!](https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release)

MotherDuck congratulates DuckDB Labs on their milestone, landmark 1.0 release. Learn more about its significance and what it means for MotherDuck! And stay tuned for some exciting news heading your way soon...

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response