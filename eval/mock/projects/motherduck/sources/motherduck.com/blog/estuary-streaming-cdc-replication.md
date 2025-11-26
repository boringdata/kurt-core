---
title: estuary-streaming-cdc-replication
content_type: guide
source_url: https://motherduck.com/blog/estuary-streaming-cdc-replication
indexed_at: '2025-11-25T19:56:45.634717'
content_hash: b71c8a855281f100
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# DuckDB, MotherDuck, and Estuary: A Match Made for Your Analytics Architecture

2025/03/06 - 9 min read

BY

[Daniel Palma](https://motherduck.com/authors/Daniel%20Palma/)
,
[Emily Lucek](https://motherduck.com/authors/Emily%20Lucek/)

The data architecture field can seem littered with products for all stages of the data lifecycle. This can make it tempting to put off implementing some of the more esoteric aspects of architecture. But one aspect you don’t want to wait on is choosing a solid analytics database.

Compared to a write-optimized transaction processing database (the kind that backs your application to keep things like online ordering quick and scalable), read-optimized analytical processing databases are designed specifically to perform intensive queries. Analytics databases can aggregate and join large tables with ease. And even if you’re not working with massive datasets (yet), it’s always good practice to separate your application database from your analytics database so queries don’t impact your production environment.

One great option for an analytics database is DuckDB. Whether you’re ready to get your feet wet with an analytics database or an old salt hoping to optimize and improve your analytics experience, integrating DuckDB into your data architecture can be a simple process when using MotherDuck and Estuary.

So, let’s take a closer look at each of these components and how they all fit together.

## DuckDB

There are lots of options if you’re searching for an analytics database, even if the space isn’t quite as cluttered as that of transaction processing databases. So, what makes [DuckDB](https://duckdb.org/) stand out? Here are some of its top features.

**Open Source**

The best things in life are open source. Open source projects are easily accessible, allow contributions from a diverse range of collaborators, and let experts evaluate products on best practices, like security. Remixing and expanding on a project’s freely-available underlying code can lead to industry-wide innovation, or simply let you tune a part of your architecture to your exact specifications.

**Embedded Analytics**

DuckDB is an embedded analytics database, so it can run within a host process, similar to SQLite. Or you can run it as a single binary. This flexibility makes it easy to implement DuckDB wherever you need it.

**Fast and Efficient**

It’s not a huge surprise that an analytics database like DuckDB would implement a columnar engine instead of a row-based write-optimized format. DuckDB takes this another step by supporting parallel and vectorized execution, speeding up intensive queries even further. When data is vectorized, a batch of values can be processed in one operation, reducing overhead.

**Portable and Extensible**

DuckDB runs on all major operating systems with drivers offered in a swath of popular programming languages. With a small, no-dependency footprint, you can deploy it directly to IoT or other resource-constrained devices. That’s not to say that DuckDB is limited; extensions provide support for additional functionality, such as file formats for geospatial data or connectivity with data sources like S3.

## MotherDuck

Once you’ve decided that DuckDB is the right analytics database for your use case, there’s still the matter of maintenance. You can, of course, deploy, scale, and upgrade your own instance of DuckDB. Or you can go with a serverless cloud offering.

[MotherDuck](https://motherduck.com/) is a cloud data warehouse that makes it easy to manage DuckDB instances in the cloud. It also provides features to collaborate with your team, securely save secrets, and intelligently query your data.

Not to mention its accessibility for various connections. Data pipeline platforms like Estuary can integrate directly with MotherDuck-hosted databases, so you can easily wire DuckDB into the rest of your data architecture.

## Estuary

To perform analytics, you first need to transfer your data from your source systems, whether that’s your own transaction database, external APIs, or streaming data. Instead of reinventing the wheel by writing custom integration code (and maintaining that code when source systems change), data pipeline platforms simplify the task of keeping your data connected.

[Estuary](https://estuary.dev/) can handle all kinds of integrations, whether you need real-time sub-second latency or batch analytics and reporting. Using Estuary Flow, you can transfer data from a wide selection of source systems to your MotherDuck instance, aggregating and transforming data along the way as needed. And if those source systems change, intelligent schema evolution keeps your pipeline running.

Estuary leverages [CDC](https://estuary.dev/blog/the-complete-introduction-to-change-data-capture-cdc/), or Change Data Capture, where possible to swiftly materialize reliable, accurate updates when source data changes. CDC lets you track incremental changes as they occur rather than loading data in batches, which would potentially require extra deduplication work and extraneous data transfer costs. It keeps latency low and ensures all update and delete events are preserved, since changes are read directly from the WAL (Write-Ahead Log) or other logs rather than simply capturing the current state of a database.

A simple view of the Estuary architecture is shown below:
![simple-estuary-architecture-with-motherduck.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsimple_estuary_architecture_with_motherduck_2d35470a21.png&w=3840&q=75)

Other reasons to love Estuary include:

- Low- and no-code pipelines that make it easy to set up in minutes.
- Rigorous security standards and compliance with industry data practices.
- Low, intuitive pricing for budget-friendly data transfer.
- Flexible deployment options, using public, private, or Bring-Your-Own-Cloud.

## Set Up a MotherDuck Connector in Estuary

Instead of just talking about it, let’s try out a demo. We’ll cover how to actually wire up your source systems and MotherDuck with Estuary.

### Prerequisites

- A [MotherDuck account](https://app.motherduck.com/?auth_flow=signup)
- An [Estuary account](https://dashboard.estuary.dev/register)
- An [AWS account](https://aws.amazon.com/) (we’ll get to why in just a moment)

Free plans and trials are available for all resources.

### Step 1: Set Up AWS Resources

First off: Estuary and MotherDuck make sense as prerequisites if we’re wiring the two together, but why is Amazon Web Services on the list?

For Estuary’s MotherDuck connector, Estuary uses an Amazon S3 bucket to stage data loads, acting as temporary file storage. The S3 bucket will basically be an intermediary step between Estuary and MotherDuck, making use of DuckDB’s S3 extension.

To create an S3 bucket in AWS:

1. Search for and select the “S3” service in your AWS console.
2. Click **Create bucket**.
3. Provide a unique name and update any other settings as desired before clicking **Create bucket**.
4. Make sure to note your bucket name and region.

Both Estuary and MotherDuck will need to access this bucket. You can create an IAM user with S3 permissions and then share the user’s credentials with both systems. To do so:

01. Search for and select the “IAM” service in your AWS console.
02. Select **User groups** from the sidebar menu under the “Access Management” section.
03. Click **Create group**.
04. Provide a group name and tick the **AmazonS3FullAccess** permission to attach it to the group.
05. Click **Create user group**.
06. Select **Users** from the sidebar menu and click **Create user**.
07. Provide a name and click **Next**.
08. Select the user group you created to provide the permission user scheme and click **Next**.
09. Click **Create user**.
10. Select your newly-created user from the list to see the details page.
11. Select the **Security credentials** tab.
12. Click **Create access key** in the “Access keys” section.
13. Select a use case and click **Next**.
14. Copy the **Access key** and **Secret access key** values and store them in a safe place.

### Step 2: Configure MotherDuck

In MotherDuck, we’ll set up access to the S3 bucket and then make sure that Estuary can access MotherDuck in turn.

To provide S3 credentials, you can either run a SQL query or set up access in the UI. For the SQL method, fill out the correct information in the following query and run it from your MotherDuck dashboard:

```sql
Copy code

CREATE OR REPLACE SECRET IN MOTHERDUCK (
	TYPE S3,
	KEY_ID '<AWS-Key-ID>',
	SECRET '<AWS-Secret-Key>',
	REGION '<AWS-S3-region>'
);
```

To create a MotherDuck access token for Estuary to use:

1. Select **Settings** from the account dropdown.
2. Select **Access Tokens** from the sidebar menu under the “Integrations” section.
3. Click **Create token**.
4. Provide a name and create the token.
5. Make sure to copy the access token before closing the modal.

Choose an existing database in MotherDuck that you want to materialize into or create a new one. Note its name. We’ll then have all the information we need to wire everything up in Estuary.

### Step 3: Create the Connector in Estuary

Since MotherDuck is a destination connector in Estuary, you’ll first need some source data. While this guide focuses specifically on the MotherDuck connector, you can see how to [set up a capture connector here](https://docs.estuary.dev/guides/create-dataflow/#create-a-capture).

Once you have some source data, set up the MotherDuck connector:

1. In the Estuary dashboard, navigate to the **Destinations** tab.
2. Click **New Materialization**.
3. Search for and select the “MotherDuck” connector.
4. Provide a name for your materialization.
5. Fill out the **Endpoint Config**.

   - **MotherDuck Service Token:** the access token you created in MotherDuck
   - **Database:** your MotherDuck database name
   - **Database Schema:** schema for bound collection tables; defaults to “main”
   - **S3 Staging Bucket:** the name of your AWS bucket
   - **Access Key ID:** the key ID of the AWS IAM user’s access key
   - **Secret Access Key:** the secret value of the AWS IAM user’s access key
   - **S3 Bucket Region:** AWS region where your bucket lives, such as “us-east-1”

![image2.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage2_8c8f8e1d4a.png&w=3840&q=75)

6. Select source data using either **Source from Capture** or adding individual collections.
7. Click **Next**, then **Save and Publish**.

Estuary will start streaming your source data into your MotherDuck database.

## Exploring Your Data in MotherDuck

MotherDuck makes it easy to explore your data, analyze it, and collect your queries in Notebooks. Here are some ways that DuckDB and MotherDuck make working with SQL more fun.

DuckDB offers streamlined syntax, such as FROM-first syntax when you’re selecting all columns.

![image1.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_50149b8388.png&w=3840&q=75)

If you need to read data from individual files for a one-off project where it wouldn’t make sense to set up a whole, continuous pipeline, there are multiple options to read directly from a file using functions like \`read\_csv\` and \`read\_parquet\`.

And if you make a mistake, don’t sweat it. MotherDuck provides a FixIt feature that catches and suggests fixes for common SQL errors so you’re not stuck hunting for a missing comma or misspelled column name.

![image6.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage6_dda11e4b7c.png&w=3840&q=75)

Explore additional options in the [MotherDuck docs](https://motherduck.com/docs/getting-started/).

## Next Steps

Once you have the basics down, unlock additional features by checking out Estuary’s and MotherDuck’s resources. At Estuary, discover all the [data sources](https://docs.estuary.dev/reference/Connectors/capture-connectors/) you can load into MotherDuck and how to perform transformations on your data between systems. At MotherDuck, learn how to [build apps](https://motherduck.com/docs/key-tasks/data-apps/) to visualize your data and manage organizations to collaborate with your team.

And, of course, we’d love to hear from you. Join [MotherDuck](https://slack.motherduck.com/) and [Estuary](https://go.estuary.dev/slack) in Slack. We’re excited to hear about your data journey.

### TABLE OF CONTENTS

[DuckDB](https://motherduck.com/blog/estuary-streaming-cdc-replication/#duckdb)

[MotherDuck](https://motherduck.com/blog/estuary-streaming-cdc-replication/#motherduck)

[Estuary](https://motherduck.com/blog/estuary-streaming-cdc-replication/#estuary)

[Set Up a MotherDuck Connector in Estuary](https://motherduck.com/blog/estuary-streaming-cdc-replication/#set-up-a-motherduck-connector-in-estuary)

[Exploring Your Data in MotherDuck](https://motherduck.com/blog/estuary-streaming-cdc-replication/#exploring-your-data-in-motherduck)

[Next Steps](https://motherduck.com/blog/estuary-streaming-cdc-replication/#next-steps)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Faster health data analysis with MotherDuck & Preswald](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fstructured_preswald_521f8cd689.png&w=3840&q=75)](https://motherduck.com/blog/preswald-health-data-analysis/)

[2025/02/14 - Amrutha Gujjar](https://motherduck.com/blog/preswald-health-data-analysis/)

### [Faster health data analysis with MotherDuck & Preswald](https://motherduck.com/blog/preswald-health-data-analysis)

Faster health data analysis with MotherDuck & Preswald

[![Effortless ETL for Unstructured Data with MotherDuck and Unstructured.io](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FUnstructured_io_connector_d2dc34c093.png&w=3840&q=75)](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck/)

[2025/02/20 - Adithya Krishnan](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck/)

### [Effortless ETL for Unstructured Data with MotherDuck and Unstructured.io](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck)

In this tutorial, learn how to load unstructured data into MotherDuck with Unstructured.io to build modern data pipelines and business applications that turn unstructured data intro structured data.

[View all](https://motherduck.com/blog/)

Authorization Response