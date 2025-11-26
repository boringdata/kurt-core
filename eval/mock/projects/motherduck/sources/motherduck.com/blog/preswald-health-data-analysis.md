---
title: preswald-health-data-analysis
content_type: tutorial
source_url: https://motherduck.com/blog/preswald-health-data-analysis
indexed_at: '2025-11-25T19:57:15.394206'
content_hash: 9a11c76fdfca8b8e
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Faster health data analysis with MotherDuck & Preswald

2025/02/14 - 6 min read

BY

[Amrutha Gujjar](https://motherduck.com/authors/%20Amrutha-Gujjar/)

## From large raw datasets to interactive data app in minutes

In this post, we'll explore how to leverage MotherDuck and Preswald's interactive data apps to more easily and quickly analyze large public health datasets, specifically cholesterol measurements at a population scale.

![MotherDuckPreswald-ezgif.com-optimize.gif](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FMother_Duck_Preswald_ezgif_com_optimize_4b193599eb.gif&w=3840&q=75)

### In this post you’ll learn

- How MotherDuck extends DuckDB to handle multi-table queries in the cloud.
- The importance of the read-scaling token for 4x faster data loading, especially when wrangling multiple tables.
- How Preswald helps you build live, Python-based data apps that go beyond static dashboards.

# Challenges researchers face

Public health datasets come in all shapes and sizes, from CSV dumps to relational systems. Linking cholesterol levels to age groups, race/ethnicity, and comorbidities isn’t a single-step process. But existing solutions often require big clusters or fancy ETL pipelines just to run a few multi-join queries. And don’t even get us started on non-interactive dashboards or spreadsheets—they leave scientists clicking “refresh” and crossing their fingers.

### Common Pain points

1. Multiple, fragmented tables: e.g., demographics, lab results, comorbidities.
2. Slow ingest and overhead: “Scaling up” typically means big clusters or advanced ETL.
3. One-dimensional dashboards: Spreadsheets and static BI can’t handle evolving questions in real time.

# MotherDuck to the Rescue

MotherDuck is powered by the DuckDB engine you know and love, but supercharged in the cloud:

- Write standard SQL queries (no new query language to learn)
- Lightning-fast aggregations. DuckDB’s columnar engine plus in-memory operations.
- Automatically offload. If your dataset doesn’t fit on your laptop, MotherDuck picks up the slack.

# Preswald: interactive data apps in Python

**Preswald** gives you a near-instant route to interactive data apps, without forcing you to wade through a sea of JavaScript frameworks or pricey BI licenses.

- Lightweight. Build dynamic dashboards with nothing but Python.
- Charts refresh as soon as data changes.
- No complicated front-end code or vendor lock-ins.
- Anyone with the app link can start exploring data.

Preswald is especially handy for public health folks who want to query large data one minute and spin up a live interactive chart the next. You don’t need to become a web developer to let your colleagues filter cholesterol ranges by age group or compare comorbidity severity across different ethnicities.

# Bringing It All Together: A Quick Demo

1. Install Dependencies
2. Connect to MotherDuck
3. Query the Cholesterol Table
4. Build a Preswald Dashboard (line chart, bar chart, scatter plot)
5. Run & View Your Interactive App

## Step 1: Install Dependencies

Make sure you have `duckdb`, `pandas`, `plotly`, and `preswald` installed in your Python environment.

```bash
Copy code

pip install duckdb pandas plotly preswald
```

## Step 2: Connect to MotherDuck

You can connect to MotherDuck using your **MotherDuck token**. By default, `duckdb.connect("md:my_db")` will look for an environment variable called `MOTHERDUCK_TOKEN`. If you’d like **read-scaling** for faster queries, append `?read_scaling_token=YOUR_TOKEN_HERE` to the connection string.

```python
Copy code

import duckdb

# Example with environment variable:
# export MOTHERDUCK_TOKEN=<your_token_here>
con = duckdb.connect("md:my_db")

# OR with read scaling explicitly:
# con = duckdb.connect("md:my_db?read_scaling_token=<your_token_here>")
```

## Step 3: Query the Cholesterol Table

In this example, we’ll pull data from a table named `DQS_Cholesterol_in_adults_age_20`. Once connected, run a standard SQL query to bring your data into a Pandas DataFrame.

```python
Copy code

# 1. Query your table
df = con.execute("SELECT * FROM DQS_Cholesterol_in_adults_age_20").df()

# 2. Take a quick peek
print(df.head())
```

This shows you the first few rows, confirming you have the data you expect.

## Step 4: Build a Preswald Dashboard

We’ll build three Plotly charts and present them with Preswald:

1. A **line chart** showing cholesterol estimates over time
2. A **bar chart** comparing age-adjusted vs. crude estimates
3. A **scatter plot** to visualize estimates across different subgroups

Here’s the [**full code**](https://github.com/StructuredLabs/preswald/tree/main/examples/health) with comments explaining each part:

```python
Copy code

import pandas as pd
import duckdb
import plotly.express as px
from preswald import text, plotly, view

# ----------------------------------------------------------------------------
# STEP A: Connect to MotherDuck
# ----------------------------------------------------------------------------
con = duckdb.connect("md:my_db")
df = con.execute("SELECT * FROM DQS_Cholesterol_in_adults_age_20").df()

# ----------------------------------------------------------------------------
# STEP B: Add descriptive text for Preswald
# ----------------------------------------------------------------------------
text("# Cholesterol Data Exploration")
text("Below are several charts that help us visualize cholesterol estimates.")

# ----------------------------------------------------------------------------
# STEP C: Create a line chart of ESTIMATE over TIME_PERIOD
# ----------------------------------------------------------------------------
text("## Chart A: Trend of Cholesterol Estimates Over Time")

# Filter out rows that don’t have an actual ESTIMATE
df_line = df.dropna(subset=["ESTIMATE"]).copy()

fig_a = px.line(
    df_line,
    x="TIME_PERIOD",
    y="ESTIMATE",
    color="ESTIMATE_TYPE",  # e.g., "Percent of population, age adjusted" vs "crude"
    markers=True,
    title="Cholesterol Estimate by Time Period"
)
plotly(fig_a)

# ----------------------------------------------------------------------------
# STEP D: Create a grouped bar chart comparing ESTIMATE_TYPE
# ----------------------------------------------------------------------------
text("## Chart B: Comparison of Age Adjusted vs. Crude Estimates")

fig_b = px.bar(
    df_line,
    x="TIME_PERIOD",
    y="ESTIMATE",
    color="ESTIMATE_TYPE",
    barmode="group",
    title="Age Adjusted vs. Crude Estimates"
)
plotly(fig_b)

# ----------------------------------------------------------------------------
# STEP E: Create a scatter plot of ESTIMATE vs. SUBGROUP
# ----------------------------------------------------------------------------
text("## Chart C: Scatter Plot of Estimate vs. Subgroup")

fig_c = px.scatter(
    df_line,
    x="SUBGROUP_ID",
    y="ESTIMATE",
    color="GROUP",      # e.g. "Total" vs. "Race and Hispanic origin"
    size="ESTIMATE",
    hover_data=["TIME_PERIOD", "ESTIMATE_TYPE"],
    title="Cholesterol Estimate by Subgroup"
)
plotly(fig_c)

# ----------------------------------------------------------------------------
# STEP F: Render the final output in Preswald
# ----------------------------------------------------------------------------
# We'll also show a table preview at the bottom.
view(df)

# Close the DuckDB connection if you like
con.close()
```

### _What’s Happening in Each Section_

1. **Connect to MotherDuck**: We use `duckdb.connect("md:my_db")` to establish a connection.
2. **Fetch Data**: A simple SQL query to pull all rows from the `DQS_Cholesterol_in_adults_age_20` table into a DataFrame.
3. **Preswald Text**: We insert headings and descriptions (`text()`) so people viewing the dashboard know what they’re looking at.
4. **Line Chart**: Shows cholesterol estimates vs. time, separated by `ESTIMATE_TYPE`.
5. **Bar Chart**: Compares different `ESTIMATE_TYPE` categories within each time period (grouped bars).
6. **Scatter Plot**: Visualizes how `ESTIMATE` varies by `SUBGROUP_ID` (e.g., an age or demographic marker), coloring by `GROUP`.
7. **View**: Finally, we call `view(df)` to render everything as an interactive web app.

## Step 5: Run & View Your Interactive App

With everything in place, run the script using Preswald:

`preswald run my_script.py`

This launches a local server. Open the provided URL in your web browser, and you’ll see your line chart, bar chart, scatter plot, plus a data table preview. From here, you can:

- Filter or pivot your data (if you add user inputs)
- Refresh the script for near-instant updates
- Share the app link with colleagues for real-time collaboration

# Bottom Line

Preswald is the quick, straightforward way to turn your data queries into interactive dashboards for broader consumption. Coupled with MotherDuck, you get speed and scalability for large datasets plus an easy path to real-time exploration (without spinning up a separate BI tool or writing tons of custom front-end code).

Ready to get quacking? If you have any questions or want to share how you’re using MotherDuck with Preswald, drop us a line in the community Slack. Here’s the [code](https://github.com/StructuredLabs/preswald/tree/main/examples/health) from the example

### TABLE OF CONTENTS

[From large raw datasets to interactive data app in minutes](https://motherduck.com/blog/preswald-health-data-analysis/#from-large-raw-datasets-to-interactive-data-app-in-minutes)

[Step 1: Install Dependencies](https://motherduck.com/blog/preswald-health-data-analysis/#step-1-install-dependencies)

[Step 2: Connect to MotherDuck](https://motherduck.com/blog/preswald-health-data-analysis/#step-2-connect-to-motherduck)

[Step 3: Query the Cholesterol Table](https://motherduck.com/blog/preswald-health-data-analysis/#step-3-query-the-cholesterol-table)

[Step 4: Build a Preswald Dashboard](https://motherduck.com/blog/preswald-health-data-analysis/#step-4-build-a-preswald-dashboard)

[Step 5: Run & View Your Interactive App](https://motherduck.com/blog/preswald-health-data-analysis/#step-5-run-view-your-interactive-app)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![MotherDuck for Business Analytics: GDPR, SOC 2 Type II, Tiered Support, and New Plan Offerings](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FPricing_v2_1_f4d4004588.png&w=3840&q=75)](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/)

[2025/02/11 - Sheila Sitaram](https://motherduck.com/blog/introducing-motherduck-for-business-analytics/)

### [MotherDuck for Business Analytics: GDPR, SOC 2 Type II, Tiered Support, and New Plan Offerings](https://motherduck.com/blog/introducing-motherduck-for-business-analytics)

Introducing new features designed to better support businesses looking for their first data warehouse, including SOC 2 Type II and GDPR compliance, tiered support, read scaling, and a new Business Plan.

[![How to build an interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFabi_blog_023f05dd0e.png&w=3840&q=75)](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/)

[2025/02/12 - Marc Dupuis](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/)

### [How to build an interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis)

Interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai

[View all](https://motherduck.com/blog/)

Authorization Response