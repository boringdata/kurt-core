---
title: cidr-paper-hybrid-query-processing-motherduck
content_type: event
source_url: https://motherduck.com/blog/cidr-paper-hybrid-query-processing-motherduck
indexed_at: '2025-11-25T19:56:16.076582'
content_hash: 23a9f33edc9cbbbb
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Just Released: Hybrid Query Processing Paper at CIDR 2024

2024/01/16 - 2 min read

BY

[Peter Boncz](https://motherduck.com/authors/peter-boncz/)

The Conference on Innovative Data systems Research (CIDR) is underway in California and we’re proud to be presenting a peer-reviewed [paper on the MotherDuck hybrid query processing architecture](https://www.cidrdb.org/cidr2024/papers/p46-atwal.pdf).

[Hybrid query processing](https://motherduck.com/learn-more/hybrid-analytics-guide/) allows you to execute database queries either on your local machine, in the cloud, or using a combination of both. It adds useful capabilities to DuckDB, for instance the sharing of DuckDB databases between different team members via the cloud. It also allows you to create web applications with DuckDB running inside your browser, that can jointly execute queries with MotherDuck in the cloud.

The research and implementation of this architecture has been a collaboration between MotherDuck, DuckDB Labs and myself as a visiting database researcher on sabbatical from CWI, the Dutch national computer science research institute from which DuckDB was born.

Because designing and implementing a cutting-edge database system like MotherDuck is non-trivial, there are in fact quite a bit of research elements in what we do, even when software engineering. For example, we need to understand how to optimally plan hybrid queries when there are asymmetrical network connections (like in consumer internet) or cost differences in storage, compute and energy. This is why the collaboration between academia and industry is so important in databases; it has already provided a lot of inspiration for my research group at CWI while providing benefits to MotherDuck’s users.

I look forward to gaining other inspiration for my research group and MotherDuck from my fellow researchers at CIDR. Although CIDR is a relatively small conference, it attracts a distinguished audience of researchers and practitioners working in data systems attending it. The conference was originally created by two Turing Award winners: Jim Gray and Michael Stonebraker, both founding figures of the database field.

Our CIDR paper is [now available for download](https://www.cidrdb.org/cidr2024/papers/p46-atwal.pdf) and provides an in-depth view of MotherDuck and our hybrid query architecture. I truly hope that you also will find it interesting. If so, please spread the word and pass it along to people who you think also will find this interesting!

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Why Python Developers Need DuckDB (And Not Just Another DataFrame Library)](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fwhy_pythondev_1_22167e31bf.png&w=3840&q=75)](https://motherduck.com/blog/python-duckdb-vs-dataframe-libraries/)

[2025/10/08 - Mehdi Ouazza](https://motherduck.com/blog/python-duckdb-vs-dataframe-libraries/)

### [Why Python Developers Need DuckDB (And Not Just Another DataFrame Library)](https://motherduck.com/blog/python-duckdb-vs-dataframe-libraries)

Understand why a database is much more than just a dataframe library

[![DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_1_4_1_b6209aca06.png&w=3840&q=75)](https://motherduck.com/blog/announcing-duckdb-141-motherduck/)

[2025/10/09 - Alex Monahan, Garrett O'Brien](https://motherduck.com/blog/announcing-duckdb-141-motherduck/)

### [DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains](https://motherduck.com/blog/announcing-duckdb-141-motherduck)

MotherDuck now supports DuckDB 1.4.1 and DuckLake 0.3, with new SQL syntax, faster sorting, Iceberg interoperability, and more. Read on for the highlights from these major releases.

[View all](https://motherduck.com/blog/)

Authorization Response