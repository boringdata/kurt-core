---
title: small-data-sf-recap
content_type: event
source_url: https://motherduck.com/blog/small-data-sf-recap
indexed_at: '2025-11-25T19:57:14.543060'
content_hash: 3b51767f0f3cb71e
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Small Data is bigger (and hotter 🔥) than ever

2024/10/19 - 12 min read

BY

[Sheila Sitaram](https://motherduck.com/authors/sheila-sitaram/)

In late September, we held the first [Small Data SF](https://www.smalldatasf.com/2024) with our friends at [Turso](https://turso.tech/) and [Ollama](https://www.ollama.com/), a two-day, in-person event featuring hands-on workshops and technical talks and sessions.

With more than 250 attendees and a packed agenda, we gathered in San Francisco to learn how to take a smaller, more pragmatic approach to simplifying our work. We mingled, shared ideas, started conversations with our awesome community, and listened to over 20 speakers with novel outlooks on this topic.

Let’s take a moment to recap what we learned.

**But first, here are a few stats about the event itself:**

- 14 keynote and technical sessions
- 1 practitioner panel of data and AI leaders with in-the-trenches experience
- 7 hands-on, instructor-led workshops
- 80+ net promoter score (NPS), which likely means we’ll be doing this again 😊

## Emerging Trends in Small Data

> “I think Small Data is a very important trend…maybe the most important trend right now.” – George Fraser, [Fivetran](https://www.fivetran.com/) Founder and CEO

Small Data is mighty, and it isn’t just about the [Small Data Manifesto](https://motherduck.com/blog/small-data-manifesto/).

**Our top learnings and insights from Small Data SF 2024 focus on several key themes -**

- Real Data Volumes Aren’t as Big as we Thought
- Agency Matters: The Future is Flexible and Multi-Engine
- The True Cost of Big Data: Time, Money, and Complexity
- Local-First, Cloud-Second Architectures
- The Power of Smart AI and Local Models
- 'Hot Data’ Rising: A Return to Joyful Data Workflows

## The Case for Real Data

> “How big are your actual queries? The fact that you've got a Petabyte of logs sitting on disk doesn't matter if all you're looking at is the last seven days.” - [Jordan Tigani](https://x.com/jrdntgn)

Thanks to the separation of storage and compute, working datasets tend to be much smaller than overall data volumes, and tools like [DuckDB](https://www.duckdb.org/) have been [pivotal in driving the shift in focus toward processing not-so-big data volumes efficiently](https://duckdb.org/2024/10/04/duckdb-user-survey-analysis.html).

While MotherDuck founder and CEO Jordan Tigani highlighted how businesses often deal with datasets that don’t require the complexity and cost overhead of big data systems to deliver business insights, others, like [Benn Stancil](https://benn.substack.com/), urged the audience to innovate and build better solutions to help users interpret and derive meaning out of smaller datasets.

[Lindsay Murphy](https://www.linkedin.com/in/lindsaymurphy4/), Head of Data at [Hiive](https://www.hiive.com/), took yet another approach to the topic of real data and implored the audience to think inside the box and use constraints to drive innovation and prioritization over the endless pursuit of more data, dashboards, and _trashboards_ for the sake of it.

Finally, a broader theme from the talks centered on our actual data workflows and use cases. To underscore the importance of data ingestion, which modern benchmarks fail to capture effectively, Fivetran CEO George Fraser shared that about 30% of most analytics workloads can be attributed to data ingest.

## Agency Matters: The Future is Flexible and Multi-Engine

> “...I do believe that the future will be a multi-engine data stack where we will choose different tools and how to execute based on the scale of the data, but hopefully, our APIs and workflows will become more and more common so that we can work locally and deploy anywhere.” - [Wes McKinney](https://x.com/wesmckinn?lang=en)

With the rise of multi-engine architectures enabled by the emergence of the data lakehouse architecture, flexibility is being taken to new heights without sacrificing costs or efficiency. Speakers including Wes McKinney, [Posit PBC](https://posit.co/) Principal Architect and Co-founder of [Apache Arrow](https://arrow.apache.org/) and [Pandas](https://pandas.pydata.org/), retraced the history of modern hardware and data warehousing that has given way to the emergence of the Small Data ethos. In the 2010s, we collectively realized a need for interoperable table and columnar data formats that can be used portably across different programming languages and processing engines.

DuckDB Labs’ [Richard Wesley](https://www.linkedin.com/in/riwesley/) also highlighted the provenance of computing that led to the [creation of DuckDB](https://www.youtube.com/watch?v=yp6yFsHszCY) by recounting his own journey in software and computing. He emphasized the ability of great software to integrate and talk to other tools and systems with connectors and data transformation. As the glue that ties together this emerging ecosystem, DuckDB has notably [helped make way for new tools and ways of working](https://github.com/duckdb/community-extensions).

> “Everything's much more pluggable than it used to be. You used to have to pick a tool, and that was the tool you used…so if you had a problem that was untenable with cheaper tools or whatever, then that was the tool you ended up using for everything because you were locked into your overall stack…Now, we \[have\] the option to compose our approaches to different problems.” - [James Winegar](https://www.linkedin.com/in/james-winegar/), [CorrDyn](https://www.corrdyn.com/) CEO

## Big Data is Costly and Complex

> “We were promised these _previously unimagined insights_…and instead we got these directional vibes, where you look at the chart, and you're like, it’s ‘up-ish,’ I don't know.” - [Benn Stancil](https://www.linkedin.com/in/benn-stancil/)

The 'cloud tax' and inflated processing costs in incumbent platforms underscore the inefficiencies of big data infrastructure that have sparked a shift toward more cost-efficient solutions.

Several speakers, including Benn Stancil and [Turso](https://turso.tech/) Co-founder and CEO [Glauber Costa](https://www.linkedin.com/in/glommer/), discussed how big data systems are often overengineered to meet the needs of most businesses, who are looking for insights and support with interpreting their normal-sized data.

In a world where single nodes and scaling out are becoming a more standard architectural pattern, Glauber’s proposal to make per-user tenancy a more widespread model is highly appealing thanks to its flexibility and simplicity. By giving each user their own database, developers won’t have to worry about things like role-level security because the database becomes their access boundary and eliminates the need for caching.

[Gaurav Saxena](https://www.linkedin.com/in/gsaxena81/), Principal Engineer at [Amazon Redshift](https://aws.amazon.com/) and author of ['Why TPC is Not Enough'](https://assets.amazon.science/24/3b/04b31ef64c83acf98fe3fdca9107/why-tpc-is-not-enough-an-analysis-of-the-amazon-redshift-fleet.pdf), shed some light on the issue of overengineered systems by discussing the inadequacies of TPC benchmarks in providing effective database evaluations and recommendations for customers based on their real needs. His analysis of of the [Redset dataset](https://motherduck.com/blog/redshift-files-hunt-for-big-data/) from Amazon Redshift customers provides insights into query patterns and workload distributions that TPC benchmarks fail to capture. Because databases face a long tail of complex, resource-intensive queries, it is important for them to manage short, repetitive, bursty queries and continuous data ingestion and transformation.

From an end user standpoint, discussions of scalable, interactive data visualizations by University of Washington PhD student [Junran Yang](https://homes.cs.washington.edu/~junran/) also highlighted the need for better ways to interact with data. Both academia and industry are focusing on simplifying data exploration to make insights more accessible and actionable for users. Scalability and interactivity that match user expectations are key to creating practical visualization solutions that use emerging technologies to simplify the complexities of Big Data.

Together, these talks point to a future where simplicity, cost-efficiency, and flexibility dominate the data landscape, with tools and systems tailored to specific needs without sacrificing performance.

## Local-First, Cloud-Second Architectures

> “If you have an application built in this local first way, you can run it without the cloud. You can run it offline for a while and then sync later. Even if the cloud goes away or the company goes out of business, as long as you still have the application and your data, you can keep it running. - [Søren Brammer Schmidt](https://x.com/sorenbs), [Prisma](https://www.prisma.io/) Founder and CEO

Our technological evolution in recent years has focused on modular, scalable systems that can adapt to changing demands. Systems that allow for local development with remote deployment offer better cost controls and performance. The re-emergence of single-node systems and the adaptability of platforms like DuckDB further emphasize and demonstrate this growing trend.

Søren Brammer Schmidt’s discussion on local-first architecture and its potential to revolutionize software development mirrors the broader move towards decentralization and moving the database to the client, close to end users. This trend aligns with a wider theme from other talks around smaller, more efficient data systems that reduce the reliance on cloud infrastructure.

[Chris Laffra](https://x.com/laffra) picked up a different angle on this topic and introduced the audience to his new project, [PySheets](https://pysheets.app/), a local-first open-source project that embeds Excel in Python to reimagine data exploration through graph dependency visualization within spreadsheets while running in the web browser. Inspired by the belief that conventional tools like Jupyter Notebooks and Python in Excel are limiting, PySheets enables intuitive, offline data manipulation without reliance on cloud services.

## Smart AI and Local Models

> “These small models only have maybe 0.5 to 70 billion parameters. They are only a few gigabytes in size, which means they definitely fit on your laptop - heck, they even fit on a phone, and they run on ordinary hardware, so you don't need these really expensive, hard-to-buy clusters of GPUs all wired up in a special way to run them. You can actually run them right here on your existing computer.” - [Jeff Morgan](https://x.com/jmorgan), [Ollama](https://www.ollama.com/) Founder

It’s no secret that AI and machine learning are significantly reshaping content creation, data analysis, and user engagement. Jeff Morgan, a founder of the open-source project [Ollama](https://www.ollama.com/), highlighted its power by demonstrating its ability to run LLMs and Small Language Models locally on consumer-grade laptops. He emphasized the capabilities of faster and more versatile small AI models due to their reduced parameter size and suitability for local operation without network dependency. While small models are not suitable for every task, they provide a unique complement to larger, cloud-based models and offer better performance and flexibility for tailored use cases.

Later in the day, [Buzzfeed](https://www.buzzfeed.com/) Head of Data Science, AI, and Analytics [Gilad Lotan](https://www.linkedin.com/in/giladlotan/) showcased how LLMs and AI tools have been integrated into their generative content systems to enable them to create a participatory style of commenting on newsworthy stories, while [Langchain](https://www.langchain.com/) GTM Lead [Julia Schottenstein](https://www.linkedin.com/in/julia-schottenstein-25424318/) discussed how Langchain’s langraph framework can balance flexibility with reliability to turn traditional directed acyclic graphs (DAGs) into directed cyclic graphs, or agent-based systems where LLMs dynamically control application workflows to allow for a more flexible and iterative workflow.

Inspired by all the excitement around small AI and local models, we recently decided to jump into the fray here at MotherDuck by [embedding a large language model inside SQL](https://motherduck.com/blog/sql-llm-prompt-function-gpt-models/).

## Hot Data Rising: The Simple Joys of Small Data

> “When I think about Small Data, it's that layer of data you're actually using and working with. It equates to **hot data**: the data that’s driving business value and decision-making, not what’s sitting in storage.” - [Celina Wong](https://www.linkedin.com/in/celinaw/), [Data Culture](https://www.datacult.com/) CEO

The key driver of cost and performance efficiency in Big Data systems with separated storage and compute is the size of the hot data. More data doesn’t mean better results, and we closed Small Data SF with a spirited panel discussion on data minimalism moderated by [Ravit Jain](https://www.linkedin.com/in/ravitjain/) to highlight what it takes to deliver real business value for the 99% of organizations that don’t have Big Data.

Even in a Small Data environment, organizations still have considerable stakeholder demands for insights and data-driven decision-making. [Josh Wills](https://x.com/josh_wills) highlighted that unlike the era of Big Data, Small Data is focused on the power and importance of individual machines. Now that laptops are powerful, workloads and use cases that once defaulted to the cloud can be executed locally, in full or in part, on a single machine.

> “We care about individual machines, we are excited about the potential, and we are writing software to optimize the potential of a single machine. We're not just focused on lots and lots of dumb individual machines anymore.” - Josh Wills, Technical Staff at [DatologyAI](https://www.datologyai.com/)

[Jake Thomas](https://www.linkedin.com/in/jake-thomas/), Data Foundations Manager at [Okta](https://www.okta.com/), also touched on the need to optimize for cost efficiency while avoiding the lure of over-engineering or over-provisioning your infrastructure as a defensive strategy against edge-case scenarios that may never come to pass. For 80-90% of everyday insights and analytics use cases, we only work with hot data, the thin slice of data containing the value you need to make business decisions.

Shouldn’t we return to making our data work for us? What happened to making data workflows simple, scalable, and fun? Or, in the words of [Marie Kondo](https://konmari.com/marie-kondo-rules-of-tidying-sparks-joy/): If it doesn’t spark joy, do you need it?

**Small data and AI is more valuable than you think.**

## Celebrating the Small Data Community

The most exciting part of Small Data SF wasn’t just the talks: It was the group of people who came together to build this movement. On site, I quickly lost track of the number of people who flagged me down to ask, _“How did you get such good attendees? When is the next one? How do I get involved?”_

Frankly, I can’t take credit for this. You all decided to show up and bring this event to life by making it yours. And if you didn’t make it this time, I hope it has piqued your curiosity and sparked something in you to find out more so you can think small, develop locally, and ship joyfully! We see you, and we’re hard at work thinking about opportunities to get more people involved.

### See you in 2025?

We’re hard at work putting the finishing touches on recordings of the talks, and we’re scheming up more plans to release these and share them online and potentially in some major cities near you. Stay tuned.

Something small is happening, and it has only just begun. The overwhelming feedback we have received points to one key theme: The people want more opportunities to come together around Small Data!

Thank you to our attendees, speakers, sponsors, and co-organizers who joined us from around the world and to our extended event production team, vendors, and [the MotherDuck team](https://motherduck.com/about-us/) for being on the ground to engage with this small but mighty community. We could not have done this without you, and we look forward to seeing you at [upcoming events](https://motherduck.com/events/).

_[Small Data SF](https://www.smalldatasf.com/) would not have been possible without our friends at [Turso](https://turso.tech/) and [Ollama](https://www.ollama.com/) and our generous sponsors: [Cloudflare](https://www.cloudflare.com/), [dltHub](https://dlthub.com/), [Evidence](https://evidence.dev/), [Omni](https://omni.co/), [Outerbase](https://www.outerbase.com/), [Posit](https://posit.co/), [Tigris Data](https://www.tigrisdata.com/), and [Essence](https://www.essencevc.fund/). Thank you for your support in bringing the very first Small Data SF to life!_

### TABLE OF CONTENTS

[Emerging Trends in Small Data](https://motherduck.com/blog/small-data-sf-recap/#emerging-trends-in-small-data)

[The Case for Real Data](https://motherduck.com/blog/small-data-sf-recap/#the-case-for-real-data)

[Agency Matters: The Future is Flexible and Multi-Engine](https://motherduck.com/blog/small-data-sf-recap/#agency-matters-the-future-is-flexible-and-multi-engine)

[Big Data is Costly and Complex](https://motherduck.com/blog/small-data-sf-recap/#big-data-is-costly-and-complex)

[Local-First, Cloud-Second Architectures](https://motherduck.com/blog/small-data-sf-recap/#local-first-cloud-second-architectures)

[Smart AI and Local Models](https://motherduck.com/blog/small-data-sf-recap/#smart-ai-and-local-models)

[Hot Data Rising: The Simple Joys of Small Data](https://motherduck.com/blog/small-data-sf-recap/#hot-data-rising-the-simple-joys-of-small-data)

[Celebrating the Small Data Community](https://motherduck.com/blog/small-data-sf-recap/#celebrating-the-small-data-community)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Performant dbt pipelines with MotherDuck](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FGroup_48096977_da7dfb8f3a.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-dbt-pipelines/)

[2024/10/07 - Jacob Matson](https://motherduck.com/blog/motherduck-dbt-pipelines/)

### [Performant dbt pipelines with MotherDuck](https://motherduck.com/blog/motherduck-dbt-pipelines)

Learn how to take your dbt pipelines to new heights with MotherDuck. This blog walks through a recap of our recent dbt + MotherDuck workshop from Small Data SF. Happy building!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response