---
title: a-new-paradigm-for-data-visualization-with-just-sql-markdown
content_type: tutorial
source_url: https://motherduck.com/videos/a-new-paradigm-for-data-visualization-with-just-sql-markdown
indexed_at: '2025-11-25T20:45:16.564161'
content_hash: 5b6ca694d38fa379
has_code_examples: true
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

A new paradigm for data visualization with just SQL + Markdown - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[A new paradigm for data visualization with just SQL + Markdown](https://www.youtube.com/watch?v=rIozitZrAT8)

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

[Watch on](https://www.youtube.com/watch?v=rIozitZrAT8&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 1:00:53

•Live

•

BI & VisualizationYouTubeQuack & Code

# A new paradigm for data visualization with just SQL + Markdown

2024/09/24

Traditional, GUI-based Business Intelligence (BI) tools are excellent for creating initial dashboards, but their "drag-and-drop" workflows often create significant long-term challenges. As data assets grow, maintenance becomes a bottleneck, version control is nearly impossible, and customization is limited, leading to a world where data professionals can spend up to 90% of their time on maintenance rather than new analysis. A modern approach, known as "BI as code," addresses these challenges by applying software engineering principles to analytics. This article explores how to use Evidence.dev, an open-source framework, and DuckDB to build maintainable, high-performance data apps using just SQL and Markdown. This combination frees data teams from tedious maintenance and unlocks deeper customization, transforming brittle dashboards into robust data applications.

## Why Traditional BI Workflows Break Down at Scale

The core issue with many BI tools is that the final output, a dashboard, is a software asset that is not treated like one. The creation process involves manual clicks and configurations within a proprietary user interface, which is not only tedious but also error-prone. When a metric definition changes or a new data source is added, an analyst must manually update every affected report. A code-based workflow fundamentally changes this dynamic. By defining reports and visualizations in code, teams can track every change in Git, providing a complete history and the ability to revert to previous versions. New logic can be submitted through pull requests for peer review, and teams can integrate automated testing into a CI/CD pipeline to ensure updates do not break existing reports. This approach makes it simple to find and replace logic across an entire project, drastically reducing maintenance time and bringing the rigor of production software to the world of analytics.

## Building Data Apps with the Tools You Already Know: SQL and Markdown

Evidence is an open-source framework designed to abstract away the complexities of web development, allowing data practitioners to focus on their core competencies. Instead of requiring knowledge of JavaScript, HTML, and CSS, Evidence enables users to build sophisticated data apps using only SQL queries and Markdown files. The workflow is straightforward. An analyst first defines their data sources, such as databases like DuckDB, Postgres, or modern cloud data warehouses like MotherDuck and Snowflake. Next, they write SQL queries to fetch and shape the data, which can be stored in dedicated `.sql` files or embedded directly within pages. Finally, they compose pages using Markdown syntax, embedding pre-built Evidence components like charts and tables that reference the SQL query results. This approach dramatically lowers the barrier to entry for creating custom, narrative-driven reports. This simple, code-based workflow also enables a highly efficient local development experience, allowing analysts to iterate on their work at speed.

## Achieving Flow State: Fast, Local Development for Analytics

One of the most powerful aspects of the "BI as code" workflow is the local development experience. Traditional BI often requires a slow, server-dependent feedback loop. With Evidence, developers run a local server that provides instant updates as they write code. This tight feedback loop is a core feature of the development process. For instance, when a developer modifies a Markdown file to change the number format on a value component, the web page refreshes instantly to reflect the change. This immediate responsiveness allows developers to stay in a state of flow, making development faster, more enjoyable, and more productive. The project structure is organized for clarity, with a `sources` directory for data source configurations and a `pages` directory for the Markdown files that define the application's content. This clean separation of concerns makes projects easy to navigate and maintain.

## Powering High-Performance Analytics with DuckDB

DuckDB plays two critical and distinct roles within the Evidence ecosystem, enabling both high-performance data processing and rich client-side interactivity.

First, Evidence supports DuckDB as a primary server-side data source. Users can connect their projects to local `.duckdb` database files or read directly from collections of Parquet and CSV files. During the build process, Evidence runs queries against this DuckDB source to fetch the data needed for the static site.

Second, and more innovatively, Evidence ships a DuckDB engine to the browser using WebAssembly (WASM). This in-browser OLAP engine unlocks powerful capabilities without requiring a round trip to a server. When a user interacts with a filter or a dropdown on a page, the query is executed by DuckDB WASM directly on the client's machine, providing lightning-fast responses. This architecture also makes it possible to perform joins and aggregations across data that originated from completely different sources, for instance, combining data from a Postgres database and a BigQuery table on the fly.

## Designing for Insight: Customization and Data Storytelling

A code-based approach unlocks a level of customization and narrative depth that is difficult to achieve in GUI-based tools. Because reports are just text files, it becomes simple to inline context, definitions, and commentary directly alongside data visualizations, solving the common problem of documentation living in a separate location. This flexibility allows for a wide range of applications. For example, a "North Star Report" can be enhanced by adding target lines, colored zones, and detailed explanations to charts, creating a clear narrative for stakeholders. At the other end of the spectrum, a highly customized football statistics site built with Evidence can look less like a traditional dashboard and more like a bespoke data web application. Moving to code does not mean sacrificing visual polish; instead, it provides the control needed to build truly tailored experiences.

## From Localhost to Production: Deploying and Sharing Your Data App

The deployment model for Evidence is another key differentiator. When a project is built, Evidence generates a static website consisting of HTML, CSS, and JavaScript files, which can be hosted on any modern serverless platform like Vercel, Netlify, or AWS S3. Because there is no active server or live database connection required to serve the application, this model is inherently secure, scalable, and cost-effective. A CI/CD pipeline handles data refreshes by triggering scheduled rebuilds, which can run daily after upstream data pipelines complete or every few minutes for lower latency.

A powerful pattern is exemplified by the `DuckDBstats.com` project, which combines Evidence with MotherDuck. The site is a static Evidence application that visualizes PyPI download statistics stored in MotherDuck. Crucially, the site also includes a MotherDuck share link, allowing users to not only view the curated report but also gain direct, queryable access to the underlying raw dataset using any DuckDB client. This approach powerfully combines polished data presentation with open data access, enabling deeper exploration for interested users.

## The Next Generation of Business Intelligence

The shift toward "BI as code" represents a maturation of the analytics engineering field. By adopting principles from software development, data teams can build more reliable, scalable, and insightful data products. Tools like Evidence, powered by the performance and flexibility of DuckDB, are lowering the barrier to this new paradigm. The future of business intelligence is not just about visualizing data, but about building interactive, maintainable, and trustworthy data applications that organizations can depend on.

...SHOW MORE

## Related Videos

[!["Can DuckDB replace your data stack?" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FCan_Duck_DB_Replace_Your_Data_Stack_Mother_Duck_Co_Founder_Ryan_Boyd_3_56_screenshot_70e18322ec.png&w=3840&q=75)\\
\\
60:00](https://motherduck.com/videos/can-duckdb-replace-your-data-stack/)

[2025-10-23](https://motherduck.com/videos/can-duckdb-replace-your-data-stack/)

### [Can DuckDB replace your data stack?](https://motherduck.com/videos/can-duckdb-replace-your-data-stack)

MotherDuck co-founder Ryan Boyd joins the Super Data Brothers show to talk about all things DuckDB, MotherDuck, AI agents/LLMs, hypertenancy and more.

YouTube

BI & Visualization

AI, ML and LLMs

Interview

[!["AI Powered BI: Can LLMs REALLY Generate Your Dashboards? ft. Michael Driscoll" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_1123cd92b9.jpg&w=3840&q=75)](https://motherduck.com/videos/ai-powered-bi-can-llms-really-generate-your-dashboards-ft-michael-driscoll/)

[2025-05-20](https://motherduck.com/videos/ai-powered-bi-can-llms-really-generate-your-dashboards-ft-michael-driscoll/)

### [AI Powered BI: Can LLMs REALLY Generate Your Dashboards? ft. Michael Driscoll](https://motherduck.com/videos/ai-powered-bi-can-llms-really-generate-your-dashboards-ft-michael-driscoll)

Discover how business intelligence is evolving from drag-and-drop tools to code-based, AI-powered workflows—leveraging LLMs, DuckDB, and local development for faster, more flexible analytics.

YouTube

AI, ML and LLMs

BI & Visualization

[![" Is BI Too Big for Small Data?" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fis_bi_too_big_cda76f20bb.jpg&w=3840&q=75)\\
\\
17:03](https://motherduck.com/videos/is-bi-too-big-for-small-data/)

[2024-11-17](https://motherduck.com/videos/is-bi-too-big-for-small-data/)

### [Is BI Too Big for Small Data?](https://motherduck.com/videos/is-bi-too-big-for-small-data)

BI tools promise deep insights, but most teams only get noise. Discover why the classic data story fails and how a new small-data playbook can help you find real meaning in your metrics.

YouTube

BI & Visualization

[View all](https://motherduck.com/videos/)

Authorization Response