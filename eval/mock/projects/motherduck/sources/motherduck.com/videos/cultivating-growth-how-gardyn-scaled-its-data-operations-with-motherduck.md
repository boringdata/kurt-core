---
title: cultivating-growth-how-gardyn-scaled-its-data-operations-with-motherduck
content_type: tutorial
source_url: https://motherduck.com/videos/cultivating-growth-how-gardyn-scaled-its-data-operations-with-motherduck
indexed_at: '2025-11-25T20:44:58.682802'
content_hash: 00f749e6dfcc958f
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

Cultivating Growth: How Gardyn Scaled its Data Operations - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Cultivating Growth: How Gardyn Scaled its Data Operations](https://www.youtube.com/watch?v=tlxql5eBFiY)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Why am I seeing this?](https://support.google.com/youtube/answer/9004474?hl=en)

[Watch on](https://www.youtube.com/watch?v=tlxql5eBFiY&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 39:48

•Live

•

YouTube

# Cultivating Growth: How Gardyn Scaled its Data Operations with MotherDuck

2025/05/28

## From MySQL to Modern Analytics: A Data Platform Transformation Story

Gardyn, the innovative indoor hydroponic gardening company, faced a critical challenge as they scaled their operations. With smart devices generating vast amounts of sensor data, computer vision outputs, and customer interaction metrics, their data infrastructure needed a complete overhaul to keep pace with business growth.

## The Starting Point: Executives Running Production Queries

When Rob joined Gardyn three years ago as their first full-time data scientist, the data landscape was minimal. Executives were running queries directly against the production MySQL database, creating risks for system performance and customer experience. The immediate priority was establishing basic analytics capabilities while separating analytical workloads from production systems.

## Building the Initial Infrastructure

Rob's first steps involved creating a MySQL replica for analytics and deploying a Kubernetes cluster to run Apache Airflow for orchestration. This homegrown solution included:

- Custom Python scripts for data ingestion
- Raw SQL transformations managed through Airflow
- Jupyter notebooks for ad hoc analysis
- Plotly Dash applications for dashboards

While this approach initially worked, it quickly became unsustainable. As the data volume grew and transformation complexity increased, the daily pipeline runtime ballooned from one hour to over 24 hours, creating significant operational challenges.

## The Modern Data Stack Migration

Facing these scaling limitations, Gardyn embarked on a comprehensive platform modernization. The new architecture centered around several key components:

### Data Warehouse: MotherDuck

The migration from MySQL to MotherDuck delivered immediate performance improvements. Pipeline runtime dropped from 24+ hours to just 10 minutes, enabling the team to build date-spined models and perform complex time series analysis that was previously impossible.

### Transformation Layer: dbt

Moving from raw SQL to dbt eliminated the need to manually manage dependencies and made the transformation logic more maintainable and scalable.

### Orchestration: Dagster

The switch from Airflow to Dagster was driven by seamless dbt integration. Dagster's asset-based approach simplified dependency management and provided better visibility into the data pipeline.

### Analytics Tools: Hex and Hashboard

These platforms replaced the self-hosted Jupyter notebooks and Dash applications, providing:

- Hex for Python-based analysis and machine learning workflows
- Hashboard for self-service BI with a semantic layer that enables non-technical users to explore data safely

## Unlocking Business Value Through Integrated Data

The new platform enabled Gardyn to finally integrate data from multiple sources:

- Device sensor readings
- Computer vision model outputs detecting plant health
- Customer app interactions
- Website engagement metrics

This unified view of the customer journey has powered new features, including a "care score" that gives customers insights into how well they're maintaining their devices. The computer vision system can now detect issues with plants and automatically notify users, as well as celebrate positive milestones like new flowers or ripe vegetables.

## Key Lessons for Scaling Data Operations

Rob's advice for other data professionals facing similar challenges emphasizes thinking long-term even when pressured for quick answers. Building generalizable models and scalable infrastructure from the start, even if it takes extra time initially, pays dividends as the business grows.

The transformation also freed Rob to focus on actual data science work rather than infrastructure maintenance. With the Kubernetes cluster retired and managed services handling the heavy lifting, the team can now concentrate on delivering insights that improve the customer experience and drive business growth.

## Looking Forward

Gardyn's data team is now focused on modeling customer journeys in greater detail and expanding their computer vision capabilities. The solid foundation built through this migration enables them to tackle increasingly sophisticated analytical challenges while maintaining the performance and reliability their growing business demands.

The journey from production database queries to a modern data platform illustrates how thoughtful architecture choices and the right tool selection can transform a company's ability to leverage its data assets effectively.

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