---
title: dosomething-non-profit-tco-cost-savings
content_type: case_study
source_url: https://motherduck.com/case-studies/dosomething-non-profit-tco-cost-savings
indexed_at: '2025-11-25T20:02:39.244038'
content_hash: 776e759c55e9a12c
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO CASE STUDIES](https://motherduck.com/case-studies/)

# DoSomething reduced data warehousing costs while empowering users to find their own answers

We found that DuckDB and MotherDuck are amazing tools for small data teams like ours.

![Dave Crusoe's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F1515814825678_e2e8b2e5e7.jpeg&w=3840&q=75)

Dave Crusoe

VP of Product & Engineering

[![Dave Crusoe company logo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FDo_Something_c872643285.png&w=3840&q=75)](https://dosomething.org/)

DoSomething is the leading hub for youth-centered leadership and service with a history of mobilizing over 8 million young people in every U.S. area code and 189 countries. They fuel young people, ages 13-25, to change the world by transforming their curiosity into commitment and equipping them to become leaders who shape the future.

**MotherDuck has been a key component of our next-generation architecture** of the DoSomething platform. As a non-profit serving young people, it’s imperative that we’re responsive to their needs and desires, and data is a critical insight-driver in that regard. We’re a “medium data” organization both in the scale of our data and the scale of our data engineering resources, so cost and complexity are both critical factors for us. We found that **DuckDB and MotherDuck are amazing tools for small data teams** like ours.

## We needed a warehouse optimized for analytics

Our old microservices architecture wasn’t nimble enough for mission-critical changes, and it couldn’t feed data to Tableau or other data visualization tools. Snowflake was too large for our needs, so we tried using Postgres as a data warehouse. Since Postgres isn’t optimized for analytics, queries that are quick in an analytical database – like `GROUP BY` or `COUNT()` – took inordinately long. Sometimes we’d leave queries running all night hoping that they would finish by morning. Plus, we had to pay for a beefier instance to even attempt to do analytics, and storing such significant amounts of user data increased our costs as well. We knew that **something better was possible**.

## MotherDuck's TCO Was Significantly Lower

**MotherDuck solved our analytics challenge outright.** We had heard that DuckDB is **a great way to handle larger-than-memory data**, and that led us to MotherDuck. It was the perfect solution for our needs and our volume of data, and the perfect addition to our new architecture of the DoSomething platform. The **total cost of ownership (TCO) was significantly lower** as well. Most importantly, using MotherDuck, **our analytics queries never go out of scope anymore**.

We were also one of the first data teams to use [Fivetran](https://motherduck.com/ecosystem/fivetran/) with MotherDuck, and **the MotherDuck team really helped make it happen** through a lot of close collaboration. Their cheerful support was an unexpected perk.

## Improved our Quality-of-Life

One of the **most profound outcomes of using MotherDuck has been its quality-of-life features**. Many of our non-technical colleagues use [the MotherDuck UI](https://motherduck.com/product/data-teams#notebook-like-ui/) on a regular basis to find the answers they’re looking for without needing SQL help from the data team. The interface is clean and easy to use, and the data is easy to find.

## Expanding Possibilities for the Future

Looking at our product roadmap, **we’re using data from MotherDuck to help us deepen the member journey** across all facets of our platform. For example, we never could have considered embedded analytics prior to using MotherDuck. Especially with new developments happening with WebAssembly and DuckDB, we even have the option to shift the computing power to the user’s browser. That’s just one of the many ideas we can now consider with MotherDuck. We see a lot of potential ahead.

## DoSomething.org's Data Stack

- **Cloud Data Warehouse:** MotherDuck (replaced Postgres)
- **Business Intelligence:** [Tableau Cloud](https://motherduck.com/ecosystem/tableau/)
- **Orchestration:** GitHub Actions (with [dbt core](https://motherduck.com/ecosystem/dbt/))
- **Data extraction and ingestion:** [Fivetran](https://motherduck.com/ecosystem/fivetran/)

> "MotherDuck’s integration with Tableau Cloud unlocks familiar Business Intelligence at the speed of DuckDB, supercharged by MotherDuck’s powerful cloud technology." - David Crusoe, VP of Product & Engineering

INFO: DoSomething Blog Post
The DoSomething team also has written a [great blog post](https://motherduck.com/blog/dosomething-motherduck-data-warehouse-ROI/) on their journey.

Authorization Response