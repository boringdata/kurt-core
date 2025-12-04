---
title: gardyn
content_type: case_study
source_url: https://motherduck.com/case-studies/gardyn
indexed_at: '2025-11-25T20:02:40.074885'
content_hash: 3267f3d1e7887e04
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO CASE STUDIES](https://motherduck.com/case-studies/)

# How Gardyn Reduced Analytics Pipeline from 24+ Hours to Under One Hour

We used to do analytics in a MySQL database with all of our daily device, telemetry, and image processing data. There was no way to scale that further using MySQL. With MotherDuck, we’re finally starting to find patterns in our data to help customers grow produce more effectively.

![Rob Teeuwen's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F1689248039646_d794e5ebef.jpeg&w=3840&q=75)

Rob Teeuwen

Data Scientist

[![Rob Teeuwen company logo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGardyn_Logo_Horizontal_400x112_c075de8ca5.webp&w=3840&q=75)](https://mygardyn.com/)

Gardyn offers a vertical, indoor home gardening system that uses a combination of hydroponics, lighting, and real-time monitoring for people to grow their own produce, regardless of space or experience.

**We use MotherDuck to do analytics on a wide portfolio of our company’s data:** ecommerce data, shipping data, finance data, production app data, IoT device telemetry data, and ML data from our image processing pipeline. Some of our production data is in MySQL, some is in Postgres and some is in Mongo. Running analytics across all that was impossible. **Before MotherDuck, our daily data pipeline took more than 24 hours to run. Today, it’s less than an hour.**

Our system allows us to collect large amounts of data. For each device, there’s data on the lights, water, telemetry, user interactions, historical configurations, foliage coverage, 100+ types of plants and more. That amount and diversity of data is full of possibilities, but it was difficult to wrangle when doing analysis to derive meaningful insights.

We needed a data warehouse that could ingest once-a-day updates from all of our sources quickly and easily. The team at [Hashboard](https://hashboard.com/) recommended MotherDuck, and we evaluated it against other options. MotherDuck was easy to use, it ended up meeting all of our requirements, and it was 10x cheaper than the leading data warehouses.

**Setting up MotherDuck was simple and straightforward and saved us a lot of development time.** When we needed a little more nurturing, the MotherDuck customer success team (called the “hatchery”) was there to help us.

[![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgardyn_with_text_5c286798ab.png&w=3840&q=75)](https://mygardyn.com/)

Today, our analysts and back-end devs can query our company data in MotherDuck through tools like Hashboard, DBeaver, or just directly in the Motherduck UI. They can use DuckDB’s [friendly SQL](https://duckdb.org/docs/sql/dialect/friendly_sql.html) which allows our queries to be much less verbose and more readable compared to traditional SQL. Using our new MotherDuck data warehouse is way easier – and quicker – than when they had to pull data from all our different production data sources.

Importantly, we now have the ability to run multiple, complex window functions on very granular time series data. It computes within 2-3 minutes on MotherDuck, even after more than doubling our column count to ~150 columns. Previously, we could only analyze at the monthly level, but MotherDuck's efficient windowing capability computes quickly enough to provide deeper insights into our data.

Now that we have our data centralized, and it’s fast for both ad hoc queries and reporting, we can focus our efforts on finding patterns in the data. We’re delighted to work on actual data science projects rather than worrying about system load and data pipeline completion. The future is bright!

### Our new data platform

- **Raw data:** Azure Storage in Parquet and CSV files
- **Data warehouse:** MotherDuck
- **Data ingestion:** Dagster Cloud and Fivetran
- **Data transformation:** dbt
- **SQL development:** VSCode and the MotherDuck UI
- **BI and dashboards:** Hashboard and Hex.tech

[Learn more about Gardyn](https://mygardyn.com/)

Authorization Response