---
title: duckdb-ecosystem-newsletter-december-2024
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-december-2024
indexed_at: '2025-11-25T19:58:24.020490'
content_hash: adbb8d5cb89bcbe1
has_code_examples: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: December 2024

2024/12/11 - 6 min read

## Hey, friend 👋

Hi everyone, [Jacob](https://www.linkedin.com/in/jacobmatson/) here with my first newsletter. I am pumped to share some great links and highlights, delivered right to your inbox.

In this December issue, I’ve gathered ten great links, covering topics from business models to benchmarks and a few other pieces. My personal favorite of course has to do with spreadsheets, and importantly the ability to read from and write to them, all with SQL inside of DuckDB. Enjoy!

If you have any feedback or links you think we missed, we would love your feedback over at [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftobi.jpg&w=3840&q=75)

### Tobias Müller

Tobias Muller is a notable builder of DuckDB things, in addition to writing about them on his blog, [tobilg.com](http://tobilg.com/). Of note recently is the great [sql-workbench.com](http://sql-workbench.com/), an in-browser IDE with some really nice capabilities that extend the experience of DuckDB, like charting and integrated AI query assistance. He wrote an [awesome article explaining it](https://tobilg.com/using-duckdb-wasm-for-in-browser-data-engineering) on his blog. Thank you Toby for always pushing the envelope with DuckDB and writing about it in public for us to share!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [Data goes Blue? Extracting analytics from Bluesky](https://motherduck.com/blog/how-to-extract-analytics-from-bluesky/)

Mehdi dives into Bluesky, the open source social network with fully open APIs (remember when the other site had that?). Thanks to some great work done by community members, it's simple to connect to this massive dataset and build your analytics playground. You can also say hello to both [Mehdi](https://bsky.app/profile/mehdio.com) and [yours truly](https://bsky.app/profile/matsonj.com) over there! (and, of course, [MotherDuck's Bluesky account](https://bsky.app/profile/motherduck.com))

### [LLMs in SQL? A real-world application to clean up your CRM data](https://www.dataduel.co/llms-in-sql-a-real-world-application-to-clean-up-your-crm-data/)

Inspired by some of the AI features integrated into MotherDuck, this article discusses leveraging Large Language Models (LLMs) within SQL queries to enhance the quality of firmographic data in Customer Relationship Management (CRM) systems. Nate addresses common challenges in maintaining accurate industry classifications and leverages LLMs, specifically within Snowflake's database environment, to automate the categorization of company names into predefined industry sectors. He aims to streamline data cleaning processes, reduce manual effort, and improve the reliability of CRM data for analytical purposes. It “mostly works” but per usual you still need a human in the loop.

### [DuckDB GSheets](https://duckdb-gsheets.com/)

Archie at [Evidence.dev](http://evidence.dev/) has been up to stuff - specifically building a DuckDB community extension for Google Sheets. While he originally set out to build this to save himself some time, it ended up manifesting as a really nice extension. It supports Auth, Read, and Write to Google Sheets, with a really nice sql abstraction that will look familiar to anyone who has copied Postgres tables:

`COPY source_table TO 'gsheet_id' (FORMAT gsheet);`

Anywhere you can write DuckDB SQL, you can also import and export Google Sheets - powerful! Give the [github repo a star](https://github.com/evidence-dev/duckdb_gsheets) and check it out!

### [Generating a Data App with your MotherDuck Data](https://motherduck.com/blog/data-app-generator/)

MotherDuck’s own Till Döhmen writes about experimenting with [Claude Artifacts](https://support.anthropic.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them) to build a [MotherDuck data app generator](https://github.com/motherduckdb/wasm-client/tree/main/data-app-generator). I think we are seeing things move quite quickly in the data + AI space, and so this end to end example from Till is a great check-in point on current “state of the art” for generative apps. While this is merely a peak into the future, I think he really lays out a clean way to think about these types of flows for data science & other analytical workflows.

### [Driving CSV Performance: Benchmarking DuckDB with the NYC Taxi Dataset](https://duckdb.org/2024/10/16/driving-csv-performance-benchmarking-duckdb-with-the-nyc-taxi-dataset)

Pedro cannot avoid continuing to work on CSVs, this time in the context of the NYC taxi dataset. He is very thoughtful about what it means to have a well designed benchmark, and provides code examples for each step of the process. Of particular note is the choice to track “Avg. deviation of CPU usage from 100%” as metric, which informs a bit about how the DuckDB Labs folks think about the effectiveness of DuckDB - it should use all available compute all the time!

### [Why the Quack will you use DuckDB?](https://blog.det.life/why-the-quack-will-you-use-duckdb-32a39ab3fc6d)

Dudhraj Sandeep gives us five reasons why you should check out DuckDB. You’ll have to click through to the article to see all five reasons, but he offers examples from handling complex queries with ease (and speed!) to operating in resource-constrained environments, and a few other scenarios where DuckDB shines.

### [David's Substack on the DuckDB Foundation Model](https://davidsj.substack.com/p/foundation?triedRedirect=true)

David Jayatillake writes a bit about DuckDb’s amazing rise, where he clearly lays out how the DuckDB Foundation with DuckDB Labs and supporting orgs (like MotherDuck & Volton) are building an alternative model for bringing this type of infrastructure to life. This framing is helpful especially for those that are unclear on how the organizations differ. It also shares a timely reference to “Santa as a Duck” that is worth clicking through just to see!

### [DuckDB WebMacro](https://github.com/quackscience/duckdb-extension-webmacro)

The team behind [quackscience](https://github.com/quackscience) brings us a new DuckDB function to allow github gists to be shared and loaded as Macros.

### [Lightning-Fast Analytics: DuckDB + WASM for Large Datasets in the Browser](https://medium.com/@davidrp1996/lightning-fast-analytics-duckdb-wasm-for-large-datasets-in-the-browser-43cb43cee164)

David Rodriguez shows off how to use DuckDB-WASM to make your analytics lightning-fast and your workflows ridiculously efficient—no backend required. This article dives into the mechanics of how DuckDB-WASM works, explores its limitations, and provides practical examples to get you started.

### [Valentina adds MotherDuck support](https://valentina-db.com/en/discussions/10463-valentina-release-14-6-improves-sql-editor,-better-charts-duckdb-1-1-2-support\#reply-10487)

I always love to see more tools adding MotherDuck support, and Valentina is no exception. They have recently added support in their Valentina Studio product to allow users to seamlessly connect to MotherDuck and build analytical queries inside their IDE. This feature is available in version 14.6 and later.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [DuckCon \#6 in Amsterdam](https://pydata.org/nyc2024/tickets/)

**31 January, Amsterdam, Netherlands - 2:30 PM Central European Time**

DuckCon #6, DuckDB's next user group meeting in Amsterdam, the Netherlands. The event will be in person + streamed online on the DuckDB YouTube channel. The [agenda has been published](https://duckdb.org/events/2025/01/31/duckcon6/) on the DuckDB website.

### [Airbyte + MotherDuck $10,000 Hackathon](https://airbyte.com/hackathon-airbytemotherduck)

**Now Until January 20th, 2025**

With the launch of the new MotherDuck connector for Airbyte, we're thrilled to continue our partnership with MotherDuck by announcing our upcoming hackathon that brings together the power of Airbyte and MotherDuck to solve the needs of delivering modern data integration, AI, and analytics solutions.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-december-2024/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-december-2024/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-december-2024/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-december-2024/#upcoming-events)

Subscribe to DuckDB Newsletter

E-mail

Subscribe to other MotherDuck news

Submit

Subscribe

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![The Serverless Backend for Analytics: Introducing MotherDuck’s Native Integration on Vercel Marketplace](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FMother_Duck_Vercel_native_integration_1_7a4de6924b.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-vercel-marketplace-native-integration/)

[2024/12/09 - Sheila Sitaram](https://motherduck.com/blog/motherduck-vercel-marketplace-native-integration/)

### [The Serverless Backend for Analytics: Introducing MotherDuck’s Native Integration on Vercel Marketplace](https://motherduck.com/blog/motherduck-vercel-marketplace-native-integration)

MotherDuck's native integration is now available on Vercel Marketplace. Developers can finally streamline their application maintenance overhead when building embedded analytics components and data apps. Start building with templates and a demo app!

[![Visualizing text embeddings using MotherDuck and marimo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FMarimo_collab_1_ff9142ff31.png&w=3840&q=75)](https://motherduck.com/blog/MotherDuck-Visualize-Embeddings-Marimo/)

[2024/12/11 - Myles Scolnick](https://motherduck.com/blog/MotherDuck-Visualize-Embeddings-Marimo/)

### [Visualizing text embeddings using MotherDuck and marimo](https://motherduck.com/blog/MotherDuck-Visualize-Embeddings-Marimo)

Visualizing text embeddings using MotherDuck and marimo

[View all](https://motherduck.com/blog/)

Authorization Response