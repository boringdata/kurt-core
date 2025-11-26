---
title: why-everybody-hates-databases
content_type: blog
source_url: https://motherduck.com/blog/why-everybody-hates-databases
indexed_at: '2025-11-25T19:57:25.288969'
content_hash: a0100095dea4e4e3
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Why does everybody hate databases? Interview with DuckDB Co-creator Hannes Mühleisen

2023/03/16 - 2 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

## How it started

During the 2nd edition of the DuckCon in Brussels, I had the pleasure of interviewing DuckDB co-creator Hannes Mühleisen. Hannes is a researcher at the Dutch research institute for computer science and mathematics, CWI. He has been working in a group called Database Architectures for ten years, where they research how data systems should be built.

In his work, he discovered that some data practitioners, particularly in the R community, were not using databases at all. Instead, they used hand-rolled dataframe engines and dataframes in memory. However, these dataframes were slow and limited because of how the engines were structured.

That was the first bit that inspired DuckDB to be created.

The Surprising Birth Of DuckDB ft. Co-creator Hannes Mühleisen - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[The Surprising Birth Of DuckDB ft. Co-creator Hannes Mühleisen](https://www.youtube.com/watch?v=kpOvgY_ykTE)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

Full screen is unavailable. [Learn More](https://support.google.com/youtube/answer/6276924)

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=kpOvgY_ykTE&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 7:35

•Live

•

## Databases are cumbersome for local development

Data practitioners were not excited about traditional databases because they’re difficult to install and configure. It’s not a smooth to run a database locally. Plus, the client protocol of databases like JDBC, built in the 90s, hasn’t faced significant upgrades. Hannes wanted to research how he could build a database for these people while removing the hassle of managing one.

SQLite was a big inspiration for DuckDB. SQLite has no server, and it’s in-process with a simple library. However SQLite was designed for transactional workloads (with row-based storage). This limited the performance of SQLite for these use cases and presented an opportunity. In-process analytics database are a brand new class of databases, which was exciting for Hannes as a researcher.

This was just the beginning of the story and not even close to what we know today as “DuckDB”. But Hannes isn’t done with the DuckDB project. To quote him :

> “My definition of success as a researcher is not to write papers but to have an impact. In the area of data systems, it is required to make something that will see widespread use in order to achieve impact.”

Check out the full interview above or [directly on YouTube](https://youtu.be/kpOvgY_ykTE).

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Solving Advent of Code with DuckDB and dbt](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fadvent_of_code_ae2c8c7684.jpeg&w=3840&q=75)](https://motherduck.com/blog/solving-advent-code-duckdb-dbt/)

[2023/02/09 - Graham Wetzler](https://motherduck.com/blog/solving-advent-code-duckdb-dbt/)

### [Solving Advent of Code with DuckDB and dbt](https://motherduck.com/blog/solving-advent-code-duckdb-dbt)

Tackling 10 days of AOC with DuckDB and dbt-duckdb, a DuckDB adapter for dbt

[![This Month in the DuckDB Ecosystem: February 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_ecosystem_monthly_feb_2023_9f0c277b5e.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-three/)

[2023/02/22 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-three/)

### [This Month in the DuckDB Ecosystem: February 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-three)

This month in the DuckDB Ecosystem, by Marcos Ortiz. Includes featured community member Pedro Holanda, DuckCon, using dbt with DuckDB, and more.

[View all](https://motherduck.com/blog/)

Authorization Response