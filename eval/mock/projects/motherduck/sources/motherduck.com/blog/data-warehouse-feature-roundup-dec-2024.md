---
title: data-warehouse-feature-roundup-dec-2024
content_type: blog
source_url: https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024
indexed_at: '2025-11-25T19:57:58.388851'
content_hash: 3f40ec05dd357a10
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# What’s New: Streamlined User Management, Metadata, and UI Enhancements

2024/12/21 - 3 min read

BY

[Sheila Sitaram](https://motherduck.com/authors/sheila-sitaram/)

December’s feature roundup is focused on improving the user experience and enabling programmatic access. Whether its through the new REST API, UI enhancements, and the ability to query your metadata, we hope these features will make your experience with MotherDuck more intuitive and ergonomic day-to-day.

## User Management API

Teams that support large numbers of users have been asking for a programmatic way to manage user accounts and access tokens.

We’re delighted to introduce the [User Management API](https://motherduck.com/docs/sql-reference/rest-api/motherduck-rest-api/), which simplifies user management for organizations with complex workflows looking to spin up separate users for BI systems or fine-tune developer access for data ingestion and processing workloads.

The API also enables new possibilities for app developers by allowing you to issue short-lived, [Read Scaling Tokens](https://motherduck.com/blog/read-scaling-preview/) to provide read-only access to embedded analytics components or standalone data applications.

## Introducing the Table Summary

Our new Table Summary in the MotherDuck UI allows you to move faster from raw data to insights before writing a **`SELECT *`** query to explore your data.

The Table Summary supports ad-hoc analysis by providing an overview of the shape of your underlying data table and fields. It empowers technical and non-technical users to easily profile and understand your data without requiring SQL for basic analysis. It also increases your data team’s bandwidth to focus on more strategic work.

View column names, types, distributions, and null percentages with just a click, access table previews and DDL statements in the Object Explorer, and empower your team to self-serve insights.

![Table Summary UI](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ftable_summary_UI_42fd80c959.gif&w=3840&q=75)

This feature was inspired by customer feedback about the [Column Explorer](https://motherduck.com/blog/introducing-column-explorer/) and takes ease of use to the next level directly in the object explorer panel on the left side of the MotherDuck UI.

## Metadata at your Fingertips with MD\_INFORMATION\_SCHEMA

We have recently introduced the [MD\_INFORMATION\_SCHEMA](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/md_information_schema/introduction/), a read-only, system-defined view that provides SQL-based access to metadata about your MotherDuck objects.

This new feature helps you retrieve information about `databases`, `owned_shares`, and `shared_with_me` databases.

[Shares](https://motherduck.com/docs/key-tasks/sharing-data/sharing-overview/) are read-only databases designed for collaboration and ad-hoc analytics. They allow users to access the same dataset as a zero-copy clone without duplicating data, enabling seamless collaboration across teams. Shares can be [attached](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/attach-share/) and [updated](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/update-share/) manually or automatically by the Share’s creator.

With `MD_INFORMATION_SCHEMA,` you can now easily retrieve and query metadata to streamline how you understand and manage your shared data resources.

## Get Started

We’re always eager to learn more about how you’re using MotherDuck: Share your success stories and feedback with us on [Slack](https://join.slack.com/t/motherduckcommunity/shared_invite/zt-2hh1g7kec-Z9q8wLd_~alry9~VbMiVqA). If you’d like to discuss your use case in more detail, please [connect with us](https://motherduck.com/contact-us/sales/) \- we’d love to hear about what you’re building and how we can make your MotherDuck experience even better!

### TABLE OF CONTENTS

[User Management API](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024/#user-management-api)

[Introducing the Table Summary](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024/#introducing-the-table-summary)

[Metadata at your Fingertips with MD\_INFORMATION\_SCHEMA](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024/#metadata-at-your-fingertips-with-mdinformationschema)

[Get Started](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024/#get-started)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![LLM-driven data pipelines with prompt() in MotherDuck and dbt](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fstructured_data_1_6c25e4539e.png&w=3840&q=75)](https://motherduck.com/blog/llm-data-pipelines-prompt-motherduck-dbt/)

[2024/12/12 - Adithya Krishnan](https://motherduck.com/blog/llm-data-pipelines-prompt-motherduck-dbt/)

### [LLM-driven data pipelines with prompt() in MotherDuck and dbt](https://motherduck.com/blog/llm-data-pipelines-prompt-motherduck-dbt)

Leveraging LLM workflow in your data pipelines

[![We made a fake duck game: compete to win!](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ffake_duck_game_thumb_064ec74176.png&w=3840&q=75)](https://motherduck.com/blog/fake-duck-game/)

[2024/12/20 - Mehdi Ouazza](https://motherduck.com/blog/fake-duck-game/)

### [We made a fake duck game: compete to win!](https://motherduck.com/blog/fake-duck-game)

Spot the fake (AI generated) duck to win!

[View all](https://motherduck.com/blog/)

Authorization Response