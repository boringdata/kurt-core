---
title: duckdb-ecosystem-newsletter-february-2024
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2024
indexed_at: '2025-11-25T19:58:33.813145'
content_hash: 4677d0a1e6187feb
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: February 2024

2024/03/01 - 5 min read

BY

[Ryan Boyd](https://motherduck.com/authors/ryan-boyd/)

## Hey, friend 👋

This is [Ryan](https://www.linkedin.com/in/ryguyrg/) from MotherDuck, and I'm excited to present the 15th DuckDB ecosystem newsletter.

I'm even more excited that the DuckDB team just released 0.10.0, which introduces backwards compatibility in the DuckDB storage format and makes many improvements around performance, memory utilization and more.

This issue goes into a bit more depth for each link we share. Let us know what you think or share your news by sending an email to [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com)

Cheers!

-Ryan

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fchristophe_oudar.jpeg&w=3840&q=75)

### Christophe Oudar

Based in France, [Christophe](https://www.linkedin.com/in/christopheoudar/) is a Staff Software Engineer who works on cross-team initiatives scaling data systems. He has written about [using DuckDB for data integration](https://motherduck.com/blog/duckdb-the-great-federator/) and also submitted a [small fix](https://github.com/duckdb/duckdb_mysql/commit/2e9d34f166d860380c584cc0d6b86edcf9c4bd44) to the DuckDB MySQL integration. He has an [upcoming talk](https://www.eventbrite.com/e/data-meetup-duckdb-traiter-les-donnees-a-vitesse-lumiere-motherduck-tickets-825278669717) at the Paris DuckDB and MotherDuck meetup.  He maintains an active Medium blog sharing knowledge around BigQuery, dbt and DuckDB, including a recent post on " [How DuckDB can be up to 1000x more efficient than BigQuery?](https://medium.com/@kayrnt/how-duckdb-can-be-up-to-1000x-more-efficient-than-bigquery-36bab2405259)"

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [DuckDB 0.10.0: Backwards compatible, CSV loader perf, multi-database support, better memory management ++](https://duckdb.org/2024/02/13/announcing-duckdb-0100.html)

The DuckDB team announced Fusca, the latest release of DuckDB.  It is named after the [Velvet scooter](https://en.wikipedia.org/wiki/Velvet_scoter) native to Europe.

This version of DuckDB is [backwards compatible](https://duckdb.org/2024/02/13/announcing-duckdb-0100.html#backward-compatibility) in the storage format, [improved memory utilization](https://duckdb.org/2024/02/13/announcing-duckdb-0100.html#temporary-memory-manager), [dramatically improved the CSV loader performance](https://duckdb.org/2024/02/13/announcing-duckdb-0100.html#csv-reader-rework) and introduced improvements throughout the engine.

There are dozens of additional improvements, so would highly encourage you to [read the blog post](https://duckdb.org/2024/02/13/announcing-duckdb-0100.html#temporary-memory-manager).

### ["DuckDB in Action" book by Manning adds 4 new chapters](https://www.manning.com/books/duckdb-in-action/)

The top-rated ["DuckDB in Action" book](https://www.manning.com/books/duckdb-in-action/) published by Manning has added four new chapters to the MEAP (early access) book.

Chapter 5: Exploring data without persistence

Chapter 6: Integrating with the Python ecosystem

Chapter 7: DuckDB in the Cloud with MotherDuck

Chapter 8: Building data pipelines with DuckDB

You can [download the book for free](https://motherduck.com/duckdb-book-brief/?utm_campaign=ecosystemnews), courtesy of MotherDuck.

### [DuckCon \#4 talk videos released](https://www.youtube.com/watch?v=cyZfpXxXojE&list=PLzIMXBizEZjhZcTiEFZIAxPpB6RE9TmgC)

The DuckDB team released [videos from the talks](https://www.youtube.com/watch?v=cyZfpXxXojE&list=PLzIMXBizEZjhZcTiEFZIAxPpB6RE9TmgC), with editing courtesy of [Mehdi Ouazza](https://www.linkedin.com/in/mehd-io?originalSubdomain=de).

\\* [State of the Duck](https://www.youtube.com/watch?v=cyZfpXxXojE&list=PLzIMXBizEZjhZcTiEFZIAxPpB6RE9TmgC&index=1) \[Hannes, Mark\]

\\* [Hugging a Duck](https://www.youtube.com/watch?v=tnlq0qGo59s&list=PLzIMXBizEZjhZcTiEFZIAxPpB6RE9TmgC&index=2) \[Polina Kazakova, Hugging Face\]

\\* [Building Data Lakes with DuckDB](https://www.youtube.com/watch?v=I1JPB36FBOo&list=PLzIMXBizEZjhZcTiEFZIAxPpB6RE9TmgC&index=3) \[Subash Roul, Fivetran\]

\\* [Duck Feather in your Parquet Cap](https://www.youtube.com/watch?v=Lq8GRFjbRCM&list=PLzIMXBizEZjhZcTiEFZIAxPpB6RE9TmgC&index=4) \[Niger Little-Pool, Prequel\]

### [PyAirbyte: pipelines-as-code powered by DuckDB](https://airbyte.com/blog/announcing-pyairbyte)

The Airbyte team released a public beta of PyAirbyte, or the packaging of Airbyte connectors to make them accessible in code to "bridge the gap between the flexibility of custom Python scripts and the power of a data integration platform."  By default, PyAirbyte uses a DuckDB cache (destination), though MotherDuck, Postgres, Snowflake and BigQuery are also available.

### [DuckDB-NSQL-7B LLM for DuckDB SQL released](https://www.numbersstation.ai/post/duckdb-nsql-how-to-quack-in-sql)

Collaborating with MotherDuck, the Numbers Station team announced a LLM specifically tuned for text-to-SQL in the DuckDB dialect, with the ability to execute locally on a M1 laptop. Model weights were open sourced on Hugging Face and the model is available in GGUF format for llama.cpp.

### [Using DuckDB + Ibis for RAG](https://ibis-project.org/posts/duckdb-for-rag/)

RAG, or retrieval-augmented generation, augments a LLM with additional knowledge before it generates its response. Is the knowledge you want to use to augment your LLM stored in DuckDB or MotherDuck? This article shows you how to build your RAG.

### [Why is DuckDB the default backend for Ibis?](https://ibis-project.org/posts/why-duckdb/)

It's becoming increasingly common to have DuckDB as the default analytics database used in data engineering tools. Earlier in the newsletter, we talked about how it's the default backend for PyAirbyte.  In this article, the Ibis folks talks about how DuckDB became their default to provide a great out-of-the-box experience.

They cite their reasons for choosing DuckDB as:

1. Great performance for local data
2. A thriving open source community
3. A solid foundation
4. A large and well-supported feature set

### [Using DuckDB-WASM for in-browser Data Engineering](https://tobilg.com/using-duckdb-wasm-for-in-browser-data-engineering)

Tobias gives an overview of how he built [sql-workbench.com](https://sql-workbench.com/) by leveraging DuckDB running in the browser via WASM (web assembly). He also uses Perspective.js for interactive data visualizations. There's quite a bit of functionality for a static website!

### [Plot(ly)ing Geo Data From DuckDB](https://medium.com/@petrica.leuca/4d3f039ed87f?sk=311f4f55bd0d8d9d3215e776f7d2770a)

Petrica demonstrates using the spatial extension in DuckDB to plot visualizations of restaurants in the Netherlands. She uses the choropleth map functionality to avoid having to acquire a Mapbox API key, which is also supported by Plotly.

### [DuckDB + dbt: Josh Wills Quacking and Coding](https://www.youtube.com/watch?v=Baoay4k2b34)

Mehdi had a very special guest on his Quack & Code livestream- Josh Wills, author of [dbt-duckdb](https://github.com/duckdb/dbt-duckdb).  They discussed how dbt and DuckDB can be used together to accelerate the developer experience by using local resources. They then dived into some code together!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [DuckDB Meetup Paris](https://www.eventbrite.com/e/data-meetup-duckdb-traiter-les-donnees-a-vitesse-lumiere-motherduck-tickets-825278669717?utm_source=hs_email&utm_medium=email&_hsenc=p2ANqtz-8pc8Vqw1puGNDZBttMTaJVK6lzUDg6_mAyRvOHcrr-rsNkx5fEzcR6EiF5ilCNWJqRAWnY)

**13 March, Paris 🇫🇷**

MotherDuck, en collaboration avec Back Market, est heureuse d'annoncer notre 4eme rencontre en personne des groupes d'utilisateurs DuckDB en France, à Paris pour parler de DuckDB, MotherDuck et de tout ce qui concerne les données!

### [PyCon US 2024](https://us.pycon.org/2024/?utm_source=hs_email&utm_medium=email&_hsenc=p2ANqtz-8pc8Vqw1puGNDZBttMTaJVK6lzUDg6_mAyRvOHcrr-rsNkx5fEzcR6EiF5ilCNWJqRAWnY)

**17 May, Pittsburgh, PA, USA 🇺🇸**

Alex Monahan of DuckDB Labs and MotherDuck will present a talk on "Python and SQL: Better Together, Powered by  @DuckDB." Exact date/time TBD

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2024/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2024/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2024/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2024/#upcoming-events)

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

[![Introducing the Column Explorer: a bird’s-eye view of your data](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fcolumn_explorer_f4ac0bae95.png&w=3840&q=75)](https://motherduck.com/blog/introducing-column-explorer/)

[2024/02/14 - Hamilton Ulmer](https://motherduck.com/blog/introducing-column-explorer/)

### [Introducing the Column Explorer: a bird’s-eye view of your data](https://motherduck.com/blog/introducing-column-explorer)

Column explorer : fewer queries, more insights

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response