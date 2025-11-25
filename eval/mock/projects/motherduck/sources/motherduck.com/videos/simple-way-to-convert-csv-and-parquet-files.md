---
title: simple-way-to-convert-csv-and-parquet-files
content_type: tutorial
source_url: https://motherduck.com/videos/simple-way-to-convert-csv-and-parquet-files
indexed_at: '2025-11-25T20:44:27.252956'
content_hash: 0215f394eabfe4ec
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

Simple way to convert CSV - Parquet files - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Simple way to convert CSV - Parquet files](https://www.youtube.com/watch?v=Y_GXdbet9Gk)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=Y_GXdbet9Gk&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 1:00

•Live

•

YouTubeShortTutorial

# Simple way to convert CSV and Parquet files

2024/01/17

As developers, we live in the terminal. It’s our command center for everything from Git commits to running applications. But we all have those small, annoying tasks that break our flow—the little papercuts of the development cycle. One of the most common? File format conversion.

You have a Parquet file, but a legacy tool or a colleague needs it in CSV format. Or maybe you have a massive CSV that you want to compress into the more efficient Parquet format. What's your go-to move? Do you spin up a Jupyter notebook and `import pandas`? Do you write a quick, one-off Python script? Or do you resort to a sketchy online file converter?

These interruptions, while small, add up. But what if the perfect tool for the job was already on your machine, ready to go?

Enter DuckDB. While you might know it as a powerful embedded analytical database, it's also a versatile Swiss army knife for your data. Because it's a lightweight, serverless tool that speaks fluent SQL and natively understands formats like Parquet, CSV, and JSON, it's the perfect utility for lightning-fast file conversions directly from your command line.

Let's build a powerful, reusable conversion utility in just a few minutes.

### Instant File Conversion with a DuckDB One-Liner

First things first, you need the `duckdb` CLI. If you're on macOS, installation is a single command with Homebrew.

```bash
Copy code

brew install duckdb
```

For other operating systems, check out the [official installation documentation](https://duckdb.org/docs/installation/index).

Once installed, you have everything you need. Let's say you have a file named `data.parquet` and you want to convert it to `data.csv`. The magic is a single command that leverages DuckDB's powerful `COPY` statement.

```bash
Copy code

duckdb -c "COPY (SELECT * FROM 'data.parquet') TO 'data.csv' (HEADER, DELIMITER ',');"
```

Let's break down this command to see what's happening:

- `duckdb -c "..."`: This is the key to using DuckDB as a scripting tool. The `-c` flag tells DuckDB to execute the SQL command that follows and then immediately exit. No interactive shell, no fuss—just pure, scriptable execution.
- `COPY (...) TO 'data.csv'`: This is the workhorse. The `COPY` command is incredibly efficient at moving data into and out of DuckDB.
- `(SELECT * FROM 'data.parquet')`: Instead of copying from a table, we're telling DuckDB to copy the result of a query. The magic here is that DuckDB can query files like Parquet or CSV directly, _as if they were database tables_. It automatically infers the file type and schema from the file extension.
- `(HEADER, DELIMITER ',')`: These are options specific to the output format. Here, we're telling DuckDB to include a header row in our final CSV file.

And that's it. In the time it would have taken you to open a new editor tab, you've converted your file.

### Building a Reusable Conversion Script

That one-liner is great, but we can make it even better. The real power of the command line comes from creating reusable, generic tools.

Let's wrap this logic into a simple Bash script. Create a file named `file-converter.sh` somewhere convenient, like `~/scripts/`.

```bash
Copy code

#!/bin/bash
# file-converter.sh

# Check if two arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_file> <output_file>"
    exit 1
fi

INPUT_FILE=$1
OUTPUT_FILE=$2

duckdb -c "COPY (SELECT * FROM '${INPUT_FILE}') TO '${OUTPUT_FILE}';"

echo "Successfully converted ${INPUT_FILE} to ${OUTPUT_FILE}"
```

Make the script executable:

```bash
Copy code

chmod +x ~/scripts/file-converter.sh
```

Now, you have a generic script that takes an input file and an output file as arguments. The final step is to create a shell alias for ultimate convenience. Open your `.zshrc`, `.bashrc`, or equivalent shell configuration file and add this line:

```bash
Copy code

# Add to your .zshrc or .bashrc
alias dconvert='~/scripts/file-converter.sh'
```

Restart your terminal or run `source ~/.zshrc` to apply the changes. Now, witness your new superpower. You can convert files back and forth with a simple, memorable command.

**Convert Parquet to CSV:**

```bash
Copy code

dconvert data.parquet data.csv
# Successfully converted data.parquet to data.csv
```

**Convert CSV to Parquet:**

```bash
Copy code

dconvert data.csv data.parquet
# Successfully converted data.csv to data.parquet
```

It doesn't get simpler than that. You've just built a universal file conversion utility that is faster and more reliable than a custom script and safer than any online tool.

### Conclusion: More Than Just Conversion

We started with a simple problem and ended with an elegant, reusable solution. With one small script, you've added a powerful tool to your developer toolkit, powered by DuckDB.

But don't forget what's happening inside that command. You aren't just copying bytes; you're running a full-fledged SQL query. This opens up a world of possibilities that go far beyond the simple 1-to-1 conversion our `dconvert` alias handles.

What if you only wanted a subset of the data? For more complex tasks, you can bypass the alias and use the `duckdb -c` command directly to run a more powerful query.

```bash
Copy code

# Filter for specific rows before converting
duckdb -c "COPY (SELECT * FROM 'data.parquet' WHERE category = 'A') TO 'filtered_data.csv' (HEADER, DELIMITER ',');"
```

What if you only needed a few columns?

```bash
Copy code

# Select specific columns
duckdb -c "COPY (SELECT user_id, event_timestamp FROM 'logs.parquet') TO 'events.csv' (HEADER, DELIMITER ',');"
```

The `SELECT` statement is your playground. You can perform filtering, transformations, and even simple aggregations as part of your conversion pipeline, all within that single command.

* * *

### Get Started Today

- Try this out and share your favorite DuckDB one-liners with us on [Twitter](https://twitter.com/motherduckcorp)!
- For more details on the options available, check out the official DuckDB documentation for the [`COPY` command](https://duckdb.org/docs/sql/data_loading/copy).
- When your challenges go beyond local files, see how [MotherDuck](https://motherduck.com/) brings the power of DuckDB to the cloud for serverless, collaborative analytics.

...SHOW MORE

## Related Videos

[!["Is DuckDB the Secret to Unlocking Your GIS Potential?" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmaxresdefault_1_c988e40ed0.jpg&w=3840&q=75)\\
\\
14:49](https://motherduck.com/videos/is-duckdb-the-secret-to-unlocking-your-gis-potential/)

[2024-08-29](https://motherduck.com/videos/is-duckdb-the-secret-to-unlocking-your-gis-potential/)

### [Is DuckDB the Secret to Unlocking Your GIS Potential?](https://motherduck.com/videos/is-duckdb-the-secret-to-unlocking-your-gis-potential)

In this video, ‪Mehdi walks you through the basics of working with geospatial data and introduces the DuckDB spatial extension. By the end, you will create your own heatmap using DuckDB, Python, and MotherDuck for sharing and scalability.

YouTube

Tutorial

[!["DuckDB & dataviz | End-To-End Data Engineering Project (3/3)" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fvideo_ta_Pzc2_EE_Eo_23e0b0a9d0.jpg&w=3840&q=75)\\
\\
0:21:46](https://motherduck.com/videos/duckdb-dataviz-end-to-end-data-engineering-project-33/)

[2024-06-27](https://motherduck.com/videos/duckdb-dataviz-end-to-end-data-engineering-project-33/)

### [DuckDB & dataviz \| End-To-End Data Engineering Project (3/3)](https://motherduck.com/videos/duckdb-dataviz-end-to-end-data-engineering-project-33)

In this part 3 of the project, @mehdio explores how to build a Dashboard with Evidence using MotherDuck/DuckDb as a data source.

YouTube

BI & Visualization

Tutorial

[!["One data tool with all its dependencies: DuckDB and extensions" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fvideo_we_RMT_Aj_Udic_9e9f5c6d41.jpg&w=3840&q=75)\\
\\
0:00:55](https://motherduck.com/videos/one-data-tool-with-all-its-dependencies-duckdb-and-extensions/)

[2024-06-21](https://motherduck.com/videos/one-data-tool-with-all-its-dependencies-duckdb-and-extensions/)

### [One data tool with all its dependencies: DuckDB and extensions](https://motherduck.com/videos/one-data-tool-with-all-its-dependencies-duckdb-and-extensions)

Learn about DuckDB extensions, including the ability to query data in your AWS S3-powered data lake.

YouTube

Short

[View all](https://motherduck.com/videos/)

Authorization Response