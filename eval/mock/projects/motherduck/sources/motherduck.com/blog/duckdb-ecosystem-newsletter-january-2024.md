---
title: duckdb-ecosystem-newsletter-january-2024
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2024
indexed_at: '2025-11-25T19:58:34.253918'
content_hash: 0d67fb91fc1de667
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: January 2024

2024/01/30 - 5 min read

BY

[Ryan Boyd](https://motherduck.com/authors/ryan-boyd/)

## Hey, friend 👋

The last issue was the end of an era - [Marcos](https://www.linkedin.com/in/mlortiz) has retired from writing the DuckDB Ecosystem Monthly newsletter. We're all enormously grateful for his contributions over the last year+.

This is [Ryan](https://www.linkedin.com/in/ryguyrg/) from MotherDuck. Don't worry, we'll keep this newsletter going monthly with help from the community!

I want to highlight a fantastic trend I've seen, having recently returned from [Data Day Texas](https://datadaytexas.com/) \- a vibrant community built and supported by [Lynn Bender](https://www.linkedin.com/in/lynnbender/) and [Alex Law](https://www.linkedin.com/in/alexandria-law/). The data community is full of amazing humans who not only care about how vectorized columnar execution works in practice, but also care sincerely about how they're impacting their fellow humans and the business. This is in contrast to some other tech communities and was best demonstrated by the accolades heard throughout the halls for a talk by [Sol Rashidi](https://www.linkedin.com/in/sol-rashidi-a672291/) on lessons learned as she moved from being a practitioner to an executive.

Let's keep building this amazing community and technologies, while supporting each other and the needs of the business.

As always, this is a two-way conversation: if you have any feedback on this newsletter, feel free to send us an email to [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com)

Cheers!

-Ryan

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fmihai_marcelo.jpg&w=3840&q=75)

### Mihai Bojin & Marcelo Cenerino

[Mihai](https://www.linkedin.com/in/mihai-bojin/) and [Marcelo](https://www.linkedin.com/in/marcelocenerino/) , both with over 15 years in tech, have made their mark in the industry. Mihai, with a background as a technical leader at big names like Salesforce, MongoDB, and now Google. Marcelo's career is equally luminous, having contributed his expertise to giants such as Ericsson and Workday, and now excelling as a Staff Software Engineer at Google. Interestingly, they're both located in Dublin. But there's more that brings them together. They successfully hosted Dublin's first DuckDB meetup! Keep an eye on [their event page for upcoming meetups](https://www.meetup.com/duckdb-dublin-meetup/)!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [SQL for Google Sheets with DuckDB](https://www.arecadata.com/sql-for-google-sheets-with-duckdb/)

DuckDB is winning largely because of developer experience. This tiny article from [Daniel Palma](https://www.linkedin.com/in/danthelion/) shares how to access a Google Sheet from DuckDB in one line of code.

### [Monte Carlo simulations talk](https://www.youtube.com/watch?v=oh0Y3MN2Tas)

Monte Carlo simulations do repeated random sampling to determine the probability of a complex result. James McNeil recently gave a talk to the [Dublin DuckDB Meetup](https://www.meetup.com/duckdb-dublin-meetup/) on doing these simulations with DuckDB.

### [Multi-Database support in DuckDB](https://duckdb.org/2024/01/26/multi-database-support-in-duckdb)

Want to join DuckDB tables with tables in Postgres, SQLite, and MySQL? You can! And you can even copy data between databases easily in single SQL statements. Learn more from [Mark Raasveldt](https://www.linkedin.com/in/mark-raasveldt-256b9a70/?originalSubdomain=nl) on the DuckDB blog.

### [ERPL DuckDB Extension for SAP data](https://medium.com/@simon.peter.mueller/sap-data-in-your-python-analytics-workflows-bd52bb4ded74)

DuckDB has definitely reached the enterprise!  [Simon Müller](https://www.linkedin.com/in/simon-m%C3%BCller/) has released a [DuckDB extension](https://erpl.io/) for using SAP Data in your workloads.

### [Excel support for Parquet files (via DuckDB)](https://erpl.io/blog/connect-excel-to-parquet/)

From the [same author](https://www.linkedin.com/in/simon-m%C3%BCller/) as the SAP extension, we have a post on how to use Parquet data in the world’s most ubiquitous “database” using DuckDB.

### [Streamlit, IBIS, DuckDB and more](https://ibis-project.org/posts/ibis-analytics/)

Want to power a dashboard deployed as an app on Streamlit? [Cody Peterson](https://www.linkedin.com/in/codydkdc/) of Voltron Data shows us how in this great step-by-step tutorial.

### [Dplyr and DucKDB](https://medium.com/@bwolatunji/speed-up-your-sql-mastery-with-dplyr-and-dbplyr-packages-in-r-998decafced1)

[Dplyr](https://dplyr.tidyverse.org/) provides a grammar for data transformation that’s higher level than SQL and consistent across data sources.  Data Scientist [Bilikisu Olatunji](https://www.linkedin.com/in/bilikisuolatunji/) dives into how to use Dplyr with DuckDB in R.

### [Quack & Code on WASM DuckDB](https://www.youtube.com/watch?v=81qCRIvKI6A)

One of the most exciting reasons to use DuckDB is that it runs **_anywhere_**, including inside the modern web browser using web assembly (WASM). Previous featured community member [Christophe Blefari](https://www.linkedin.com/in/christopheblefari/) quacks and codes WASM with MotherDuck’s [Mehdi Ouazza](https://www.linkedin.com/in/mehd-io/) in this episode.

### [Small Data, Big Impact talk on MLOps Community](https://home.mlops.community/public/videos/small-data-big-impact-the-story-behind-duckdb)

Do you like to drink stale coffee? [Demetrios Brinkmann](https://www.linkedin.com/in/dpbrinkm/?originalSubdomain=de) brings on [Hannes Mühleisen](https://www.linkedin.com/in/hfmuehleisen/) and [Jordan Tigani](https://www.linkedin.com/in/jordantigani/) to talk about this question, building an empathetic developer experience, open source business models and more.

### [CIDR paper on Hybrid Query Processing](https://motherduck.com/blog/cidr-paper-hybrid-query-processing-motherduck/)

One of the most popular pages on the MotherDuck website focuses on the hybrid system architecture. [Peter Boncz](https://www.linkedin.com/in/peterboncz/), Visiting Researcher at MotherDuck and database luminary, corralled the MotherDuck team to dive into the details in this peer-reviewed article recently presented at the CIDR conference.

### [DuckDB: the Rising Star in the Big Data landscape](https://mihaibojin.medium.com/duckdb-the-big-data-rising-star-71916f953f18)

[Mihai](https://www.linkedin.com/in/mihai-bojin/) discussed why DuckDB has been popular recently and why, you should care about it in case you haven’t already ;-)

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [SQL IDE Safari: Harlequin in your terminal](https://www.linkedin.com/events/sqlidesafari-harlequin-inyourte7156240121262993408/comments/)

**31 January 2024 \| Online 🌐**

This latest episode of Quack and Code stars Ted Conbeer who built an amazing SQL IDE that runs in your terminal.

### [DuckCon \#4 by DuckDB Labs and Foundation](https://duckdb.org/2023/10/06/duckcon4.html)

**2 February 2024 \| Amsterdam, Netherlands 🇳🇱**

The event will begin with a talk by DuckDB's creators, Hannes Mühleisen and Mark Raasveldt, discussing DuckDB's current state and the upcoming release of version 1.0, followed by presentations from two DuckDB users. Additionally, there will be a series of lightning talks from the DuckDB community.

### [Chill Data Summmit](https://events.ringcentral.com/events/chill-data-summit?utm_source=Speakers&utm_campaign=Speakers)

**06 February 2024 \| Online 🌐**

Ryan Boyd of MotherDuck will give a talk on "Data infrastructure through the lens of scale, performance and usability," and will demo how Iceberg works in DuckDB for accessing data in your lakehouse.

### [DataTune conference](https://www.datatuneconf.com/)

**9 March 2024 \| Nashville, USA 🇺🇸**

David Neal will speak about “Hybrid Queries: the Future of Data Analytics”

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2024/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2024/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2024/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2024/#upcoming-events)

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