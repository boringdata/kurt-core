---
title: analyze-data-in-azure-with-duckdb
content_type: tutorial
source_url: https://motherduck.com/blog/analyze-data-in-azure-with-duckdb
indexed_at: '2025-11-25T19:57:46.386521'
content_hash: 0ec937ba8cad5a60
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Analyze Data in Azure with DuckDB or MotherDuck

2023/11/01 - 4 min read

BY
David Neal

So, you've got some data in Azure blob storage, and you want to run some queries? You can do that with DuckDB or MotherDuck! DuckDB is a lightweight app you install on your computer and execute queries by typing in commands at your terminal. MotherDuck is essentially DuckDB in the cloud, with a UI running in your browser. There's nothing to install. The good news is that _both_ now support querying data stored on Azure!

## Find your Azure connection string

Whether you use DuckDB or MotherDuck, you need your Azure connection string to authenticate to the Azure platform. You can find your connection string in the [Azure portal](https://portal.azure.com/). Under _Resources_, click your storage container. Under _Security + networking_, click _Access keys_. If this is your first time using access keys, you may need to generate a new one. Next, click the _Show_ button to reveal your connection string. Select the entire connection string and copy it to your clipboard.

![Find your Azure connection string under access keys](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_azure_access_keys_ef01a61726.jpg&w=3840&q=75)

As mentioned on this page in the Azure portal, keeping your connection string secure is very important. Learn more about [Azure connection strings](https://learn.microsoft.com/en-gb/azure/storage/common/storage-configure-connection-string).

## Query Azure with DuckDB

The DuckDB command-line interface (CLI) application supports Azure queries through an [optional extension](https://duckdb.org/docs/extensions/azure). To use this extension, you must start the application, install the extension, and configure your Azure connection string.

### Launch DuckDB

If you haven't already, [download and install DuckDB](https://duckdb.org/docs/installation/index.html) on your computer. Open your terminal or command prompt, and start the DuckDB application.

```sh
Copy code

./duckdb
```

### Install and configure the Azure extension for DuckDB

Now that you have DuckDB running, you must install and activate the Azure extension. You can do this in the DuckDB CLI with the following commands.

```sql
Copy code

INSTALL azure;
LOAD azure;
```

With the Azure extension loaded, you can configure the extension to use your Azure connection string. Use the following `SET` command, replacing `<your_connection_string>` with the value copied from the Azure portal.

```sql
Copy code

SET azure_storage_connection_string = '<your_connection_string>';
```

You are now ready to query data files stored in your Azure container!

### Query data files in Azure from DuckDB

Here is the syntax for querying a file in Azure Blob storage.

```sql
Copy code

FROM 'azure://[container]/[file-name-or-file-pattern]'
```

For example, to query a file named `survey_results.csv` in a container named `my_container`, the SQL may look like the following.

```sql
Copy code

SELECT count(*) FROM 'azure://my_container/survey_results.csv';
```

You can also query across multiple files with a file-matching pattern. For example, if you have separate files for each month of the year named `year-month-sales.csv`, you could query across the entire year using the following.

```sql
Copy code

SELECT count(*) FROM 'azure://my_container/2023-*-sales.csv';
```

### Query across multiple cloud storage providers using DuckDB

Combining the new Azure extension and the HTTPS extension, it's possible to query across multiple storage providers, should the need arise. For example, you may have historical data stored in Amazon S3 and more recent data stored in Azure and need to query across both.

```sql
Copy code

-- Load and configure Azure
INSTALL azure;
LOAD azure;
SET azure_storage_connection_string = 'your-connection-string';

-- Load and configure Amazon S3
INSTALL httpfs;
LOAD httpfs;
SET s3_access_key_id='your-access-key-id';
SET s3_secret_access_key='your-secret-access-key';
SET s3_region='your-region';

SELECT t1.*
FROM (
    SELECT * FROM 's3://my-s3-bucket/sales-history.csv'
    UNION ALL
    SELECT * FROM 'azure://my-container/ytd-sales.csv'
) t1
ORDER BY "Gross Amt" DESC
LIMIT 10;
```

## Query data in Azure from MotherDuck

MotherDuck is a powerful, serverless analytics tool that enables you to run queries directly from your browser. And, there are _fewer_ steps to configure MotherDuck to query Azure.

### Configure your Azure connection in MotherDuck

MotherDuck provides a secure and convenient way to store your Azure connection string so you can query Azure whenever you need. To save your Azure connection string in MotherDuck, log in to your [MotherDuck](https://app.motherduck.com/) account and complete the following steps.

1. Click your profile menu and click _Settings_.
2. Under _Secrets_, click the _ADD_ button.
3. Click the _Secret type_ and click _Azure_.
4. Paste your connection string in the box labeled _Azure storage connection string_.
5. Click _Save_.

![Add MotherDuck Secret to connect to Azure](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fduckdb_azure_add_motherduck_secret_8938a4ccba.jpg&w=3840&q=75)

### Query Azure data from MotherDuck

Next, create a new cell in your MotherDuck notebook. Then, write a SQL query to access your Azure storage account. For example, if you have a file saved in `my_container` named `ytd-sales.csv`, you might try the following.

```sql
Copy code

SELECT *
FROM 'azure://my_container/ytd-sales.csv'
ORDER BY "Gross Sales"
LIMIT 10;
```

You are ready to _duck_ and roll with MotherDuck and Azure!

## Further reading

With the Azure extension for DuckDB, you can now query data in secure Azure Blob storage, including CSV, JSON, parquet, Apache Iceberg, and others. To learn more, you may be interested in the following.

- [MotherDuck support for Azure Blob Storage](https://motherduck.com/docs/integrations/cloud-storage/azure-blob-storage/)
- [MotherDuck supported cloud storage providers](https://motherduck.com/docs/category/cloud-storage/)
- [DuckDB Azure extension documentation](https://duckdb.org/docs/extensions/azure)

### TABLE OF CONTENTS

[Find your Azure connection string](https://motherduck.com/blog/analyze-data-in-azure-with-duckdb/#find-your-azure-connection-string)

[Query Azure with DuckDB](https://motherduck.com/blog/analyze-data-in-azure-with-duckdb/#query-azure-with-duckdb)

[Query data in Azure from MotherDuck](https://motherduck.com/blog/analyze-data-in-azure-with-duckdb/#query-data-in-azure-from-motherduck)

[Further reading](https://motherduck.com/blog/analyze-data-in-azure-with-duckdb/#further-reading)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: October 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumbnail_duckdb_newsletter_october_8a16e1b66e.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-eleven/)

[2023/10/30 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-eleven/)

### [This Month in the DuckDB Ecosystem: October 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-eleven)

This Month in the DuckDB Ecosystem: October 2023

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response