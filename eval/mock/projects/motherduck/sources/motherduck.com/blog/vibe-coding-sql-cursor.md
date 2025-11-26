---
title: vibe-coding-sql-cursor
content_type: tutorial
source_url: https://motherduck.com/blog/vibe-coding-sql-cursor
indexed_at: '2025-11-25T19:56:32.890361'
content_hash: 5a8b932fcf007e05
has_code_examples: true
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# I Made Cursor + AI Write Perfect SQL. Here's the Exact Setup

2025/06/27 - 11 min read

BY

[Jacob Matson](https://motherduck.com/authors/jacob-matson/)

The AI confidently returns 847 lines of SQL. You run it. ERROR: column 'user\_segments' doesn't exist. You fix that. ERROR: invalid syntax near 'LATERAL'. You fix that too. ERROR: cannot resolve 'customer\_lifetime\_value\_v2\_final'.

Twenty minutes later, you're manually rewriting the query the AI "helped" you create.
We've all been there with AI-generated SQL. The promise is intoxicating: describe what you want, get working code. But anyone who's actually tried it knows the reality—endless debugging cycles where you end up rewriting everything anyway.

After a ton of frustration with chat interfaces and slow databases, I decided to flip the script. Instead of fixing the AI's mistakes, what if the AI could see and fix its own mistakes? What if it could execute its code, analyze errors, peek at your actual schema, and iterate until it works?

I built exactly that setup using Cursor and a self-correcting AI workflow with MotherDuck and DuckDB. The result? AI that writes SQL that actually works on the first try—or fixes itself until it does.
Here's the exact system I use, step by step.

## Why Your Current AI-SQL Workflow Is Probably Broken

There’s a few things you want to avoid if you are using AI-driven SQL workflows:

**Running on Production:** In the worst-case scenario, you're running unverified, AI-generated code directly on your live database. Even with a replica, the stakes are high. I still remember getting prod access for the first time over a decade ago when replicas weren't standard practice - the thought still makes me nervous.

**The Workload isn’t Isolated:** You have no idea if the AI will generate clean, efficient SQL. A runaway query with an unfortunate CROSS JOIN can consume massive resources, affecting other users and potentially running up a large bill. Nobody wants to be the person who accidentally "fork bombs" their Snowflake instance.

**Separate Write and Execute Loops:** You end up being the manual bridge between two different contexts: your LLM for code generation and your SQL client for execution. When you see an error, you must copy it and feed it back to the LLM. It's inefficient and frankly quite frustrating.

## A Better Approach: Let Your SQL Fly with the Right Flock

![image5.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage5_1b4dcdbeff.png&w=3840&q=75)

We can design a much better system by asking a few simple questions:

- What if we could work on a safe, accurate replica of our data?
- What if our AI's workload was completely isolated on our local machine?
- What if the LLM could run its own SQL and fix its own errors right away?

We can achieve this by combining three key technologies:

1. **MotherDuck & DuckDB:** The scalable cloud data warehouse that serves as our single source of truth.
2. **uv:** By leveraging the uv package manager, we can simply ignore our python environment (our AI usually does too, but sometimes will still try to fall back to `pip`).
3. **Cursor:** The AI-first editor that functions as our development environment, the control center for our AI assistant.

The core concept is creating a feedback loop where the AI doesn't just write code - it executes it locally against a replica of the data, observes what happens, and learns from it in real-time.

## Setting Up Your SQL Co-pilot

Here's how to build this workflow step by step so you can try it with your own data.

### Step 1: Bring Your Data Home (Safely)

First, we use MotherDuck's hybrid architecture to create a local copy of our database. With a single SQL command, we can replicate a database from our MotherDuck cloud account to a local DuckDB file.

For this example, I'm using the [Foursquare places](https://docs.foursquare.com/data-products/docs/places-overview) dataset called FSQ:

```sql
Copy code

-- Filename: clone_db.sql
attach 'md:';
attach 'local.db' as local_db;
COPY FROM DATABASE fsq TO local_db;
```

Running this command pulls the data from MotherDuck and creates a local\_fsq.duckdb file on my machine. Now I have a perfect, isolated sandbox.

**Practical Tip:** If your production dataset is very large, you don't need to pull all of it. DuckDB's [`SAMPLE`](https://duckdb.org/docs/stable/sql/query_syntax/sample.html) feature lets you grab a representative subset of your data, keeping your local copy manageable and responsive.

### Step 2: Give Your AI a Map (Schema as XML)

An LLM's biggest limitation is context. To get quality SQL, we need to provide the AI with a map of our database structure.

Through conversations with researchers at MotherDuck, we've found that providing the schema as an XML file within the prompt's context is particularly effective for getting good results.

We can automate this with a simple Python script that connects to our local DuckDB file, extracts the schema, and saves it as an XML file:

```python
Copy code

# Filename: scripts/get_schema.py
"""Script to extract database schema from DuckDB and output as XML.

This script connects to a DuckDB database, extracts the schema information,
and outputs it in a machine-readable XML format that can be used in Cursor.
"""

import duckdb
import xml.etree.ElementTree as ET
from pathlib import Path

def get_schema_as_xml(db_path: str) -> ET.Element:
    """Extract schema from DuckDB database and return as XML Element.

    Args:
        db_path: Path to the DuckDB database file

    Returns:
        ET.Element: XML Element containing the database schema
    """
    # Connect to the DuckDB database
    conn = duckdb.connect(db_path)

    # Get all tables
    tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()

    # Create XML root
    root = ET.Element("database")
    root.set("name", Path(db_path).stem)

    # For each table, get its schema
    for (table_name,) in tables:
        table_elem = ET.SubElement(root, "table")
        table_elem.set("name", table_name)

        # Get column information
        columns = conn.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'main' AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """).fetchall()

        for col_name, data_type, is_nullable in columns:
            column_elem = ET.SubElement(table_elem, "column")
            column_elem.set("name", col_name)
            column_elem.set("type", data_type)
            column_elem.set("nullable", is_nullable)

    conn.close()
    return root

def save_schema_to_file(root: ET.Element, output_path: str) -> None:
    """Save the XML schema to a file with pretty printing.

    Args:
        root: XML Element containing the schema
        output_path: Path where to save the XML file
    """
    ET.indent(root)
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    db_path = "local.db"
    output_path = "schema/local_db_schema.xml"

    root = get_schema_as_xml(db_path)
    save_schema_to_file(root, output_path)
    print(f"Schema saved to {output_path}")
```

Now, whenever we chat with our AI, we'll include this local\_db\_schema.xml file as context.

### Step 3: Define the Rules of Engagement

This is where we automate the "run and fix" loop. In Cursor, we can create [rules](https://docs.cursor.com/context/rules) to give the LLM persistent instructions for the project.

First, we define our SQL rule. We tell the AI that whenever it writes a SQL file, it should immediately execute it using the DuckDB CLI against our local database file. This creates the essential feedback mechanism:

```md
Copy code

---
description:
globs: *.sql
alwaysApply: false
---
# SQL Rules
This rule applies to all SQL files in the project.
## File Pattern
*.sql
## Description
When working with SQL files, we use DuckDB as our database engine. SQL files should be executed using the command `duckdb local.db -f {file}`.
## Formatting
- Use 4 spaces for indentation
- Use SQLFluff for formatting with DuckDB dialect
- Format on save
## Commands
- Run SQL file: duckdb local.db -f {file}
## Best Practices
- Use consistent naming conventions
- Include comments for complex queries
- Use proper indentation for readability
- Follow DuckDB's SQL dialect specifications
```

Next, we set up similar rules for Python work, directing the AI to use `uv` for package management. This ensures clean, reproducible environments for any data visualization or scripting we do.

```markdown
Copy code

---
description:
globs: *.py
alwaysApply: false
---
# Python Rules
This rule applies to all Python files in the project.

## File Pattern
*.py

## Description
When working with Python files, we use uv as our package manager and runtime. Python files should be executed using the command `uv run {file}`.

## Formatting
- Use 4 spaces for indentation
- Follow PEP 8 style guide
- Use Ruff for code formatting and linting
- Format on save

## Best Practices
- Use type hints where appropriate
- Include docstrings for functions and classes
- Use virtual environments for dependency management
```

With these pieces in place, our intelligent co-pilot is ready to waddle into action.

## Putting It to the Test: Finding a New Restaurant Location

With our setup ready, let's walk through a real-world analysis. Our goal is to find a suitable location to open a new restaurant in Oakland, California, using our Foursquare places dataset.

When working with an LLM this way, I like to think of it as partnering with a clever but sometimes literal-minded colleague. You need to guide it, not just issue commands.

### The First Question

We start by asking for the basic data.

> **Prompt:** "Give me a SQL query for restaurants in Oakland, CA."

![image6.gif](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage6_de3aad1717.gif&w=3840&q=75)

By providing our schema and SQL rules as context, the AI generates a correct query, saves it to a file, and immediately runs it using the DuckDB CLI. It sees that the query executes successfully and returns over 3,000 rows.

### From Data to Visualization

A table with 3,000 rows isn't particularly insightful. Let's visualize it.

> **Prompt:** "Let's use Folium to chart this data on a map. Create the map in HTML and then serve it with Python."

![image4.gif](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage4_7a4de6a273.gif&w=3840&q=75)

Recognizing the need for visualization, the AI switches from SQL to Python. Following our rules, it adds `folium` and `pandas` to our `pyproject.toml` file, writes a Python script to read the SQL output and generate a map, and serves it on a local webserver. Just like that, we have an interactive map showing every restaurant in our dataset.

### Iterating for Clarity

The map looks a bit crowded with individual points. Let's refine it.

> **Prompt:** "Can we render this as a heatmap instead of points?"

![image2.gif](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage2_4ae5079101.gif&w=3840&q=75)

The AI modifies the Python script, importing the `HeatMap` plugin from Folium and regenerating the map. Now we have a much clearer view of restaurant density across Oakland.

### The 'Aha!' Moment - Self-healing SQL

Now for the real test. Let's ask a much more complex question that requires spatial analysis.

> **Prompt:** "Load the spatial extension for DuckDB. Find me three 1-acre locations where we have high restaurant density, but no African cuisine within one mile. Score the locations based on the number of other restaurants nearby."

![image3.gif](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage3_a4bf3d754e.gif&w=3840&q=75)

This is where things get interesting. The AI's first attempt at this complex spatial query returns... **zero results**.

In a traditional workflow, this is where you'd start the tedious debugging cycle. But in our closed-loop system, the AI recognizes its failure. It sees the empty result set and immediately begins troubleshooting _itself_. It thinks, "The query ran but returned nothing. Let's run a diagnostic query. Do we even have any African restaurants in the dataset?" It runs a `COUNT(*)` on that category, confirms the data exists, and then reevaluates its initial query. It realizes its initial spatial join was too restrictive and broadens the search radius before running the query again.

This is when you realize you're working with something more than just a code generator. The AI is functioning as an analyst. It can reason about its own failures and adjust course without your intervention.

After a few self-corrections, it produces a new query that works, identifying three promising locations.

### Putting It All Together

> **Prompt:** "Add these three proposed locations as colored boxes on our heatmap."

![image1.gif](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_2a925b42ad.gif&w=3840&q=75)

The AI updates the Python script one more time, adding a new layer to our Folium map. We now have a complete, informative visualization: a heatmap of existing restaurant density with three clear boxes highlighting the top-scoring, underserved areas for our new venture.

## Moving Beyond Hope-Based Coding

By building this workflow, we've transformed how we interact with AI. We've gone from a fragile, manual process to one that is:

**Safe:** We never put our production database at risk. All experimentation happens in an isolated local environment.

**Fast:** The feedback loop is nearly instantaneous. DuckDB's performance means even complex queries run quickly.

**Intelligent:** The AI doesn't just write code; it executes, observes, debugs, and refines it.

This changes your role from a simple "prompter" to a "director" of an AI agent. You guide the high-level strategy using your knowledge and intuition, while the AI handles implementation and debugging details. It's a practical partnership that makes SQL work quicker and with fewer headaches.

Ready to try it yourself? You can:

- **Clone the demo repository [here](https://github.com/matsonj/cursor_eda)**
- **Connect it to your [MotherDuck account](https://app.motherduck.com/) and start quacking away at your own data.**
- **Join our [community on Slack](https://slack.motherduck.com/) to share what you build!**

Don't let your SQL queries waddle aimlessly through your database anymore. With this approach, they can swim with precision - and you might find yourself with more time to tackle the interesting problems that actually require human creativity.

### TABLE OF CONTENTS

[Why Your Current AI-SQL Workflow Is Probably Broken](https://motherduck.com/blog/vibe-coding-sql-cursor/#why-your-current-ai-sql-workflow-is-probably-broken)

[A Better Approach: Let Your SQL Fly with the Right Flock](https://motherduck.com/blog/vibe-coding-sql-cursor/#a-better-approach-let-your-sql-fly-with-the-right-flock)

[Setting Up Your SQL Co-pilot](https://motherduck.com/blog/vibe-coding-sql-cursor/#setting-up-your-sql-co-pilot)

[Putting It to the Test: Finding a New Restaurant Location](https://motherduck.com/blog/vibe-coding-sql-cursor/#putting-it-to-the-test-finding-a-new-restaurant-location)

[Moving Beyond Hope-Based Coding](https://motherduck.com/blog/vibe-coding-sql-cursor/#moving-beyond-hope-based-coding)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Getting Started with DuckLake: A New Table Format for Your Lakehouse](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fducklake_5c914ac5f3.png&w=3840&q=75)](https://motherduck.com/blog/getting-started-ducklake-table-format/)

[2025/06/09 - Mehdi Ouazza](https://motherduck.com/blog/getting-started-ducklake-table-format/)

### [Getting Started with DuckLake: A New Table Format for Your Lakehouse](https://motherduck.com/blog/getting-started-ducklake-table-format)

Learn how DuckLake simplifies metadata and brings fast, database-like features to your data lakehouse — with a hands-on example using DuckDB and PostgreSQL

[![Why REST and JDBC Are Killing Your Data Stack — Flight SQL to the Rescue](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fflight_thumbnail_31453866be.png&w=3840&q=75)](https://motherduck.com/blog/flight-sql-vs-rest-vs-jdbc/)

[2025/06/13 - Thomas (TFMV) McGeehan](https://motherduck.com/blog/flight-sql-vs-rest-vs-jdbc/)

### [Why REST and JDBC Are Killing Your Data Stack — Flight SQL to the Rescue](https://motherduck.com/blog/flight-sql-vs-rest-vs-jdbc)

Understand how Flight SQL can speed up how your serve data with DuckDB

[View all](https://motherduck.com/blog/)

Authorization Response