---
title: motherduck-in-europe
content_type: blog
source_url: https://motherduck.com/blog/motherduck-in-europe
indexed_at: '2025-11-25T19:56:18.969020'
content_hash: df1920bcd555945c
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# MotherDuck is Landing in Europe! Announcing our EU Region

2025/09/24 - 6 min read

BY

[Garrett O'Brien](https://motherduck.com/authors/garrett-obrien/)
,
[Sheila Sitaram](https://motherduck.com/authors/sheila-sitaram/)

**TLDR:** MotherDuck's first European cloud region is now in private preview, bringing European customers fast, serverless analytics running entirely within the EU. Running on AWS region `eu-central-1`, the new region ensures your data never leaves Europe while delivering sub-second query performance for business intelligence and customer-facing analytics. [Join the waitlist](http://motherduck.com/eu-region) to get notified when it becomes generally available later this fall.

* * *

We're quacking excited to announce MotherDuck's expansion into Europe with our first dedicated EU region!

DuckDB is soaring in popularity across Europe, and for good reason. Born out of CWI in Amsterdam, DuckDB is a powerful analytical query engine in a lightweight, in-process package. MotherDuck scales DuckDB to a full-fledged data warehouse, and we’ve seen growing demand from European customers who want to use MotherDuck for cloud-scale analytics while addressing compliance and data residency requirements.

European companies like Trunkrs are already relying on MotherDuck for sub-second queries without the overhead of large distributed systems. With the EU region reaching general availability this fall, more European businesses will be able to experience the same performance benefits while keeping their data exactly where it needs to be.

## **Hypertenancy: a different warehouse architecture**

If you’re new to MotherDuck, here’s what you need to know: MotherDuck is fundamentally different from traditional data warehouses. Most data warehouses were built a decade ago when compute resources were much smaller. The systems were architected to distribute workloads over many compute nodes, processing much larger datasets than previously possible. We got “Big Data” as a paradigm, plus a promise that no matter how large your data set, you could (eventually) query it.

Plot twist: most people don’t actually query Big Data! [Only 1 in 600 Redshift users _ever_ scan more than 10TB in a query](https://motherduck.com/blog/redshift-files-hunt-for-big-data/). However, even the users who _aren’t_ running massive queries are still paying the Big Data Tax: high costs and latency for large, distributed systems.

MotherDuck flips this pattern on its head with a **hypertenancy** architecture. In MotherDuck, each user gets their own fully-isolated compute instance that stays connected to the central warehouse. The instances, called Ducklings, can be scaled up or down to fit each compute use case. You can use Standard instances for normal BI workloads while allocating a Jumbo to query a massive historical dataset–each workload runs fully-isolated, avoiding the “noisy neighbor” problem where multi-tenant systems become bottlenecked.

**Through hypertenancy, MotherDuck runs faster, more efficient queries.** Because each Duckling runs on a single, powerful compute instance rather than coordinating across multiple nodes, you eliminate the network overhead and coordination complexity that slows down distributed systems.

![Diagram showing MotherDuck's hypertenancy architecture.](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fhypertenancy_5ccde83666.webp&w=3840&q=75)

## **Same-day delivery that flies: migrating to MotherDuck at Trunkrs**

Trunkrs is a perfect example of how MotherDuck shines. A Netherlands-based same-day delivery company, Trunkrs operates more like a software company than a traditional logistics provider. They orchestrate a network of existing vehicles—assets that would otherwise sit idle in the evenings—to create an efficient delivery system specializing in frozen and perishable goods, making them the market leader in frozen meat delivery.

Trunkrs migrated from Redshift to MotherDuck to power their real-time operational decisions. Their Redshift setup required constant optimization and couldn't handle the parallel requests from users monitoring fast-changing operations. Slow queries during daily meetings meant teams would stop drilling into problems after waiting too long for results.

"With MotherDuck, we're seeing that response is just a lot snappier," explains Hidde Stokvis, COO and data leader at Trunkrs. "We can see that we're just going deeper because we have more time to spend on the data."

The faster queries unlocked deeper analysis, better problem identification, and fewer repeated operational mistakes—exactly what you need when coordinating perishable goods delivery across the Netherlands.

![Image depicting Trunkrs case study with MotherDuck.](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fcase_study_trunkrs_17c85a1c59.png&w=3840&q=75)

## **Ducks in a row: flying with trusted European partners**

We're thrilled to have a network of official launch partners with long histories of helping European companies build data solutions that transform their businesses.

[**Artefact**](http://artefact.com/) is a global data and AI consulting company with 1,700+ experts across 26 countries, partnering with clients including Samsung, L'Oréal, and Orange. Founded in 2014, Artefact sits at the intersection of consulting, data science, AI technologies, and marketing, helping organizations transform into consumer-centric leaders. Read more about Artefact’s partnership with MotherDuck [here](http://www.artefact.com/news/artefact-partners-with-motherduck/).

[**Codecentric AG**](https://www.codecentric.de/en) is Germany's leader in agile software development and innovative technologies. The B Corp-certified company has 550+ employees, specializing in custom software solutions, cloud-native development, and digital transformation.

[**Corail Analytics**](https://www.corailanalytics.com/) is a data agency partnering with French-speaking businesses that want to harness data for more impactful decision-making.

[**Tasman**](http://tasman.ai/) helps companies across Europe sharpen their analytics, data science and business intelligence. Tasman builds what matters for each specific organisation, delivering insights and enabling client teams—not just more data or technical headaches.

[**Xebia**](http://xebia.com/) is a global leader in IT consulting, software engineering, and training. With over 25 years of experience and a team of 5,500+ professionals across 16 countries, Xebia specializes in Artificial Intelligence, Data and Cloud, Intelligent Automation, and Digital Products and Platforms. With a strong focus on engineering excellence and a people-first culture, they equip organizations to apply emerging technologies that accelerate business innovation and drive sustainable competitive advantage. Xebia leads with a responsible and human-centric approach to AI, ensuring organizations shape a better tomorrow for all.

On the technology side, we’re excited to be growing our partnerships with the Modern Duck Stack partners that European businesses trust:

[**Omni**](http://omni.co/) is a business intelligence and embedded analytics platform that helps customers improve self-service, accelerate AI adoption, and build customer-facing data products. Whether users prefer SQL, spreadsheets, AI, or a point-and-click interface, Omni makes it easy for anyone to explore data — all from the same platform. At Omni’s core is a built-in semantic layer that ensures answers are trustworthy and provides AI the business context it needs.

[**dltHub**](http://dlthub.com/) is building Python tools for working with data, including their popular library dlt (data load tool). Based in Berlin and New York City, dltHub blends software and services for data platform teams building in Python.

We’re grateful to our partners for the opportunity to serve European customers together—they're teams with deep understandings of how European businesses think about data, compliance, and analytics architecture.

## **General availability landing soon**

The European region is currently in private preview, with general availability arriving later this fall.

Interested in being among the first to experience MotherDuck in Europe? [Join our waitlist](http://motherduck.com/eu-region) to get notified when the region becomes generally available.

### TABLE OF CONTENTS

[Hypertenancy: a different warehouse architecture](https://motherduck.com/blog/motherduck-in-europe/#hypertenancy-a-different-warehouse-architecture)

[Same-day delivery that flies: migrating to MotherDuck at Trunkrs](https://motherduck.com/blog/motherduck-in-europe/#same-day-delivery-that-flies-migrating-to-motherduck-at-trunkrs)

[Ducks in a row: flying with trusted European partners](https://motherduck.com/blog/motherduck-in-europe/#ducks-in-a-row-flying-with-trusted-european-partners)

[General availability landing soon](https://motherduck.com/blog/motherduck-in-europe/#general-availability-landing-soon)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![PAINLESS GEOSPATIAL ANALYTICS USING MOTHERDUCK’S NATIVE INTEGRATION WITH GALILEO.WORLD](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgalileo_world_4ca0bc68e1.png&w=3840&q=75)](https://motherduck.com/blog/galileo-world-geospatial/)

[2025/09/09 - Patrick Garcia](https://motherduck.com/blog/galileo-world-geospatial/)

### [PAINLESS GEOSPATIAL ANALYTICS USING MOTHERDUCK’S NATIVE INTEGRATION WITH GALILEO.WORLD](https://motherduck.com/blog/galileo-world-geospatial)

Discover how Galileo.world is revolutionizing geospatial analysis. Say goodbye to slow performance and complex setups. Analyze and visualize big data right in your browser.

[![DuckDB Ecosystem: September 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_3_72ab709f58.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

[2025/09/09 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

### [DuckDB Ecosystem: September 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025)

DuckDB Monthly #33: DuckDB 58× faster spatial joins, pg\_duckdb 1.0, and 79% Snowflake cost savings

[View all](https://motherduck.com/blog/)

Authorization Response