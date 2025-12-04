---
title: reflex-careers-gig-economy-retail
content_type: event
source_url: https://motherduck.com/case-studies/reflex-careers-gig-economy-retail
indexed_at: '2025-11-25T20:02:36.067197'
content_hash: f9632ed0cbf2f332
has_code_examples: true
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO CASE STUDIES](https://motherduck.com/case-studies/)

# Reflex accelerates retail analytics while avoiding expensive BI tools

MotherDuck is the GOAT

![Nate Hamm's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_15820c5f78.png&w=3840&q=75)

Nate Hamm

Senior Software Developer

[![Nate Hamm company logo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Freflex_3ad1ed4aca.svg&w=3840&q=75)](https://www.workreflex.com/)

Reflex is transforming how retail works. The Austin-based startup connects major brands like Ariat, Deckers, Everlane, Faherty with on-demand retail associates across 40+ cities. Instead of hiring part-time workers, retailers can post open shifts (flexes) and connect with experienced retail associates that can help that same day in-store.

As the company scaled nationally to over 100 brands, their data infrastructure began showing cracks. The team had built a culture of data-driven decision making, but their Metabase instance running directly against production Postgres was creating performance headaches.

"We had thousands of queries we had to maintain," explains Carson Jones, co-founder of Reflex. "All of a sudden, these Frankensteined queries were dependent on other Frankensteined queries that just created quite a bit of load."

## Small, hungry data team

At Reflex, their strategic focus for early-stage development prioritized core product innovation and user experience, with plans to scale their data infrastructure in the latter half of the year. However, the rapidly evolving needs of the product team meant that insights from their clickstream, visibility metrics, and other operational data were becoming increasingly critical. And the existing solution was beginning to show strain under the load of more complex business analytics queries.

Recognizing this growing internal demand for data insights, Nathan Hamm, a talented software engineer at Reflex, stepped up. With a strong interest in data, Nathan saw an opportunity to accelerate our capabilities. Under the guidance of Reflex’s technical leadership, Nathan took on the initiative to explore more robust data solutions.

'I actually wanted to work on data. I think it's really cool,' Hamm says. 'This was a great project to dip my toes in, and MotherDuck provided an accessible yet powerful platform to get started quickly.'

This proactive approach allowed them to centralize key operational data, making it readily accessible to our data-hungry product and analytics stakeholders.

## Discovering MotherDuck through YouTube

The path to MotherDuck began with a YouTube recommendation. Jones was served a video walkthrough of MotherDuck that demonstrated combining data from multiple sources—production databases, CSVs, and JSON files—into a unified schema.

"I was like, whoa, Nate, check this out," Jones recalls. "And honestly, it was the branding that caught us. We want to enjoy the things we're building. I felt like you guys had that ethos as well."

The team was particularly impressed by video tutorials on getting started with dbt and MotherDuck by MotherDuck’s Mehdi Ouazza. These end-to-end walkthroughs provided the practical guidance they needed to evaluate whether MotherDuck could solve their challenges.

## Simple implementation, powerful results

Setting up MotherDuck proved remarkably straightforward. Using the open-source Data Load Tool (DLT) with its built-in MotherDuck integration, Hamm implemented the data pipeline in about 15 lines of code.

"It's been really easy to take it from a platform that isn't really meant for these business analytics queries and move it to MotherDuck, which is much more suited for it," Hamm explains.

The architecture remained simple:

**• App hosting:** Reflex is hosted on Heroku

• **Data ingestion**: dlt pulls data directly from the Postgres follower into MotherDuck

• **Transformation**: dbt pipelines transform the raw data into analytics-ready tables

• **Storage**: Parquet files in S3 serve as backup and archive

• **Analytics**: Metabase connects to MotherDuck for all reporting needs

One immediate benefit was the ability to create new tables without touching production. Previously, any new analytics table had to be built in their production database due to Heroku's constraints. Now, their business analyst could build specialized digest tables directly in MotherDuck.

## Enabling customer-facing analytics

The performance improvements unlocked new possibilities. For the first time, Reflex could email automated Metabase reports to customers and has begun planning to embed analytics directly in their retailer portal.

"Before, I was less comfortable doing this," says Mike Moore, product manager at Reflex. "If we were doing this all through our follower databases, that would start to hit and we'd have long load times. Having MotherDuck means we can send reports more frequently and exactly when we want."

The team also solved a long-standing request to incorporate Excel data into their analytics. A task that had lingered for six months was completed in under 10 minutes once they moved to MotherDuck. They built a simple tool to upload Google Sheets exports to S3, where their pipeline automatically ingests them into MotherDuck as join tables alongside production data.

## Avoiding the expensive BI trap

Perhaps the most significant impact was financial. As Reflex grew, pressure mounted to adopt expensive business intelligence tools like Tableau. The improved performance from MotherDuck eliminated that need.

"We were looking at spending a couple thousand a month on some sort of analytics tool," Moore notes. "It took some convincing to say it's not the analytics tool, it's how our data is formatted underneath. If we can solve those problems, we don't need to switch to a fancy analytics platform."

Jones adds: "By going with MotherDuck, we've been able to give the team ownership and let them stay in Metabase. We haven't had to make the full dive to a hugely expensive BI suite yet."

## Built for growth

Today, Reflex processes large volumes of transactions daily across their marketplace, with MotherDuck handling all analytics workloads. The team uses different instance sizes based on workload requirements and plans to switch read queries to Pulse instances for additional cost savings.

"We're a tiny team doing what we think is a large amount of transactions every day, but it really pales in comparison to where we're going," Jones reflects. "We have a lot of comfort knowing that as we level up and need to grow within our data stack, we have a solid foundation."

For a 30+person startup that's grown 3x+ annually, the ability to scale their data infrastructure without massive investments has proven invaluable. As Hamm succinctly puts it: "MotherDuck is the GOAT."

The partnership extends beyond technology. Reflex particularly values MotherDuck's responsive support team and the rapid pace of feature development. For a company focused on building the best way to work in retail, having a data platform that keeps pace with their ambitions—and their budget—has made all the difference.

Authorization Response