---
title: duckdb-ecosystem-newsletter-september-2024
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2024
indexed_at: '2025-11-25T19:58:38.249249'
content_hash: d95124a9b1a3fa33
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: September 2024

2024/09/03 - 5 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

## Hey, friend 👋

This is again your usual data cap dude, aka Mehdio. I hope you all are taking a break from the online world this summer to recharge plentifully. I was out also and had to catch up with a LOT of content that happened over these past weeks. A major announcement was pg\_duckdb, the official Postgres extension for DuckDB, but we also had a couple of pieces of content around geospatial (including one made by yours truly).

DuckDB 1.1 is right around the corner, so expect next month to be interesting too! By the way, DuckDB publishes their release calendar [here](https://duckdb.org/docs/dev/release_calendar.html) in case you didn't know.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fned_simon_.png&w=3840&q=75)

### Simon Aubury & Ned Letcher

[Simon Aubury](https://www.linkedin.com/in/simonaubury/) and [Ned Letcher](https://www.linkedin.com/in/nletcher/), authors of [Getting Started with DuckDB](https://www.packtpub.com/en-us/product/getting-started-with-duckdb-9781803241005?srsltid=AfmBOoq_7Sj84rKVR6eFq12_k4hkLxnG0bGbIXVQz3e9iPy-wz1LrSuL), bring a wealth of experience in data engineering and software development. Simon, with a background in creating robust data systems for various industries since 2000, and Ned, a data science and software engineering consultant since completing his PhD, combine their expertise to guide readers through enhancing data workflows with DuckDB. It's great to see more books about DuckDB, so if you are starting your journey with DuckDB, it's definitely worth a read!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [Practical Applications for DuckDB (with Simon Aubury & Ned Letcher)](https://youtu.be/_nA3uDx1rlg?si=uwByNUu3o_nCm5NW)

Thanks to [Kris Jenkins](https://www.linkedin.com/in/krisjenkins/) and his awesome YouTube channel Developer Voices, we had an insightful discussion with the book authors! They dive into how DuckDB simplifies data wrangling, enhances edge processing, and integrates smoothly with programming languages like R and Python, all through an engaging discussion.

### [Ibis Dropping Pandas Support - DuckDB is the Default](https://ibis-project.org/posts/farewell-pandas/)

Ibis is a portable Python dataframe that enables you to write your pipeline and use different engines like DuckDB, Polars, DataFusion, or PySpark. They used to support Pandas but are dropping support as of version 10.0. As they mentioned: "There is no feature gap between the \`pandas\` backend and our default DuckDB backend, and DuckDB is \_much\_ more performant."

### [PostgreSQL in Line for DuckDB-Shaped Boost in Analytics Arena](https://www.theregister.com/2024/08/20/postgresql_duckdb_extension/)

A big release this month was the official [open source Postgres extension](https://github.com/duckdb/pg_duckdb) for DuckDB where multiple companies will partner (including MotherDuck) together to provide the best analytical experience, directly in Postgres! While it's still in an experimental state, this is a big project that will get significant resources and attention, stay tuned! You can also read our [blog](https://motherduck.com/blog/pg_duckdb-postgresql-extension-for-duckdb-motherduck/) about this release.

### [Modern GIS with DuckDB](https://youtu.be/OuCY7_DzCTA?si=VhNw3_yhxR8tMJny)

Geospatial analysis always seemed like a niche in data that was hard to access. The reason for this is that the toolkit and knowledge were significantly different from what you commonly do. Thanks to DuckDB, that's not the case anymore. I tried to wrap up a getting started video about how to create your first heatmap using open EV charging spot data.

### [Letsql, a Multi-Engine Supporting DuckDB](https://www.letsql.com/posts/cache-operator/)

Letsql is another multi-engine framework, like Ibis but much younger. The blog linked above discusses their caching feature for upstream source data. This allows you to cache the results of a SQL query in a dataframe for rapid iteration. It's great to see multiple tools adopting the strategy to avoid cloud dependency while developing and significantly improve the overall developer experience.

### [DuckDB Tricks](https://duckdb.org/2024/08/19/duckdb-tricks-part-1.html)

Gabor from DuckDB Labs shows us some kung fu SQL, or rather, some underrated functions through this pragmatic blog. For instance, did you know that in the CLI the \`.schema\` command will show all of the SQL statements used to define the schema of the database?!

### [Ibis + DuckDB Geospatial: A Match Made on Earth](https://www.youtube.com/watch?v=xQnHhPMgWdM)

The annual SciPy Conference is a gathering where participants from various sectors showcase projects, learn from experts, and collaborate on Scientific Python development. In this talk, [Naty Clementi](https://www.linkedin.com/in/ncclementi/) from Voltron Data explains how you can leverage Ibis and DuckDB for geospatial work.

### [How to Bootstrap a Data Warehouse with DuckDB](https://www.youtube.com/watch?v=svKo_1wNWjo)

A couple of MotherDuckers were at SciPy for a SQL workshop and also to present! In this talk, [Guen](https://www.linkedin.com/in/gueneverep/) from our ecosystem team delivered a pragmatic talk to demonstrate how you can bootstrap a data warehouse with DuckDB and MotherDuck. No sales fluff, just a straightforward project for you to get started [here](https://github.com/guenp/cookiecutter-data-warehouse).

### [Why Do People Like DuckDB](https://www.reddit.com/r/dataengineering/comments/1eoaq8s/why_do_people_in_data_like_duckdb/)

The subreddit data engineering is a popular and insightful place to learn about others' experience with data tools (if you omit the troll comment here and there ;-). This thread shows how people are currently using DuckDB. A lot of comments compared their experience with SQLite, Pandas, and others.

### [How DuckDB Function Chaining Works](https://www.youtube.com/watch?v=CqH2MZ_tojY)

[Mark Needham](https://www.linkedin.com/in/markhneedham/) shows us in this video how to make your long SQL script more readable using DuckDB function chaining with the \`.\` operator. It's again something I haven't seen many people using but really useful to make your code cleaner!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [dbt Data Modeling Challenge](https://www.paradime.io/dbt-data-modeling-challenge)

**9 September - online**

Paradime, Hex, and MotherDuck have joined forces to bring data professionals worldwide a one-of-a-kind competition with some sweet prizes. Showcase your dbt, analytics, and SQL prowess on a global stage for a panel of esteemed judges!

### [Data Engineering for AI/ML](https://mlops.notion.site/Data-Engineering-for-AI-ML-Virtual-Conference-September-12th-4481e15caae84eefa2d96099d1b6bf77?pvs=4)

**12 September - online**

Organized by the MLOps community, Hannes (co-creator of DuckDB) and Mehdi (data engineer & developer relations at MotherDuck) will each have their own talk about data, and of course, ducks.

### [Small Data SF](https://www.smalldatasf.com/)

**24 September, San Francisco, CA, USA**

Small data and AI is more powerful than you think. Data and AI that was once "Big" can now be handled by a single machine. Join MotherDuck, Ollama, Turso, and Cloudfare in San Francisco.

**Location:** San Francisco, CA 🌁 - 8:00 AM America/Los\_Angeles

**Type:** In Person

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2024/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2024/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2024/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2024/#upcoming-events)

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

[![Swimming in Google Sheets with MotherDuck](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2024_09_03_at_10_13_04_PM_9b7eafd794.png&w=3840&q=75)](https://motherduck.com/blog/google-sheets-motherduck/)

[2024/09/04 - Jacob Matson](https://motherduck.com/blog/google-sheets-motherduck/)

### [Swimming in Google Sheets with MotherDuck](https://motherduck.com/blog/google-sheets-motherduck)

Learn how to use DuckDB's read\_csv functionality to easily load data from Google Sheets into MotherDuck for Analysis!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response