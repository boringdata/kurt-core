---
title: hack-night
content_type: tutorial
source_url: https://motherduck.com/hack-night
indexed_at: '2025-11-25T20:37:01.144440'
content_hash: b7c50bbf0ba2814e
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# Quickstart Challenge

![Header](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGroup_48096402_b6ae83825f.png&w=3840&q=75)

## Use **Hugging Face** datasets and **MotherDuck** to enrich and prepare your dataset for your project.

Check out the example we've included below to see how you could explore endangered species, and a couple downstream ideas. Feel free to explore your own ideas and be creative!

- While the examples below cover Python and SQL, MotherDuck supports multiple clients, such as Node.JS, Golang, Java, and Rust. More information on these clients is available [here](https://duckdb.org/docs/api/overview).
- You can also use the [MotherDuck Web UI](https://app.motherduck.com/) to explore data, visualize your tables with [Column Explorer](https://motherduck.com/blog/introducing-column-explorer/), and take advantage of MotherDuck’s AI SQL error fixer, [FixIt](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/).

## Getting Started with MotherDuck in Python

### Head to [https://motherduck.com](https://motherduck.com/), and create an account.

- Every new account receives a 30-day free trial of the MotherDuck Standard Plan, with no credit card required.
- After the end of your Standard Plan free trial, your account will automatically move to the MotherDuck Free Plan, no action needed on your part.

### How to get started with MotherDuck in Python:

- In the MotherDuck UI, grab an access token to connect with Python.
- Next, run the following in Python:

```ini
Copy code

!pip install duckdb==1.0.0
import duckdb

# Connect to MotherDuck con = duckdb.connect('md:?motherduck_token=<your_motherduck_token>')

# Run a sample query using MotherDuck
res = con.execute("""
SELECT
  created_date, agency_name, complaint_type,
  descriptor, incident_address, resolution_description
FROM
  sample_data.nyc.service_requests
WHERE
  created_date >= '2022-03-27' AND
  created_date <= '2022-03-31';
""")

# Fetch MotherDuck query results to pandas df
df = res.df()
```

### Reading a dataset from Hugging Face using Python:

```ini
Copy code

# Run a query on Hugging Face data, using MotherDuck
hf_query = con.execute("""
SELECT *
FROM read_parquet('hf://datasets/<user>/<dataset-name>/data/*.parquet'));
""")
```

Read more about using Hugging Face with DuckDB and MotherDuck [in the documentation here](https://duckdb.org/docs/extensions/httpfs/hugging_face.html).

## Example Using SQL

### Start with [this dataset](https://huggingface.co/datasets/datonic/threatened_animal_species) of 150k endangered species:

- The dataset has very little information about the species. So it would be ideal to enrich with data from Wikipedia to enable downstream tasks: https://huggingface.co/datasets/wikimedia/wikipedia

```sql
Copy code

-- Load endangered animal species dataset from Hugging Face (hf)
CREATE OR REPLACE TABLE animals AS (SELECT * FROM read_parquet(
'hf://datasets/datonic/threatened_animal_species/data/threatened_animal_species.parquet'));

-- Load wiki en dataset from hf (this may take a few minutes)
CREATE OR REPLACE TABLE wiki AS (SELECT * FROM read_parquet('hf://datasets/wikimedia/wikipedia/20231101.en/*'));

-- Join both datasets, and create a table in MotherDuck
CREATE OR REPLACE TABLE animals_wiki AS (SELECT * FROM animals LEFT JOIN wiki ON wiki.title = animals.scientific_name);

-- Create a SHARE of your database, to share it with others in MotherDuck
(Learn more about shares here: https://motherduck.com/docs/key-tasks/sharing-data/sharing-overview)
CREATE SHARE hacknight FROM my_db (ACCESS UNRESTRICTED);
```

## Sample Analysis Ideas with SQL

```sql
Copy code

-- Show a sample of endangered animal species, including their wikipedia info
SELECT * FROM animals_wiki LIMIT 100;

-- Check how many animal species have a wikipedia entry
SELECT count(*) FROM animals_wiki WHERE text IS NOT NULL;

-- Check the distribution of endangerment categories across all species
SELECT category, count(*) AS cnt FROM animals_wiki
GROUP BY category
ORDER BY cnt DESC;

-- Check how many wikipedia articles contain the word “endangered” and which endangerment category those animals are in
SELECT category, count(*) AS cnt FROM animals_wiki
WHERE text IS NOT NULL AND text LIKE '%endangered%'
GROUP BY category
ORDER BY cnt DESC;
```

## Downstream Task Ideas

- How many endangered duck species are there?
- DuckDB versions are named after duck species. Which DuckDB version has the most endangered duck as its namesake?
- Help Wikipedia editors keep endangerment information in articles up-to-date.
- Try to find most relevant Wikipedia article for animals that didn’t have an exact match based on the scientific\_name.
- Enrich endangered species data with structured data extracted from Wikipedia articles.

![Footer](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGroup_48096401_99dbfb925f.png&w=3840&q=75)

Authorization Response