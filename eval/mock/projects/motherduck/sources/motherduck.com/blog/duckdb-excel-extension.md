---
title: duckdb-excel-extension
content_type: tutorial
source_url: https://motherduck.com/blog/duckdb-excel-extension
indexed_at: '2025-11-25T19:56:31.610696'
content_hash: 51ef03341dae31d2
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Breaking the Excel-SQL Barrier: Leveraging DuckDB's Excel Extension

2025/05/27 - 5 min read

BY

[Jacob Matson](https://motherduck.com/authors/jacob-matson/)

One of the underrated features that snuck into DuckDB 1.2.0 was the excel extension got a [major upgrade](https://github.com/duckdb/duckdb-excel/pull/3). In the recent past, it was used merely for formatting text in excel format (important for a very specific use case, I suppose) but now it can **_read and write XLSX files!!_**

I am excited for this as someone who spent a good chunk of my career working in and with finance teams that had key datasets in Excel files. Integrating them into our data warehouse for downstream reporting was a painful, manual process. It was so painful that at one company we wrote a custom excel plugin to allow end users to import their excel files into tables in our SQL Server based data warehouse! (I think about that plugin more than I care to admit).

Now with the this upgraded extension, I don't need to think about that plugin anymore - we have something frankly way better and easier to integrate into workflows.

![ddb excel icon.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fddb_excel_icon_d48a3b067e.png&w=3840&q=75)

## Getting Started with the Excel Extension

Installation is similar to other DuckDB Extensions:

```sql
Copy code

-- Install the extension (needed only once per DuckDB installation)
INSTALL excel;

-- Load the extension into the current database session
LOAD excel;
```

Once its installed, it works similar to the `csv` or `json` readers: We can query directly from `.xlsx` files without any functions as the use of the extension is implied.

```sql
Copy code

FROM 'my_excel_file.xlsx'
```

Of course, there are a [few config knobs](https://duckdb.org/docs/stable/core_extensions/excel.html) available in this extension, which can be invoked with the `read_xlsx()` function, again similar to `csv` or `json`. Where this comes in handy most often with reading Excel sheet is for **(1)** choosing a sheet that's not the first sheet (which is the default behavior), and **(2)** handling datatype issues with `all_varchar` and `ignore_errors` flags.

For example, reading the second tab of an excel sheet and casting all the data to varchar is invoked like this:

```sql
Copy code

FROM read_xlsx(
  'my_excel_file.xlsx',
  all_varchar = true,
  sheet = 'sheet2');
```

## Handling Excel files with MotherDuck

_It should be noted that as of this writing, the MotherDuck UI does not allow importing of Excel extension files, so you need to use the DuckDB CLI to accomplish this integration. While this is fine for data pipeline work, it is fairly annoying for ad-hoc data exploration; we are aware of this and working on it._

Now that we've established how to use the Excel extension for reading, lets handle some hygiene as it relates to loading Excel based data into MotherDuck. In general, when handling certain adversarial data sources like Excel files, I like to use the `all_varchar` flag when reading and loading the data, and then handling typing as a second stage.

An example of this would be something like this in the CLI:

```sql
Copy code

-- attach motherduck so you can see your cloud databases
ATTACH 'md:';

-- add the data to motherduck
CREATE OR REPLACE TABLE my_db.my_table AS
  FROM read_xlsx(
  'my_excel_file.xlsx',
  all_varchar = true,
  sheet = 'sheet2');

-- enforce types
CREATE OR REPLACE TABLE my_db.my_cleaned_table AS
  SELECT col1::int, col2::numeric
  FROM my_db.my_table
```

By separating these steps, we can assure the data is loaded and potentially add some [try / catch logic](https://duckdb.org/docs/stable/sql/expressions/try.html) in our pipeline when our ~~adversaries~~ users inevitably introducing some typing issues in the source data.

Additionally, you can load ad-hoc data sets into MotherDuck from excel files and join them to your core data warehouse data. This especially helpful in classification exercises where you may have a list of products or customers with additional dimensions for aggregation, and traditional warehouses would force you through a formal data pipeline to make those columns available. With MotherDuck, you are empowered as an analyst to enrich the data in an ad-hoc manner to answer pressing business questions, without dependencies on your data engineering team. This illustrated in the ad-hoc query below:

```sql
Copy code

SELECT
  e.category,
  SUM(d.sales) as tot_sales
FROM dwh.sales d
LEFT JOIN (FROM 'my_excel_file.xlsx') e ON e.product_id = d.product_id
GROUP BY ALL
```

Of course, we aren't limited to merely reading Excel files, we can also write them out. This is helpful especially when dealing with finance stakeholders who may need the data in Excel so they can fold it into a larger process, or are just more familiar with using Excel.

Again, for this exercise of writing files, its best to use the CLI so you can interact with your local file system to produce the file. This can also be done in your data pipelines, i.e. writing the files out to Object Storage.

We can see an example of Excel writes here:

```sql
Copy code

COPY report_data
TO 'products.xlsx'
WITH (
    FORMAT xlsx,
    HEADER true,
    SHEET 'SalesData'
);
```

This will save the file in directory we are running DuckDB in, although you can also specify the path in the `TO` clause.

## Take-aways

With the Excel Extension and MotherDuck, you have all you need to build both a robust reporting pipeline and also handle ad-hoc requests from users based on Excel data. Or if you so desire, even treat Excel files as sources with your data pipeline itself. This type of flexibility is core to MotherDuck and is critical to make sure that business value is never blocked by IT frameworks. Keep Quacking!

### TABLE OF CONTENTS

[Getting Started with the Excel Extension](https://motherduck.com/blog/duckdb-excel-extension/#getting-started-with-the-excel-extension)

[Handling Excel files with MotherDuck](https://motherduck.com/blog/duckdb-excel-extension/#handling-excel-files-with-motherduck)

[Take-aways](https://motherduck.com/blog/duckdb-excel-extension/#take-aways)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Taming Wild CSVs: Advanced DuckDB Techniques for Data Engineers](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FTaming_Wild_CS_Vs_v3_f21b5fe692.png&w=3840&q=75)](https://motherduck.com/blog/taming-wild-csvs-with-duckdb-data-engineering/)

[2025/05/17 - Ryan Boyd](https://motherduck.com/blog/taming-wild-csvs-with-duckdb-data-engineering/)

### [Taming Wild CSVs: Advanced DuckDB Techniques for Data Engineers](https://motherduck.com/blog/taming-wild-csvs-with-duckdb-data-engineering)

How to ingest and query CSV files in DuckDB using auto-detection, sniffing, manual configuration and more.

[![The Open Lakehouse Stack: DuckDB and the Rise of Table Formats](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fopendata_stack_7f9a4498ee.png&w=3840&q=75)](https://motherduck.com/blog/open-lakehouse-stack-duckdb-table-formats/)

[2025/05/23 - Simon Späti](https://motherduck.com/blog/open-lakehouse-stack-duckdb-table-formats/)

### [The Open Lakehouse Stack: DuckDB and the Rise of Table Formats](https://motherduck.com/blog/open-lakehouse-stack-duckdb-table-formats)

Learn how DuckDB and open table formats like Iceberg power a fast, composable analytics stack on affordable cloud storage

[View all](https://motherduck.com/blog/)

Authorization Response