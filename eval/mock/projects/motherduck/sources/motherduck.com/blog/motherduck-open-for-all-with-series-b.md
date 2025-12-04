---
title: motherduck-open-for-all-with-series-b
content_type: blog
source_url: https://motherduck.com/blog/motherduck-open-for-all-with-series-b
indexed_at: '2025-11-25T19:58:20.189858'
content_hash: 57000f1a77141ffa
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Duck and Roll: MotherDuck is Open for All With $100M in the Nest

2023/09/20 - 5 min read

BY

[Ryan Boyd](https://motherduck.com/authors/ryan-boyd/)

Three months ago we [announced MotherDuck](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/) to the world under a waitlist. Since the launch, we’ve had 2,000 users querying on MotherDuck and are grateful to have [received feedback](https://www.linkedin.com/posts/valentinotereshko_a-month-ago-a-motherduck-user-submitted-a-activity-7101995642360664065-M-Dh?utm_source=share&utm_medium=member_desktop) from over a hundred users. We’ve iterated on the product with our users and are excited to open MotherDuck for all data analysts, data engineers, data scientists and their flocks. [Sign up today](https://app.motherduck.com/?auth_flow=signup) to start using serverless SQL analytics powered by DuckDB.

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fhome_sweet_584fc8e135.png&w=3840&q=75)

## Why are companies flocking to MotherDuck?

Users excite us every day with novel usage of MotherDuck, but we’ve seen three primary use cases that we’re using to drive the development of the product.

### Cloud Data Warehouse for the Rest of Us

Hardware has advanced a lot in the last 10 years, but we’re still using complicated distributed data processing circa 2005. MotherDuck provides a simplified, performant and efficient data warehouse based on the lightweight DuckDB engine for the 95% of data warehouses that don’t need petabyte scale.

### Data Lake Query Engine

Do you have all your data in a cloud data lake? Or perhaps just your cold data? MotherDuck uses DuckDB to query your data where it sits as parquet, iceberg \[soon\], or CSV files. With a notebook-like web UI and vectorized execution, you can run SQL queries on your data sitting in-place.

### Serverless Backend for Data Apps

Customers of SaaS applications are demanding fast and fresh analytics on their data to make better decisions. Developers often tackle this with analytics queries running on the transactional database (hopefully a replica) which are not designed for the task. MotherDuck uses DuckDB to provide a better solution.

> "We looked at various OLAP platforms that could serve our broad and demanding data platform that serves the modern CFO as we were hitting scale limits (price and performance) with Postgres on RDS. MotherDuck with DuckDB was by far the fastest - both in the cloud and run on our developer's machines - bridging price and performance and greatly increasing productivity. We feel we have partnered with the future of Cloud and desktop-based OLAP providers with MotherDuck." Jim O'Neill, CTO & Co-Founder, SaaSWorks.

## How does MotherDuck fit into the Modern Duck Stack?

As data engineers and analysts, we need to combine many tools together from a rich ecosystem to handle orchestration, ingestion, transformation, business intelligence and data science + AI. Because of the ease of working with MotherDuck and DuckDB, we’ve been able to build out an impressive Modern Duck Stack with 28+ technologies. We’re excited that Airbyte announced today that MotherDuck and DuckDB support is available in both the cloud product and open source project.

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmds_7bdf5cb5e8.png&w=3840&q=75)

## What Makes MotherDuck Different?

The key to MotherDuck is a simplified scale-up approach to SQL analytics. We believe that basing our service on DuckDB can make analytics faster, cheaper and more user-friendly than distributed architectures.

We also believe there is huge unutilized compute capacity in our laptops we use everyday. We have learned from data engineers and analysts that they want a workflow which intelligently uses this local compute in concert with the cloud. This is why we created hybrid query execution, with DuckDB running not only in our cloud, but also in the clients that connect to MotherDuck.

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Farchitecture_1fd112f558.png&w=3840&q=75)

Today, hybrid query execution allows you to access both local and cloud data in the same SQL statement, with the query planner intelligently deciding how to split the workload. You can also easily materialize data locally or in the cloud, from the command-line or Python. This type of flexibility and analyst-friendly experience is what has [driven DuckDB’s popularity](https://db-engines.com/en/ranking_trend/system/DuckDB).

## What’s Next for MotherDuck?

We’re all just getting started making analytics ducking awesome. We’re grateful to have been joined on this journey by talented investors who believe in our vision, our team and the combined MotherDuck and DuckDB communities. Today, Felicis joins us as the lead investor of our $52.5M Series B round along with existing investors a16z, Madrona, Amplify Partners, Altimeter, Redpoint, Zero Prime, and more. This round brings the total capital raised to $100M.

> “We are excited to partner with Jordan and the MotherDuck team as they build a platform designed to seamlessly blend speed and user-friendliness, thereby simplifying and making analytics widely accessible. Analysts clearly need the speed of working with data at the edge, as well as the [flexibility](https://duckdb.org/2023/08/23/even-friendlier-sql.html) to query cloud-based data. The era of serverless data analytics is here.” - Viviana Faga, General Partner, Felicis.

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fyellow_make_analytics_ducking_awesome_sticker_2x_e73a9c286b.png&w=3840&q=75)

We’ll be growing the team as we accelerate on this journey. [Learn more](https://motherduck.com/careers/) about the culture we’re building and apply to join the flock!

You can learn more about why Felicis invested in their [blog post](https://www.felicis.com/insight/motherduck-series-b). Our CEO, Jordan Tigani, also shared some of his thoughts on the raise in his [LinkedIn post](https://www.linkedin.com/feed/update/urn:li:activity:7110287011223154689/)

## Get Started Querying Today

We’re available for everyone today, so [create your account](https://app.motherduck.com/?auth_flow=signup), [read our docs](https://motherduck.com/docs/intro) and [join our slack community](https://slack.motherduck.com/). MotherDuck is currently free to use until we enable billing next year. You’ll find more information and answers to other frequently asked questions [on our website](https://motherduck.com/product/).

### TABLE OF CONTENTS

[Why are companies flocking to MotherDuck?](https://motherduck.com/blog/motherduck-open-for-all-with-series-b/#why-are-companies-flocking-to-motherduck)

[How does MotherDuck fit into the Modern Duck Stack?](https://motherduck.com/blog/motherduck-open-for-all-with-series-b/#how-does-motherduck-fit-into-the-modern-duck-stack)

[What Makes MotherDuck Different?](https://motherduck.com/blog/motherduck-open-for-all-with-series-b/#what-makes-motherduck-different)

[What’s Next for MotherDuck?](https://motherduck.com/blog/motherduck-open-for-all-with-series-b/#whats-next-for-motherduck)

[Get Started Querying Today](https://motherduck.com/blog/motherduck-open-for-all-with-series-b/#get-started-querying-today)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![MotherDuck + dbt: Better Together](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2023_09_07_at_16_10_13_d4360ccc33.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-duckdb-dbt/)

[2023/09/07 - Sung Won Chung](https://motherduck.com/blog/motherduck-duckdb-dbt/)

### [MotherDuck + dbt: Better Together](https://motherduck.com/blog/motherduck-duckdb-dbt)

MotherDuck + dbt: Better Together

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response