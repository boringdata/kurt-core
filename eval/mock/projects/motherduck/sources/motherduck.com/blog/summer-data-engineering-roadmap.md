---
title: summer-data-engineering-roadmap
content_type: guide
source_url: https://motherduck.com/blog/summer-data-engineering-roadmap
indexed_at: '2025-11-25T19:56:26.188059'
content_hash: fb8ba4d903bc6f17
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Summer Data Engineering Roadmap

2025/07/21 - 15 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

With this summer edition, you'll have a roadmap for your vacation time to learn the basics of being a full-stack data engineer. Fill your knowledge gaps, refresh the basics, or learn with a curated list and path towards a full-time data engineer.

After covering the essential toolkit in [Part 1](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/) (essential tools for your machine) and [Part 2](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/) (infrastructure and DevOps), this article teaches you **how** and in **what order** to learn these skills. The roadmap provides a structured path to level up during the slower summer months.

The roadmap is organized into 3 weeks that you can learn at your own pace and time availability:

- **Week 1**: Foundation (SQL, Git, Linux basics)
- **Week 2**: Core Engineering (Python, Cloud, Data Modeling)
- **Week 3**: Advanced Topics (Streaming, Data Quality, DevOps)

![data_engineering_roadmap_6](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fde_roadmap_1de442a139.png&w=3840&q=75)

**How to use this guide**: Each section contains curated resources (articles, videos, tutorials) for that topic. Click on the links that interest you most. It's meant as a guided roadmap to learn the fundamentals of a "full stack" data engineer.

TIP: Learning at Your Own Pace
While structured as a three-week program, everyone learns differently. Pick what's most relevant to your goals and skip sections you won't need immediately or in the near-term future. Consistency matters more than speed. Sometimes we forget how far 30 minutes a day can take us. And no, after three weeks, you won't know everything you need to know, but you'll be able to understand the problems and identify potential angles to solve them.

## Week 1: Foundation and Core Skills

Let's get started with building your technical foundation skills for data engineering.

You can learn the foundational skills in many ways: there are bootcamps, courses, blogs, YouTube videos, hands-on projects, and many more ways to learn them (free and paid ones), including the more advanced skills.

### SQL Foundations

Probably the most important skill of any data engineer, at any level, whether they are closer to the business or more technical, is SQL—the language of data. You can descriptively explain what you want from your data much more precisely than natural language through LLM workflows. That's why it will always be a core skill. For example, in the English language, you won't specify the partitions or the exact date range (including or excluding the current month). There are many questions that you need to define in your WHERE statement or in the SELECT, which you would miss otherwise.

To get started with SQL until you master it, you can follow this roadmap below:

- Start with [understanding SQL](https://www.w3schools.com/sql/sql_intro.asp).
- Database design principles, from [relational database basics to key concepts for beginners](https://www.freecodecamp.org/news/learn-relational-database-basics-key-concepts-for-beginners/). Learn DDL (`ALTER`, `CREATE`), DML (`INSERT`, `UPDATE`, `DELETE`), and [relational theory by Edgar F. Codd](https://www.geeksforgeeks.org/dbms/introduction-of-relational-model-and-codd-rules-in-dbms/), who invented the theoretical basis for relational databases.
- Advanced SQL queries, such as [Window functions](https://mode.com/sql-tutorial/sql-window-functions/) for performing advanced aggregations without additional subqueries within the current query. Or, [CTEs](https://www.datacamp.com/tutorial/cte-sql) are a powerful syntax that allows for better readability, creating aliases for sub-queries, and even recursion is possible.
- [ACID properties and transactions](https://www.geeksforgeeks.org/dbms/acid-properties-in-dbms/) within databases such as Postgres, MySQL, and DuckDB.
- Learn the differences between OLTP vs. OLAP with a [beginner's guide](https://www.datacamp.com/blog/oltp-vs-olap). Also, check out an explainer of [What is OLAP?](https://motherduck.com/learn-more/what-is-OLAP/)
- [dbt core](https://medium.com/@suffyan.asad1/getting-started-with-dbt-data-build-tool-a-beginners-guide-to-building-data-transformations-28e335be5f7e) and [SQLMesh](https://thedatatoolbox.substack.com/p/getting-started-with-sqlmesh-a-comprehensive): frameworks to encapsulate SQL into a structure that can be versioned, tested, and run in order, including well-documented lineage as a web page.

### Version Control

If you use SQL, very quickly you'll want to work with coworkers and want to version it so as not to lose essential changes or to roll back added bugs.

Therefore, you need version control. This short chapter gives you some starting points for the most common one.

- What is version control - [a visual guide to version control](https://betterexplained.com/articles/a-visual-guide-to-version-control/).
- The tool, [Git fundamentals](https://www.coursera.org/learn/version-control-with-git).
- GitHub/GitLab Collaboration: Learn about platforms like GitHub and GitLab for hosting Git repositories and for sharing and collaborating with others. Main features include Pull Requests and Issues for [communicating your changes in a structured](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests) way.
- Learn the different [git workflows](https://www.atlassian.com/git/tutorials/comparing-workflows). Also, check out [git worktree](https://dev.to/yankee/practical-guide-to-git-worktree-58o0). Although it's a bit advanced, it's good to know it's there, especially if you need to **work on different branches simultaneously** without constantly stashing or committing your unfinished changes before switching to another branch.

There are many more helpful topics, such as GitHub Actions/Pipelines for CI/CD or basic automation (uploading documents to a website, checking grammar automatically before publishing, etc.). However, for the first week, let's keep it simple and move on to the next chapter: Linux and scripting.

### Environment Setup, Linux Fundamentals & Basic Scripting

Set up your development environment and master essential Linux skills for data engineering. This depends on your operating system of choice, too, but most data engineering tasks are typically run on servers. In almost all cases, they are executed on Unix-based systems. That's why Linux fundamentals are key to elevating your data engineering skills.

Below are the resources and roadmap to learn about these topics:

- [Bash scripting essentials](https://www.freecodecamp.org/news/bash-scripting-tutorial-linux-shell-script-and-command-line-for-beginners/), starting with the basics of bash scripting, including variables, commands, inputs/outputs, and debugging. Alternatively, use this course with an interactive command line in the browser: [Linux command line basics](https://www.codecademy.com/learn/learn-the-command-line) (Paid).
- Package managers (Apt, yum, Homebrew, Wget): [How to Use Package Managers in Linux? (APT and YUM)](https://www.geeksforgeeks.org/techtips/apt-and-yum-package-managers-in-linux/) and [Homebrew for macOS](https://brew.sh/)
- [SSH and remote connections](https://www.hostinger.com/tutorials/ssh-tutorial-how-does-ssh-work): Connecting to a remote server and fixing a DAG or updating a script on the fly.
- Development environment setup: Simple yet powerful dev setups: [MacOS setup](https://ghostinthedata.info/posts/2025/2025-02-02-setting-up-your-data-engineering-environment-on-macos/) with pyenv, docker, uv, VSCode, Linux ( [Omakub](https://github.com/basecamp/omakub), [Omarchy](https://github.com/basecamp/omarchy)) and [Windows Setup for data scientist](https://medium.com/bitgrit-data-science-publication/how-to-setup-a-windows-laptop-for-data-science-e56ee3f0dcf0).
- [Cron jobs and scheduling](https://ostechnix.com/a-beginners-guide-to-cron-jobs/): Basic automation scripts without the need for a heavy tool.

Congratulations, this wraps up week one. If you have watched, experimented, and taken notes, you now possess the fundamentals of data engineering and, frankly, any engineering or technical job. Give yourself some time to ponder and review, and then proceed to week two below.

## Week 2: Core Data Engineering

Week two is all about the essential data concepts, primarily established principles for manipulating and architecting data flows for data engineering tasks.

### Data Modeling & Warehousing

To avoid creating independent SQL queries and persistent data tables without connected data sets, we need to model our data with a more holistic approach.

This is where the concepts of so-called data modeling and the long-standing term data warehousing originate. The sole purpose of these is to organize data optimized for consumption, whereas data in Postgres and other operational databases is optimized for storage.

This chapter will teach you and point you to key knowledge to prepare you to model enterprise workloads.

- **[Data modeling](https://www.integrate.io/blog/mastering-data-warehouse-modeling/)** is a significant one, and somewhat underappreciated these days. However, with the rise of AI and automation, it hasn't been more critical to learn.

  - [Dimensional modeling](https://www.getdbt.com/blog/guide-to-dimensional-modeling) with a [star schema](https://learn.microsoft.com/en-us/fabric/data-warehouse/dimensional-modeling-overview).
  - [Snowflake schema vs star schema](https://www.datacamp.com/blog/star-schema-vs-snowflake-schema): Understanding when to use normalized vs denormalized dimension tables.
  - [Data normalization](https://www.freecodecamp.org/news/database-normalization-1nf-2nf-3nf-table-examples/): 1NF, 2NF, 3NF principles for reducing data redundancy
  - [Fact tables vs dimension tables](https://www.montecarlodata.com/blog-fact-vs-dimension-tables-in-data-warehousing-explained/): Understanding measures, metrics, and descriptive attributes.
  - [Granularity](https://www.ssp.sh/brain/granularity/) is a key concept to understand, so your facts will not suffer from too low detail that is slow, or too high-level detail that loses crucial information when drilling down in a dashboard.
- Data warehouse design methodologies:
  - [Kimball methodology](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/): Bottom-up, business process-focused approach.
  - [Inmon methodology](https://www.astera.com/type/blog/data-warehouse-concepts/): Top-down, enterprise data model approach.
  - [Data Vault 2.0](https://www.scalefree.com/blog/data-vault/quick-guide-of-a-data-vault-2-0-implementation/): An approach with hubs, links, and satellites for agility and scalability.
- Advanced modeling concepts:
  - [Slowly changing dimensions](https://learn.microsoft.com/en-us/fabric/data-factory/slowly-changing-dimension-type-two): Handling changes in dimension data over time.
  - [Bridge tables and many-to-many relationships](https://www.kimballgroup.com/2012/02/design-tip-142-building-bridges/): Managing complex relationships in dimensional models.

### Python for Data Engineering & Workflow Orchestration

After SQL, Python is the next most important language to learn. While it's beneficial to have deep knowledge about SQL, and you only need preliminary Linux skills to get around a server and run some commands from the command line, Python is the utility language of data. It's the **glue code that connects everything** you can't achieve with SQL, most notably working with external systems and orchestrating your data workflows with Python libraries and frameworks.

Orchestration and other more modern tools help you automate and organize, as well as version your data tasks and pipelines.

- Starting with a [Python general introduction](https://realpython.com/python-beginner-tips/).
- [DataFrame and data manipulation](https://motherduck.com/blog/duckdb-python-e2e-data-engineering-project-part-1/) with Pandas, Polars and [DuckDB](https://www.youtube.com/watch?v=ZX5FdqzGT1E). [Navigating the Dataframe Landscape](https://motherduck.com/learn-more/dataframes/) and [DuckDB vs Pandas vs Polars for Python Developers](https://motherduck.com/blog/duckdb-versus-pandas-versus-polars/), [Video Format](https://www.youtube.com/watch?v=4DIoACFItec)
- Python libraries for [Data validation with Pydantic](https://realpython.com/python-pydantic/) or [Data Testing with pytest](https://docs.pytest.org/en/stable/getting-started.html).
- Utilitarian Python knowledge. Connecting to any API quickly with [FastAPI](https://fastapi.tiangolo.com/tutorial/).
- Workflow orchestration is almost as important as the Python language itself. [Apache Airflow](https://airflow.apache.org/docs/apache-airflow/stable/index.html) is the biggest name. You learn about task dependencies and scheduling, as well as how orchestration and integration of data tools and stacks work through workflow management. Also, check out related [DAG design patterns](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html) for guidance on designing pipelines that are easy to maintain and separate business logic from technical logic in an organized and conventional manner.

INFO: Example Data Sets to Test for Yourself
To manipulate data or create an example project, you can use the provided datasets out of the box with DuckDB: \[Example Datasets\](https://motherduck.com/docs/getting-started/sample-data-queries/datasets/), containing interesting datasets such as HackerNews, Foursquare, PyData, StackOverflow, and many more.

### Cloud Platforms Introduction

Getting to know major cloud platform providers can save you a significant amount of time and enhance your employability because you know how to work around permissions, the services provided, and how to automate specific tasks. Ensure you select the right provider based on your location and primary use, or the company you prefer to work for.

- Introduction to [AWS](https://aws.amazon.com/getting-started/), [Azure](https://azure.microsoft.com/en-us/get-started), or [Google Cloud](https://cloud.google.com/docs/get-started/). Vital is permission management, such as security and IAM basics, on all platforms.
- Dedicated data services: [MotherDuck](https://motherduck.com/), [BigQuery](https://cloud.google.com/bigquery/docs/quickstarts), [Fabric](https://learn.microsoft.com/en-us/fabric/), [hosted Airflow](https://cloud.google.com/composer/docs) (Azure & AWS).
- [Object Storage or blob storage setup](https://lakefs.io/blog/object-storage/) on all platforms.

Depending on where your resume positions you, you'll do different work. But some sort of analytics through business intelligence (BI) is always involved. Visualizing your data and showing it in a way that makes sense immediately is hard; that's where BI tools and data visualization come into play.

- Introduction to BI tools and using [notebooks](https://motherduck.com/docs/getting-started/interfaces/motherduck-quick-tour/). Others are Jupyter Notebooks, Hex, DeepNote, and many more. Check [Jupyter notebooks for analytics](https://www.geeksforgeeks.org/data-analysis-and-visualization-with-jupyter-notebook/), which is a super helpful toolkit for data analysis and iteration.
- [Metrics and KPI design](https://atlan.com/metrics-layer/) with metrics layers and semantics.
- [Data visualization best practices](https://www.toptal.com/designers/data-visualization/data-visualization-best-practices). Tools like [color management](https://www.datawrapper.de/blog/10-ways-to-use-fewer-colors-in-your-data-visualizations) and a [high-level grammar of interactive graphics](https://vega.github.io/vega-lite/) help understand data presentation. [Hichert SUCCESS Rules](https://www.controlling-strategy.com/hichert-success-regeln.html) is another great option, although it is only available in German. Check also [Data Visualization with Hex/Preset and DuckDB/MotherDuck](https://www.youtube.com/watch?v=F9yHuAO50PQ&t=2s).
- [Self-service analytics](https://www.rilldata.com/blog/has-self-serve-bi-finally-arrived-thanks-to-ai) enables business people to serve themselves.

This concludes Week Two. You're ready to tackle the advanced topics in Week three.

## Week 3: Advanced Topics

This final week focuses on advanced topics, including data quality and streaming. This last part of the data engineering roadmap focuses on cost optimization, data quality, event-driven approaches, DevOps learnings, and advanced data quality and observability.

Some of these topics are rarer approaches and should be avoided initially, but there's a time when you need any of them.

### Stream Processing & Event-Driven Data

Event-driven approaches or integrating your data as a stream, end-to-end from source to your analytics, is sometimes a must and business-critical, especially for ad-tech or sports, where you need live results that are as up-to-date as possible.

Understanding stream processing fundamentals is especially beneficial for validating users' requests for real-time data insights, as they will often ask for it, but it's not always necessary.

- [Event-driven architecture](https://codeopinion.com/change-data-capture-event-driven-architecture/) and design practices: How do they differ from batch loads? Key players in this category are [Apache Kafka](https://howtodoinjava.com/kafka/apache-kafka-tutorial/) and [Flink](https://dev.to/mage_ai/getting-started-with-apache-flink-a-guide-to-stream-processing-e19).
- Real-time analytics patterns: [Change Data Capture (CDC)](https://www.datacamp.com/blog/change-data-capture) and the difference in propagating that stream compared to batch. See [Postgres change data capture possibilities](https://bryteflow.com/postgres-cdc-6-easy-methods-capture-data-changes/).

### Data Quality & Testing

Implementing robust data quality frameworks and testing strategies is crucial for maintaining a stable data platform. Most often, it's quick to set up a data platform, or a stack to extract analytics from your data, but doing it stably and with high data quality is an entirely different job. The tools in this chapter will help you with that.

- Great Expectations and other [data quality frameworks](https://www.startdataengineering.com/post/implement_data_quality_with_great_expectations/).
- [Unit testing for data pipelines](https://docs.dagster.io/guides/test/unit-testing-assets-and-ops): How to test your data and pipelines in an automated fashion.
- [Data lineage and governance](https://www.montecarlodata.com/blog-data-lineage/): How to get the lineage of your data flow.
- [A Beginner’s Guide for Observability](https://sixthsense.rakuten.com/blog/Demystifying-Data-Observability-A-Beginners-Guide-for-2025). Be sure to learn about [Data Contracts](https://atlan.com/data-contracts/), a concept for defining data interfaces between data and business teams.
- [Metadata Management](https://www.informatica.com/resources/articles/what-is-metadata-management.html): Data discovery with data catalogs, ratings of datasets to know which ones are actively used and of good quality. Check also the [Schema registry management](https://docs.confluent.io/platform/current/schema-registry/fundamentals/data-contracts.html) to handle metadata.

### Cost Optimization & Resource Management

Most of the time, especially if you use cloud solutions, the price to pay for these services is relatively high. Therefore, stopping the creation of a heavy temp table on an hourly basis can save a significant amount of costs. Consequently, it's crucial to debug heavy SQL queries or wasted orchestration tasks, including orphaned ones that aren't connected to any upstream datasets or that aren't in use.

Stacks that don't run in the cloud are optimized differently. Here, you don't pay for cloud services, but to run your own. That's why you optimize for team members and tasks. As data engineering tasks are elaborate, **spending time on the right tasks** can **save a lot of money**, too.

In the past, it was referred to as performance tuning. At that time, we were optimizing for speed, which remains the case today. Similarly, if you maximize performance, you also improve cost efficiency at the same time, as it runs for shorter periods. Over time, this can result in significant savings.

- [Cloud cost monitoring and optimization](https://spot.io/resources/cloud-cost/cloud-cost-optimization-15-ways-to-optimize-your-cloud/): Tools to monitor the cost and usage of data engineering tasks.
- [Performance Tuning](https://mode.com/sql-tutorial/sql-performance-tuning): Indexing, partitioning strategies, and caching mechanisms are important components, as is [query optimization for better efficiency](https://turbo360.com/blog/significance-of-sql-query-consumption-analysis) and lower cost.
- [Storage tiering and lifecycle management](https://min.io/product/automated-data-tiering-lifecycle-management)

### Infrastructure as Code & DevOps

Infrastructure management and deploying new software in an automated fashion typically occurs through Infrastructure as Code (IaC) using Kubernetes or a similar platform. That's why it's good to have preliminary knowledge about these tools and when to use them.

- Docker containerization is a good start; here's [a beginner's guide](https://www.datacamp.com/tutorial/docker-tutorial).
- [Kubernetes](https://kubernetes.io/docs/tutorials/) and [Terraform](https://developer.hashicorp.com/terraform/tutorials) basics.
- [Monitoring and logging explained](https://medium.com/@mcgeejasond/devops-monitoring-and-logging-explained-939c3b5e17c4).
- [Advanced CI/CD](https://circleci.com/blog/learn-iac-part02/) for deploying entire data stacks and data platforms.

That's it. This is a three-week roadmap with numerous courses and links to help you learn data engineering. Let's take a break and dive into the final part, observing what we've learned throughout these three weeks.

## Congratulations, You've Learned the Essentials of Data Engineering

This roadmap provides the foundation, but data engineering is a field that requires continuous learning. Stay curious, build projects, and connect with the community. The skills you've developed here will serve as your starting point into more specialized areas as you grow in your career.

A quick recap of what you have learned. By the end of this 3-week roadmap, you should have learned a lot, especially the key components of data engineering. With a little bit of picking and choosing, it should have been fun to engage in new, interesting, and potentially unknown topics.

By **Week 1**, you learned how to write SQL to query the data you want, and some additional functions that SQL provides that you didn't know before. You know how to safely version control your SQL statements and collaborate with others on them. And you have some basic Linux skills.

After **Week 2**, you can navigate and use a cloud-based data warehouse on one of the major cloud providers of your choice. You learned different ways to model your data and its flow, as well as which Python libraries and helper frameworks are available.

**Week 3** enables you to understand basic analytics skills and present data to clients. You know how to implement the glue code between SQL and run it on Linux using workflow orchestration tools. You have a rough idea of what real-time data workloads look like and how they differ from batch workloads. You should have an understanding of how to package production-ready code for deploying scalable data stacks using DevOps tools and methodologies. You have heard and seen various approaches to architecting an enterprise data platform.

### What's Next?

All of it will help you **build your portfolio** and land your dream data engineering role. Each week builds upon the previous, creating a comprehensive learning experience that mirrors real-world data engineering challenges.

Throughout the entire process, it's beneficial to build your online portfolio, where you showcase your data engineering learnings, Git projects, website, and links to hackathons you participated in, among other things that demonstrate your motivation. Above all, sharing is also fun; people will reach out to you after reading your content, especially if they learn from it too.

Remember to take your time learning new concepts. If you give yourself time to digest, you learn more easily, you'll be able to recall specific terms better, and it's easier to connect the knowledge—this is how our brains learn.

Consistency is key. Dedicate 1-2 hours daily for a couple of weeks, and you'll be amazed at what compounding and consistent learning can achieve.

* * *

I hope you enjoyed this write-up. If so, you may also find the essential toolkit article for data engineers, available in [Part 1](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/) and [Part 2](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/), or check an [End-To-End Data Engineering Project](https://www.youtube.com/watch?v=3pLKTmdWDXk&t=1s) with Python and DuckDB.

If you want more? Check out the [Mastering Essentials](https://motherduck.com/learn-more/) resources by MotherDuck, or follow their [YouTube channel](https://www.youtube.com/@motherduckdb) for additional resources. If you like DuckDB and need a cost-efficient data warehouse or data engine, check out [MotherDuck](https://app.motherduck.com/) for free.

Further in-depth content can be found and learned through bootcamps, events, and courses. Please don't give up; it's a lot to take in when you start. Begin with the fundamentals as guided in this roadmap, and also follow your interests. It's better to learn something that might not be suitable right now, but because you are passionate about it, learning comes much more easily. And over time, that knowledge may be put to use at a crucial moment later on.

### TABLE OF CONTENTS

[Week 1: Foundation and Core Skills](https://motherduck.com/blog/summer-data-engineering-roadmap/#week-1-foundation-and-core-skills)

[Week 2: Core Data Engineering](https://motherduck.com/blog/summer-data-engineering-roadmap/#week-2-core-data-engineering)

[Week 3: Advanced Topics](https://motherduck.com/blog/summer-data-engineering-roadmap/#week-3-advanced-topics)

[Congratulations, You've Learned the Essentials of Data Engineering](https://motherduck.com/blog/summer-data-engineering-roadmap/#congratulations-youve-learned-the-essentials-of-data-engineering)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![DuckDB Ecosystem: September 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_3_72ab709f58.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

[2025/09/09 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

### [DuckDB Ecosystem: September 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025)

DuckDB Monthly #33: DuckDB 58× faster spatial joins, pg\_duckdb 1.0, and 79% Snowflake cost savings

[![MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Feu_launch_blog_b165ff2751.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-in-europe/)

[2025/09/24 - Garrett O'Brien, Sheila Sitaram](https://motherduck.com/blog/motherduck-in-europe/)

### [MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/blog/motherduck-in-europe)

Serverless analytics built on DuckDB, running entirely in the EU.

[View all](https://motherduck.com/blog/)

Authorization Response