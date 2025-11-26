---
title: app-developers
content_type: event
source_url: https://motherduck.com/product/app-developers/
indexed_at: '2025-11-25T20:15:51.011701'
content_hash: 162dc900f9969538
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# Build insanely interactive data apps

Zero latency, in-browser analytics on DuckDB in the cloud

[Get Started](https://app.motherduck.com/?auth_flow=signup)

LEARN MORE

![YouTube video preview](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fproduct-hero-data-apps-thumbnail.4d35d885.jpg&w=3840&q=75)

Why MotherDuckWhy MotherDuckWhy MotherDuckWhy MotherDuckWhy MotherDuckWhy MotherDuckWhy MotherDuckWhy MotherDuckWhy MotherDuckWhy MotherDuckWhy MotherDuckWhy MotherDuckWhy MotherDuck

## Ultra-fast analytics

We already do everything in the browser. Why not analytics? The bar for in-app analytics experiences has never been higher! Data-driven decision making is essential, and high-latency, static dashboards don’t meet user needs.

Using the power of DuckDB, MotherDuck helps developers build warp speed, responsive data experiences that run in the browser and the cloud.

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fzero-latency-between-users-and-their-data.caf2edd1.png&w=3840&q=75)

### Zero latency between users and the data

Analytics should be faster than a display refresh cycle. Think about it: would you use an app that had a 10-second lag? Didn’t think so. Thanks to its [dual execution query engine](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/), MotherDuck reclaims unused compute on users’ local machines to seamlessly deliver the performance they expect. Building remarkable analytics experiences that delight users and scale smoothly without ruffling any feathers…now that’s something to quack about.

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fnovel-1.5-tier-architecture.9172989e.png&w=3840&q=75)

### Novel 1.5-tier architecture powered by WebAssembly (Wasm)

Traditional applications are built on a 3-tier architecture, which requires several intermediary operations to run between the end user interface, server, and underlying database. MotherDuck’s [1.5-tier architecture](https://motherduck.com/product/app-developers/#architecture) has the same DuckDB engine running inside the user’s web browser and in the cloud. Developers can finally move data closer to the user to create analytics experiences that run at a supercharged pace.

Our [peer-reviewed paper](https://motherduck.com/blog/cidr-paper-hybrid-query-processing-motherduck/) on 1.5-tier architecture and dual engine, hybrid query execution was presented at CIDR: The Conference on Innovative Data Systems Research.

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fsticky-ultra-fast-analytics.cca090c0.png&w=1920&q=75)

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fsticky-ultra-fast-analytics.cca090c0.png&w=1920&q=75)

## Build on a true analytics database

MotherDuck is purpose-built and architected for data applications to handle high-concurrency and low-latency workloads.

Many data app developers start by building analytics on top of a transactional database before hitting performance limitations. When they move to a traditional data warehouse, they then run into latency and cost concerns. Haven’t you done enough? Let us do the heavy lifting when you start building your next app.

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fditch-the-scaling-limitations-of-postgres.4635cecf.png&w=3840&q=75)

### Ditch the scaling limitations of Postgres

PostgreSQL is the default transactional database used by millions of developers. It excels at this core functionality, but it is not designed for analytics. As applications expand their analytics capabilities, they require a database, like DuckDB, designed and optimized for these workloads.

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fuse-the-best-sql-dialect-for-analytics.44d7b08b.png&w=3840&q=75)

### Use the best SQL dialect for analytics

MotherDuck leverages DuckDB’s pragmatic, friendly approach to SQL. This enables a more intuitive developer workflow, as DuckDB extends a Postgres style of SQL with syntax from other databases. For additional flexibility, DuckDB also has a dataframe-style API if SQL isn’t your fancy.

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fsticky-true-analytics-db.b30f9c80.png&w=1920&q=75)

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fsticky-true-analytics-db.b30f9c80.png&w=1920&q=75)

## Won’t break the bank

DuckDB is an analytics database built from the ground up with columnar vectorized execution. It uses CPU and memory more efficiently for analytics than any transactional database.

MotherDuck extends DuckDB to enable data app developers to push workloads down to the client. Together, these techniques prevent flyaway cloud costs and let us pass the resulting savings on to you.

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fefficient-but-not-lightweight.96773547.png&w=3840&q=75)

### Efficiency of DuckDB

DuckDB is designed for analytical workloads where low latency query performance is crucial. With MotherDuck, DuckDB’s small footprint delivers remarkable efficiency without the need for complex infrastructure or configuration. Data is stored in a columnar format that streamlines analytical queries by reducing the data read from storage and into memory.

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fmanage-compute-predictably-per-user.b9d2b210.png&w=3840&q=75)

### Manage compute predictably per-user

MotherDuck’s unique per-user tenancy model provides each user of your app with access to their own isolated compute instance “duckling,” a database engine in the cloud. Instead of forcing your users to share a monolith with others, they are free to enjoy your application’s low-latency, interactive experience, no matter how many people are using it simultaneously.

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fpush-work-down-to-the-client.0a165825.png&w=3840&q=75)

### Push work down to the client

MotherDuck extends DuckDB’s portability to turn end users’ laptops into local execution nodes. Workloads can be pushed to the client or kept on the server (or both). Running DuckDB locally in the web browser with the MotherDuck Wasm SDK lets you push data and processing down to otherwise-unused hardware to achieve ultra low latency.

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fsticky-wont-break-the-bank.64c63f2c.png&w=1920&q=75)

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fsticky-wont-break-the-bank.64c63f2c.png&w=1920&q=75)

## Features

[![Cloud database storage feature](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Ffeature-cloud.3e9c0a0a.png&w=640&q=75)\\
**Cloud database storage** \\
Manage your DuckDB database catalog in the cloud for easy scaling and collaboration.\\
\\
More Details](https://motherduck.com/product/app-developers/cloud-database-storage/)

[![SQL analytics engine feature](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Ffeature-analytics.f04308e0.png&w=640&q=75)\\
**SQL analytics engine** \\
Efficiently run the same SQL queries on data stored locally, in MotherDuck or in your data lake.\\
\\
More Details](https://motherduck.com/product/app-developers/sql-analytics-engine/)

[![WebAssembly (WASM) SDK feature](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Ffeature-web.44e7f69f.png&w=1920&q=75)\\
**WebAssembly (WASM) SDK** \\
Create fast data experiences by running DuckDB in the end user’s web browser with access to data hosted in the cloud.\\
\\
More Details](https://motherduck.com/product/app-developers/webassembly-wasm-sdk/)

[![Dual query execution feature](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Ffeature-query.28419698.png&w=640&q=75)\\
**Dual query execution** \\
Use idle compute on your laptop in concert with the cloud to increase speed and lower cost.\\
\\
More Details](https://motherduck.com/product/app-developers/dual-query-execution/)

[![Notebook-like UI feature](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Ffeature-ui.c08b01e4.png&w=1080&q=75)\\
**Notebook-like UI** \\
Use the web to browse the data catalog, write SQL, filter and sort results and share data.\\
\\
More Details](https://motherduck.com/product/app-developers/notebook-like-ui/)

[![Strong DuckDB ecosystem feature](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Ffeature-ecosystem.0ab95f7c.png&w=640&q=75)\\
**Strong DuckDB ecosystem** \\
Use with 25+ tools in the modern data stack for import, orchestration and business intelligence.\\
\\
More Details](https://motherduck.com/product/app-developers/strong-duckdb-ecosystem/)

## Architecture

Managed DuckDB-in-the-cloud

Since DuckDB is highly portable, it can run anywhere, including in the cloud. Using WebAssembly, you can even run DuckDB in the browser. At MotherDuck, we can help your web application adopt a 1.5-tier architecture that offers the best of both modes.

#### MotherDuck Signature

### WASM-Powered 1.5-tier architecture

Want to build an application that’s pure frontend JavaScript, with no backend to worry about? While DuckDB can run anywhere, including in the browser, MotherDuck’s Wasm SDK enables you to extend the speed of a local SQL engine to data persisted in the cloud.

Using Wasm, client-side JavaScript processes data locally to enable analytics experiences that are faster than you can blink!

### Basic 2-Tier architecture

While a 2-tier architecture allows client-side applications to connect directly to the database, developer maintenance and overhead are only incrementally better...and you still don’t have the option to run your database locally.

### Traditional 3-tier architecture

A 3-tier architecture powers the vast majority of applications today. While it feels familiar, managing integrations and updates between the client, server, and database is time-consuming and unwieldy. For users, multiple steps between them and the data may slow down performance and speed at scale.

## Ducking simple cloud data warehouse pricing

Blazing fast analytics without flyaway costs

[Learn more](https://motherduck.com/product/pricing/)

## Ecosystem

Modern Duck Stack

### CLOUD DATA WAREHOUSE

### Sources

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fpostgres-sql.d737f4f5.png&w=750&q=75)

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Famazon-s3.72386dfc.png&w=640&q=75)

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fsalesforce.35d52b31.png&w=384&q=75)

![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fstripe.2160e881.png&w=384&q=75)

[**Business Intelligence**\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Ftableau.0ec523e2.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fpower-bi.f3563826.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fomni.cb7aa381.png&w=384&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fmetabase.5f8fe44e.png&w=640&q=75)\\
\\
MORE INFO](https://motherduck.com/ecosystem/?category=Business+Intelligence) [**Ingestion**\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Ffivetran.26f3817d.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fairbyte.8371d2f0.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Festuary.babad369.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fdlthub.e9892b97.png&w=384&q=75)\\
\\
MORE INFO](https://motherduck.com/ecosystem/?category=Ingestion) [**Data Science & AI**\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fhex.275dad7d.png&w=256&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fjupyter.2a6af3de.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fcolab.30ab10af.png&w=384&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fmarimo.b699c73d.png&w=640&q=75)\\
\\
MORE INFO](https://motherduck.com/ecosystem/?category=Data+Science+%26+AI) [**Reverse ETL**\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fcensus.352f1d69.png&w=640&q=75)\\
\\
MORE INFO](https://motherduck.com/ecosystem/?category=Reverse+ETL) [**Transformation**\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fdbt.fd2184d1.png&w=384&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Ftobiko.d0e3d1e5.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fsql-mesh.6fceb012.png&w=640&q=75)\\
\\
MORE INFO](https://motherduck.com/ecosystem/?category=Transformation) [**Dev Tools**\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fdatagrip.f48eba23.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fpuppy-graph.848400c6.png&w=750&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fdagster.e1970a7c.png&w=640&q=75)\\
\\
MORE INFO](https://motherduck.com/ecosystem/?category=Dev+Tools)

[**Orchestration**\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fairflow.7f70081a.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fdagster.e1970a7c.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fprefect.fd6371b3.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fkestra.aa10acfc.png&w=640&q=75)\\
\\
MORE INFO](https://motherduck.com/ecosystem/?category=Orchestration)

[**Data Quality**\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fmonte-carlo.2143f962.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fsecoda.9b7e86fb.png&w=640&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fsoda.59e5aa02.png&w=384&q=75)\\
\\
![](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fgreat-expectations.c544f1ef.png&w=640&q=75)\\
\\
MORE INFO](https://motherduck.com/ecosystem/?category=Data+Quality)

## Case Studies

With MotherDuck, it only took an hour to get an app up and running, which was pretty cool. It uses 18 million rows of data, but once it’s loaded, we have all this interactivity right on the website. And since it's all coming from MotherDuck, we can create a shareable snapshot of our data that others can attach to and query.

[READ MORE](https://motherduck.com/case-studies/dominik-moritz/)

![Dominik Moritz's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdominik_berlin_f8a31170af.jpg&w=3840&q=75)

Dominik Moritz

Professor at Carnegie Mellon University

With MotherDuck, it only took an hour to get an app up and running, which was pretty cool. It uses 18 million rows of data, but once it’s loaded, we have all this interactivity right on the website. And since it's all coming from MotherDuck, we can create a shareable snapshot of our data that others can attach to and query.

[READ MORE](https://motherduck.com/case-studies/dominik-moritz/)

We can create an instance per customer easily as opposed to Postgres, where it’s a hassle to create and manage that many instances. We've now got these new levers for performance scaling because we can split and store the data and query efficiently as needed. If we need to handle a load spike or a huge amount of queries, we can spin up more ducklings on demand.

[READ MORE](https://motherduck.com/case-studies/dexibit/)

![Ravi Chandra's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fravi_chandra_photo_7db3a4c457.jpg&w=3840&q=75)

Ravi Chandra

CTO at Dexibit

We can create an instance per customer easily as opposed to Postgres, where it’s a hassle to create and manage that many instances. We've now got these new levers for performance scaling because we can split and store the data and query efficiently as needed. If we need to handle a load spike or a huge amount of queries, we can spin up more ducklings on demand.

[READ MORE](https://motherduck.com/case-studies/dexibit/)

Our data pipelines used to take eight hours. Now they're taking eight minutes, and I see a world where they take eight seconds. This is why we made the big bet on DuckDB and MotherDuck. It's only possible with DuckDB and MotherDuck.

[READ MORE](https://motherduck.com/case-studies/finqore/)

![Jim O’Neill's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fjim_oneil_photo_930c637f49.jpg&w=3840&q=75)

Jim O’Neill

Co-founder and CTO at FinQore

Our data pipelines used to take eight hours. Now they're taking eight minutes, and I see a world where they take eight seconds. This is why we made the big bet on DuckDB and MotherDuck. It's only possible with DuckDB and MotherDuck.

[READ MORE](https://motherduck.com/case-studies/finqore/)

MotherDuck’s innovative approach to managing data and providing easy-to-use tooling has allowed us to expand our application use cases (e.g., getting data into the client's browser) and offer more value to our customers.

[READ MORE](https://motherduck.com/case-studies/dexibit/)

![Ravi Chandra's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fravi_chandra_photo_7db3a4c457.jpg&w=3840&q=75)

Ravi Chandra

CTO at Dexibit

MotherDuck’s innovative approach to managing data and providing easy-to-use tooling has allowed us to expand our application use cases (e.g., getting data into the client's browser) and offer more value to our customers.

[READ MORE](https://motherduck.com/case-studies/dexibit/)

With MotherDuck, it only took an hour to get an app up and running, which was pretty cool. It uses 18 million rows of data, but once it’s loaded, we have all this interactivity right on the website. And since it's all coming from MotherDuck, we can create a shareable snapshot of our data that others can attach to and query.

[READ MORE](https://motherduck.com/case-studies/dominik-moritz/)

![Dominik Moritz's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdominik_berlin_f8a31170af.jpg&w=3840&q=75)

Dominik Moritz

Professor at Carnegie Mellon University

With MotherDuck, it only took an hour to get an app up and running, which was pretty cool. It uses 18 million rows of data, but once it’s loaded, we have all this interactivity right on the website. And since it's all coming from MotherDuck, we can create a shareable snapshot of our data that others can attach to and query.

[READ MORE](https://motherduck.com/case-studies/dominik-moritz/)

We can create an instance per customer easily as opposed to Postgres, where it’s a hassle to create and manage that many instances. We've now got these new levers for performance scaling because we can split and store the data and query efficiently as needed. If we need to handle a load spike or a huge amount of queries, we can spin up more ducklings on demand.

[READ MORE](https://motherduck.com/case-studies/dexibit/)

![Ravi Chandra's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fravi_chandra_photo_7db3a4c457.jpg&w=3840&q=75)

Ravi Chandra

CTO at Dexibit

We can create an instance per customer easily as opposed to Postgres, where it’s a hassle to create and manage that many instances. We've now got these new levers for performance scaling because we can split and store the data and query efficiently as needed. If we need to handle a load spike or a huge amount of queries, we can spin up more ducklings on demand.

[READ MORE](https://motherduck.com/case-studies/dexibit/)

Our data pipelines used to take eight hours. Now they're taking eight minutes, and I see a world where they take eight seconds. This is why we made the big bet on DuckDB and MotherDuck. It's only possible with DuckDB and MotherDuck.

[READ MORE](https://motherduck.com/case-studies/finqore/)

![Jim O’Neill's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fjim_oneil_photo_930c637f49.jpg&w=3840&q=75)

Jim O’Neill

Co-founder and CTO at FinQore

Our data pipelines used to take eight hours. Now they're taking eight minutes, and I see a world where they take eight seconds. This is why we made the big bet on DuckDB and MotherDuck. It's only possible with DuckDB and MotherDuck.

[READ MORE](https://motherduck.com/case-studies/finqore/)

MotherDuck’s innovative approach to managing data and providing easy-to-use tooling has allowed us to expand our application use cases (e.g., getting data into the client's browser) and offer more value to our customers.

[READ MORE](https://motherduck.com/case-studies/dexibit/)

![Ravi Chandra's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fravi_chandra_photo_7db3a4c457.jpg&w=3840&q=75)

Ravi Chandra

CTO at Dexibit

MotherDuck’s innovative approach to managing data and providing easy-to-use tooling has allowed us to expand our application use cases (e.g., getting data into the client's browser) and offer more value to our customers.

[READ MORE](https://motherduck.com/case-studies/dexibit/)

With MotherDuck, it only took an hour to get an app up and running, which was pretty cool. It uses 18 million rows of data, but once it’s loaded, we have all this interactivity right on the website. And since it's all coming from MotherDuck, we can create a shareable snapshot of our data that others can attach to and query.

[READ MORE](https://motherduck.com/case-studies/dominik-moritz/)

![Dominik Moritz's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdominik_berlin_f8a31170af.jpg&w=3840&q=75)

Dominik Moritz

Professor at Carnegie Mellon University

With MotherDuck, it only took an hour to get an app up and running, which was pretty cool. It uses 18 million rows of data, but once it’s loaded, we have all this interactivity right on the website. And since it's all coming from MotherDuck, we can create a shareable snapshot of our data that others can attach to and query.

[READ MORE](https://motherduck.com/case-studies/dominik-moritz/)

We can create an instance per customer easily as opposed to Postgres, where it’s a hassle to create and manage that many instances. We've now got these new levers for performance scaling because we can split and store the data and query efficiently as needed. If we need to handle a load spike or a huge amount of queries, we can spin up more ducklings on demand.

[READ MORE](https://motherduck.com/case-studies/dexibit/)

![Ravi Chandra's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fravi_chandra_photo_7db3a4c457.jpg&w=3840&q=75)

Ravi Chandra

CTO at Dexibit

We can create an instance per customer easily as opposed to Postgres, where it’s a hassle to create and manage that many instances. We've now got these new levers for performance scaling because we can split and store the data and query efficiently as needed. If we need to handle a load spike or a huge amount of queries, we can spin up more ducklings on demand.

[READ MORE](https://motherduck.com/case-studies/dexibit/)

Authorization Response