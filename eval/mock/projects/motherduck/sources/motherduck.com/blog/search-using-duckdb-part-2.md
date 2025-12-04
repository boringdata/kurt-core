---
title: search-using-duckdb-part-2
content_type: blog
source_url: https://motherduck.com/blog/search-using-duckdb-part-2
indexed_at: '2025-11-25T19:57:23.343470'
content_hash: 3cc6e4cc3d63603f
has_code_examples: true
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Developing a RAG Knowledge Base with DuckDB

2024/05/06 - 6 min read

BY

[Adithya Krishnan](https://motherduck.com/authors/adithya-krishnan/)

_This blog is the second in a series of three on search using DuckDB. It builds on knowledge from the [first blog on AI-powered search](https://motherduck.com/blog/search-using-duckdb-part-1/), which shows how relevant textual information is retrieved using cosine similarity._

Different facets of our work and our lives are documented in different places, from note-taking apps to PDFs to text files, code blocks, and more. AI assistants that use large language models (LLMs) can help us navigate this mountain of information by answering contextual questions based on it. But how do AI assistants even get this knowledge?

Retrieval Augmented Generation (RAG) is a technique to feed LLMs relevant information for a question based on stored knowledge. A knowledge base is a commonly used term that refers to the source of this stored knowledge. In simple terms, it’s a database that contains information from all the documents we feed into our model.

One common method of storing this data is to take documents and chunk up the underlying text into smaller parts (e.g., a group of four sentences) so these ‘chunks’ can be stored along with their vector embeddings. These blocks of text can later be retrieved based on their cosine similarity. At its simplest, a RAG can retrieve relevant information as text and feed it to an LLM, which in turn will output an answer to a question. For example, if we asked a question, we would retrieve the top 3 relevant chunks of text from our knowledge base and feed them to an LLM to generate an answer. Lots of research has been done in the field, from pioneering new, better ways to chunk information, store it, and retrieve it based on a variety of techniques. That said, information retrieval in RAG is typically based on semantic similarity.

How cool would it be to build your own AI-powered personal assistant? In this blog post, we walk through a step-by-step example of how to build an AI-powered knowledge base and use it as a foundation to answer end users’ questions by running embedding and language models.

## Building an AI Assistant with a Local Knowledge Base

Building an AI assistant consists of three parts: the embedding model, the knowledge base, and the LLM that uses relevant information to form the answer. In our example, we use [Llama-Index](https://github.com/run-llama/llama_index), a Python data framework for building LLM applications to put all the pieces of the AI assistant together.

![conceptual architecture](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_d3e01cd0dd.png&w=3840&q=75)

To kick things off, let’s install the dependencies for our project:

```perl
Copy code

pip install llama-index
pip install llama-index-embeddings-huggingface
pip install llama-index-vector-stores-duckdb
pip install llama-index-llms-ollama
```

## Embedding Model with HuggingFace and Sentence Transformers

[HuggingFace](https://huggingface.co/) provides access to a large repository of embedding models. The HuggingFace-LlamaIndex integration makes it easier to download an embedding model from HuggingFace and run embedding models using the Python package SentenceTransformers. In this project, we will use “BAAI/bge-small-en-v1.5,” a small model that generates a vector embedding of 384 dimensions with a maximum input tokens limit of 512. This means that the maximum chunk size of the text will be 512 tokens.

The following code will download and run the model:

```ini
Copy code

from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# loads BAAI/bge-small-en-v1.5, embed dimension: 384, max token limit: 512
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
```

Now, let’s test the model by generating vector embeddings for the following text: “knowledge base”

```python
Copy code

test_embeddings = embed_model.get_text_embedding("knowledge base")
print(len(test_embeddings))

>>> 384
```

When we print the length of the generated embeddings, we get 384, the dimension size of the vector for this model that we mentioned above.

## The Knowledge Base

DuckDB provides a convenient fixed array size and list (variable size) data type to store vector embeddings. LlamaIndex has a DuckDB integration that helps you store your compiled knowledge base and save it to disk for future use.

Next, let’s build our knowledge base by importing the necessary dependencies:

```python
Copy code

# Imports for loadings documents and building knowledge
from llama_index.core import (
    StorageContext,
    ServiceContext,
    VectorStoreIndex,
    SimpleDirectoryReader,
)

# DuckDB integration for storing and retrieving from knowledge base
from llama_index.vector_stores.duckdb import DuckDBVectorStore
```

In this project, we will load documents from a folder called local\_documents using the ‘SimpleDirectoryReader.’

By using the ‘ServiceContext’ object, we can define the chunking strategy for the text in the documents:

```ini
Copy code

# Load the files in the folder 'papers' and store them as Llama-Index Document object
documents = SimpleDirectoryReader("./local_documents").load_data()

# Set the size of the chunk to be 512 tokens
documents_service_context = ServiceContext.from_defaults(chunk_size=512)
```

It’s finally time to build our knowledge base. When we initialize the DuckDBVectorStore and pass it to the StorageContext, LlamaIndex learns that DuckDB should be used for storage and retrieval. The initialization process also tells LlamaIndex how to use DuckDB.

By passing the embedding model, DuckDB storage context, and documents’ context to the VectorStoreIndex object, we can create our knowledge base.

In the following code snippet, the DuckDBVectorStore is initialized by passing a directory location to use to persist your knowledge base:

```ini
Copy code

vector_store = DuckDBVectorStore(
    database_name="knowledge_base",
    persist_dir="./",
    embed_dim=384,
)

storage_context = StorageContext.from_defaults(vector_store=vector_store)

knowledge_base = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context,
    embed_model=embed_model,
    service_context=documents_service_context,
)
```

This means that a database file with the specified database name ‘knowledge\_base’ will be created in the listed directory. It’s important to note that our database file can be reused, which means you can add new documents to it. You can learn more about this [here](https://github.com/run-llama/llama_index/blob/main/llama-index-integrations/vector_stores/llama-index-vector-stores-duckdb/examples/DuckDBDemo.ipynb).

**Note:** It is important to specify the dimensions of the vector embeddings used, as this information will be required for the embedding field data type when we create the table to store the embeddings.

## The Large Language Model (LLM)

One benefit of [Ollama](https://ollama.ai/) is that it lets you run language models on your system. LlamaIndex has a convenient integration for Ollama, enabling you to connect any of your data sources to your LLMs. In this project, we use the ‘llama2’ model, but there are plenty of other models in its library, which you can find here.

Let’s begin by initializing the model:

```ini
Copy code

from llama_index.llms.ollama import Ollama

llm = Ollama(model="llama2", request_timeout=60.0)
```

**Note:** a request timeout has been configured to cancel the request if a response is not obtained within the specified time frame.

## Query Answer Engine

Although small, the model has captured decent knowledge of the world. To provide better context for questions, we can pass relevant knowledge from our knowledge base to the model and generate answers. We do this by building a query engine with our knowledge base and passing the LLM object to the query engine.

With this query engine, you can ask questions, and it will fetch the relevant information from the knowledge base and generate an answer:

```ini
Copy code

# The query engine
query_engine = knowledge_base.as_query_engine(llm=llm)

# Run a query
answer = query_engine.query("...fill in your question...")
```

## Conclusion

Turning documents into a knowledge base for AI with DuckDB is incredibly exciting because you can run this workflow directly on your computer. The possibilities created by having a personalized AI assistant that can browse your documents and answer questions on demand are still emerging, and we can’t wait to see what the future has in store.

Using DuckDB, you can store your knowledge, persist it on disk, and retrieve the relevant information for your AI assistants. As we’ve seen above, the Llama-Index integration is easy to integrate with the other parts of an AI assistant, like the LLM and embedding model.

### TABLE OF CONTENTS

[Building an AI Assistant with a Local Knowledge Base](https://motherduck.com/blog/search-using-duckdb-part-2/#building-an-ai-assistant-with-a-local-knowledge-base)

[Embedding Model with HuggingFace and Sentence Transformers](https://motherduck.com/blog/search-using-duckdb-part-2/#embedding-model-with-huggingface-and-sentence-transformers)

[The Knowledge Base](https://motherduck.com/blog/search-using-duckdb-part-2/#the-knowledge-base)

[The Large Language Model](https://motherduck.com/blog/search-using-duckdb-part-2/#the-large-language-model)

[Query Answer Engine](https://motherduck.com/blog/search-using-duckdb-part-2/#query-answer-engine)

[Conclusion](https://motherduck.com/blog/search-using-duckdb-part-2/#conclusion)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: April 2024](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fapril_2024_fe841dae08.jpg&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2024/)

[2024/04/30 - Luciano Galvão Filho](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2024/)

### [This Month in the DuckDB Ecosystem: April 2024](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2024)

DuckDB Monthly: Dr. Qiusheng Wu, CSVs, 1 Billion Row challenge, duckplyr, and more

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response