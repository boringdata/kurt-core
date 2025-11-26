---
title: data-engineering-toolkit-infrastructure-devops
content_type: guide
source_url: https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops
indexed_at: '2025-11-25T19:58:20.248503'
content_hash: cceb8d86cfadfc64
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# The Data Engineer Toolkit: Infrastructure, DevOps, and Beyond

2025/07/03 - 16 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

Remember when data scientists spent 80% of their time wrestling with data wrangling instead of building models?

I'd argue that today's data engineers face similar challenges, but with the added complexity of infrastructure setup. We're architects of entire data ecosystems, orchestrating everything from real-time pipelines to AI workflows. The secret? Infrastructure as Code and DevOps principles that transform scattered server management into elegant, declarative configurations.

The catch is that while abstractions have made complex deployments more accessible, the toolkit has exploded in scope. One day, you're optimizing SQL queries, the next, you're debugging Kubernetes deployments, and by afternoon, you'll be explaining data quality metrics to stakeholders who just want to know why their dashboard is empty.

This is Part 2 of my in-depth exploration of the modern data engineer's toolkit. While [Part 1](https://motherduck.com/blog/data-engineering-toolkit-essential-tools/) covered the fundamentals of your development environment, programming languages, and core productivity tools, this essay addresses the more advanced technologies—such as data processing, infrastructure, data quality, and observability—required to transform data pipelines into production-grade data platforms.

We'll explore everything from SQL engines and workflow orchestration that form your daily toolkit to DevOps practices that make your deployments bulletproof, and the advanced utility tools that help you sleep better at night. Additionally, we'll explore the soft skills that can make the difference between a data engineer and a data engineering leader.

WARNING: Disclaimer
Not every tool link or tool here belongs in every data engineer's toolkit. Your domain, company size, and tech stack will heavily influence what matters most for you. This is a curated collection from years of working in the field, covering the wide range of what you might use at some point.

## Data Processing and Analytics

Continuing from the developer productivity and data engineering programming languages discussed in Part I, we have data processing and analytics technologies that are at the core of data engineering. SQL, relational databases, and BI tools are the bread and butter of everyday work, and Python is the glue language that ties everything together.

But most of the time, we must also set up a project that connects all the dots through orchestration, whether it's a simple cron job or Python script.

### SQL and Databases

SQL is the **language of data**. SQL is a **fundamental skill** for doing any data work. There's almost nothing you do without needing SQL. If you work with a REST API with no direct SQL interface, it's still beneficial to know, as the REST service will most certainly perform a SQL query against the database based on your REST request.

With that said, what SQL engines and databases do data engineers use?

The most common **relational databases** are also called [OLTP](https://en.wikipedia.org/wiki/Online_transaction_processing) databases:

- **[SQLite](https://github.com/sqlite/sqlite)**: A single-file database that is very handy for web development or when you need a database that can go with the code to avoid long latency for network or fetching and pushing data.
- **[Postgres](https://github.com/postgres/postgres)**: Perfect for any transactional and smallish data, but also scales up relatively high.
- **[MySQL](https://www.mysql.com/)** / **[MariaDB](https://github.com/MariaDB/server)**: Wide adoption before Postgres, good performance. MariaDB forked from MySQL around the Oracle acquisition of MySQL (acquired through the Sun purchase).

Analytical databases that speak SQL - also called [OLAP](https://en.wikipedia.org/wiki/Online_analytical_processing) \- are optimized for fast query responses:

- **[DuckDB](https://github.com/duckdb/duckdb)**: A single-file OLAP database, optimized for analytical queries.
- **[MotherDuck](https://motherduck.com/)**: Scaled out DuckDB in the cloud, DWH in minutes.
- **[ClickHouse](https://github.com/ClickHouse/ClickHouse)**: A fast analytical (OLAP) database.
- **[StarRocks](https://github.com/StarRocks/starrocks)**: A newer fast analytical database, focusing on making data-intensive real-time analytics easy.
- Cloud Data Warehouses: **Snowflake**, **BigQuery**, **Redshift**, **Azure Fabric**

Database utilities that help us with both:

- **[pg\_duckdb](https://github.com/duckdb/pg_duckdb)**: small library and plugin to make Postgres work with DuckDB, mainly extending Postgres with analytical features.
- **[JDBC](https://en.wikipedia.org/wiki/Java_Database_Connectivity)** / **[ODBC](https://en.wikipedia.org/wiki/Open_Database_Connectivity)** and newer versions **[Arrow-ADBC](https://github.com/apache/arrow-adbc)**.
- **[Apache Calcite](https://github.com/apache/calcite)**: SQL parser and query optimization framework

### Python Processing Tools

Python, on the other hand, is the ultimate toolkit language. Pulling data from a REST API or web, cleaning out some insufficient data, and storing it in Postgres. How would you do that in a safe, ordered fashion? Right, Python. It allows you to easily reach an API and automate tasks that Bash can't handle.

Besides the [generic Python libraries](https://motherduck.com/blog/data-engineering-toolkit-essential-tools#python-libraries) in Part 1, here are Python data processing libraries, potentially lesser-known, and suitable for advanced use-cases:

- **[Ibis](https://github.com/ibis-project/ibis)**: It provides a lightweight, universal interface for data wrangling, helping explore and transform data of any size, stored anywhere.
- **[Dask](https://github.com/dask/dask)**: A flexible library for parallel computing. Dask scales Python code from multi-core local machines to large distributed clusters in the cloud.
- **[ConnectorX](https://github.com/sfu-db/connector-x)**: The fastest library to load data from the database to DataFrames.
- **[Modal](https://modal.com/docs)**: A cloud function platform that lets you run any code remotely within seconds.
- **[reladiff](https://github.com/erezsh/reladiff)** (formerly [data-diff](https://github.com/datafold/data-diff) by Datafold): Tool to efficiently diff rows across databases
- **[Quokka](https://marsupialtail.github.io/quokka/)**: An open-source push-based vectorized query engine.
- **[Vaex](https://github.com/vaexio/vaex)**: High-performance library for lazy out-of-core DataFrames, to visualize and explore big tabular datasets.
- **[Xorq](https://github.com/xorq-labs/xorq)**: A declarative framework for building multi-engine computations.
- **[gspread](https://github.com/burnash/gspread)**: Work with Google Sheets through Python API, or [with DuckDB](https://duckdb.org/community_extensions/extensions/gsheets.html).

Want more? Check out the [Awesome Python List](https://github.com/vinta/awesome-python) with thousands of more frameworks, libraries, software, and resources.

### Workflow Orchestration Platforms

A key tool, often used within Python, are data orchestrators. These orchestrate the workflow of data processes in certain needed steps.

These are typically in Python, such as **[Apache Airflow](https://github.com/apache/airflow)**, **[Dagster](https://github.com/dagster-io/dagster)**, **[Prefect](https://github.com/PrefectHQ/prefect)**. But there are also others, such as **[Temporal](https://github.com/temporalio/temporal)**, **[Kestra](https://github.com/kestra-io/kestra)**, **[Mage](https://github.com/mage-ai/mage-ai)**, **[Argo Workflows](https://github.com/argoproj/argo-workflows)**, **[Flyte](https://github.com/flyteorg/flyte)**, and many more.

### Analytics and BI

Besides relational databases, SQL, and Python, in all cases, you want to present the data to your users or stakeholders. This is where BI tools, Notebooks, and data apps for visualization come into play.

There's [plenty out there](https://github.com/thenaturalist/awesome-business-intelligence), but here are the major ones and my favorites:

- **[Apache Superset](https://github.com/apache/superset)**: Original open-source BI tool.
- **[Rill](https://github.com/rilldata/rill)**: Open-source and BI-as-Code platform.
- **[PowerBI](https://www.microsoft.com/en-us/power-platform/products/power-bi)**: Microsoft's business intelligence platform.
- **[Omni](https://omni.co/)**: Business intelligence platform that helps companies explore data with a point-and-click UI, spreadsheets, AI, or SQL.
- **[Sigma Computing](https://www.sigmacomputing.com/)**: Next-generation analytics and business intelligence platform with SQL in a familiar spreadsheet interface.
- **[Lightdash](https://github.com/lightdash/lightdash)**: Instantly turn your dbt project into a full-stack BI platform.
- **[Tableau](https://www.tableau.com/business-intelligence)**: An Enterprise BI tool that has existed for a long time, with powerful ETL and other features.
- **[TARGIT](https://www.targit.com/)**: Enterprise BI solution specializing in industry-specific implementations in the Nordics.

Beyond BI tools, there are also notebooks:

- **[Jupyter Notebook](https://github.com/jupyter/notebook)** / **[Zeppelin](https://zeppelin.apache.org/)**, **[Marimo](https://github.com/marimo-team/marimo)**: Open-Source notebooks
- **[Hex](https://hex.tech/)**, **[Deepnote](https://deepnote.com/)**, **[MotherDuck Notebook](https://motherduck.com/docs/getting-started/interfaces/motherduck-quick-tour/)**: Closed-source
- More exotic ones: **[Count](https://count.co/)** (canva style), **[Quadratic](https://www.quadratichq.com/)** (spreadsheet style), **[Excel](https://www.notboring.co/p/excel-never-dies)** (mother of BI tools)

## DevOps and Infrastructure

Once you have a setup with integration, orchestration, and visualization, you usually need to scale it or deploy it to internal cloud servers or one of the major cloud providers. You typically use something more than plain Docker Compose or a quick [`uv init`](https://github.com/astral-sh/uv) for setting up all relevant Python settings. Usually, it involves Kubernetes, [Terraform](https://github.com/hashicorp/terraform), or Infrastructure as Code.

Either you pay for a service to do that for you, or if you have chosen a set of open-source tools, you mostly end up doing it yourself.

Popular frameworks, such as Terraform, Helm, and Ansible, as well as other scripts, can be deployed on any cloud. Typically, a Kubernetes cluster is used to deploy them. It's the de facto standard for cloud-agnostic deployment and works well for data engineering projects, as you declaratively define the state you'd like to have for your data platform. Kubernetes matches that and ramps the right amount of server, CPU, memory, etc., to make it runnable and scalable on any cloud.

Most of the time, it includes setting up an automated CI/CD pipeline that handles automated testing, deployment, version control, and all the software engineering best practices for data engineering.

### Infrastructure as Code, GitOps, and DataOps

DevOps has become a bigger part of data engineers' work in most scenarios in recent years, making deployment of every updated OSS tool straightforward, easy to test, and reproducible.

Making the data stack **modular** so that additional tools can be added with a clearly defined path for integration, such as metadata, logging at the same place, and security, so user permissions can be given to existing users without needing to re-create users every single time. This usually involves integration with [Keycloak](https://github.com/keycloak/keycloak), [Okta](https://www.okta.com/), or [Auth0](https://auth0.com/). A good example of such an integrated data stack is [HelloData](https://github.com/kanton-bern/hellodata-be), but there are more—see [declarative data stacks](https://sh.reddit.com/r/dataengineering/comments/1g50jwi/should_we_use_a_declarative_data_stack/).

But why would you invest all this energy and effort to have something run on Kubernetes? Besides the declarative approach mentioned, which is more robust than [imperative](https://www.ssp.sh/brain/imperative/) approaches that tend to break down more often, especially for large projects, Kubernetes has significant advantages. The DevOps-style deployment fosters a culture of collaboration and shared responsibility through configuration YAML files checked into a git repo, which is pivotal for how data teams can work with an efficient workflow and increase productivity.

TIP: Why YAML for DevOps: Descriptive configs
There are a few advantages to using YAML files. The changes become more structured as we have a **straightforward** interface for each fix, which makes them more **maintainable**. They are easy to read, modify, and incrementally test instead of loose SQL files that are very complex. They are easily portable between programming languages.

This way of working is called Infrastructure as Code, or [GitOps](https://kestra.io/blogs/2024-02-06-gitops), and is strongly related to [DataOps](https://en.wikipedia.org/wiki/DataOps). So, what are the toolkits for DevOps, you might ask?

**Container & Orchestration**:

- **[Kubernetes](https://kubernetes.io/)** (k8s): De facto standard for container orchestration that provides scalable, cloud-agnostic deployment with declarative infrastructure management.

  - **[Red Hat OpenShift](https://www.redhat.com/en/technologies/cloud-computing/openshift)**: Enterprise Kubernetes platform with integrated developer tools, security features, and multi-cloud capabilities.
  - **[kubectl](https://kubernetes.io/docs/reference/kubectl/)**: Command-line tool for managing Kubernetes clusters and debugging containerized data pipelines
  - **[Kustomize](https://github.com/kubernetes-sigs/kustomize/)**: Configuration management tool for Kubernetes that allows environment-specific customizations without template complexity
- **[Helm](https://helm.sh/)**: Package manager for Kubernetes that simplifies the deployment of complex data stack applications with reusable charts
- **[Docker](https://www.docker.com/)**: A containerization platform that ensures consistent environments across development, testing, and production for data engineering workloads

**Infrastructure as Code (IaC)**:

- **[Terraform](https://github.com/hashicorp/terraform)**: A multi-cloud infrastructure provisioning tool that enables versioned, reproducible cloud resource management for data platforms
- **[Pulumi](https://github.com/pulumi/pulumi)**: Modern IaC platform supporting multiple programming languages for infrastructure definition with strong typing and testing capabilities
- **[Ansible](https://www.ansible.com/)**: A configuration management and automation tool that handles server provisioning, application deployment, and system administration tasks
- **[Koreo](https://koreo.dev/)**: A new approach to Kubernetes configuration management and resource orchestration, empowering developers through programmable workflows and structured data

**GitOps & CD Tools**:

- **[ArgoCD](https://github.com/argoproj/argo-cd)**: Declarative GitOps continuous delivery tool for Kubernetes that automatically syncs cluster state with Git repositories
- **[Flux](https://github.com/fluxcd/flux2)**: GitOps toolkit for keeping Kubernetes clusters synchronized with Git repository configurations using pull-based deployment
- **[Octopus Deploy](https://octopus.com/)**: Advanced deployment automation platform for complex multi-environment releases with approval workflows

**CI/CD Platforms**:

- **[GitHub Actions](https://docs.github.com/en/actions)**: Native GitHub CI/CD platform with an extensive marketplace ecosystem for automated testing and deployment workflows
- **[GitLab CI/CD](https://docs.gitlab.com/ee/ci/)**: Integrated DevOps platform providing end-to-end automation from code to deployment with built-in security scanning
- **[Jenkins](https://www.jenkins.io/)**: Open-source automation server with controller/agent architecture ideal for complex, customizable build and deployment pipelines
- **[CircleCI](https://circleci.com/)**: Cloud-native CI/CD platform known for fast build times and Docker-first approach to testing data engineering workflows
- **[Bamboo](https://www.atlassian.com/software/bamboo)**: Atlassian's CI/CD tool with tight integration to Jira and Bitbucket for teams already using the Atlassian ecosystem

**Security & Secrets Management**:

- **[SOPS](https://github.com/getsops/sops)**: Encrypted secrets management tool that works with PGP/age keys to secure sensitive configuration data in Git repositories
- **[HashiCorp Vault](https://github.com/hashicorp/vault)**: A dynamic secrets management system for secure storage and access to tokens, passwords, and certificates

There's a lot more, but these are some of the first tools you will encounter if you start scaling out your data platform on Kubernetes and use modern DevOps practices to build a data engineering platform that is maintainable and scalable, ensuring reproducible deployments and efficient collaboration across development and operations teams.

WARNING: Setting up GitOps is hard and shouldn't be underestimated
Setting up GitOps for new data projects is hard and best done by having a central team specializing in deployment and operations with deep knowledge. These teams help you deploy a new data engineering tool in days rather than weeks. Data engineers and other personnel can then focus on their core workload.
TIP: TUIs for more efficiency (and fun!)
If you use git or Docker frequently, please check out [Lazygit](https://github.com/jesseduffield/lazygit), [Lazydocker](https://github.com/jesseduffield/lazydocker), and [k9s](https://github.com/derailed/k9s). These are TUIs that show you all commands within a single command. Instead of remembering or typing long commands, you can just use a graphical user interface in the terminal and navigate with the keyboard.

### DevOps Abstraction Levels

What are the alternatives to DevOps?

DevOps isn't binary; it's about selecting the appropriate level of control and abstraction for your specific needs. You're still practicing DevOps, whether you're managing Kubernetes clusters or deploying serverless functions; you're just operating at different levels of abstraction.

**Serverless and Managed Services** represent the highest abstraction level, where you focus purely on your data logic while the platform handles infrastructure concerns. Tools like AWS Lambda, Google Cloud Functions, and managed data warehouses let you deploy code and query data without worrying about servers, scaling, or maintenance. Your application remains portable, with core business logic that can typically be moved between providers, but you trade some customization for operational simplicity.

**Container-as-a-Service (CaaS)** platforms, such as Google Cloud Run, AWS Fargate, or Azure Container Instances, offer a middle ground. You containerize your applications (maintaining portability) but delegate orchestration complexity to the platform. You still get the benefits of DevOps practices—version control, automated deployments, Infrastructure as Code—without managing the underlying infrastructure.

**Managed Kubernetes** services, such as Google GKE, Azure AKS, and AWS EKS, provide another abstraction layer, offering full Kubernetes capabilities without requiring control plane management. This bridges the gap between complete infrastructure control and operational simplicity.

The key is matching your abstraction level to your team's expertise and requirements. Start with higher abstraction levels for faster delivery, then move toward more control only when specific customizations become necessary.

## Data Quality and Observability

As the data platform becomes more complex and features additional tools, it becomes increasingly sensible to have a data quality or observability stack—tools to have an automated overview of the **health of your data platform**.

Below are some of the standard tools (without getting too lengthy) that we haven't covered and were not mentioned in Part 1:

- **[ELK Stack](https://www.elastic.co/elastic-stack)**: Elasticsearch, Kibana, and Logstash. Reliably and securely take data from any source, in any format, then search, analyze, and visualize.
- **[Prometheus](https://github.com/prometheus/prometheus)**: Open-source monitoring system and time series database.
- **[DataDog + Metaplane](https://www.datadoghq.com/)**: Monitoring and security platform for developers, IT operations teams, and business users in the cloud age. DataDog recently acquired [Metaplane](https://www.metaplane.dev/), an end-to-end data observability platform that catches silent data quality issues before they impact your business.
- **[Datafold](https://www.datafold.com/data-quality-monitoring)**: Comprehensive data monitoring to prevent downtime and detect data quality issues early.
- **[Soda](https://www.soda.io/)**: Soda is a data quality testing solution, with parts of it [open-source](https://github.com/sodadata/soda-core), like data quality testing for the modern data stack (SQL, Spark, and Pandas).
- **[Monte Carlo](https://www.montecarlodata.com/)**: Enterprise-ready with extensive data lake integrations
- **[Bigeye](https://www.bigeye.com/)**: ML-driven automatic threshold tests and alerts

## AI-Enhanced Workflow Development

New AI-enhanced tools with LLMs or MCPs are being invented and are already useful today.

For example, for data engineers, there are dedicated IDEs or integrations into MCPs—especially **agentic workflows**:

- **[nao](https://getnao.io/)**: An AI-enhanced editor specifically for data engineers. In its early days, it understands dbt and can create and run pipelines.
- **[MCP server for DuckDB and MotherDuck](https://github.com/motherduckdb/mcp-server-motherduck)**: Makes your editor autonomously query the underlying database on the fly.
- **[Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview)**: An agentic coding tool that lives in your terminal, understands your codebase, and helps you code faster through natural language commands.
- **[dbt MCP](https://github.com/dbt-labs/dbt-mcp)**: A MCP server provides tools to interact with dbt autonomously, like running dbt build or docs, etc.
- **[Rill MCP Server](https://docs.rilldata.com/explore/mcp)**: Exposes Rill's most essential APIs to LLMs. It is currently designed primarily for data analysts.

Also, check out [Faster Data Pipeline Development with MCP and DuckDB](https://www.youtube.com/watch?v=yG1mv8ZRxcU&t=1s), which explains MCP in more detail and directly showcases some of the use cases.

INFO: Agentic Workflows vs. AI Agents
One word on the distinction between an agent and a workflow. Anthropic defines _Workflows_ as systems where Large Language Models and tools are orchestrated through predefined code paths. And _Agents_ are systems where LLMs dynamically direct their own processes and tool usage, maintaining control over how they accomplish tasks.

## Soft Skill: Communication, Business Requirements

As AI workflows reduce the need for coding, business acumen and soft skills become even more crucial. This section focuses on the human aspect of communication within the organization or among team members, and gathering the right **business requirements** before developing a platform or solution that may not be needed in the first place.

### Essential Soft Skills

Business **understanding** is crucial for practical data engineering. This means being genuinely interested in business nuances, actively listening to domain experts, and developing strong **communication** skills for requirements engineering, which significantly overlaps with traditional BI engineering roles.

Cross-functional **collaboration** is equally important. Data engineers must translate technical constraints and possibilities into business terms for stakeholders, while also understanding their pain points and priorities. This includes stakeholder management, **documentation skills**, and the ability to ask the right questions to uncover hidden requirements and assumptions.

While you can be a technical expert without these skills, combining technical expertise with strong business understanding and communication will set you apart. It helps you solve real business problems and deliver measurable value—something we should always keep in mind.

## Building Your Data Engineering Toolkit

Wrapping up these two articles on the in-depth toolkit for data engineers, I hope you've learned a tool or two that will improve your workflow as a data engineer or in the data field.

Hopefully, you won't be overwhelmed by all the links. Again, it's not meant to be a toolkit for everyone, but instead provides pointers for the direction you'd like to explore when starting or when you want to venture into a slightly different area of data engineering.

We've gone from fundamental to advanced DevOps skills and learned along the way:

- Developer tools and programming languages in Part 1 and the sophisticated ecosystem of modern data engineering in Part 2.
- SQL databases and Python as your foundational toolkit, with analytics and BI platforms for presenting insights.
- DevOps and Infrastructure as Code for scalable deployments with Kubernetes.
- Data quality and observability solutions for maintaining platform health.
- Emerging AI-enhanced workflows that are reshaping how we build data pipelines.
- Technical expertise alone isn't always enough; strong communication skills and business understanding transform data engineers into 10x contributors, delivering real value to the business.

If you want to learn more tips and tricks about the toolset, please follow the [MotherDuck newsletter](https://motherduck.com/duckdb-news/) for the latest news about DuckDB, which usually contains great insights and tools for working with data through DuckDB or MotherDuck. You can also [try MotherDuck](https://app.motherduck.com/), which allows you to handle many data use cases in a notebook environment with many of the tools mentioned in these articles.

If you have a toolkit you use every day as a data engineer or a unique tool that cannot be found in the two parts, please let me know on social media in the comments. I'd be happy to know what you use as your core toolkit for everyday work.

### TABLE OF CONTENTS

[Data Processing and Analytics](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/#data-processing-and-analytics)

[DevOps and Infrastructure](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/#devops-and-infrastructure)

[Data Quality and Observability](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/#data-quality-and-observability)

[AI-Enhanced Workflow Development](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/#ai-enhanced-workflow-development)

[Soft Skill: Communication, Business Requirements](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/#soft-skill-communication-business-requirements)

[Building Your Data Engineering Toolkit](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/#building-your-data-engineering-toolkit)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![I Made Cursor + AI Write Perfect SQL. Here's the Exact Setup](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fvibe_coding_0d05fa9c9f.png&w=3840&q=75)](https://motherduck.com/blog/vibe-coding-sql-cursor/)

[2025/06/27 - Jacob Matson](https://motherduck.com/blog/vibe-coding-sql-cursor/)

### [I Made Cursor + AI Write Perfect SQL. Here's the Exact Setup](https://motherduck.com/blog/vibe-coding-sql-cursor)

Stop debugging AI-generated SQL queries. Learn the exact Cursor + MotherDuck setup that makes AI write working SQL on the first try, with step-by-step instructions.

[![MotherDuck Managed DuckLakes Now in Preview: Scale to Petabytes](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFully_Managed_30cac547cd.png&w=3840&q=75)](https://motherduck.com/blog/announcing-ducklake-support-motherduck-preview/)

[2025/07/01 - Ryan Boyd](https://motherduck.com/blog/announcing-ducklake-support-motherduck-preview/)

### [MotherDuck Managed DuckLakes Now in Preview: Scale to Petabytes](https://motherduck.com/blog/announcing-ducklake-support-motherduck-preview)

Preview support of MotherDuck includes both fully-managed DuckLake support and ability to bring your own bucket. Combined with MotherDuck's storage, you get both high-speed access to recent data and support for massive scale historical data.

[View all](https://motherduck.com/blog/)

Authorization Response