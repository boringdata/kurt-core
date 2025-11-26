---
title: google-sheets-motherduck
content_type: tutorial
source_url: https://motherduck.com/blog/google-sheets-motherduck
indexed_at: '2025-11-25T19:57:07.249721'
content_hash: b0fc0fadd7651451
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Swimming in Google Sheets with MotherDuck

2024/09/04 - 4 min read

BY

[Jacob Matson](https://motherduck.com/authors/jacob-matson/)

## Quack Notes

Often you will have spreadsheets that you want to mash up with other spreadsheets, or data in your database, or some random files on your desktop. With MotherDuck, you can easily handle all of these scenarios. In this series of post, you will learn how to read from Google Sheets in two ways: (1) with publicly-shared sheets and (2) with private sheets.

## Publicly-Shared Sheets

For Google Sheets that are shared with a public link, extracting the sheet data is as simple as using the [read\_csv](https://duckdb.org/docs/data/csv/overview.html) function and passing the URL. There are two things to note here - you will want to make sure to set the format as ‘csv’ and the gid as the tab that you want to load.

```sql
Copy code

FROM read_csv('https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={tab_id}')
```

As a practical example, you can extract the sheet id and tab id from the URL, as seen in the screenshot below.

![Screenshot 2024-08-30 at 9.19.49 AM.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2024_08_30_at_9_19_49_AM_be4c0721c0.png&w=3840&q=75)

I have loaded some [F1 data from kaggle](https://www.kaggle.com/datasets/rohanrao/formula-1-world-championship-1950-2020) into a Google Sheet and made the link public. This Google Sheet has id **'1unpDUkTx8UVhuO0bo2yyC4RrAHNhxGnzJziLu5jeXvw'** with the following tabs:

- [Constructors, gid= **0**](https://docs.google.com/spreadsheets/d/1unpDUkTx8UVhuO0bo2yyC4RrAHNhxGnzJziLu5jeXvw/edit?gid=0#gid=0)
- [Constructor Results, gid= **1549360536**](https://docs.google.com/spreadsheets/d/1unpDUkTx8UVhuO0bo2yyC4RrAHNhxGnzJziLu5jeXvw/edit?gid=1549360536#gid=1549360536)
- [Races, gid= **2031195234**](https://docs.google.com/spreadsheets/d/1unpDUkTx8UVhuO0bo2yyC4RrAHNhxGnzJziLu5jeXvw/edit?gid=2031195234#gid=2031195234)

Depending on the use case, we can use either views or tables. If you want to keep things in sync with the spreadsheet, a view will work best. If you want to do more complex analysis, materializing as a table (or a temp table for this session) are great ideas for better performance.

The code example below creates the destination schema and then loads the data into MotherDuck:

```sql
Copy code

CREATE SCHEMA IF NOT EXISTS f1;

CREATE OR REPLACE TABLE f1.races AS
FROM read_csv('https://docs.google.com/spreadsheets/d/1unpDUkTx8UVhuO0bo2yyC4RrAHNhxGnzJziLu5jeXvw/export?format=csv&gid=2031195234');

CREATE OR REPLACE TABLE f1.constructors AS
FROM read_csv('https://docs.google.com/spreadsheets/d/1unpDUkTx8UVhuO0bo2yyC4RrAHNhxGnzJziLu5jeXvw/export?format=csv&gid=0');

CREATE OR REPLACE TABLE f1.constructor_results AS
FROM read_csv('https://docs.google.com/spreadsheets/d/1unpDUkTx8UVhuO0bo2yyC4RrAHNhxGnzJziLu5jeXvw/export?format=csv&gid=1549360536');
```

This allows easy subsequent analysis, for example, identifying the top scoring teams in the [constructors championship each year](https://en.wikipedia.org/wiki/List_of_Formula_One_World_Constructors%27_Champions).

```sql
Copy code

SELECT
    c."name" as constructor_name,
    r.year::text as year,
    sum(cr.points) as points_scored,
    count(*) as races
FROM f1.constructor_results cr
LEFT JOIN f1.races r on r.raceid = cr.raceid
LEFT JOIN f1.constructors c on c.constructorid = cr.constructorid
GROUP BY ALL
HAVING points_scored > 0
ORDER BY points_scored desc
```

![Screenshot 2024-08-30 at 10.02.52 AM.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2024_08_30_at_10_02_52_AM_5ec6d8895d.png&w=3840&q=75)

## Private Sheets

In order to load private sheets into MotherDuck, we need to handle Google Authentication. This is a complex topic, so I'll leave the details to this [tutorial by Saturn Cloud](https://saturncloud.io/blog/how-to-get-google-spreadsheet-csv-into-a-pandas-dataframe/).

The high-level overview is that you need to do the following:

1. Create a Service Account in Google Cloud
2. Create an Access Token for that Service Account
3. Add the Service Account as user with access to your Google Sheet
4. Create an Access Token for MotherDuck

That being said, importing a table into MotherDuck is simple as this bit of code. It should be noted this assumes that you store your Tokens in your `.env` file.

```python
Copy code

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import duckdb
import os
import json

# create & load creds
creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS_JSON'))
creds = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)

# create the service
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()
# note that we use literal tab name instead of gid
result = sheet.values().get(spreadsheetId='1unpDUkTx8UVhuO0bo2yyC4RrAHNhxGnzJziLu5jeXvw', range = 'Constructors').execute()

# create the df with the column headers based on the values in the first row of the sheet
df = pd.DataFrame(result.get('values', [])[1:], columns=result.get('values', [])[0])

# create a duck connection
con = duckdb.connect(database='md:my_db?motherduck_token=' + os.getenv('MOTHERDUCK_TOKEN'))

# create a table
con.query("create or replace table main.google_sheets as select * from df")
```

You will note that in this case that tables, not views, are used - because python runtime is outside of MotherDuck, views are not possible, as they will reference objects that the user's scope will not have access to.

## Getting started with MotherDuck

Try out [MotherDuck](https://app.motherduck.com/) for free, explore our integrations like the one with Google Sheets, and keep coding and quacking!

### TABLE OF CONTENTS

[Quack Notes](https://motherduck.com/blog/google-sheets-motherduck/#quack-notes)

[Publicly-Shared Sheets](https://motherduck.com/blog/google-sheets-motherduck/#publicly-shared-sheets)

[Private Sheets](https://motherduck.com/blog/google-sheets-motherduck/#private-sheets)

[Getting started with MotherDuck](https://motherduck.com/blog/google-sheets-motherduck/#getting-started-with-motherduck)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Small Data SF: The Agenda is now live…with *NEW* hands-on workshops](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F1080x1350_4_f9e191578d.png&w=3840&q=75)](https://motherduck.com/blog/small-data-sf-workshops-agenda/)

[2024/08/29 - Sheila Sitaram](https://motherduck.com/blog/small-data-sf-workshops-agenda/)

### [Small Data SF: The Agenda is now live…with \*NEW\* hands-on workshops](https://motherduck.com/blog/small-data-sf-workshops-agenda)

We had such an awesome response to Small Data SF after launch: It was so great that we decided to add an additional day of hands-on workshops! Learn more about the full lineup on 9/23 - 9/24 and grab a ticket before it's too late.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response