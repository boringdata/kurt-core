---
title: announcing-motherduck-duckdb-in-the-cloud
content_type: blog
source_url: https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud
indexed_at: '2025-11-25T19:57:33.138925'
content_hash: a5ee88402c607603
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Announcing MotherDuck: Hybrid Execution Scales DuckDB from your Laptop into the Cloud

2023/06/22 - 4 min read

BY
MotherDuck team

DuckDB has become widely known as “SQLite for Analytics” – a powerful SQL analytics engine with broad adoption in development workflows, ad-hoc analytics on the laptop and embedded applications. MotherDuck wants to make it even easier to use, so we’ve worked alongside the creators of DuckDB to build a cloud-based serverless analytics platform. Today is a large milestone in that journey – MotherDuck is now available by invitation.

MotherDuck in 100 seconds (by a duck 🦆) - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[MotherDuck in 100 seconds (by a duck 🦆)](https://www.youtube.com/watch?list=PLIYcNkSjh-0zP7fwKzhnbx5ur1Mf80Q_p&v=BINA_ytZXMY)

MotherDuck

Search

Watch later

Share

Copy link

1/1

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

Full screen is unavailable. [Learn More](https://support.google.com/youtube/answer/6276924)

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?list=PLIYcNkSjh-0zP7fwKzhnbx5ur1Mf80Q_p&v=BINA_ytZXMY&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

[Previous (SHIFT+p)](https://www.youtube.com/watch?list=PLIYcNkSjh-0zP7fwKzhnbx5ur1Mf80Q_p&v=BINA_ytZXMY "Previous (SHIFT+p)")

0:00 / 1:51

•Live

•

## Hybrid execution: cloud and laptop working together

Data scientists, analysts, and engineers love DuckDB because it works great no matter where their data lives. Since many data professionals have powerful laptops sitting 85% idle, they often want to bring the data to their local machine to make it even more efficient to crunch, especially when performing ad hoc analysis and development. MotherDuck lets you analyze this local data locally, while still JOINing with data processed in the cloud, giving you efficient use of all your compute resources.

In the example below, the table `yellow_cab_nyc` lives in MotherDuck in the cloud, and I have a CSV on my laptop table with currency conversions. We want to see the average cost of NYC taxi trips by passenger count in different currencies by JOINing these two tables. Yes, we’re seamlessly joining data on my laptop with data in the cloud!

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fexample_hybrid_7bb8f08e2d.png&w=3840&q=75)

You can even do hybrid query execution with data stored in s3, with MotherDuck securely storing and managing your AWS credentials.

![example_s3.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fexample_s3_d97e746203.png&w=3840&q=75)

Note, these examples are part of our [sample datasets and queries](https://motherduck.com/docs/category/sample-datasets--queries/), feel free to run them yourself!

You might wonder how this works under the covers. By connecting your DuckDB instance to MotherDuck, you establish a radically different type of distributed system - one, in which one node is MotherDuck in the cloud, and another node is wherever your DuckDB lives, be it your laptop or a lambda, Python or CLI, JDBC or MotherDuck’s own web app. Both nodes execute queries in concert in the most optimal way, automatically routing parts of queries to the right location.

## MotherDuck includes a web notebook and Git-style Collaboration

Want to run some quick SQL queries without downloading and installing DuckDB? The MotherDuck web application provides a notebook-like UI. This enables you to analyze local CSVs and parquet files, upload them and manage them alongside your other data stored in MotherDuck.

![app_motherduck_beta.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fapp_motherduck_beta_v2_69fbe04dcf.png%3Fupdated_at%3D2023-06-21T23%3A24%3A18.647Z&w=3840&q=75)

As a DuckDB-in-the-cloud company, naturally MotherDuck embeds DuckDB in its web application using WASM. Results of your SQL queries are cached in this DuckDB instance, enabling you to instantly sort, pivot, and filter query results!

Want to share your DuckDB data with colleagues? Using SQL, you can create a shareable snapshot of your data, which your colleagues can easily attach in MotherDuck.
![example_share.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fexample_share_cfe1d14570.png&w=3840&q=75)

This SQL command will return a shareable URL which can then be used by your colleague to access the shared database.
![example_attach.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fexample_attach_ff22a57c32.png&w=3840&q=75)

## Anywhere you can Duck, you can MotherDuck

DuckDB has been starred by over 10k developers on GitHub, and it might be due to the simplicity of getting up and running with a downloadable, open source analytics engine. We want to continue (and improve!) that amazing experience as we bring DuckDB to the cloud.

One way to do this is by ensuring MotherDuck works well with many of the most popular technologies in the modern data stack, including ingestion, orchestration and BI+Visualization tools.

![partner-logos.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpartner_logos_242d207bb6.png&w=3840&q=75)

We strive to make MotherDuck as easy to adopt as DuckDB. To that end, any DuckDB instance in the world running in Python or CLI can connect to MotherDuck with a single line of code. Suddenly, by running this command your DuckDB magically becomes supercharged by MotherDuck. Such ease of onboarding could only have been possible via close collaboration with the creators of DuckDB!

![d_to_md.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fd_to_md_1dfe63b09b.png&w=3840&q=75)

## Continuing to Make Analytics Ducking Awesome

One of the primary reasons we were driven to build a serverless analytics platform on top of DuckDB was their fast-paced innovation. Many features in DuckDB have gone from thoughts in academic papers to committed code in a few weeks.

We’re launching MotherDuck now and doing weekly releases because we admire and want to emulate this speed of execution. Thanks in advance for all the feedback you can provide to make MotherDuck a better product!

## Get Started

[Request an invite](https://motherduck.com/) now to get started using MotherDuck, and join the flock on [slack.motherduck.com](https://slack.motherduck.com/).

And, if you’re in San Francisco next week, don’t forget to [register for the MotherDuck Party](https://motherduck-party.eventbrite.com/), watch DuckDB co-creator Hannes [keynote the Data + AI conference](https://www.databricks.com/dataaisummit/session/data-ai-summit-keynote-thursday), and join MotherDuck co-founder Ryan Boyd in his [technical session](https://www.databricks.com/dataaisummit/session/if-duck-quacks-forest-and-everyone-hears-should-you-care).

### TABLE OF CONTENTS

[Hybrid execution: cloud and laptop working together](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/#hybrid-execution-cloud-and-laptop-working-together)

[MotherDuck includes a web notebook and Git-style Collaboration](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/#motherduck-includes-a-web-notebook-and-git-style-collaboration)

[Anywhere you can Duck, you can MotherDuck](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/#anywhere-you-can-duck-you-can-motherduck)

[Continuing to Make Analytics Ducking Awesome](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/#continuing-to-make-analytics-ducking-awesome)

[Get Started](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/#get-started)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: June 2023](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumbnail_duckdb_newsletter_1_34b0dc65cf.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-seven/)

[2023/06/16 - Marcos Ortiz](https://motherduck.com/blog/duckdb-ecosystem-newsletter-seven/)

### [This Month in the DuckDB Ecosystem: June 2023](https://motherduck.com/blog/duckdb-ecosystem-newsletter-seven)

This Month in the DuckDB Ecosystem: June 2023

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response