---
title: duckdb-ecosystem-newsletter-august-2024
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2024
indexed_at: '2025-11-25T19:58:21.079748'
content_hash: d5073a5bea09259a
has_code_examples: true
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: August 2024

2024/08/01 - 7 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

## Hey, friend 👋

It's Mehdi for this edition. And yes, if I'm not behind the camera, I'm behind the keyboard.
This month is full of pragmatic projects from the community and interesting blogs from both DuckDB themselves and MotherDuck. It's great to see the community starting to build more complex end-to-end solutions!
Note that the [StackOverflow Survey 2024](https://survey.stackoverflow.co/2024) is out and DuckDB usage has grown from 0.6% to 1.4%, ranking it at [#3 of the most desired databases to use](https://survey.stackoverflow.co/2024/technology#2-databases)!

MotherDuck, Cloudflare and Turso announced also announced [Small Data SF](https://www.smalldatasf.com/), an IRL gathering in San Francisco for data people and developers to learn together and celebrate the simple joys of local development and building with small data and AI. DuckDB Newsletter readers get **$100 off tickets with code ‘DuckDB100’.** With only 250 tickets total and speakers like Chris Laffra (PySheets) and Wes McKinney (Posit, Pandas), once they’re gone, they’re gone.

Finally, the book DuckDB in Action is officially out 🎉, you can get a free sample [here](https://motherduck.com/duckdb-book-brief/).

If you have feedback, news, or any insight, they are always welcome. 👉🏻 [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

## Featured Community Members

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_authors_256c689694.png&w=3840&q=75)

### Mark Needham, Michael Hunger, and Michael Simons

Can you guess what these three folks have in common? Well, I just spoiled the answer above—they all contributed to the DuckDB in Action book! [Mark Needham](https://www.linkedin.com/in/markhneedham/) is not only a skilled blogger and video creator at @LearnDataWithMark, but he's also an avid educator in the data community. [Michael Hunger](https://www.linkedin.com/in/jexpde/) has been pioneering product innovation at Neo4j, a leader in graph databases. Lastly, [Michael Simons](https://www.linkedin.com/in/michael-simons-196712139/), a Java Champion and Engineer at Neo4j, adds his profound expertise to the mix.

Together, they've contributed to the very first DuckDB book. This is a tremendous effort, especially considering that DuckDB 1.0 was just released—adapting and ensuring everything is current was no small feat. Congratulations to them!

Thank you, Mark, Michael, and Michael, for your significant contributions and for pushing the boundaries of data technology.

## Top DuckDB Links this Month

### [Food Transparency in the Palm of Your Hand: Explore the Largest Open Food Database using DuckDB](https://blog.openfoodfacts.org/en/news/food-transparency-in-the-palm-of-your-hand-explore-the-largest-open-food-database-using-duckdb-%f0%9f%a6%86x%f0%9f%8d%8a)

In this blog, [Jeremy](https://www.linkedin.com/in/jeremy-arancio/?locale=fr_FR) tackles a medium-sized dataset (10 - 43 GB) of compressed JSON with ease using DuckDB. He showcases how effectively DuckDB can parse JSON files. The blog provides clear, step-by-step code samples and introduces an interesting dataset about food!

### [Memory Management in DuckDB](https://duckdb.org/2024/07/09/memory-management.html\#streaming-execution)

Memory management might seem boring in the sense that if it works, it "just works." However, it is a critical component for a high-performance analytics engine. In this blog, [Mark](https://www.linkedin.com/in/mark-raasveldt-256b9a70/), co-creator of DuckDB, dives into three main behind-the-scenes features that make DuckDB great: streaming execution, intermediate spilling, and the buffer manager.
If you are curious about how DuckDB can process files larger than memory, or if you want to learn more about tuning and profiling memory usage, this is a must-read!

### [Build a Dashboard to Monitor Your Python Package Usage with DuckDB & MotherDuck](https://motherduck.com/blog/duckdb-dashboard-e2e-data-engineering-project-part-3/)

This is the last part of a series on an end-to-end data engineering project using DuckDB. I started this series a couple of months ago, and in this blog, we explore how to build a dashboard using [Evidence](https://evidence.dev/) and MotherDuck.

The project is live at [duckdbstats.com](https://duckdbstats.com/), and you can find the full source code on [GitHub](https://github.com/mehd-io/pypi-duck-flow). There's also a video tutorial you can watch [here](https://www.youtube.com/watch?v=ta_Pzc2EEEo).

### [A Hybrid Information Retriever with DuckDB](https://www.architecture-performance.fr/ap_blog/a-hybrid-information-retriever-with-duckdb/)

Search is a very hot topic around vector databases and AI, but DuckDB doesn't have to shy away from them, as several features enable it to offer search functionality with embeddings.
[Francois Pacull](https://www.linkedin.com/in/francois-pacull-50483445/) explores the implementation of search functions in Python with [DuckDB](https://duckdb.org/), open-source embedding models, and uses it on a [DBpedia](https://www.dbpedia.org/) text dataset. For those new to these concepts, he also provides a gentle introduction to hybrid search, lexical search, and fused score.

### [Crunchy Bridge Adds Iceberg to Postgres & Powerful Analytics Features](https://www.crunchydata.com/blog/crunchy-bridge-adds-iceberg-to-postgres-and-powerful-analytics-features?ref=dailydev)

Crunchy Data (one Postgres for Cloud) is extending Postgres features with DuckDB functionality. This makes sense as the [Postgres extension](https://duckdb.org/docs/extensions/postgres.html) is quite powerful for querying tables directly from Postgres, but what if you could directly use the power of DuckDB without leaving Postgres?

Note: They are not the only ones working on this; watch out for other Postgres Cloud providers 👀.

### [DuckDB Community Extensions](https://duckdb.org/2024/07/05/community-extensions.html)

We shared this during our last newsletter, but there was an official announcement from DuckDB regarding Community Extensions. There's now also a website to highlight [these](https://community-extensions.duckdb.org/list_of_extensions.html). If you want to add your extension there, head over to the [community extension repository](https://github.com/duckdb/community-extensions) and open a PR!

### [Querying Datasets with the Datasets Explorer Chrome Extension](https://huggingface.co/blog/cfahlgren1/querying-datasets-with-sql-in-the-browser)

DuckDB Wasm is great because it enables you to run DuckDB directly in a browser! This opens up interesting use cases for browser extensions, like creating a Firefox extension to display Parquet's metadata or, in this blog, exploring HuggingFace datasets.
[Caleb Fahlgren](https://www.linkedin.com/in/calebfahlgren/) walks us through various creative case studies using the [spatial extension of DuckDB](https://duckdb.org/docs/extensions/spatial.html) and some HuggingFace datasets. It's great to see how we can enhance our querying capabilities in our browser, directly on the client, with just an extension!

### [Data Stack in a Box — New South Wales Department of Education](https://davidgriffiths-data.medium.com/data-stack-in-a-box-new-south-wales-department-of-education-ft-e2bd12840d3e)

Data Stack in a Box is not a new concept. As the landscape of data tools becomes complicated, data professionals are looking for ways to consolidate things.
[David](https://www.linkedin.com/in/david-griffiths-5a9387a1/) walks us through another pragmatic end-to-end case study using DuckDB, and you can play with your own data stack in a box with just a click on [GitHub Codespace](https://github.com/wisemuffin/nsw-doe-data-stack-in-a-box).

### [Using DuckDB+dbt, FastAPI for Real-Time Analytics](https://www.nintoracaudio.dev/data-eng,duckdb,fastapi,dbt/2024/06/28/duckapi.html)

This is an interesting setup if you need to provide an external interface for common pipelines. The idea here is to put DuckDB + dbt in front of an API using FastAPI. I have already seen such a setup when providing "pipelines as a service" to software engineers where the only thing they would need to do is make an API call. Or, if you have a front-end with lightweight transformations that you want to run, everything can operate here within a Python process with DuckDB!

### [Delta Lake Meets DuckDB via Delta Kernel](https://www.youtube.com/watch?v=7E7PrBDvTOw)

During the DATA+AI Summit 2024 by Databricks, a major announcement was the support of Delta Lake in [DuckDB through an extension](https://duckdb.org/docs/extensions/delta). The talk is now online and dives into how this extension works. I also delved into that topic during a [livestream of Quack&Code with Holly](https://www.youtube.com/live/WzTRW_j-dpI?si=PIpVMWvrPLV6ybve) from Databricks, where we discussed table formats, how Delta works generally, and especially with DuckDB.

## Upcoming Events

### [Data Discoverability with Secoda and MotherDuck](https://motherduck.com/webinar/data-discoverability-secoda-motherduck/)

**31 July**

Join Secoda and MotherDuck for a masterclass in using dbt, MotherDuck, and Secoda to enable data producers and consumers, regardless of technical ability, to easily locate and access the data they need.

**Location:** Online 🌐 - 7:00 PM Central European Summer Time

**Type:** Online

### [MotherDuck/DuckDB Meetup: NYC Edition](https://www.eventbrite.com/e/motherduck-duckdb-meetup-nyc-edition-tickets-949275387237?aff=oddtdtcreator)

**7 August, New York, NY, USA**

We are pleased to announce our next in-person user group meetup in NYC to talk about MotherDuck, DuckDB, and all things data and analytics featuring talks from Nick Ursa, Matt Forrest, and Joseph Machado!

**Location:** New York, NY 🗽 - 5:00 PM America/New\_York

**Type:** In Person

### [DuckCon \#5 in Seattle](https://duckdb.org/2024/08/15/duckcon5.html)

**15 August, Seattle, WA, USA**

Join us for DuckCon #5, the DuckDB user group meeting, at the SIFF Cinema Egyptian.

**Location:** Seattle, WA, USA 🇺🇸 - 1:30 PM US/Pacific

**Type:** In Person

### [Small Data SF](https://www.smalldatasf.com/)

**24 September, San Francisco, CA, USA**

Small data and AI is more powerful than you think. Data and AI that was once "Big" can now be handled by a single machine. Join MotherDuck, Ollama, Turso, and Cloudfare in San Francisco.

**Location:** San Francisco, CA 🌁 - 8:00 AM America/Los\_Angeles

**Type:** In Person

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2024/#hey-friend)

[Featured Community Members](https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2024/#featured-community-members)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2024/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-august-2024/#upcoming-events)

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

[![Secoda x MotherDuck: The newest member of the Modern Duck Stack 🦆](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FSecoda_1_73cc39ad7a.png&w=3840&q=75)](https://motherduck.com/blog/secoda-motherduck-integration-modern-duck-stack/)

[2024/07/19 - Andrew McEwen](https://motherduck.com/blog/secoda-motherduck-integration-modern-duck-stack/)

### [Secoda x MotherDuck: The newest member of the Modern Duck Stack 🦆](https://motherduck.com/blog/secoda-motherduck-integration-modern-duck-stack)

The MotherDuck x Secoda integration allows you to enable data producers and consumers, regardless of technical ability, to easily locate and access the data they need! Learn how to enable the integration in two easy steps.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response