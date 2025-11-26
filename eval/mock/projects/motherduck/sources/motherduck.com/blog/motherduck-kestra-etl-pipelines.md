---
title: motherduck-kestra-etl-pipelines
content_type: tutorial
source_url: https://motherduck.com/blog/motherduck-kestra-etl-pipelines
indexed_at: '2025-11-25T19:58:29.561676'
content_hash: 8333c90bd01022ac
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Beyond Storing Data: How to Use DuckDB, MotherDuck and Kestra for ETL

2023/08/18 - 8 min read

BY

[Anna Geller](https://motherduck.com/authors/anna-geller/)

DuckDB is not _just_ a database — it’s also a data transformation engine. This post will explore how DuckDB and MotherDuck can transform data, mask sensitive PII information, detect anomalies in event-driven workflows, and streamline reporting use cases.

MotherDuck is a serverless DuckDB running in the cloud. While we’ll use MotherDuck in this post, everything shown here will also work on DuckDB on your local machine. Check the [product launch announcement](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/) to learn more about MotherDuck and how to get access.

Let’s dive in!

## Simplified reporting

Whether you use a data lake, data warehouse, or a mix of both, it’s common to first extract raw data from a source system and load it in its original format into a staging area, such as S3. The Python script below does just that — it extracts data from a source system and loads it to an S3 bucket:

![extract_upload](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage17_084a85e8f6.png%3Fupdated_at%3D2023-08-17T19%3A51%3A21.259Z&w=3840&q=75)

[Github Gist](https://gist.github.com/anna-geller/32975520c71a0742cfd821bbc5bcdb56)

For reproducibility, this script loads data from [a public GitHub repository](https://github.com/kestra-io/datasets/tree/main/monthly_orders) to a private S3 bucket. In a real-world scenario, you would extract data from a production database rather than from GitHub.

This script ingests monthly orders with one CSV file per month. For reporting, we will need to consolidate that data.

### Use case: consolidate data and send a regular email report

Let’s say your task is to read all these S3 objects and generate a CSV report with the total order volume per month, showing the top-performing months first. This report should be sent via email to the relevant stakeholders every first day of the month.

When using a traditional data warehousing approach, you would need to create a table and define the schema. Then, you would load data to that table. Once data is in the warehouse, you can finally start writing analytical queries. This multi-step process might be a little too slow if all you need is to get a single report with monthly aggregates. Let’s simplify it with DuckDB.

### Query data from a private S3 bucket with DuckDB

DuckDB can read multiple files from S3, auto-detect the schema, and query data directly via HTTP. The code snippet below shows how DuckDB can simplify such reporting use cases.

![montly](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage20_cf2d6e2abf.png%3Fupdated_at%3D2023-08-17T19%3A51%3A20.887Z&w=3840&q=75)

[Github Gist](https://gist.github.com/anna-geller/4a602ef0acf900b0e5d7c72d98200fce)

You can execute that SQL code anywhere you can run DuckDB — the CLI, Python code, or [WASM](https://github.com/duckdb/duckdb-wasm) as long as you provide your AWS S3 credentials and change the S3 path to point to your bucket.

Here is how you can securely handle S3 credentials in DuckDB:

```ini
Copy code

SET s3_region='us-east-1';

SET s3_secret_access_key='supersecret';

SET s3_access_key_id='xxx';
```

MotherDuck makes it even easier thanks to the notebook-like SQL environment from which you can add and centrally manage your [AWS S3 credentials](https://motherduck.com/docs/integrations/cloud-storage/amazon-s3/) without having to hard-code them in your queries. By default, the query execution will also be [routed to MotherDuck](https://motherduck.com/docs/architecture-and-capabilities#hybrid-execution) for better scalability. The image below shows how you can add S3 credentials ( _see the settings on the right side_) and how you can create a MotherDuck table from a query reading S3 objects ( _see the catalog on the left side_).

![ui](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage19_39d515fe44.png%3Fupdated_at%3D2023-08-17T11%3A32%3A21.283Z&w=3840&q=75)

To send that final result as an email report and schedule it to run every first day of the month, you can leverage an open-source orchestration tool such as Kestra.

### Getting started with Kestra

To [get started with Kestra](https://kestra.io/docs/getting-started), download the [Docker Compose file](https://github.com/kestra-io/kestra/blob/develop/docker-compose.yml):

```arduino
Copy code

curl -o docker-compose.yml https://raw.githubusercontent.com/kestra-io/kestra/develop/docker-compose.yml
```

Then, run docker compose up -d and launch `http://localhost:8080` in your browser. Navigate to **Blueprints** and select the tag **DuckDB** to see example workflows using DuckDB and MotherDuck. The third Blueprint in the list contains the code for our current reporting use case:

![kestra_ui](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage3_f37d79e1ed.png%3Fupdated_at%3D2023-08-17T11%3A32%3A25.466Z&w=3840&q=75)

### The data pipeline

Click on the **Use** button to create a flow from that blueprint. Then, you can save and execute that flow.

![kestra_ui2](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage11_b8019db2ed.png%3Fupdated_at%3D2023-08-17T11%3A32%3A22.618Z&w=3840&q=75)

If you scroll down, the [blueprint description](https://demo.kestra.io/ui/blueprints/community/109) at the bottom provides detailed instructions on how to use it for both DuckDB and MotherDuck.

### Why use MotherDuck over DuckDB for ETL and reporting

MotherDuck adds several features to the vanilla DuckDB, including the following:

- [Convenient persistent storage](https://motherduck.com/docs/key-tasks/loading-data-into-motherduck) for your tables and files
- [Hybrid execution](https://motherduck.com/docs/architecture-and-capabilities#hybrid-execution) between datasets on your computer and datasets on MotherDuck
- [Secrets management](https://motherduck.com/docs/integrations/cloud-storage/amazon-s3/#setting-s3-credentials-by-creating-a-secret-object) to store, e.g., your AWS S3 credentials
- Additional [notebook-like SQL IDE](https://motherduck.com/docs/getting-started/motherduck-quick-tour) built into the [UI](https://motherduck.com/docs/getting-started/motherduck-quick-tour) for interactive queries, analysis, and data management ( _to load and organize your data_)
- [Sharing databases with your teammates](https://motherduck.com/docs/key-tasks/sharing-data/sharing-overview/) and additional collaboration features.

### Why do we need an orchestration tool for this use case

An orchestrator can help here for a number of reasons:

1. **To establish a process:** the process can start by querying relevant data, saving the result to a CSV file, and sending that CSV report via email. The process can then evolve to incorporate more tasks and report recipients or scale to cover more reporting use cases while ensuring robust execution and dependency management.
2. **To automate that established process:** the schedule trigger will ensure that this report gets automatically sent every first day of the month to the relevant business stakeholders.
3. **To gain visibility and manage failure**: adding retries and alerts on failure is a matter of adding a couple of lines of YAML configuration from the UI without having to redeploy your code. Just type “retries” or “notifications” to find blueprints that can help you set that up.

Here is a DAG view showing the structure of the process:

![kestra_ui3](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage22_1ca797a3e8.png%3Fupdated_at%3D2023-08-17T11%3A32%3A12.916Z&w=3840&q=75)

When the workflow finishes execution, the following email should be generated as a result:

![mail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage23_93304affb1.png%3Fupdated_at%3D2023-08-17T11%3A32%3A11.065Z&w=3840&q=75)

Let’s move on to the next use cases.

## Using DuckDB to mask sensitive data between the extract and load steps in ETL workflows

ETL pipelines usually move data between various applications and databases. Source systems often contain sensitive data that has to be masked before it can be ingested into a data warehouse or data lake. DuckDB provides hash() and md5() utility functions that can hash sensitive columns between the extract and load steps in a pipeline. The SQL query below obfuscates customer names and emails.

```sql
Copy code

CREATE TABLE orders AS
    SELECT *
    FROM read_csv_auto('https://raw.githubusercontent.com/kestra-io/examples/main/datasets/orders.csv');

SELECT order_id,
        hash(customer_name) as customer_name_hash,
        md5(customer_email) as customer_email_hash,
        product_id,
        price,
        quantity,
        total
FROM orders;
```

[Github Gist](https://gist.github.com/anna-geller/4a602ef0acf900b0e5d7c72d98200fce)

Here is the result of that query:

![result_query](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage2_40d6acffce.png%3Fupdated_at%3D2023-08-17T11%3A32%3A25.318Z&w=3840&q=75)

[Github Gist](https://gist.github.com/anna-geller/ebd41a04a0013021914f36c51aeda950)

For a full workflow code, check [the following blueprint](https://demo.kestra.io/ui/blueprints/community/108). The flow extracts data from a source system. Then, it uses DuckDB for data masking. Finally, it loads data to BigQuery. Note that you can skip that load step when [persisting data directly to MotherDuck](https://motherduck.com/docs/key-tasks/loading-data-into-motherduck).

## ![kestra_ui4](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage16_337cb21a2a.png%3Fupdated_at%3D2023-08-17T11%3A32%3A24.796Z&w=3840&q=75)

## Using DuckDB and MotherDuck as a lightweight data transformation engine

In the same fashion as with data masking, DuckDB can serve as a lightweight ( _and often faster_) alternative to Spark or Pandas for data transformations. You can leverage the [dbt-duckdb](https://pypi.org/project/dbt-duckdb/) package to transform data in SQL by using dbt and DuckDB together.

Switching between using DuckDB and MotherDuck in your dbt project is a matter of adjusting the profiles.yml file:

```yaml
Copy code

# in-process duckdb
jaffle_shop:
  outputs:
    dev:
      type: duckdb
      path: ':memory:'
      extensions:
        - parquet
  target: dev

# MotherDuck - the Secret macro below is specific to Kestra
jaffle_shop_md:
  outputs:
    dev:
      type: duckdb
      database: jaffle_shop
      disable_transactions: true
      threads: 4
      path: |
        md:?motherduck_token={{secret('MOTHERDUCK_TOKEN')}}
  target: dev
```

[Github Gist](https://gist.github.com/anna-geller/2016c5acd78661b7ab02adc8c775b1b9)

There are two Kestra blueprints that you can use as a starting point:

- [Git workflow for dbt with DuckDB](https://demo.kestra.io/ui/blueprints/community/50)
- [Git workflow for dbt with MotherDuck](https://demo.kestra.io/ui/blueprints/community/111) (see the image below)

![kestra_dbt](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage5_57a4ce8140.png%3Fupdated_at%3D2023-08-17T11%3A32%3A17.186Z&w=3840&q=75)

To use those workflows, adjust the Git repository and the branch name to point it to your dbt code. If you want to schedule it to run, e.g., every 15 minutes, you can add a schedule as follows:

```yml
Copy code

id: your_flow_name
namespace: dev

tasks:
  - id: dbt
    type: io.kestra.core.tasks.flows.WorkingDirectory
    tasks:
      - id: cloneRepository
        type: io.kestra.plugin.git.Clone
        url: https://github.com/dbt-labs/jaffle_shop_duckdb
        branch: duckdb

      - id: dbt-build
        type: io.kestra.plugin.dbt.cli.Build
        # dbt profile config...

triggers:
  - id: every-15-minutes
    type: io.kestra.core.models.triggers.types.Schedule
    cron: "*/15 * * * *"
```

[Github Gist](https://gist.github.com/anna-geller/2fc306dafbcd901de242476612bbbb2b)

After you execute the flow, all dbt models and tests will be rendered in the UI so you can see their runtime and inspect the logs:

![kestra_dbt_1](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage18_eb82eea189.png%3Fupdated_at%3D2023-08-17T11%3A32%3A22.811Z&w=3840&q=75)

You can access the tables created as a result of the workflow in your MotherDuck SQL IDE:

![md_ui](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage13_fcf4fae27b.png%3Fupdated_at%3D2023-08-17T11%3A32%3A22.900Z&w=3840&q=75)

So far, we’ve covered reporting and scheduled batch data pipelines. Let’s move on to event-driven use cases.

* * *

## Event-driven anomaly detection using MotherDuck queries and Kestra triggers

Scheduled batch pipelines can lead to slow time-to-value when dealing with near real-time data. Imagine that a data streaming service regularly delivers new objects to an S3 bucket, and you want some action to be triggered as soon as possible based on specific conditions in data. Combining DuckDB’s capabilities to query data stored in S3 with Kestra’s event triggers makes that process easy to accomplish.

The workflow below will send an email alert if new files detected in S3 have some anomalies. This workflow is available [in the list of DuckDB Blueprints in the UI](https://demo.kestra.io/ui/blueprints/community/110).

![kestra_flows](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage9_e3e8752eb4.png%3Fupdated_at%3D2023-08-17T11%3A32%3A26.337Z&w=3840&q=75)

To test that workflow locally, add your credentials to S3, MotherDuck, and email, for example, using [Secrets](https://kestra.io/docs/developer-guide/secrets). Then, upload [one of these files from GitHub](https://github.com/kestra-io/datasets/tree/main/monthly_orders) to S3 ( _or upload all files_). You can change the numbers, e.g., in the 2023\_01.csv file, to create a fake anomaly. Then, upload the file to S3:

![vscode](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage10_36051b90fc.png%3Fupdated_at%3D2023-08-17T11%3A32%3A23.355Z&w=3840&q=75)

As soon as the file is uploaded, the flow will check it for anomalies using a DuckDB query. The anomaly will be identified as shown in the image:

![kestra_run](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage14_4a9b4d91d0.png%3Fupdated_at%3D2023-08-17T11%3A32%3A22.514Z&w=3840&q=75)

The result of this flow execution is an email with anomalous rows attached, and a message pointing to the S3 file with these outliers, making it easier to audit and address data quality issues:

![email](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage15_4ad374e814.png%3Fupdated_at%3D2023-08-17T11%3A32%3A14.305Z&w=3840&q=75)

## Next steps

This post covered various ways to use DuckDB and MotherDuck in your data pipelines. If you have questions or feedback about any of these use cases, feel free to reach out using one of these Slack communities: [MotherDuck](https://slack.motherduck.com/) and [Kestra](https://kestra.io/slack).

### TABLE OF CONTENTS

[Simplified reporting](https://motherduck.com/blog/motherduck-kestra-etl-pipelines/#simplified-reporting)

[Using DuckDB to mask sensitive data between the extract and load steps in ETL workflows](https://motherduck.com/blog/motherduck-kestra-etl-pipelines/#using-duckdb-to-mask-sensitive-data-between-the-extract-and-load-steps-in-etl-workflows)

[Using DuckDB and MotherDuck as a lightweight data transformation engine](https://motherduck.com/blog/motherduck-kestra-etl-pipelines/#using-duckdb-and-motherduck-as-a-lightweight-data-transformation-engine)

[Event-driven anomaly detection using MotherDuck queries and Kestra triggers](https://motherduck.com/blog/motherduck-kestra-etl-pipelines/#event-driven-anomaly-detection-using-motherduck-queries-and-kestra-triggers)

[Next steps](https://motherduck.com/blog/motherduck-kestra-etl-pipelines/#next-steps)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Exploring StackOverflow with DuckDB on MotherDuck (Part 1)](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FPART_1_d3f0edae28.png&w=3840&q=75)](https://motherduck.com/blog/exploring-stackoverflow-with-duckdb-on-motherduck-1/)

[2023/08/09 - Michael Hunger](https://motherduck.com/blog/exploring-stackoverflow-with-duckdb-on-motherduck-1/)

### [Exploring StackOverflow with DuckDB on MotherDuck (Part 1)](https://motherduck.com/blog/exploring-stackoverflow-with-duckdb-on-motherduck-1)

Exploring StackOverflow with DuckDB on MotherDuck (Part 1)

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response