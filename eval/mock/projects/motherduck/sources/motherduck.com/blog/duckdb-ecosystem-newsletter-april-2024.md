---
title: duckdb-ecosystem-newsletter-april-2024
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2024
indexed_at: '2025-11-25T19:58:23.027751'
content_hash: a85a9338392531a3
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: April 2024

2024/04/30 - 6 min read

BY

[Luciano Galvão Filho](https://motherduck.com/authors/luciano-galv%C3%A3o-filho/)

## Hey, friend 👋

Hello, I'm Luciano, and I bring you your monthly dose of what's up in DuckDB. This month, we've put together a series of articles and videos to update you on the ecosystem.

Your insights and news are always welcome. Feel free to share by emailing [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com)

Enjoy,
Luciano

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FQiusheng_Wu_2645c50106.jpeg&w=3840&q=75)

### Qiusheng Wu

[Dr. Qiusheng Wu](https://twitter.com/giswqs) is the creator of advanced open-source geospatial tools like geemap, leafmap, and segment-geospatial, with thousands of users. His work is inspiring and serves as the foundation for numerous studies. He is an Associate Professor in the Department of Geography & Sustainability at the University of Tennessee, Knoxville, and also serves as an Amazon Visiting Academic and a Senior Research Fellow at the United Nations University. Dr. Wu specializes in geospatial data science and open-source software development, with a particular focus on utilizing big geospatial data and cloud computing to study environmental changes, especially surface water and wetland inundation dynamics.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [DuckDB behind the magic : Parsing the Unparseable CSVs](https://www.youtube.com/watch?v=xXapEmO-Iog)

DuckDB is fast, there's no doubt about it, right? But a lot of work is being done to make our solution even more robust and reliable in data reading and ingestion. Who hasn't had to deal with a CSV file with corrupted or incorrectly formatted lines? A series of improvements have been implemented on how DuckDB detects and manages formatting errors in our datasets. [Pedro Holanda](https://www.linkedin.com/in/pdet/) and [Mehdi Quazza](https://www.linkedin.com/in/mehd-io/) bring the latest in a relaxed and practical conversation.

### [CMU 15-721 - DuckDB: Advanced Database Systems](https://www.youtube.com/watch?v=4iD4h4sGLz4)

[Andy Pavlo](https://www.linkedin.com/in/andy-pavlo/) provided a comprehensive overview of DuckDB and a detailed discussion on the internal workings of DuckDB, such as its execution model, vectorized query processing, and handling of data storage and retrieval. This includes how DuckDB processes queries and utilizes hardware efficiently, ensuring fast response times for analytical queries.

### [duckplyr: dplyr powered by DuckDB](https://duckdb.org/2024/04/02/duckplyr)

If you work with R, you need to try the 'duckplyr' package. It integrates the efficiency of DuckDB with the familiar functionalities of dplyr. 'Duckplyr' enables data analysts to perform complex transformations directly on their data frames, significantly improving performance without leaving the familiar dplyr environment. This represents a considerable advantage for daily R users, as it combines ease of use with powerful data processing capabilities.

### [Managing raster (Satellite Imagery) in DuckDB with the spatial extension](https://www.linkedin.com/pulse/managing-raster-satellite-imagery-duckdb-spatial-extension-huarte-mudif/?trackingId=9XgrwvflQDy3m5txR4iXTA%3D%3D)

The possibilities with DuckDB are vast and continue to expand. [Alvaro Huarte](https://www.linkedin.com/in/alvarohuarte/) delves into the integration of geospatial images with DuckDB's spatial extension in detail. As spatial analysis has become essential in various fields, from geographic information systems (GIS) to urban planning and beyond, this integration offers new possibilities for such analyses and has been gaining significant momentum in our community.

### [How Fast can Python Parse 1 Billion Rows of Data?](https://www.youtube.com/watch?v=utTaPW32gKY)

No spoilers please. But can you guess which Python implementation performed the best? The 1 billion line challenge provides an opportunity to investigate how efficiently we can process a large text file and obtain some general statistics. This video explores the most effective strategies for processing lines using both pure Python and external libraries. Are you surprised by the result?

### [Using DuckDB JupySQL and Pandas in a notebook](https://medium.com/@deepa.account/using-duckdb-jubysql-and-pandas-in-a-notebook-af4ed943d655)

Fly high with the full potential of your Jupyter Notebooks using DuckDB! In this article, Deepa Vasanthkumar demonstrates how integrating these powerful tools enhances your data analysis experience with fast querying and robust data manipulation. Ideal for efficiently handling large datasets, this combination ensures you never compromise on performance or flexibility. Learn the simple steps to take flight and elevate your data skills.

### [PyIceberg as a solution to Multi-engine data stack](https://juhache.substack.com/p/multi-engine-data-stack-v1)

PyIceberg could be the solution you've been looking for to integrate DuckDB with Snowflake. In this article, Julien Hurault presents a step-by-step guide to building a 'multi-engine data stack' that combines Snowflake, DuckDB, and Iceberg, offering efficiency, scalability, and integration between these two platforms. While Iceberg is still in its early stages, enabling interoperability among different engines opens up so many possibilities.

### [A portable Data Analytics stack using Docker, Mage, dbt-core, DuckDB and Superset](https://medium.com/data-engineers-notes/a-portable-data-analytics-stack-using-docker-mage-dbt-core-duckdb-and-superset-70f10f92dfb9)

Who else loves testing out new technologies and exploring them through tutorials and end-to-end projects? If you're like me, check out this project exploring the creation of a complete data stack. It leverages technologies like Mage, DuckDB, dbt core, and Superset to provide a comprehensive solution. It's a fantastic starting point for demos, templates, or learning how all these components work together. Have fun!

### [Orchestrating data quality with Soda, Motherduck and Prefect](https://dataroots.io/blog/orchestrating-data-quality)

This month, our page is full of end-to-end projects, with a highlight now on building a data quality pipeline. If the topic of data quality keeps you up at night, check out this solution that integrates Prefect, Soda, MotherDuck, and YData Profiling. With YData Profiling providing exploratory analysis and Soda performing accurate checks, you can get back to having a peaceful night's sleep.

### [File-based Postgres Analytics with DuckDB and AWS S3](https://www.youtube.com/watch?v=diL00ZZ-q50)

If you're looking for a practical introduction to using Supabase storage, this video is for you! With clear, step-by-step demonstrations, you'll learn how to connect DuckDB to your PostgreSQL database in Supabase, export data to storage buckets, and perform analyses directly on the files.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

We aim to centralize all Duck-related events at [motherduck.com/events](https://motherduck.com/events/), but here are some highlights:

### [MotherDuck / DuckDB User Meetup \[Seattle May 2024 Edition\]](https://www.eventbrite.com/e/motherduck-duckdb-user-meetup-seattle-may-2024-edition-tickets-879702021427?aff=oddtdtcreator)

**20 May, Seattle, WA, USA**

Join us for an exciting in-person MotherDuck / DuckDB meetup 🐥 at the MotherDuck office in Seattle on May 20, 2024, from 6:00 PM to 9:00 PM! We'll have engaging talks, networking opportunities with industry experts, and SWAG for attendees.

### [Data @Scale Conference: Taking Flight with Interactive Analytics](https://atscaleconference.com/events/data-scale-2024/)

**22 May, Online**

Join Frances Perry, Engineer Manager at MotherDuck, for a talk and walkthrough of interactive visualizations done in-browser using Mosaic and WebAssembly (WASM), powered by DuckDB and extended to the cloud with MotherDuck’s serverless analytics platform.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2024/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2024/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2024/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2024/#upcoming-events)

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

[![Structured memory management for AI Applications and AI Agents with DuckDB](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FCognee_Blog_Post_1f4e213cf3.png&w=3840&q=75)](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions/)

[2024/04/29 - Vasilije Markovic](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions/)

### [Structured memory management for AI Applications and AI Agents with DuckDB](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions)

Learn how to optimize Retrieval-Augmented Generation (RAG) systems with DuckDB, dlt, and Cognee to streamline data management and workflows for accurate LLM outputs.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response