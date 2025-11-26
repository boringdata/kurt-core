---
title: data-engineer-highlights-PyConDE-2023
content_type: blog
source_url: https://motherduck.com/blog/data-engineer-highlights-PyConDE-2023
indexed_at: '2025-11-25T19:57:36.787948'
content_hash: 901acc390642d35f
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Data Engineer's Highlights from PyCon DE 2023

2023/05/04 - 5 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

Greetings, Python enthusiasts! As you may know, PyCon is a global phenomenon that brings together the brightest minds in the Python programming world. Originating in the United States in 2003, this event has since spread its wings and now takes place in numerous countries across the globe. Each PyCon event showcases the latest developments, innovations, and trends in Python, all while fostering collaboration, networking, and learning within the community.

It's astounding to witness the numerous volunteers who contributed to organising the event. Even the person handing you your ticket might be a senior data engineer!

In this blog post, I’ll share my data engineering highlights from PyCon DE, where over 1,300 (plus 400 joining remotely) Python enthusiasts gathered to exchange ideas and share knowledge.

![20230417_100826.jpg](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpycon_de_0_49ea2be764.jpg&w=3840&q=75)

## Pandas and Polars dominating discussions

There were a lot of talks, workshops dedicated to Pandas and Polars. These two dataframes libraries are indeed in front of the data Python recently with some major new features.

## Pandas 2.0

This release was officially launched on April 3rd, and there was plenty to discuss.

Two major improvements that significantly increased efficiency include:

- Support for Pyarrow backend, resulting in faster and more memory-efficient operations.
- Copy-on-Write Optimization

Apache Arrow is beginning to dominate the data world, providing a method to define data in memory. For Pandas, Arrow serves as an alternative data storage format. Being a columnar format, it interacts seamlessly with Parquet files, for example.

Even when discussing competitors libraries (more on that below), some people acknowledge that Arrow has resolved many issues.

![Screenshot 2023-05-03 at 11.04.08.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpycon_de_1_3beb39cc5a.png&w=3840&q=75)

Copy-on-write is a smart method for working with modifiable resources, like Pandas dataframes. Instead of making a copy of the data right away, Pandas simply refers to the original data and waits to create a new copy until it's really needed. This approach helps save memory and improves performance, all while avoiding unnecessary data copies.

Talks :

- [Pandas 2.0 and beyond by Joris Van den Bossche & Patrick Hoefler](https://vimeo.com/user171811262/review/818527397/d4b6371f29)
- [Apache Arrow: connecting and accelerating dataframe libraries across the PyData ecosystem by Joris Van den Bossche](https://vimeo.com/819239432)

## Polars for faster pipelines

Polars is making waves as the new go-to library for fast data manipulation and analysis in Python. Built in Rust, its primary distinction lies in the performance features it brings to the table:

- Lightweight - no extra dependencies needed
- Multi-threaded and SIMD: harnessing all your cores and performing parallel processing when possible

The lazy feature in Polars offers substantial performance and resource management benefits. Lazy evaluation, a technique where expressions or operations are delayed until explicitly requested, allows Polars to smartly optimize the execution plan and conduct multiple operations in a single pass.

However, it's worth noting that Polars may not fully replace Pandas in certain cases. The existing Python data ecosystem, built on Pandas over the years, remains robust, particularly for visualization.

![Screenshot 2023-05-03 at 11.03.36.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpycon_de_2_339274b466.png&w=3840&q=75)

What about DuckDB? To be honest, SQL isn't everyone's favorite language. It appears that many Python enthusiasts are not even aware of [DuckDB's relational API](https://duckdb.org/docs/api/python/relational_api). Despite this, you can maintain a Python-based workflow and take advantage of DuckDB's key features, such as extensions and file formats. Additionally, DuckDB is compatible with your existing dataframe libraries, thanks to Arrow.

Talks :

- [Polars - make the switch to lightning-fast dataframes by Thomas Bierhance](https://vimeo.com/818670333)
- [Raised by Pandas, striving for more: An opinionated introduction to Polars by Nico Kreiling](https://vimeo.com/818667511)

## Rust FTW

Fun that we get to hear more Rust at a Python conference. This is typical since Rust is incredibly powerful when developing Python keybindings. Many major Python data projects, such as Delta-rs (Delta lake Rust implementation), have Rust implementations. Pydantic and Polars work in a similar way, boosting Python performance by rewriting some core components in Rust while maintaining the beautiful simplicity of Python as the main interface.

Robin Raymond created a fantastic slides summary to demonstrate that even though Rust delivers excellent performance, writing better Python is also a viable option.

![Screenshot 2023-05-02 at 15.02.02.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpycon_de_3_837e1cffd8.png&w=3840&q=75)

Talk :

- [Rusty Python : A case study by Robin Raymond](https://vimeo.com/818792575)
- [Pragmatic ways of using Rust in your data project by Christopher Prohm](https://vimeo.com/819029984)

## Data roles definition are still confusing

I’ve been advocating for a long time about the confusion of data roles. Especially around data engineering.

In this talk, Noa Tamir covers the story about the data science role and how it has evolved.

What I found particularly interesting was the comparison between data science management and management in general, as well as with software engineering. If we recognise the differences, I believe we are one step further to get better at managing data science teams and project.

Talk : [How Are We Managing? Data Teams Management IRL by Noa Tamir](https://vimeo.com/818787463)

## Towards Learned Database Systems

My favorite keynote as I learned more about learned databases!

The speaker presented two intriguing techniques, data-driven learning and zero-shot learning, which address some of the limitations of current learned DBMS approaches.

Data-driven learning caught my attention as it learns data distributions over complex relational schemas without having to execute large workloads. This method is promising for tasks like cardinality estimation and approximate query processing. However, it has its limitations, which led the speaker to introduce zero-shot learning.

![Screenshot 2023-05-02 at 15.02.31.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpycon_de_4_99f1df7da4.png&w=3840&q=75)

Talk :

- [Towards Learned Database Systems by Carsten Binnig](https://vimeo.com/819071781)

## That’s a wrap!

PyCon talks are usually all available on YouTube, and I’ll be curious to catchup on some talks when the PyCon US releases them. I expect however to see the same trends on the data engineering side : Pandas & Polars wars, Arrow and Rust FTW.

May the data conference be with you.

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: April 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_ecosystem_monthly_april_2023_bb2015c778.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-five/)

[2023/04/17 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-five/)

### [This Month in the DuckDB Ecosystem: April 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-five)

This month in the DuckDB Ecosystem, by Marcos Ortiz. Latest updates, including featured community member Josh Wills, upcoming events like webinars and top links.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response