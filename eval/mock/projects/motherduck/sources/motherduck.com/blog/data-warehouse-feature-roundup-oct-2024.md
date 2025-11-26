---
title: data-warehouse-feature-roundup-oct-2024
content_type: blog
source_url: https://motherduck.com/blog/data-warehouse-feature-roundup-oct-2024
indexed_at: '2025-11-25T19:56:52.214983'
content_hash: 1d1ff13c5a3e4773
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# You asked, We Listened: Sharing, UI and Performance Improvements

2024/10/22 - 2 min read

BY

[Doug Raymond](https://motherduck.com/authors/doug-raymond/)

Hello all - this is Doug, the new Head of Produck at MotherDuck.

In my first blog post, I’m writing to tell you about some recent improvements we’ve made that might not be huge on their own, but collectively make our product better. MotherDuck is constantly improving as a data warehouse - in this post, I’ll briefly introduce recently-launched features that make exploring large data sets, querying, and data sharing more efficient and intuitive.

## Preview cell contents UI

Working with complex data types, such as JSON or nested structures, can be cumbersome. Often, the values are too large to fit within a single cell, making it difficult to see the complete picture.

With the new cell preview UI, you can view the full contents of selected cells, allowing you to inspect large or complex data types—like `STRUCTs, ARRAYS, MAPS`, or even `BLOBs`—in full detail.

![Preview Animated GIF](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fanimated_preview_cell_inf_54d115d103.gif&w=3840&q=75)

## Dual Execution performance optimizations

With Dual Execution, MotherDuck lets you analyze this local data locally, while still JOINing with data processed in the cloud, giving you efficient use of all your compute resources and allowing you to query local data in milliseconds.

We’ve made optimizations to reduce the round trips needed for many Dual Execution queries from two to one. This will result in many users will see significant improvements in response times, which will range from 10s to 100s of milliseconds, depending on your proximity to the data center you are querying.

## Auto Update Shares

With the introduction of Auto Update, you can now set your database shares to automatically sync with the latest changes—both DDL and DML—within five minutes of any completed writes.

Previously, when sharing a database, the snapshot you shared remained static until you explicitly updated it by running the `UPDATE SHARE` statement. Now, users can automate updates by setting the `UPDATE AUTOMATIC` option during [share creation](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/create-share/).

## What's next?

I’m excited to get to know the MotherDuck community. What would you like to see next? Reach out in the #feature\_request channel in our [MotherDuck Community Slack](https://join.slack.com/t/motherduckcommunity/shared_invite/zt-2hh1g7kec-Z9q8wLd_~alry9~VbMiVqA)!

### TABLE OF CONTENTS

[Preview cell contents UI](https://motherduck.com/blog/data-warehouse-feature-roundup-oct-2024/#preview-cell-contents-ui)

[Dual Execution performance optimizations](https://motherduck.com/blog/data-warehouse-feature-roundup-oct-2024/#dual-execution-performance-optimizations)

[Auto Update Shares](https://motherduck.com/blog/data-warehouse-feature-roundup-oct-2024/#auto-update-shares)

[What's next?](https://motherduck.com/blog/data-warehouse-feature-roundup-oct-2024/#whats-next)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Small Data is bigger (and hotter 🔥) than ever](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fblog_c71a983762.png&w=3840&q=75)](https://motherduck.com/blog/small-data-sf-recap/)

[2024/10/19 - Sheila Sitaram](https://motherduck.com/blog/small-data-sf-recap/)

### [Small Data is bigger (and hotter 🔥) than ever](https://motherduck.com/blog/small-data-sf-recap)

Catch up on the latest developments around simple, scalable workflows for Real data volumes from the first Small Data SF!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response