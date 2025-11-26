---
title: effortless-etl-unstructured-data-unstructuredio-motherduck
content_type: tutorial
source_url: https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck
indexed_at: '2025-11-25T19:57:09.624649'
content_hash: e2bb536cbffae546
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Effortless ETL for Unstructured Data with MotherDuck and Unstructured.io

2025/02/20 - 7 min read

BY

[Adithya Krishnan](https://motherduck.com/authors/adithya-krishnan/)

LLMs have extensive abilities to process data across multiple modalities. This has elevated the potential for using unstructured data in novel ways to deliver business insights. Advancements in AI have propelled the use of data sources like PDFs, text files, and HTML pages to build AI applications, and having a reliable way to store and retrieve unstructured data is now an essential capability for modern data pipelines and business applications. [Unstructured.io](https://unstructured.io/) provides a robust solution for transforming raw, unstructured data into structured data.

This blog post introduces a [powerful new integration between MotherDuck and Unstructured.io](https://docs.unstructured.io/api-reference/ingest/destination-connector/motherduck) that paves the way for ingesting unstructured data into MotherDuck to make unstructured data analytics and RAG application development a breeze.

![Core Integration Flow](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fcore_workflow_unstructured_io_motherduck_493769800b.png&w=3840&q=75)

## Why use Unstructured.io?

Handling unstructured data for AI applications may pose several challenges, from inconsistent data formats to wrangling and keeping track of valuable metadata. Building a RAG system that processes multiple file types while maintaining a structured format for retrieval is complex, often requiring custom parsing and pre-processing. Additionally, integrating data from different sources like cloud storage, databases, and local files can be difficult without a standardized approach.

[Unstructured.io](https://unstructured.io/) addresses these issues by simplifying the Extract, Transform, and Load (ETL) process for unstructured data. Its framework converts diverse document formats into structured JSON while preserving the metadata, ensuring that critical information remains intact throughout your pipeline. In addition, Unstructured.io provides built-in chunking strategies and robust mechanisms for batch processing and handling incremental updates. By providing built-in connectors to various data sources, Unstructured.io streamlines data preparation and reduces the complexity of working with unstructured content in AI workflows.

## Why use MotherDuck?

Building AI applications with unstructured data can become unwieldy and cumbersome, especially when integrating multiple data sources. [MotherDuck](https://motherduck.com/product/), the efficient, in-process cloud data warehouse for analytics, streamlines this workflow by consolidating the storage of scattered information from both structured and unstructured sources into a single, accessible location, effectively eliminating data silos. Powered by DuckDB's blazing fast query engine and purpose built for analytics, it enables high-performance queries across numerical and textual data.

With its built-in AI integration, MotherDuck enhances text analysis using its [prompt()](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/prompt/) function, allowing seamless processing of unstructured content. Additionally, vector search and full-text search capabilities provide advanced retrieval mechanisms, enabling AI applications to build richer contextual models. By using metadata-preserving pipelines, developers can further enhance data filtering, searchability, and structured-unstructured data integration within their data workflows.

## TUTORIAL: Using the Integration

**To use Unstructured.io's MotherDuck destination connector, you will need the following:**

- A [MotherDuck account](https://motherduck.com/product/pricing/) and [access token](https://motherduck.com/docs/key-tasks/authenticating-and-connecting-to-motherduck/authenticating-to-motherduck/#creating-an-access-token).
- A database and a schema within your MotherDuck account.
- A table with the appropriate schema to store your processed data.

The [Unstructured.io connector](https://docs.unstructured.io/api-reference/ingest/destination-connector/motherduck) does not automatically create a database, schema, or table for data ingestion into MotherDuck. Instead, these must be set up manually before configuring the connector to load data correctly. By default, Unstructured.io uses the schema name `main` and the table name `elements` unless specified otherwise.

**To ensure maximum compatibility with Unstructured.io, the following table schema can be used as a reference:**

```sql
Copy code

CREATE TABLE elements (
    id VARCHAR,
    element_id VARCHAR,
    text TEXT,
    embeddings FLOAT[],
    type VARCHAR,
    system VARCHAR,
    layout_width DECIMAL,
    layout_height DECIMAL,
    points TEXT,
    url TEXT,
    version VARCHAR,
    date_created INTEGER,
    date_modified INTEGER,
    date_processed DOUBLE,
    permissions_data TEXT,
    record_locator TEXT,
    category_depth INTEGER,
    parent_id VARCHAR,
    attached_filename VARCHAR,
    filetype VARCHAR,
    last_modified TIMESTAMP,
    file_directory VARCHAR,
    filename VARCHAR,
    languages VARCHAR[],
    page_number VARCHAR,
    links TEXT,
    page_name VARCHAR,
    link_urls VARCHAR[],
    link_texts VARCHAR[],
    sent_from VARCHAR[],
    sent_to VARCHAR[],
    subject VARCHAR,
    section VARCHAR,
    header_footer_type VARCHAR,
    emphasized_text_contents VARCHAR[],
    emphasized_text_tags VARCHAR[],
    text_as_html TEXT,
    regex_metadata TEXT,
    detection_class_prob DECIMAL
);
```

## How to Build your Unstructured Data Pipeline

Unstructured.io provides a Python framework to orchestrate your ETL pipeline and a no-code interface for building data pipelines for unstructured data.

Learn more about the newly released MotherDuck connector [here](https://unstructured.io/developers#get-started) to get started.

**First, install the MotherDuck connector and its dependencies using the following command:**

```arduino
Copy code

pip install "unstructured-ingest[motherduck]"
```

**You will need the following environment variables:**

- `MOTHERDUCK_MD_TOKEN` \- The access token for the target MotherDuck account, represented by `md_token` in the Python client.
- `MOTHERDUCK_DATABASE` \- The name of the target database in the account, represented by `database` in the Python client.
- `MOTHERDUCK_DB_SCHEMA` \- The name of the target schema in the database, represented by `db_schema` in the Python client.
- `MOTHERDUCK_TABLE` \- The name of the target table in the schema, represented by `table` in the Python client.
- `UNSTRUCTURED_API_KEY` \- Your Unstructured API key value. Follow [these instructions](https://docs.unstructured.io/api-reference/api-services/saas-api-development-guide) to get your API key.
- `UNSTRUCTURED_API_URL` \- Your Unstructured API URL.

Now let's use the [Unstructured Python SDK](https://docs.unstructured.io/api-reference/api-services/sdk-python) to build the pipeline. An example pipeline is provided using the local source connector, which can help you load all the unstructured documents present in your local folder into MotherDuck. In practice, the source connector can be [any of the ones supported by Unstructured.io](https://docs.unstructured.io/api-reference/ingest/source-connectors/overview).

### Create an example pipeline using local documents

The pipeline below ingests local documents (PDFs) from a specified folder, utilizing the default document chunker.

**This example pipeline can be used to process a collection of documents, including PDFs, Word files, and more, before storing them in MotherDuck for retrieval-augmented generation (RAG) applications:**

```ini
Copy code

import os

from unstructured_ingest.v2.pipeline.pipeline import Pipeline
from unstructured_ingest.v2.interfaces import ProcessorConfig

from unstructured_ingest.v2.processes.connectors.duckdb.motherduck import (
    MotherDuckAccessConfig,
    MotherDuckConnectionConfig,
    MotherDuckUploadStagerConfig,
    MotherDuckUploaderConfig
)
from unstructured_ingest.v2.processes.connectors.local import (
    LocalIndexerConfig,
    LocalConnectionConfig,
    LocalDownloaderConfig
)
from unstructured_ingest.v2.processes.partitioner import PartitionerConfig
from unstructured_ingest.v2.processes.chunker import ChunkerConfig

# Chunking and embedding are optional.

if __name__ == "__main__":
    Pipeline.from_configs(
        context=ProcessorConfig(),
        indexer_config=LocalIndexerConfig(input_path=os.getenv("LOCAL_FILE_INPUT_DIR")),
        downloader_config=LocalDownloaderConfig(),
        source_connection_config=LocalConnectionConfig(),
        partitioner_config=PartitionerConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
            partition_endpoint=os.getenv("UNSTRUCTURED_API_URL"),
            additional_partition_args={
                "split_pdf_page": True,
                "split_pdf_allow_failed": True,
                "split_pdf_concurrency_level": 15
            }
        ),
        chunker_config=ChunkerConfig(chunking_strategy="by_title"),
        destination_connection_config=MotherDuckConnectionConfig(            access_config=MotherDuckAccessConfig(md_token=os.getenv("MOTHERDUCK_MD_TOKEN")),
            database=os.getenv("MOTHERDUCK_DATABASE"),
            db_schema=os.getenv("MOTHERDUCK_DB_SCHEMA"),
            table=os.getenv("MOTHERDUCK_TABLE")
        ),
        stager_config=MotherDuckUploadStagerConfig(),
        uploader_config=MotherDuckUploaderConfig(batch_size=50)
    ).run()
```

### Generate Embeddings for the Text Chunks

For retrieval-augmented generation (RAG) applications, finding the most relevant context chunk is essential. MotherDuck enables retrieval using [Vector Search](https://motherduck.com/blog/search-using-duckdb-part-1/) based on cosine similarity functions (list\_cosine\_similarity() and array\_cosine\_similarity() depending on the data type), [Full-Text Search](https://motherduck.com/blog/search-using-duckdb-part-3/) with the FTS extension, or a combination of both for [Hybrid Search](https://motherduck.com/blog/search-using-duckdb-part-3/).

Embeddings can be generated directly within the SQL layer using MotherDuck’s [embedding()](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/embedding/) function.

**The simple query below can be used to create embeddings for stored text without external processing:**

```ini
Copy code

UPDATE unstructured_data.main.elements SET embeddings = embedding(text);
```

MotherDuck currently supports OpenAI’s text-embedding-3-small (512 dimensions) and text-embedding-3-large (1024 dimensions) for embedding generation.

With these capabilities, complete RAG applications can be built within MotherDuck that integrate vector search, full-text search, and hybrid retrieval into a single cloud data warehouse environment.

### Sample the Output Data

Now that your pipeline is set up, you can run it to check the ingestion output in MotherDuck’s web UI.

**Here’s an example SQL query we used to view some of the fields:**

```sql
Copy code

SELECT id, element_id, "text", embeddings, "type", date_created,
date_modified, date_processed, permissions_data, record_locator,
filetype, last_modified, file_directory, filename, languages, page_number
FROM elements;
```

![MotherDuck UI](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FMother_Duck_UI_0b51dee138.png&w=3840&q=75)

## Building AI Use Cases on MotherDuck

Building AI applications or analytics pipelines on unstructured data comes with challenges such as inconsistent formats, and inefficient retrieval processes. [Unstructured.io](https://unstructured.io/) addresses these challenges by transforming raw, unstructured content into structured formats while preserving metadata, ensuring consistency across workflows. However, structured and unstructured data often remain siloed, making comprehensive analysis difficult. By integrating with [MotherDuck](https://motherduck.com/product/), developers can consolidate and query across structured and unstructured data within a single data store, enriching data models with better context.

Applications relying on both data types, benefit from fast analytical querying on structured data and keyword [(Full Text Search)](https://motherduck.com/blog/search-using-duckdb-part-3/) and embedding-based vector search [(Cosine similarity)](https://motherduck.com/blog/search-using-duckdb-part-1/) on unstructured data.

Whether you're optimizing a RAG system or handling large-scale AI applications, [using Unstructured.io and MotherDuck together](https://docs.unstructured.io/api-reference/ingest/destination-connector/motherduck) provides a powerful solution for maximizing the value of unstructured data. Streamlining data pipelines from ingestion to retrieval enhances scalability and efficiency in AI application development and enables you to build future-proofed data pipelines.

### TABLE OF CONTENTS

[Why use Unstructured.io?](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck/#why-use-unstructuredio)

[Why use MotherDuck?](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck/#why-use-motherduck)

[TUTORIAL: Using the Integration](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck/#tutorial-using-the-integration)

[How to Build your Unstructured Data Pipeline](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck/#how-to-build-your-unstructured-data-pipeline)

[Building AI Use Cases on MotherDuck](https://motherduck.com/blog/effortless-etl-unstructured-data-unstructuredio-motherduck/#building-ai-use-cases-on-motherduck)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![How to build an interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFabi_blog_023f05dd0e.png&w=3840&q=75)](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/)

[2025/02/12 - Marc Dupuis](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/)

### [How to build an interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis)

Interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai

[![Faster health data analysis with MotherDuck & Preswald](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fstructured_preswald_521f8cd689.png&w=3840&q=75)](https://motherduck.com/blog/preswald-health-data-analysis/)

[2025/02/14 - Amrutha Gujjar](https://motherduck.com/blog/preswald-health-data-analysis/)

### [Faster health data analysis with MotherDuck & Preswald](https://motherduck.com/blog/preswald-health-data-analysis)

Faster health data analysis with MotherDuck & Preswald

[View all](https://motherduck.com/blog/)

Authorization Response