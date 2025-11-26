---
title: duckdb-ecosystem-newsletter-five
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-five
indexed_at: '2025-11-25T19:58:03.397219'
content_hash: 6cd25e38f4c15565
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: April 2023

2023/04/17 - 6 min read

BY

[Marcos Ortiz](https://motherduck.com/authors/marcos-ortiz/)

## Hey, friend 👋

It’s [Marcos](https://marcosortiz.carrd.co/) again, your “DuckDB News Reporter” with another issue of “This Month in the DuckDB Ecosystem" for April 2023. In this issue, we have a lot of great stuff to share with you, especially Jordan Tigani’s conversation with The Register, Mark Litwintschik’s play with the DuckDB Spatial extension, and much more. Every single day, we see more and more people using DuckDB in production environments with a very diverse set of use cases. So: It’s time to embrace the 🦆.

Remember: if you have any feedback for the newsletter, feel free to send us an email to [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com)

-Marcos

## Featured Community Member

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fjosh_wills_d6a197acdf.png%3Fupdated_at%3D2023-04-17T17%3A00%3A58.775Z&w=3840&q=75)

### Josh Wills

Josh Wills
If you have been in the Data Analytics space for a while, you know very well who Josh Wills is.
Perhaps you have read his famous quote
“Data Scientist (n.): Person who is better at statistics than any software engineer and better at software engineering than any statistician”.

Or perhaps you have read his co-authored book called [“Advanced Analytics with Spark”](https://www.amazon.com/Advanced-Analytics-PySpark-Patterns-Learning/dp/1098103653?crid=2CGSK7IGUGLS9&keywords=Apache%20Spark&qid=1681417883&sprefix=apache%20spark%20%2Caps%2C162&sr=8-49&linkCode=ll1&tag=marcos20-20&linkId=7a6c1f3aca89e7fdf6b3f2e26988c728&language=en_US&ref_=as_li_ss_tl&utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email).
Or even better: you have used the [dbt extension for DuckDB](https://github.com/jwills/dbt-duckdb?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email) created by him on production.
You can find him on Twitter as [@josh\_wills](https://twitter.com/josh_wills).

[Learn more about Josh here](https://github.com/jwills/?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email)

## Top DuckDB Links this Month

### [How We Silently Switched Mode’s In-Memory Data Engine to DuckDB To Boost Visual Data Exploration Speed](https://mode.com/blog/how-we-switched-in-memory-data-engine-to-duck-db-to-boost-visual-data-exploration-speed/)

This very interesting post from the Mode team explains why they selected DuckDB as its in-memory data engine for one of its core features: **speed**.

### [DuckDB's Spatial Extension](https://tech.marksblogg.com/duckdb-gis-spatial-extension.html)

In this post, Mark Litwintschik walks through some example GIS workflows with the [DuckDB Spatial extension](https://github.com/duckdblabs/duckdb_spatial). Highly recommended reading!!!

### [How fast does a compressed file in Part 2](https://www.spsanderson.com/steveondata/posts/rtip-2023-03-28/index.html)

[Steven P. Sanderson II](https://www.linkedin.com/in/spsanderson/), MPH came with a second part of his series about compressed files.
This time using the combination of DuckDB and Apache Arrow

### [DuckDB makes SQL a first-class citizen on DataCamp Workspace](https://www.datacamp.com/blog/duckdb-makes-sql-first-class-citizen-datalab)

In this blog post, [Filip Schouwenaars](https://www.linkedin.com/in/filip-schouwenaars-b576b74a/) lists out all recent improvements that make it seamless and efficient to query data with SQL, all without leaving the tool; thanks to DuckDB.

### [Use dbt and DuckDB instead of Spark in data pipelines](https://medium.com/datamindedbe/use-dbt-and-duckdb-instead-of-spark-in-data-pipelines-9063a31ea2b5)

[Niels Claeys](https://www.linkedin.com/in/nielsclaeys/?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email) made a bold proposal here: ditch Spark for the combination of dbt and DuckDB. We are at a perfect time to explore this approach

### [DuckDB Document Loader by Trent Hauck](https://twitter.com/langchainai/status/1640745201311580160?s=46&t=Ky_VahIlwkAqVrZ_H93UpQ&utm_medium=email&_hsmi=254512019&_hsenc=p2ANqtz-9CrdhYdU-LyrbvZo2L-9Uda1_5Vc9oHmjypybZGQUErkr9F2jxPl8OJc7IipUEYJdxL5YJAhl9i_iAqRCiPtKj8Ry-vQ&utm_content=254512019&utm_source=hs_email)

In this tweet, the LangChain team showed the awesome work of Trent Hauck about how to use the DuckDB Document Loader with an example. If you want to play with it, you can find the docs [here](https://python.langchain.com/v0.2/docs/integrations/document_loaders/duckdb/).

### [Ex-BigQuery exec and Motherduck CEO: For some users, the answer is to think small](https://www.theregister.com/2023/03/21/motherduck_ceo_jordan_tigani_interview/?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email)

A very insightful interview with [Jordan Tigani](https://motherduck.com/authors/jordan-tigani/), CEO of MotherDuck where he shared things like

“DuckDB has been able to kind of strip all that away by being an in-process database, and that means that you basically can marshal data in and out of your application, or your data frames, with the minimum of data movements”.

It’s time to **think small first**.

### [Using DuckDB with Your Dremio Data Lakehouse](https://www.dremio.com/blog/using-duckdb-with-your-dremio-data-lakehouse/?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email)

In this article, [Alex Merced](https://www.linkedin.com/in/alexmerced/?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email) from Dremio discusses how you can use technologies like Dremio and DuckDB to create a low-cost, high-performance data lakehouse environment accessible to all your users.

### [Fixing iMessage search with DuckDB](https://medium.com/@danthelion/fixing-imessage-search-with-duckdb-6f8a5314c980)

Perhaps Apple: you should listen to Daniel Palma on this. DuckDB could be perfect for this use case here. Fixing iMessages on iOS is one of the most requested features out there, and with DuckDB they could actually fix this easily.

The message is given, Tim.

## Upcoming events

### [Webinar: Doing Analysis in a Post Big Data Era: How industry leaders are driving high-impact decisions with smaller data](https://events.mode.com/webinar/post-big-data-era)

**April 19, 2023, 10:00 AM PDT**

Join us for a conversational webinar between [Jordan Tigani](https://motherduck.com/authors/jordan-tigani/), Founder and CEO at MotherDuck, and [Benn Stancil](https://www.linkedin.com/in/benn-stancil/?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email), co-founder and CTO at Mode, two industry leaders who’ve called at the end of big data (Benn’s take; Jordan’s take).

In this discussion, they'll talk about how the hyped “We have tons of data, and we’re going to change the world with it” narrative of the 2010s looks from today’s vantage point — and how leading companies are navigating a higher impact, faster moving data-informed decision-making process using smaller data.

### [Webinar: Big Data: Funeral or Renaissance?](https://streamyard.com/watch/dNfM8QgchjE5?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email)

**April 20, 2023, 12:00 PM**

Jordan Tigani, CEO + Founder of MotherDuck and one of the founding engineers on Google BigQuery, recently wrote a blog post called " [Big Data is Dead](https://motherduck.com/blog/big-data-is-dead)" which took the internet by storm.

[Aditya Parameswaran](https://www.linkedin.com/in/aditya-parameswaran-0714b63/?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email), Co-Founder of [Ponder](https://ponder.io/?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email) and Associate Professor at UC Berkeley, wrote a rebuttal called "Big Data Is Dead… Long Live Big Data."

This interactive broadcast will be a fun and lively debate answering the question of whether we should host a funeral for big data or if big data is having a renaissance.

The debate will be moderated by [Aaron Elmore](https://www.linkedin.com/in/aaron-elmore-6882a52/?utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email), Associate Professor at the University of Chicago.

### [Data + AI Summit Keynote Day 2](https://register.dataaisummit.com/flow/db/dais2023/sessioncatalog23/page/sessioncatalog?search=%22Hannes%20M%C3%BChleisen%22&utm_medium=email&_hsmi=254512019&utm_content=254512019&utm_source=hs_email)

**June 29, 2023, San Francisco**

**Data, analytics and AI landscape**
Discover what’s driving so much focus on data and why data professionals are zeroing in on new ways to tackle their database challenges. Learn why there is so much interest in LLMs, what is happening across the data, analytics and AI landscape and the future of the market

**Evolution of the lakehouse**
Take a look at the larger universe that the lakehouse lives inside of, learn what’s new and explore the evolution with us

**Open source technologies**
Hear from the open source community about what’s new and what’s to come for Apache Spark™, Delta Lake and MLflow and learn how this affects the lakehouse and the overall market at large

**Presenters:**

- Hannes Mühleisen, Co-Founder & CEO, DuckDB Labs
- Lin Qiao, Co-creator of PyTorch, Co-founder and CEO, Fireworks
- Nat Friedman, Creator of Copilot; Former CEO, Github
- Jitendra Malik, Computer Vision Pioneer, Former Head of Facebook AI Research, University of California at Berkeley

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

[![Why does everybody hate databases? Interview with DuckDB Co-creator Hannes Mühleisen](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumbnail_int_d89ac74fd8.png&w=3840&q=75)](https://motherduck.com/blog/why-everybody-hates-databases/)

[2023/03/16 - Mehdi Ouazza](https://motherduck.com/blog/why-everybody-hates-databases/)

### [Why does everybody hate databases? Interview with DuckDB Co-creator Hannes Mühleisen](https://motherduck.com/blog/why-everybody-hates-databases)

Interview with co-creator of DuckDB Hannes

[![This Month in the DuckDB Ecosystem: March 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_ecosystem_monthly_feb_2023_352e669717.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-four/)

[2023/03/23 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-four/)

### [This Month in the DuckDB Ecosystem: March 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-four)

This month in the DuckDB Ecosystem, by Marcos Ortiz. Includes featured community member Elliana May, Python ecosystem, top links, upcoming events and more.

[View all](https://motherduck.com/blog/)

Authorization Response