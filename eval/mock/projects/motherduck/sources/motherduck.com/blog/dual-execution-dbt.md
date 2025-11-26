---
title: dual-execution-dbt
content_type: tutorial
source_url: https://motherduck.com/blog/dual-execution-dbt
indexed_at: '2025-11-25T19:57:41.215232'
content_hash: 2b6c5ae395798479
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Local dev and cloud prod for faster dbt development

2025/01/16 - 8 min read

BY

[Jacob Matson](https://motherduck.com/authors/jacob-matson/)

## Introducktion

I hate waiting for slow pipelines to run, so I am delighted to share some strategies to iterate on your data problems at maximum speed - MotherDuck even gave a talk on this concept at [dbt Coalesce in 2024](https://www.youtube.com/watch?v=oqwIHvSfOVQ). By harnessing the capabilities of DuckDB locally, backed by MotherDuck in the cloud, we can unlock an incredibly fast and efficient development cycle. We'll explore how to configure your dbt profile for dual execution and share some tips on how much data to bring local. By implementing these techniques, you can significantly accelerate your data pipeline development and iterate even faster to solve business problems.

Looking to following along in the code?

Check out the [example repo](https://github.com/motherduckdb/motherduck-examples/tree/main/dbt-dual-execution)!

![Instant feedback loop](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FInstant_feedback_loop_b99078a679.png&w=3840&q=75)

## Setting up your Profile

In order to take advantage of these capabilities, we need to configure our dbt profile to execute in the correct place, as well as define the behavior that we want in our sources. In the example dbt profile below, `prod` runs entirely in the cloud, while `local` runs mostly on local but is also linked to MotherDuck for reading data into your local database.

```yml
Copy code

dual_execution:
  outputs:
    local:
      type: duckdb
      path: local.db
      attach:
        - path: "md:"	# attaches all MotherDuck databases
    prod:
      type: duckdb
      path: "md:jdw"
  target: local
```

## Sources & Models

With your sources, you need to define which ones to replicate entirely, which ones are ok as views, and which ones to sample. Keep in mind for sampling, you need to think about your data model and make sure that related samples are hydrated (i.e. if you only bring in 100 customers, you need to make sure you also bring in their orders too).

In my example project using TPC-DS as the source data, I am sampling 1% of the data when running locally on the large tables. In general, I am aiming to keep the datasets less than a million rows per table, although there is no hard limit. For the remaining tables, I am replicating the entire data set locally since they are so small.

The way that we conditionally sample our models is by using the [‘target’ variable](https://docs.getdbt.com/reference/dbt-jinja-functions/target). You can add this parameter by checking your `target` and running it conditionally on your model.

An example sql snippet is below (using jinja).

```sql
Copy code

from {{ source("tpc-ds", "catalog_sales") }}
{% if target.name == 'local' %} using sample 1 % {% endif %}
```

As an example of a simple “create local table from cloud”, consider the following query plan. The “L” indicates Local and the “R” indicates Remote (i.e. MotherDuck).

```bash
Copy code

🦆 explain create table
        "local"."main"."call_center"
      as (
        from "jdw_dev"."jdw_tpcds"."call_center"
      );

┌─────────────────────────────┐
│┌───────────────────────────┐│
││       Physical Plan       ││
│└───────────────────────────┘│
└─────────────────────────────┘
┌───────────────────────────┐
│ BATCH_CREATE_TABLE_AS (L) │
└─────────────┬─────────────┘
┌─────────────┴─────────────┐
│    DOWNLOAD_SOURCE (L)    │
│    ────────────────────   │
│        bridge_id: 1       │
└─────────────┬─────────────┘
┌─────────────┴─────────────┐
│  BATCH_DOWNLOAD_SINK (R)  │
│    ────────────────────   │
│        bridge_id: 1       │
│       parallel: true      │
└─────────────┬─────────────┘
┌─────────────┴─────────────┐
│       SEQ_SCAN  (R)       │
│    ────────────────────   │
│        call_center        │
│                           │
│        Projections:       │
│     cc_call_center_sk     │
│     cc_call_center_id     │
│     cc_rec_start_date     │
│      cc_rec_end_date      │
│     cc_closed_date_sk     │
│      cc_open_date_sk      │
│          cc_name          │
│          cc_class         │
│        cc_employees       │
│          cc_sq_ft         │
│          cc_hours         │
│         cc_manager        │
│         cc_mkt_id         │
│        cc_mkt_class       │
│        cc_mkt_desc        │
│     cc_market_manager     │
│        cc_division        │
│      cc_division_name     │
│         cc_company        │
│      cc_company_name      │
│      cc_street_number     │
│       cc_street_name      │
│       cc_street_type      │
│      cc_suite_number      │
│          cc_city          │
│         cc_county         │
└───────────────────────────┘
```

This can also be extended to your `sources.yml` if necessary for testing local datasets (i.e. json or parquet on experimental pipelines that have not yet made it to your data lake). Configuring these is similar:

```ini
Copy code

{%if- target.name == 'local' -%}
   meta:
      external_location:
        data/tpcds/{name}.parquet
{%- endif -%}
```

## Running your pipeline

Once you have this configuration in place, you can simply run your pipeline as normal, although for ease of use, you may want to add tags to the models that you are working on so you can avoid going back to the cloud data set too often. This can be set simply in the `dbt_project.yml` like this:

```yml
Copy code

models:
  dual_execution:
    tpcds:
      raw:
        +tags: ['raw']
        +materialized: table
      queries:
        +materialized: view
        +tags: ['queries']
```

From there, it is as simple as running `dbt build -s tag:raw` to load your raw data and then for subsequent query iteration, run `dbt build -s tag:queries` in the CLI. The subsequent runs can be visualized like this:

![data flow cloud to local](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdata_flow_cloud_to_local_792a293673.png&w=3840&q=75)

## Shipping dev to the cloud

Certain tables may need to be available in your cloud data warehouse for testing even in the local workflow. This may be something like a BI tool, that is connected to your cloud instance and is difficult to run locally. This can be accomplished by setting the database attribute in your model, so that after the model is run, it is available in the cloud as well.

```yml
Copy code

{{ config(
    database="jdw_dev",
    schema="local_to_prod"
    materialized="table"
) }}
```

It should be noted that this is a static configuration that is best used for testing. If you don’t want to manually flip models between dev / prod destinations, you can define the database as an attribute of a specific model in your `dbt_project.yml` file.

## Wrapping up

As you can see from this example, using MotherDuck’s dual execution allows us to leverage the unique value proposition of DuckDB to run an accelerated development cycle on your local machine. With some basic optimization, we can get ~5x faster dbt runs by making the data smaller and using local compute. This is a very powerful combination for rapidly iterating on your pipeline and then pushing a high quality change back into your production environment.

Want to learn more? Join our webinar about Local Dev & Cloud Prod on [February 13th, 2025](https://lu.ma/0die8ual?utm_source=blog).

### TABLE OF CONTENTS

[Introducktion](https://motherduck.com/blog/dual-execution-dbt/#introducktion)

[Setting up your Profile](https://motherduck.com/blog/dual-execution-dbt/#setting-up-your-profile)

[Sources & Models](https://motherduck.com/blog/dual-execution-dbt/#sources-models)

[Running your pipeline](https://motherduck.com/blog/dual-execution-dbt/#running-your-pipeline)

[Shipping dev to the cloud](https://motherduck.com/blog/dual-execution-dbt/#shipping-dev-to-the-cloud)

[Wrapping up](https://motherduck.com/blog/dual-execution-dbt/#wrapping-up)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![What’s New: Streamlined User Management, Metadata, and UI Enhancements](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FMother_Duck_Feature_Roundup_2_47f5d902c0.png&w=3840&q=75)](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024/)

[2024/12/21 - Sheila Sitaram](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024/)

### [What’s New: Streamlined User Management, Metadata, and UI Enhancements](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024)

December’s feature roundup is focused on improving the user experience on multiple fronts. Introducing the User Management REST API, the Table Summary, and a read-only MD\_INFORMATION\_SCHEMA for metadata.

[![DuckDB Ecosystem: January 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fnewsletter_a65cff5430.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025/)

[2025/01/10 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025/)

### [DuckDB Ecosystem: January 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025)

DuckDB Monthly #25: PyIceberg, 0$ data distribution and more!

[View all](https://motherduck.com/blog/)

Authorization Response