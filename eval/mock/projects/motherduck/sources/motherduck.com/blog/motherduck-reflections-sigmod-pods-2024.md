---
title: motherduck-reflections-sigmod-pods-2024
content_type: blog
source_url: https://motherduck.com/blog/motherduck-reflections-sigmod-pods-2024
indexed_at: '2025-11-25T19:56:50.770663'
content_hash: 48992a9a5c7782c5
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Reflections on SIGMOD/PODS 2024: Insights and Highlights

2024/07/02 - 7 min read

BY

[Stephanie Wang](https://motherduck.com/authors/stephanie-wang/)
,
[Till Döhmen](https://motherduck.com/authors/till-d%C3%B6hmen/)

The [SIGMOD PODS 2024](https://2024.sigmod.org/) conference, sponsored by MotherDuck and several tech giants, was full of groundbreaking research, innovative technologies, and engaging discussions. It was a hub of intellectual exchange and collaboration, which made for an inspiring and productive week in Santiago, Chile for the MotherDuck team.

This blog will walk through an overview of MotherDuck’s presence at SIGMOD and cover key highlights and innovation themes that caught our attention. Our biggest takeaway? There has never been a better time to be part of the database community, and we look forward to seeing how these advancements progress in the future.

## MotherDuck’s Presence at SIGMOD

MotherDuck showcased our contributions at SIGMOD/PODS 2024 with a series of presentations.

Peter Boncz from [Centrum Wiskunde & Informatica](https://www.cwi.nl/en/) (CWI) is currently on sabbatical at MotherDuck. He delivered [an inspiring keynote](https://vimeo.com/958649913/bce7542125), "Making Data Management Better with Vectorized Query Processing," to make the case for doing data systems research with impact in the real world. And he did not fail to mention all the exciting work currently in progress at MotherDuck!

![Peter Boncz SIGMOD 2024](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage2_04c4d77bdd.png&w=3840&q=75)_Peter Boncz from CWI presenting his SIGMOD keynote on data systems research_

Till Döhmen, AI/ML Lead, presented his research on " [SchemaPile: A Large Collection of Relational Database Schemas](https://dl.acm.org/doi/10.1145/3654975)" and provided the community with a corpus of 221,171 database schemas containing rich metadata to improve various data management applications.

[Effy Xue Li](https://effyli.github.io/), PhD Intern, introduced innovative approaches through her research, " [Towards Efficient Data Wrangling with LLMs using Code Generation](https://dl.acm.org/doi/10.1145/3650203.3663334)," to demonstrate how LLM-based data wrangling through code generation significantly improves data transformation tasks at lower computational costs.

![Effy Xue Li and Till Döhmen](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage4_db9a31f690.jpg&w=3840&q=75)_(From left to right): Effy Xue Li, PhD Intern, and Till Döhmen, AI/ML Lead, in front of their co-authored paper “Towards Efficient Data Wrangling with LLMs using Code Generation”_

Stephanie Wang, Founding Engineer, and Till Döhmen collaborated on a sponsor talk, "Simplifying Data Warehousing for Efficient and User-Friendly Data Management," that emphasizes MotherDuck's commitment to making data warehousing more accessible and efficient for users.

![MotherDuck demo booth](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage3_8b7f40aaf8.jpg&w=3840&q=75)_(Pictured from left to right): Effy Xue Li, PhD Intern, and Stephanie Wang, Founding Engineer, at MotherDuck’s demo station_

MotherDuck’s sponsorship of SIGMOD and deep involvement in the academic community underscore our commitment to fostering innovation and supporting innovative database research. In the following sections, we’ll outline highlights and themes that caught our attention at SIGMOD 2024.

## Disaggregated Memory

A key conference theme focused on the exploration of disaggregated memory systems. Disaggregated memory systems involve the separation of memory and compute, which requires advanced networking technologies to enable low-latency, high-bandwidth communication.

AlibabaCloud showcased [PolarDB-MP](https://dl.acm.org/doi/abs/10.1145/3626246.3653377), their multi-primary cloud-native database that leverages disaggregated shared memory, and also presented scalable distributed inverted list indexes designed for disaggregated memory.

## Adaptive Lossless Floating-Point Compression (ALP)

The CWI research group, the origin of DuckDB, presented [a new floating-point compression method](https://ir.cwi.nl/pub/33334).

A series of new codecs were recently introduced, starting with [Facebook’s Gorilla encoding](https://www.vldb.org/pvldb/vol8/p1816-teller.pdf) and followed by codecs called [Chimp and Patas](https://openproceedings.org/2024/conf/edbt/paper-248.pdf).

Notably, ALP outperforms these codecs in both compression and decompression speeds and compression ratio. The algorithm was first published in SIGMOD 2024 and presented by PhD student Leonardo Kuffo, and it has already been incorporated into [DuckDB 0.10](https://duckdb.org/2024/02/13/announcing-duckdb-0100.html), which means MotherDuck customers can already take advantage of its efficiency benefits!

![Group photo at SIGMOD](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_e3d9b5a4cd.jpg&w=3840&q=75)_(Pictured from left to right): Stephanie Wang, Peter Boncz, [Ilaria Battiston](https://www.cwi.nl/en/people/ilaria-battiston/), Effy Xue Li, and [Leonardo Kuffo](https://github.com/lkuffo)_

## SQL Alternatives and Additions

While SQL has existed since the early 1970s, there has never been a more opportune moment to innovate on its syntax and make analytics more intuitive. This is one of many reasons MotherDuck has adopted [DuckDB’s intuitive, highly flexible SQL dialect](https://motherduck.com/product/data-teams/#boost#productivity), and we’re excited about the possibilities in this area and its potential applications. SIGMOD 2024 showcased new ideas on this topic by proposing novel SQL alternatives and additions.

TypeDB showcased [TypeQL](https://typedb.com/docs/core-concepts/typeql/), a new query language inspired by natural language. It offers an expressive type system that promises to revolutionize how we interact with databases.

Looker by Google introduced [Measures in SQL](https://cloud.google.com/looker/docs/reference/param-field-sql#:~:text=or%20yyyymmdd%20format.-,sql%20for%20Measures,based%20on%20several%20other%20measures), which brings composable calculations to SQL, allowing context-sensitive expressions to be attached to tables, which makes tables with measures composable and closed when used in queries. This innovative addition is a significant enhancement to traditional SQL capabilities.

## Proactive and Hybrid Resource Allocation

### Proactive Resource Allocation

There was a significant focus on distributed systems at SIGMOD 2024, emphasizing proactive and hybrid resource allocation.

Microsoft presented its [proactive resource allocation strategies for millions of serverless Azure SQL databases](https://dl.acm.org/doi/10.1145/3626246.3653371), while Alibaba showcased [Flux](https://dl.acm.org/doi/abs/10.1145/3626246.3653381), a cloud-native workload auto-scaling platform designed for AnalyticDB. It offers decoupled auto-scaling for heterogeneous query workloads.

Amazon also introduced [RAIS](https://www.amazon.science/publications/intelligent-scaling-in-amazon-redshift), Redshift’s next-generation AI-powered Scaling, which includes new optimization techniques for intelligent scaling in Amazon Redshift.

### Hybrid Resource Allocation

Microsoft’s scalable Container-As-A-Service Performance Enhanced Resizing algorithm for the cloud [(CaaSPER)](https://www.microsoft.com/en-us/research/publication/caasper-vertical-autoscaling/) stood out in the hybrid resource allocation category. CaaSPER [uses a combination of reactive and predictive approaches based on historical time-series data](https://www.microsoft.com/en-us/research/blog/research-focus-week-of-february-19-2024/) to make informed decisions about CPU requirements for monolithic applications.

## Generative AI and Large Language Models (LLMs)

This year, there were many talks on Generative AI and LLMs and their applications in data management. With dozens of research papers and industry sessions, four (!) workshops, and two keynotes, it was impossible to ignore that Generative AI has arrived in the data management world and is here to stay.

### Natural Language Interfaces

There were many panel discussions, industry talks, and hallway conversations where Text2SQL was a topic. The importance of context was repeatedly emphasized, particularly regarding rich schema metadata and query history. Several sessions also highlighted responsible AI safeguards and downstream feedback mechanisms. Preferred architectural patterns are converging towards a combination of Foundation Models (FM) and Retrieval Augmentation Generation (RAG), with optionally fine-tuned foundation models. It was exciting to see that progress has also continued in the development of smaller Text2SQL models. Notably, Renmin University of China presented the [CodeS model](https://dl.acm.org/doi/10.1145/3654930), which achieved a new top score on the Spider benchmark.

Industry presentations underscored how [Text2SQL solutions](https://motherduck.com/blog/duckdb-text2sql-llm/) are primarily used today as co-pilots for SQL analysts and data scientists to yield significant productivity gains. Solutions such as semantic layers seem promising for enabling natural language interfaces for business users, particularly those that allow essential business metrics (e.g., organization-specific definitions of revenue) to be represented on the language layer.

### Data Discovery

Finding the right data in a data lake with hundreds or thousands of tables often presents a challenging problem for data analysts and data scientists. Madelon Hulsebos from UC Berkeley presented an insightful [user study](https://dl.acm.org/doi/10.1145/3665939.3665959) on how users actually want to use data search systems. Simple search features that help users quickly identify the most relevant dataset are the most effective, but data freshness and semantics are crucial to their swift identification.

[Cocoon](https://dl.acm.org/doi/10.1145/3626246.3654748), a semantic data profiling tool built by Zezhou Huang on DuckDB, fits in here very well! The future of dataset search is moving towards more interactive and flexible search solutions that go beyond keyword search. One fascinating example is [Ver](https://dl.acm.org/doi/10.1145/3626246.3654748), a view discovery system, and we look forward to seeing how this space evolves and where MotherDuck can evolve to make data sharing and discovery more intuitive.

## Looking Ahead

The SIGMOD/PODS 2024 conference highlighted ongoing advancements in database technologies and the importance of collaboration between academia and industry.

At MotherDuck, we look forward to seeing how these innovations will shape the data management landscape in the years to come.

Stay tuned for more updates and reflections on our involvement in upcoming conferences, and learn more about [events and talks](https://motherduck.com/events/) we’re giving worldwide!

### TABLE OF CONTENTS

[MotherDuck’s Presence at SIGMOD](https://motherduck.com/blog/motherduck-reflections-sigmod-pods-2024/#motherducks-presence-at-sigmod)

[Disaggregated Memory](https://motherduck.com/blog/motherduck-reflections-sigmod-pods-2024/#disaggregated-memory)

[Adaptive Lossless Floating-Point Compression](https://motherduck.com/blog/motherduck-reflections-sigmod-pods-2024/#adaptive-lossless-floating-point-compression)

[SQL Alternatives and Additions](https://motherduck.com/blog/motherduck-reflections-sigmod-pods-2024/#sql-alternatives-and-additions)

[Proactive and Hybrid Resource Allocation](https://motherduck.com/blog/motherduck-reflections-sigmod-pods-2024/#proactive-and-hybrid-resource-allocation)

[Generative AI and Large Language Models](https://motherduck.com/blog/motherduck-reflections-sigmod-pods-2024/#generative-ai-and-large-language-models)

[Looking Ahead](https://motherduck.com/blog/motherduck-reflections-sigmod-pods-2024/#looking-ahead)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![DuckDB Ecosystem: September 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_3_72ab709f58.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

[2025/09/09 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

### [DuckDB Ecosystem: September 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025)

DuckDB Monthly #33: DuckDB 58× faster spatial joins, pg\_duckdb 1.0, and 79% Snowflake cost savings

[![MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Feu_launch_blog_b165ff2751.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-in-europe/)

[2025/09/24 - Garrett O'Brien, Sheila Sitaram](https://motherduck.com/blog/motherduck-in-europe/)

### [MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/blog/motherduck-in-europe)

Serverless analytics built on DuckDB, running entirely in the EU.

[View all](https://motherduck.com/blog/)

Authorization Response