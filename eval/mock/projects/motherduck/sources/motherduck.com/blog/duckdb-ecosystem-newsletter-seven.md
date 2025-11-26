---
title: duckdb-ecosystem-newsletter-seven
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-seven
indexed_at: '2025-11-25T19:57:36.809175'
content_hash: 4d3528b81116c41f
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: June 2023

2023/06/16 - 4 min read

BY

[Marcos Ortiz](https://motherduck.com/authors/marcos-ortiz/)

## Hey, friend 👋

It’s [Marcos](https://www.linkedin.com/in/mlortiz) again, aka “ _DuckDB News Reporter_” with another issue of “This Month in the DuckDB Ecosystem for June 2023.

This month keeps showing the rising popularity of DuckDB as a great developer tool. From **analyzing music data** to **being the choice to work with 50k+ datasets in the Hugging Face Hub**, from using it for creating dummy data to **analyzing your own Fitbit data** with it.

As always we share here, this is a two-way conversation: if you have any feedback on this newsletter, feel free to send us an email to _[duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com)_

-Marcos

## Featured Community Member

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmax_30274bccd3.jpeg%3Fupdated_at%3D2023-06-16T15%3A55%3A25.443Z&w=3840&q=75)

### Max Gabrielsson

[Max Gabrielsson](https://github.com/Maxxen) is a Junior Software engineer at DuckDB labs but he has already made some impressive waves! He’s the creator of the official [spatial DuckDB extension](https://github.com/duckdblabs/duckdb_spatial).  While it’s still WIP, it’s much more welcome for any geo data processing. You can read more about this one [here](https://duckdb.org/2023/04/28/spatial.html).

[Learn more about Max here](https://www.linkedin.com/in/max-gabrielsson-22459a156/)

## Top DuckDB Links this Month

### [DuckDB: run SQL queries on 50,000+ datasets on the Hugging Face Hub](https://huggingface.co/blog/hub-duckdb)

![image6.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F1_newsletter_574f72d7ef.png%3Fupdated_at%3D2023-06-16T17%3A15%3A35.498Z&w=3840&q=75)

The Hugging Face team just announced the integration with DuckDB, which means that now you can use the simplicity of SQL on 50k+ datasets on its Hub.

### [Correlated Subqueries in SQL](https://duckdb.org/2023/05/26/correlated-subqueries-in-sql.html)

This new feature from DuckDB will allow building more readable and easier-to-maintain complex queries.

### [Shredding deeply nested JSON, one vector at a time by Laurens Kuiper - DuckDB Labs](https://www.youtube.com/watch?v=7MtJZqBdYTI)

In this video, Laurens shows how to work with deeply nested JSON data in DuckDB

### [What's the hype behind DuckDB?](https://blog.mattpalmer.io/p/whats-the-hype-behind-duckdb)

[Matt Palmer](https://www.linkedin.com/in/matt-palmer/) shares a very interesting perspective in this post on why DuckDB is so popular these days.

### [DuckDB + Dagster](https://docs.dagster.io/integrations/duckdb)

The Dagster team just released a tutorial to show how to combine DuckDB I/O Manager and Dagster’s Software-Defined Assets. If you use Dagster in production today, you will benefit a lot from this seamless integration here

### [Cross-filtering 10 Million Entries with FalconVis + DuckDB](https://observablehq.com/@cmudig/falcon-vis-10m)

Researchers from the CMU Data Interaction Group just shared this notebook on Observable where they combined the power of FalconVIS and DuckDB to cross-filter 10 Million rows.

### [My (very) personal data warehouse — Fitbit activity analysis with DuckDB](https://simonaubury.com/posts/202306_duckdb_fitbit/)

![image6.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F4_0d0cfdfef9.png&w=3840&q=75)

In this post, [Simon Aubury](https://www.linkedin.com/in/simonaubury/) analyzed its own Fitbit activity with the help of DuckDB and Seaborn

### [clickhouse-local vs DuckDB on Two Billion Rows of Costs](https://www.vantage.sh/blog/clickhouse-local-vs-duckdb)

![image6.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F5_newsletter_8d2221942c.png%3Fupdated_at%3D2023-06-16T15%3A55%3A27.807Z&w=3840&q=75)

The Vantage team shared an insightful comparison between clickhouse-local and DuckDB. The post is worth a read because it highlights a very important point on why people are selecting DuckDB for more and more projects: developer productivity with DuckDB is just awesome

### [DuckDB: Generate dummy data with user-defined functions (UDFs)](https://www.markhneedham.com/blog/2023/06/02/duckdb-dummy-data-user-defined-functions/)

![imagemark.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F6_newsletter_c1da62da16.webp%3Fupdated_at%3D2023-06-19T17%3A21%3A42.883Z&w=3840&q=75)

[Mark Needham](https://www.linkedin.com/in/markhneedham/) (a regular person in this newsletter) wrote about how to use the potential of UDFs on DuckDB to generate dummy data. If you are a visual person, you can watch the video Mark did explaining the same thing [here](https://www.youtube.com/watch?v=EVLDg-RNjoc).

### [Graph components with DuckDB](https://maxhalford.github.io/blog/graph-components-duckdb/)

[Max Halford](https://www.linkedin.com/in/maxhalford/) show a simple way to work with graphs with Python and DuckDB

### [Music Stats with DuckDB](https://arturdryomov.dev/posts/music-stats-with-duckdb/)

[Arthur Dryomov](https://www.linkedin.com/in/arturdryomov/) wrote about how to analyze music data with DuckDB

### [Using DuckDB to query beneficial ownership data in Parquet files](https://www.openownership.org/en/blog/using-duckdb-to-query-beneficial-ownership-data-in-parquet-files/)

In this post, [Stephen Abbott Pugh](https://www.linkedin.com/in/stephendabbott/) explains in great detail how DuckDB could be the perfect tool to work with the [Beneficial Ownership Data Standard](https://standard.openownership.org/en/0.2.0/) (BODS)

## Upcoming events

### DuckCon in San Francisco - 29th June

“DuckCon,” the DuckDB user group, will be held for the first time outside of Europe in [San Francisco Museum of Modern Art (SFMOMA)](https://www.sfmoma.org/), in the Phyllis Wattis Theater. In this edition, there will be talks from DuckDB creators [Hannes Mühleisen](https://hannes.muehleisen.org/) and [Mark Raasveldt](https://mytherin.github.io/) about the current state of DuckDB and future plans. It will also talks from data industry notables [Lloyd Tabb](https://twitter.com/lloydtabb) (of Looker and Malloy fame) and [Josh Wills](https://github.com/jwills) (creator of dbt-duckdb). The full agenda is available [here](https://duckdb.org/2023/04/28/duckcon3.html).

[Grab your ticket here](https://www.eventbrite.com/e/duckcon-san-francisco-tickets-618906505017?discount=duckconpreregisteredlatebird), as there is limited space!

### MotherDuck Party in San Francisco - 29th June

Following DuckCon, MotherDuck will host a party celebrating ducks at 111 Minna (located very close to SFMOMA). DuckCon attendees are cordially invited to attend to eat, drink, listen to music and play games (skeeball!). MotherDuck’s Chief Duck Herder will also demo the latest work bringing DuckDB to the cloud.

[Register now](https://www.eventbrite.com/e/motherducking-party-after-duckcon-and-dataai-summit-san-francisco-tickets-586172165727) before they run out of space!

### Data + AI Summit - 28th and 29th June

DuckDB co-creator Hannes will be giving a [keynote](https://register.dataaisummit.com/flow/db/dais2023/sessioncatalog23/page/sessioncatalog?search=%22Hannes%20M%C3%BChleisen%22) at this 10-track data conference hosted by Databricks. Additionally, Ryan Boyd (co-founder at MotherDuck) will be delivering a technical session: [If A Duck Quacks In The Forest And Everyone Hears, Should You Care?](https://register.dataaisummit.com/flow/db/dais2023/sessioncatalog23/page/sessioncatalog?search=Boyd)

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-seven/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-seven/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-seven/#top-duckdb-links-this-month)

[Upcoming events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-seven/#upcoming-events)

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

[![This Month in the DuckDB Ecosystem: May 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_ecosystem_monthly_may_2023_721d92a81f.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-six/)

[2023/05/24 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-six/)

### [This Month in the DuckDB Ecosystem: May 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-six)

Exciting month for DuckDB and the whole ecosystem: DuckdB 0.8.0 is released. The OSS project reached 10k stars on GitHub. Spatial extension. Native Swift API.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response