---
title: csv-files-persist-duckdb-solution
content_type: blog
source_url: https://motherduck.com/blog/csv-files-persist-duckdb-solution
indexed_at: '2025-11-25T19:57:13.232430'
content_hash: 28f2997ebdb99804
has_code_examples: true
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Why CSV Files Won’t Die and How DuckDB Conquers Them

2025/02/04 - 9 min read

BY

[Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/)

I've been working in the data field for a decade, across various companies, and one constant challenge that’s almost unavoidable is dealing with CSV files.

Yes, there are far more efficient formats, such as [Parquet](https://motherduck.com/learn-more/why-choose-parquet-table-file-format/), which avoid schema nightmares thanks to their typing, but CSV files persist for many reasons:

- They’re easy to edit and read, requiring no dependencies—just open the file.
- They’re universal: many services still exchange data in CSV format.
- Want to download data from social media or your CRM? CSV.
- Need transaction history from your bank? CSV.

However, this simplicity comes with its own set of challenges, especially if you want to process CSVs without breaking pipelines or pulling your hair out.

Fortunately, DuckDB has an exceptional CSV parser. The team behind it invested heavily in building their own, and in this post, I’ll show you a real-world example where I had to parse multiple CSV files. I’ll also share some SQL tricks and demonstrate how smoothly everything worked using DuckDB and MotherDuck, resulting in a ready-to-query database.

The cherry on top? The final output is a database containing all Stack Overflow survey responses from the past seven years. Stick around if you’re curious about extracting insights or querying the data yourself!

## The biggest challenges when reading CSVs

In my opinion, there are four significant challenges when working with CSV files:

1. **Schema Management**
2. **Row-Level Errors**
3. **Encoding Issues**

These challenges become even more complex when handling multiple CSVs that need to be read or joined to each other.

Let’s see how we address these issues with Stack Overflow survey data.

## About the Dataset

Each year, Stack Overflow publishes the results of their developer survey, including raw data in—you guessed it—CSV format. These files are available on their website: [https://survey.stackoverflow.co/](https://survey.stackoverflow.co/).

Here’s an example of how the dataset is organized:

```css
Copy code

├── raw
│   ├── 2011 Stack Overflow Survey Results.csv
│   ├── 2012 Stack Overflow Survey Results.csv
│   ├── 2013 Stack Overflow Survey Responses.csv
│   ├── 2014 Stack Overflow Survey Responses.csv
│   ├── 2015 Stack Overflow Developer Survey Responses.csv
│   ├── 2016 Stack Overflow Survey Results
│   │   ├── 2016 Stack Overflow Survey Responses.csv
│   │   └── READ_ME_-_The_Public_2016_Stack_Overflow_Developer_Survey_Results.txt
│   ├── stack-overflow-developer-survey-2017
│   │   ├── DeveloperSurvey2017QuestionaireCleaned.pdf
│   │   ├── README_2017.txt
│   │   ├── survey_results_public.csv
│   │   └── survey_results_schema.csv
│   ├── stack-overflow-developer-survey-2018
│   │   ├── Developer_Survey_Instrument_2018.pdf
│   │   ├── README_2018.txt
│   │   ├── survey_results_public.csv
│   │   └── survey_results_schema.csv
│   ├── stack-overflow-developer-survey-2019
│   │   ├── README_2019.txt
│   │   ├── so_survey_2019.pdf
│   │   ├── survey_results_public.csv
│   │   └── survey_results_schema.csv
[..]
```

Key observations:

1. **Schema Changes Over the Years**


Some questions and their formats evolve annually, making it difficult to standardize across years.
2. **Pre-2016 Format**


Each column represents a question, with names like:

`What Country or Region do you live in?, How old are you?, How many years of IT/Programming experience do you have?, ...`

Additional challenges include:

• Column names with unusual characters.

• Querying such column names can be tedious.

From 2017 onward, Stack Overflow improved the exports by separating:

• A file containing the answers (columns with clean names for each question).

• A schema file (.csv) that maps question codes to full question text.

To keep things manageable, I focused on datasets from 2017 onward.

## Manual cleaning over automation

We’ve all wasted hours trying to automate tasks that could have been done manually in minutes. This is a common trap for data engineers. Sometimes, quick manual cleanup is the most efficient approach.

Here’s what I did:

• Placed all CSVs in a single folder.

• Renamed files by adding the corresponding year as a prefix (e.g., `<year>_<file_name>`).

• Ensured column names in schema files were consistent (e.g., renamed name to qname where needed).

These steps took less than five minutes and saved me headaches later. Not everything needs to be automated!

## Loading the CSVs

Now for the exciting part: loading the data. DuckDB supports glob patterns for loading multiple files. For complex structures like [Hive partitions](https://duckdb.org/docs/data/partitioning/hive_partitioning.html), it works seamlessly too.

Here’s the core query for loading survey results:

```sql
Copy code

CREATE OR REPLACE TABLE stackoverflow_survey.survey_results AS
    SELECT
        * EXCLUDE (filename),
        substring(parse_filename(filename), 1, 4) as year,
    FROM read_csv_auto(
        'data_2017_2024/*survey_results*.csv',
        union_by_name=true,
        filename=true)
```

**Breakdown:**

1. We `CREATE` a table based on a `SELECT` statement.
2. We select all columns but `EXCLUDE` the filename. This is a path of the containing file; we get this one by enabling `filename=true`.
3. We parse the `filename` to get only the year. As we have a convention on the file name to prefix by `<year>`, we take the first four chars and create a `year` column
4. We use the glob pattern to only load `*survey_results*` as a single table (we'll do another query for the `survey_schemas`)

Alright, let's run this one... 🙏

```sql
Copy code

duckdb.duckdb.ConversionException: Conversion Error: CSV Error on Line: 35365
Original Line: 35499,I am a developer by profession,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA
Error when converting column "Hobbyist". Could not convert string "NA" to 'BOOLEAN'

Column Hobbyist is being converted as type BOOLEAN
This type was auto-detected from the CSV file.
Possible solutions:
* Override the type for this column manually by setting the type explicitly, e.g. types={'Hobbyist': 'VARCHAR'}
* Set the sample size to a larger value to enable the auto-detection to scan more values, e.g. sample_size=-1
* Use a COPY statement to automatically derive types from an existing table.

  file = ./2017_2024_schema/2020_survey_results_public.csv
  delimiter = , (Auto-Detected)
  quote = " (Auto-Detected)
  escape = " (Auto-Detected)
  new_line = \n (Auto-Detected)
  header = true (Auto-Detected)
  skip_rows = 0 (Auto-Detected)
  comment = \0 (Auto-Detected)
  date_format =  (Auto-Detected)
  timestamp_format =  (Auto-Detected)
  null_padding = 0
  sample_size = 20480
  ignore_errors = false
  all_varchar = 0
```

Bad news, it didn't successfully parse the CSVs. But the GREAT news is that we have an excellent log error!

We know :

- On which line we have an issue
- A proper error message `Could not convert string "NA" to 'BOOLEAN'`
- Possibles solutions

This saves so much time! Sometimes, just one row can mess up the whole process, and if the error message isn’t clear, you’re stuck guessing what went wrong. You might even end up throwing out your CSV or trying random fixes over and over.

For us, increasing the sample\_size fixed the problem right away. 👍

## Wrapping up and automate the rest

With the initial query successful, the next steps were to:

1. Repeat the process for schema files.
2. Add row count checks to ensure no data was lost during merging of the CSVs

Here's a generic function to wrap the query we saw and run them depending on the pattern name of the files (either for `results` or `schemas`).

```python
Copy code

CSV_DIR = './data_2017_2024'

# Global configuration
FILE_CONFIGS = [\
    {'pattern': 'schema', 'table': 'survey_schemas'},\
    {'pattern': 'public', 'table': 'survey_results'}\
]

def process_survey_files(csv_dir: str) -> None:
    """
    Process Stack Overflow survey CSV files and load them into DuckDB tables
    """
    con = duckdb.connect('stackoverflow_survey.db')

    for config in FILE_CONFIGS:
        logging.info(f"Processing {config['pattern']} files...")
        con.execute(f"""
            CREATE OR REPLACE TABLE stackoverflow_survey.{config['table']} AS
            SELECT
                * EXCLUDE (filename),
                substring(parse_filename(filename), 1, 4) as year,
            FROM read_csv_auto(
                '{csv_dir}/*{config['pattern']}*.csv',
                union_by_name=true,
                filename=true,
                sample_size=-1
            )
        """)

        # Log row count
        count = con.execute(f"SELECT COUNT(*) FROM stackoverflow_survey.{config['table']}").fetchone()[0]
        logging.info(f"Loaded {count} rows into {config['table']}")

        # Log unique years
        years = con.execute(f"SELECT DISTINCT year FROM stackoverflow_survey.{config['table']} ORDER BY year").fetchall()
        logging.info(f"{config['table']} years: {[year[0] for year in years]}")

    con.close()
```

Finally, we added another function to check row count and make sure we didn't lose any rows during the process :

```python
Copy code

def verify_row_counts(csv_dir: str) -> None:
    """
    Verify that the sum of individual file counts matches the merged table counts
    """
    con = duckdb.connect('stackoverflow_survey.db')

    for config in FILE_CONFIGS:
        pattern = config['pattern']
        table = config['table']

        logging.info(f"\nVerifying {pattern} files counts...")
        individual_counts = 0

        for filename in os.listdir(csv_dir):
            if pattern in filename and filename.endswith('.csv'):
                file_path = os.path.join(csv_dir, filename)
                count = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{file_path}')").fetchone()[0]
                logging.info(f"{filename}: {count} rows")
                individual_counts += count

        merged_count = con.execute(f"SELECT COUNT(*) FROM stackoverflow_survey.{table}").fetchone()[0]
        logging.info(f"Individual {pattern} files total: {individual_counts}")
        logging.info(f"Merged {table} total: {merged_count}")

        assert individual_counts  merged_count, f"{pattern} row count mismatch: {individual_counts} != {merged_count}"

    con.close()
    logging.info("✅ All row counts verified successfully!")
```

## Sharing the dataset

Now that I have a DuckDB database containing both tables (results and schemas), the only thing left is to share it! Let's see how that works with MotherDuck.

I’m using the DuckDB CLI, but this could also be part of a Python script. It’s just four simple commands:

```sql
Copy code

duckdb
D ATTACH 'stackoverflow_survey.db'
D ATTACH 'md:'
D CREATE DATABASE cloud_stackoverflow_survey FROM stackoverflow_survey;
D CREATE SHARE FROM cloud_stackoverflow_survey;
┌─────────────────────────────────────────────────────────────────┐
│                            share_url                            │
│                             varchar                             │
├─────────────────────────────────────────────────────────────────┤
│ md:_share/sample_data/23b0d623-1361-421d-ae77-125701d471e6      │
└─────────────────────────────────────────────────────────────────┘
```

1. We attach the local DuckDB database with `ATTACH` command.
2. We connect to MotherDuck using `ATTACH 'md';`. Note that I have my [`motherduck_token`](https://motherduck.com/docs/key-tasks/authenticating-and-connecting-to-motherduck/authenticating-to-motherduck/#authentication-using-an-access-token) stored in an `ENV`.
3. We upload the database to MotherDuck using the `CREATE DATABASE x FROM x`
4. We create a public share so that anyone can start querying!

To make it even easier for MotherDuck users, I put this one in the existing demo database [`sample_data`](https://motherduck.com/docs/getting-started/sample-data-queries/datasets/), which is attached by default for any users.

## Querying the dataset

This dataset offers plenty of opportunities to uncover insights, but I’ll wrap up this blog with a simple query that wasn’t included in the original StackOverflow study.

I wanted to explore the average happiness score of people based on their work location (remote, in-person, or hybrid).

```sql
Copy code

SELECT RemoteWork,
       AVG(CAST(JobSat AS DOUBLE)) AS AvgJobSatisfaction,
       COUNT(*) AS RespondentCount
FROM sample_data.stackoverflow_survey.survey_results
WHERE JobSat NOT IN ('NA')
  AND RemoteWork NOT IN ('NA')
  AND YEAR='2024'
GROUP BY ALL;
```

and the results :

```sql
Copy code

┌──────────────────────────────────────┬────────────────────┬─────────────────┐
│              RemoteWork              │ AvgJobSatisfaction │ RespondentCount │
│               varchar                │       double       │      int64      │
├──────────────────────────────────────┼────────────────────┼─────────────────┤
│ In-person                            │  6.628152818991098 │            5392 │
│ Remote                               │  7.072592992884806 │           11103 │
│ Hybrid (some remote, some in-person) │  6.944303596894311 │           12622 │
└──────────────────────────────────────┴────────────────────┴─────────────────┘
```

Two interesting takeaways: remote and ybrid workers make up the majority of survey responses, and on average, they seem to be happier too!

Check out [our documentation](https://motherduck.com/docs/getting-started/sample-data-queries/stackoverflow-survey/) if you want to explore this dataset further.

In the meantime, get ready to tackle future CSV challenges with ease—DuckDB and MotherDuck (start for [free!](https://motherduck.com/get-started/)) have got you covered!

* * *

### Why DuckDB’s CSV Parser is Special

- [https://duckdb.org/2023/10/27/csv-sniffer.html](https://duckdb.org/2023/10/27/csv-sniffer.html)
- [https://duckdb.org/2024/12/05/csv-files-dethroning-parquet-or-not.html](https://duckdb.org/2024/12/05/csv-files-dethroning-parquet-or-not.html)
- [Why CSVs Still Matter: The Indispensable File Format](https://youtu.be/I07qV2hij4E?si=DjCapBT3eg5UWLdn)

### TABLE OF CONTENTS

[The biggest challenges when reading CSVs](https://motherduck.com/blog/csv-files-persist-duckdb-solution/#the-biggest-challenges-when-reading-csvs)

[About the Dataset](https://motherduck.com/blog/csv-files-persist-duckdb-solution/#about-the-dataset)

[Manual cleaning over automation](https://motherduck.com/blog/csv-files-persist-duckdb-solution/#manual-cleaning-over-automation)

[Loading the CSVs](https://motherduck.com/blog/csv-files-persist-duckdb-solution/#loading-the-csvs)

[Wrapping up and automate the rest](https://motherduck.com/blog/csv-files-persist-duckdb-solution/#wrapping-up-and-automate-the-rest)

[Sharing the dataset](https://motherduck.com/blog/csv-files-persist-duckdb-solution/#sharing-the-dataset)

[Querying the dataset](https://motherduck.com/blog/csv-files-persist-duckdb-solution/#querying-the-dataset)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![DuckDB Ecosystem: January 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fnewsletter_a65cff5430.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025/)

[2025/01/10 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025/)

### [DuckDB Ecosystem: January 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2025)

DuckDB Monthly #25: PyIceberg, 0$ data distribution and more!

[![Local dev and cloud prod for faster dbt development](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FLocal_Dev_Cloud_Prod_083b07b92e.png&w=3840&q=75)](https://motherduck.com/blog/dual-execution-dbt/)

[2025/01/16 - Jacob Matson](https://motherduck.com/blog/dual-execution-dbt/)

### [Local dev and cloud prod for faster dbt development](https://motherduck.com/blog/dual-execution-dbt)

Spark the Joy of beautiful local development workflows with MotherDuck & dbt

[View all](https://motherduck.com/blog/)

Authorization Response