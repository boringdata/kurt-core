---
title: streamlining-ai-agents-duckdb-rag-solutions
content_type: blog
source_url: https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions
indexed_at: '2025-11-25T19:58:32.481094'
content_hash: cca41b677f15bcbb
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Structured memory management for AI Applications and AI Agents with DuckDB

2024/04/29 - 10 min read

BY

[Vasilije Markovic](https://motherduck.com/authors/vasilije-markovic/)

For those familiar with retrieval-augmented generation (RAG), the initial challenge is often preparing the data to be loaded into the vector database. RAG enhances large language models (LLMs) by incorporating an external data store during the inference stage. Data processing can be messy; it requires complex Extraction, Transformation, and Loading (ETL) processes, new database setups, and overcoming various technical hurdles that can be daunting, even for enthusiasts.

Meanwhile, less experienced RAG users need to do even more manual work in order to personalize their LLM outputs and provide new data to LLMs at every step of the way. With all the possibilities to implement RAGs, the right way to go about it is rarely straightforward. Getting RAGs to production is still difficult and intimidates many Python developers due to its notorious deployment complexity. Data management in a RAG pipeline often prevents coders from using RAGs effectively and impedes the accuracy of answers retrieved from LLMs.

With that in mind, in this post, we will explore the possibility of structuring and managing data for AI applications and AI Agents by using DuckDB and applying analytical querying to enrich the data. First, let's define all the platforms and concepts needed for this process to work.

## What is Retrieval-Augmented Generation?

The RAG framework boosts the precision and relevance of LLMs. It tackles two common issues with LLMs: their tendency to provide outdated information and the absence of dependable references. RAG enhances LLMs by integrating them with a retrieval mechanism. Upon receiving a query, RAG doesn't just depend on the LLM's prior training; it first searches a content repository, which might be an open resource like the web or a proprietary set of documents, to find the most recent and pertinent data. The LLM then uses this information to generate a response. This approach not only ensures responses are up to date but also cites sources, thereby significantly reducing the risk of retrieving unfounded or incorrect answers.

## Challenges of building RAGs

Building a RAG system requires a lot of preparatory work for it to produce meaningful outputs. One of the first requirements is having a solid grasp of the system’s acceptance criteria; once we understand these, we can start thinking about other major components of the system.

Most key activities can be grouped as follows:

- **Context sanitization**: Contexts tend to become overloaded with irrelevant data and get bloated. This makes a LLM less efficient in answering the questions. Actively managing the context size is therefore one of the key requirements of any RAG system.
- **Metadata indexing**: When handling metadata for a RAG system, we often need a unified data model that can easily evolve. This makes metadata management the backbone of any RAG system.
- **Data preparation**: Most of the data we provide to a system can be conceived of as unstructured, semi-structured, or structured. Rows from a database would belong to structured data, JSONs to semi-structured data, and logs to unstructured data. To organize and process this data, we need to have custom loaders for all data types, which can unify and organize the data well.
- **Data enrichment**: W Often need to enrich the data. This can be done in various ways, such as by adding additional timestamps or summaries or by extracting keywords.

**Here is an example of a typical RAG system:**

![An example of a typical RAG system](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fexample_RAG_application_5b6567bb69.png&w=3840&q=75)

### What is DuckDB?

DuckDB is an open-source, in-process OLAP database used by data professionals to analyze data quickly and efficiently.

### What is dlt?

DLT is an open-source library that can be integrated into Python scripts, enabling the loading of data from diverse and frequently disorganized sources into neatly organized, real-time datasets.

### What is Cognee?

Cognee is an open-source framework for knowledge and memory management for LLMs. By using dlt as a data loader and DuckDB as a metastore, Cognee is able to auto-generate customized datasets to enable LLMs to produce deterministic outputs at scale.

### How it all connects

![How congee connects to other systems](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fcongee_overview_8bd03b3b80.png&w=3840&q=75)

Cognee serves as a plugin for any langchain or llama index pipeline, allowing you to create a semantic layer of text above vector, graph and relational stores. In order to provide deterministic, verifiable outputs, Cognee first needs to perform a few actions.

Let’s walk through how it works step-by-step:

1. We select our dataset. An example could be the following string:


```sql
Copy code


“A large language model (LLM) is a language model notable for its ability to achieve general-purpose language generation and other natural language processing tasks such as classification.”
```

2. The first step is the cognee.add() command. To process the data further, we need a way to load it from a wide variety of sources. Then, we need to move it to destinations like DuckDB, which we can do by using dlt. Cognee uses DuckDB as the metadata store and creates a pipeline to prepare the data for further processing. We treat the string above as a dataset, load it to the filestore destination, and then load all metadata to DuckDB.
3. After we have cleaned our dataset and associated the metadata (in case we need to rerun our processes or update the existing datasets), we execute cognee.cognify(). Here, we create the following enrichments for the dataset or datasets in question:


1. Summaries
2. Labels
3. Categories
4. Layers of semantic analysis (content, authors etc.)
5. Facts relevant for each analysis level as a graph
6. Relevance to other documents

In our example string, we could have the following outputs displayed in a graph structure:
1. Summary - “Document talks about large language models and their characteristics”
2. Labels -\[ “NLP”, “data”, LLM”\]
3. Categories - \[“Text”\]
4. Layers - \[“Semantic analysis”, “Structural analysis”\]
5. Nodes and edges of the graph
6. Links between this document and other documents mentioning LLMs in the graph

**This is what a single, processed document would look in graph form:**![Visualization of a single processed document in graph form](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fprocessed_document_graph_99192760f1.png&w=3840&q=75)

4. Finally, we can search the graph and associated vector store to retrieve information of interest. This approach opens a variety of ways to do a search. For example, we could:
Get all documents with category “LLM”
Get all documents where in the summary we mention “LLM”
Find all documents that talk about the training of LLMs via vector search, and then return associated summaries
Search only a part of the graph that focuses on “Semantic analysis” to retrieve information about the concept of an LLM and its definition

Using cognee and dlt+DuckDB+graphs, we can connect and enrich datasets that were previously unrelated, as well as analyze the data more effectively to get better, more deterministic insights.

## Why build RAGs?

By integrating DuckDB with Cognee, RAG developers can seamlessly use a relational store and have a metastore available for their documents and data.

The following sections will cover some basic strategies for building RAGs, including the use of vector and graph stores. We will focus on the data preparation aspect of the flow, using tools like dlt to help us along the way. Finally, we will create a simple loader to demonstrate how structuring data for RAGs could work.

## Can you run RAGs without a metastore and DuckDB?

A simple answer is: yes. If you are running a simple RAG as a demonstration, you will probably not need a metastore.

However, in case you want to run a RAG in production, things become more complicated.

You often need to maintain specific user contexts, organize and store the data, load IDs, and, in general, write a lot of code to ensure your data does not get overwritten and can be retrieved when needed, as well as that you have the appropriate guardrails in place to make it work.

## How DuckDB and DLT solve these challenges

Dlt and DuckDB can help us build a RAG system in several ways.

RAG systems usually need loaders and the ability to receive and process multiple data types. Once the data is loaded, we sometimes need to perform additional analysis on the datasets or extract summaries in order to provide information to our RAG so that it can navigate the large amounts of provided data more efficiently.

In the demo below, we show how to perform the following tasks:

1. Load the data to Cognee using dlt.
2. Create metadata and have a reliable store of typical data engineering tasks performed, such as data extraction, normalization, validation, transformation, and more.
3. Retrieve the information from DuckDB in order to enable cognee to use an out-of-the-box system for creating deterministic LLM outputs.
4. Create an additional metastore for document processing.

![An example RAG system using congee](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fcongee_architecture_a85c09dc45.png&w=3840&q=75)

## Step-by-step tutorial

First, let’s add some data:

```python
Copy code

import requests
import os
import os

# URL of the file you want to download
url = 'https://www.libraryofshortstories.com/storiespdf/soldiers-home.pdf'

# The path to the folder where you want to save the file
folder_path = '.data/example/'

# Create the folder if it doesn't already exist
if not os.path.exists(folder_path):
   os.makedirs(folder_path)

# The path to the file where you want to save the PDF
file_path = os.path.join(folder_path, 'soldiers-home.pdf')

# Download the file
response = requests.get(url)

# Check if the request was successful (status code 200)
if response.status_code == 200:
   with open(file_path, 'wb') as file:
       file.write(response.content)
   print(f'File downloaded and saved to {file_path}')
else:
   print(f'Failed to download the file. Status code: {response.status_code}')

import cognee
from os import listdir, path

data_path = path.abspath(".data")

results = await cognee.add("file://" + file_path, "example")

for result in results:
   print(result)
```

We can use DuckDB to easily fetch the datasets we need:

```scss
Copy code

datasets = cognee.datasets.list_datasets()
print(datasets)
for dataset in datasets:
  print(dataset)
  data_from_dataset = cognee.datasets.query_data(dataset)
  for file_info in data_from_dataset:
      print(file_info)
```

And we can also interact with DuckDB directly:

```python
Copy code

import duckdb
from cognee.root_dir import get_absolute_path

db_path = get_absolute_path("./data/.cognee_system")
db_location = db_path + "/cognee.db"
print(db_location)

db = duckdb.connect(db_location)

tables = db.sql("SELECT DISTINCT schema_name FROM duckdb_tables();").df()
print(list(filter(lambda table_name: table_name.endswith('staging') is False, tables.to_dict()["schema_name"].values())))
```

Next, we can create graphs out of our datasets:

```ini
Copy code

import cognee

graph = await cognee.cognify("example")
```

Now, it’s time to search:

```python
Copy code

from cognee.api.v1.search.search import SearchType

query_params = {
   "query": "Tell me about the soldier and his home",
}

results = await cognee.search(SearchType.SIMILARITY, query_params)

for result in results:
   print(result)
```

The context that is returned is the following:

```vbnet
Copy code

['Soldier’s Home\nErnest Hemmingway\nKrebs went to the war from a Methodist college in Kansas. There is a picture which shows him \namong his fraternity brothers, all of them wearing exactly the same height and style collar. He \nenlisted in the Marines in 1917 and did not return to the United States until the second division \nreturned from the Rhine in the summer of 1919.\nThere is a picture which shows him on the Rhine with two German girls and another corporal. \nKrebs and the corporal look too big for their uniforms. The German girls are not beautiful. The \nRhine does not show in the picture.\nBy the time Krebs returned to his home town in Oklahoma the greeting of heroes was over. He \ncame back much too late. The men from the town who had been drafted had all been welcomed \nelaborately on their return. There had been a great deal of hysteria. Now the reaction had set in. \nPeople seemed to think it was rather ridiculous for Krebs to be getting back so late, years after \nthe war was over.\’...]
```

## Conclusion

DuckDB, dlt and Cognee play a crucial role in optimizing and supporting RAG systems, thereby providing solutions to the challenges of data handling and processing. We can streamline the management of diverse data types through efficient loaders and robust data operations which are essential for the functioning of RAG systems.

In our demonstration, we used DuckDB as a metastore and dlt to load various datasets into the system and efficiently manage data-related tasks including extraction, normalization, validation, and transformation.

As a next step, we may want to try DuckDB for storing embeddings and create an analytical layer to enrich the graph with additional information.

### TABLE OF CONTENTS

[What is Retrieval-Augmented Generation?](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions/#what-is-retrieval-augmented-generation)

[Challenges of building RAGs](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions/#challenges-of-building-rags)

[Why build RAGs?](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions/#why-build-rags)

[Can you run RAGs without a metastore and DuckDB?](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions/#can-you-run-rags-without-a-metastore-and-duckdb)

[How DuckDB and DLT solve these challenges](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions/#how-duckdb-and-dlt-solve-these-challenges)

[Step-by-step tutorial](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions/#step-by-step-tutorial)

[Conclusion](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions/#conclusion)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Building Vector Search in DuckDB](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FSearch_Using_Duck_DB_series_1_of_3_007effdde5.png&w=3840&q=75)](https://motherduck.com/blog/search-using-duckdb-part-1/)

[2024/04/19 - Adithya Krishnan](https://motherduck.com/blog/search-using-duckdb-part-1/)

### [Building Vector Search in DuckDB](https://motherduck.com/blog/search-using-duckdb-part-1)

Discover the power of AI search by using vector embeddings in natural language processing in the first blog in our informative three-part series! We'll cover the basics of vector embeddings and cosine similarity using DuckDB and MotherDuck.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response