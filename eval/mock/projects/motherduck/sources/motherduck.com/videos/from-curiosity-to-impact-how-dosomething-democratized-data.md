---
title: from-curiosity-to-impact-how-dosomething-democratized-data
content_type: event
source_url: https://motherduck.com/videos/from-curiosity-to-impact-how-dosomething-democratized-data
indexed_at: '2025-11-25T20:45:14.011777'
content_hash: bcc85b471bb05864
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

From Curiosity to Impact How DoSomething Democratized Data - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[From Curiosity to Impact How DoSomething Democratized Data](https://www.youtube.com/watch?v=WTIFBc0xn4I)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

More videos

## More videos

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Why am I seeing this?](https://support.google.com/youtube/answer/9004474?hl=en)

[Watch on](https://www.youtube.com/watch?v=WTIFBc0xn4I&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 56:04

•Live

•

YouTube

# From Curiosity to Impact How DoSomething Democratized Data

2025/09/10

For any organization, especially lean data teams at startups or non-profits, DoSomething's story is a powerful testament to the fact that you don't need to choose between over-engineered, expensive solutions and the limitations of spreadsheets. With the right modern data stack, you can achieve speed, affordability, and a culture of data empowerment.For a lean data team, the choice between slow, costly enterprise tools and wrestling with spreadsheets is a constant struggle. Hear how DoSomething.org, a non-profit fueling young people to change the world, escaped this data trap. By building a new modern data stack with MotherDuck, they achieved a 20x cost reduction, transformed their data culture, and empowered their entire team with [self-serve analytics](https://motherduck.com/learn-more/self-service-analytics-startups/) —all managed by a single data engineer.

### The Challenge: A High-Cost, Low-Value Data System

DoSomething has a long history of leveraging technology for good, but their previous data stack, built between 2015 and 2024, had become a significant burden. The architecture consisted of Fivetran for data extraction, a Postgres database used as a data warehouse, and dbt Cloud for nightly transformations.

This system presented several critical problems:

- **Cripplingly Slow Queries:** As an OLTP (Online Transaction Processing) database, Postgres is not optimized for heavy analytical queries. Sahil, DoSomething's Senior Data Engineer, recalls queries taking hours to run, "if they ran at all." This made it impossible for stakeholders to get timely insights.
- **Exorbitant Costs:** The infrastructure was expensive. Fivetran, used to ingest massive volumes of web event data that were rarely used, became the "largest single line item" in their data budget. The 4TB Postgres data warehouse was also costly to maintain.
- **Data Request Bottlenecks:** The slow performance of Tableau dashboards connected to Postgres meant most insights were locked behind the data team. Non-technical users had no direct access, leading to a constant stream of data requests and an inability for them to answer their own questions.

### The Solution: A Lean, Fast, and Accessible Modern Data Stack

During a complete platform rebuild in 2024, Sahil discovered DuckDB and the "small data movement." The simplicity and performance of DuckDB for local analysis led him to MotherDuck, a serverless data warehouse built on DuckDB. This became the cornerstone of their new, cost-effective data stack.

The new architecture is a model of efficiency:

- **Extraction:** Fivetran is now used sparingly, only for Google Analytics 4 data, putting them on the free tier.
- **Loading:** Data is loaded directly into MotherDuck, which provides significant compression and performance.
- **Transformation:** Nightly dbt Cloud jobs that took 8 hours were replaced with a dbt Core project running via GitHub Actions. The new runtime? Just two to three minutes, falling within GitHub's free tier.

### The Impact: 20x Lower Costs and True Self-Service Analytics

The shift to MotherDuck delivered transformative results, enabling DoSomething to remain a sustainable, data-driven organization.

**1\. Massive Cost Reduction (95% Savings)**
The new data system costs roughly 5% of the old one. The bill for their MotherDuck data warehouse is approximately 20 times less than what they were paying AWS for their previous Postgres-based system. This dramatic cost reduction was not just a budget win; it was essential for the non-profit's long-term sustainability.

**2\. Simplicity and Blazing Speed**
The new stack is orders of magnitude more performant. With dbt runs dropping from 8 hours to 2 minutes and queries returning in seconds, the solo data engineer can develop and iterate with unprecedented speed. This is the power of using a dedicated OLAP (Online Analytical Processing) system like MotherDuck for analytics instead of an OLTP database like Postgres.

**3\. Democratized Data with Self-Serve Analytics**
The most profound change was the empowerment of non-technical team members. Sahil describes a "revelatory moment" when a colleague answered their own data question using the MotherDuck UI without knowing SQL.

As demonstrated in the video, MotherDuck's user-friendly interface makes this possible:

- **Column & Table Explorer:** Users can instantly see aggregations, value distributions, and schema information to quickly understand the data without writing a single line of code.
- **Natural Language Queries:** Using the "Command-K" feature, anyone can ask questions in plain English (e.g., "how many active actions have a scholarship?") and get back a SQL query and the answer.
- **AI in the Warehouse:** The `PROMPT()` function allows users to perform complex analysis, like sentiment analysis or categorization, on text data directly within the warehouse, opening the door for agentic AI workflows.

This shift from data request dependence to self-sufficiency has allowed the entire DoSomething team to have a clearer, more immediate understanding of their user activity, fostering a true data-driven culture.

For any organization, especially lean data teams at startups or non-profits, DoSomething's story is a powerful testament to the fact that you don't need to choose between over-engineered, expensive solutions and the limitations of spreadsheets. With the right modern data stack, you can achieve speed, affordability, and a culture of data empowerment.

...SHOW MORE

## Related Videos

[!["Data-based: Going Beyond the Dataframe" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FData_based_f32745b461.png&w=3840&q=75)](https://motherduck.com/videos/going-beyond-the-dataframe/)

[2025-11-20](https://motherduck.com/videos/going-beyond-the-dataframe/)

### [Data-based: Going Beyond the Dataframe](https://motherduck.com/videos/going-beyond-the-dataframe)

Learn how to turbocharge your Python data work using DuckDB and MotherDuck with Pandas. We walk through performance comparisons, exploratory data analysis on bigger datasets, and an end-to-end ML feature engineering pipeline.

Webinar

Python

AI, ML and LLMs

[!["Empowering Data Teams: Smarter AI Workflows with Hex & MotherDuck" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FHex_Webinar_778e3959e4.png&w=3840&q=75)](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck/)

[2025-11-14](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck/)

### [Empowering Data Teams: Smarter AI Workflows with Hex & MotherDuck](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck)

AI isn't here to replace data work, it's here to make it better. Watch this webinar to see how Hex and MotherDuck build AI workflows that prioritize context, iteration, and real-world impact.

Webinar

AI, ML and LLMs

[!["Lies, Damn Lies, and Benchmarks" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FLies_Damn_Lies_and_Benchmarks_Thumbnail_404db1bf46.png&w=3840&q=75)](https://motherduck.com/videos/lies-damn-lies-and-benchmarks/)

[2025-10-31](https://motherduck.com/videos/lies-damn-lies-and-benchmarks/)

### [Lies, Damn Lies, and Benchmarks](https://motherduck.com/videos/lies-damn-lies-and-benchmarks)

Why do database benchmarks so often mislead? MotherDuck CEO Jordan Tigani discusses the pitfalls of performance benchmarking, lessons from BigQuery, and why your own workload is the only benchmark that truly matters.

Stream

Interview

[View all](https://motherduck.com/videos/)

Authorization Response