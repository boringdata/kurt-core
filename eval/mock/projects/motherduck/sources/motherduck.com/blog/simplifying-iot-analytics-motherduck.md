---
title: simplifying-iot-analytics-motherduck
content_type: blog
source_url: https://motherduck.com/blog/simplifying-iot-analytics-motherduck
indexed_at: '2025-11-25T19:56:33.892045'
content_hash: c01d4590f80c237e
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Simplifying IoT Analytics with MotherDuck

2025/04/03 - 7 min read

BY

[Faraz Hameed](https://motherduck.com/authors/faraz-hameed/)

How simple can a modern data warehouse really be? As a solutions architect working with large data teams and enterprises, I have witnessed firsthand the complexity that often comes with data systems. But how much of the complexity can be stripped away while maintaining flexibility and control? Are any of the layers, dare I say, unnecessary?

During the recent [Airbyte+MotherDuck Hackathon](https://airbyte.com/blog/and-the-winner-of-the-airbyte-motherduck-hackathon-is), I put this question to the test by building a lean Industrial IoT analytics platform. This blog explores the surprising lessons learned about simplicity in data architecture, using DuckDB and MotherDuck as the foundation. While the technical details live in [GitHub](https://github.com/fhameed1/AirQuacks-Innovation-Lab), here we will focus on a more intriguing question: Where's the sweet spot between simplicity and capability in modern data systems?

## How Simple Can Simple Get? The Case for Simpler Data Systems

The path to data analysis is often paved with complexity. Before you can even touch your data, you are faced with a cascade of decisions:

- Cloud or local?
- Open source or proprietary? (Or maybe the managed proprietary version of open source which the company may market as open source)?
- Which cloud provider?

Even with “managed” solutions the decisions keep coming about machine types, cluster configurations, compute engines, storage and security.

You continue to navigate a maze where each turn presents new choices, each adding cognitive load and, most critically, delaying the moment when you can actually start querying your data.

What does "simple" really mean when it comes to data infrastructure?

Working with MotherDuck was a refreshing experience. Just open a notebook and start querying! Did I know what compute it was running on? No. Did I need to? Eh…maybe? Under the hood, it implements a tenancy architecture which provisions isolated instances for each user with 3 instance types to pick from (as of this writing). The queries were blazing fast with the default selection (granted this was simulated “small” data) and I was focused on what mattered most, getting my hackathon project up and running!

It was almost unsettling at first, this feeling of not being in control of the underlying infrastructure. But as I pushed through that initial discomfort, I found myself amazed by how negligible the cost was. (Seriously, MotherDuck, how are you planning to make money off of this thing?)

I understand the instinct of data teams to want control. There's a certain type of data engineer who needs to know they can pull every lever and turn every knob to optimize their jobs, and they might initially balk at a tool that abstracts these decisions away. For these teams, MotherDuck might not be love at first sight.

But in a world where time-to-value is increasingly critical, the ability to start working with your data immediately, without cognitive overhead, might be worth more than the satisfaction of feeling like a superhero after mastering every system parameter. I found this to be quite liberating!

## Rethinking Client-Server Architecture

One of the most interesting capabilities I discovered working with MotherDuck is "dual execution" and I don't think I initially grasped just how significant this feature is.

Here's why: In traditional client / server architectures, you have to be cognizant of what processes should run where. Should the transformation be pushed down to the server? Is it maybe more efficient to pull data to the client and work locally? Take Pandas, for example (I love you Pandas!). Unless you are carefully using the right APIs in your big data system of choice, it is easy to accidentally pull an entire dataset into local memory when you only needed a small subset. This context switching and data transfer between client and server becomes a mental tax that gets in the way of your project.

MotherDuck's dual execution takes this decision making burden off your shoulders. It automatically determines what should run where, even splitting the query plan itself between client and server. It provides transparency into these decisions through its query plan visualization. During my project, I found myself marveling at how I was using DuckDB as both the client AND server (the exact same compute engine!), while MotherDuck was optimizing the execution path without me having to think about it.

## Simplicity Meets IoT: A Hackathon Project

Here is a quick overview of how these concepts of simplicity and dual execution worked in a real project. For the hackathon, I built an [industrial IoT analytics platform](https://github.com/fhameed1/AirQuacks-Innovation-Lab) for monitoring machines using sensor data.

1. Edge layer ( [FastAPI](https://github.com/fastapi/fastapi?tab=readme-ov-file)) for sensor data simulation
2. [Ngrok](https://ngrok.com/) for connectivity
3. [Airbyte](https://airbyte.com/) for data movement and orchestration
4. [MotherDuck](https://motherduck.com/) for analytics
5. [Streamlit](https://streamlit.io/) for visualization

![img4](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage4_77c8722983.png&w=3840&q=75)

### Edge Layer

This layer represents the physical connection point where your IoT devices would transmit readings in a production environment. The edge layer simulates industrial machine sensors, generating realistic data including:

- Temperature readings (typically averaging around 70°F)
- Vibration measurements
- RPM (revolutions per minute) values

For this demonstration, I created a FastAPI service that generates semi-structured JSON data with controlled randomness (approximately 5% variation) to simulate conditions. The system creates batches of 500 records per request, providing sufficient volume for meaningful analysis.

![img2](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_f2a68989da.png&w=3840&q=75)

### Ingestion Layer

AirByte serves as the data ingestion and orchestration platform, handling the critical task of reliably moving data from the edge to MotherDuck. Key implementation details include:

- Custom Connector Builder: I used AirByte's no code connector builder which helped quickly create an integration with the API endpoint.

- Establishing Connectivity: I used ngrok to create a secure tunnel allowing AirByte (running in the cloud) to access my locally-hosted simulation API.


![img3](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage2_7041908e15.png&w=3840&q=75)

### Analytics Layer

MotherDuck provides our analytics layer (duh!), highlights include:

- **Automatic Schema Detection:** Identifies data types and structures from the semi-structured JSON.
- **Flattening Nested Data:** Simple SQL transformations to flatten nested data and prepare it for analysis.
- **Anomaly Detection:** Using standard deviation calculations, we can identify machines operating outside normal temperature ranges.
- **Natural Language Querying:** The platform's approach to LLMs was refreshing. While I discovered it sends requests to OpenAI under the hood (and this might evolve in the future), what struck me was how the integration prioritized immediate utility over configuration complexity. The SQL assistance through FixIt was notably faster than other copilots I have used, again emphasizing MotherDuck's commitment to rapid time to value.

![img5](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage5_1d7d74d91e.png&w=3840&q=75)

### Application Layer

Streamlit powers our data app that combines:

- **Interactive Visualizations:** Including 3D plots (because why not?) showing relationships between temperature, vibration, and RPM.
- **Filtering Capabilities**: Users can focus on specific machines or time periods.
- **Natural Language Interface:** Users can ask questions about the data in plain English.
- **Anomaly Highlighting:** The system visually emphasizes readings that fall outside normal parameters.

![img3](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage3_23e304bd6a.png&w=3840&q=75)

### DuckDB’s Potential as an Edge Agent

Perhaps the most intriguing future of dual execution to me, having worked with customers in manufacturing, is its potential implications for edge computing. In my project, I simulated IoT data as JSON, but in a real-world scenario, this data would typically come from edge systems via protocols like MQTT. Traditional architectures require a broker -> bridge -> cloud pipeline, but imagine running DuckDB directly at the edge as an "Agent." The dual execution capability could fundamentally simplify how edge systems interact with cloud analytics, potentially eliminating entire layers of complexity in current IoT architectures.

## The Future is Simpler Than We Think (I Hope)

As I reflect on simplicity in data systems, I keep coming back to a fundamental question: What are we really optimizing for? Modern data platforms often err on the side of more control for developers, but my experience with MotherDuck suggests there might be more value on the other end of the spectrum.

For this hackathon project specifically, while the data transformations and storage needs were relatively straightforward, I believe these observations about simplicity and abstraction hold true for more complex scenarios. The ability to iterate quickly and focus on my data needs rather than infrastructure meant I could push the boundaries of what I thought was possible in the given timeframe for the hackathon.

This experience has made me wonder: Are we perhaps best served by data systems, where the goal isn't to meet every possible use case, but rather to make the right choices invisible for the vast majority of data needs? Maybe the future isn't about having more knobs to turn, but about having systems smart enough to turn the right knobs for us.

### TABLE OF CONTENTS

[How Simple Can Simple Get? The Case for Simpler Data Systems](https://motherduck.com/blog/simplifying-iot-analytics-motherduck/#how-simple-can-simple-get-the-case-for-simpler-data-systems)

[Rethinking Client-Server Architecture](https://motherduck.com/blog/simplifying-iot-analytics-motherduck/#rethinking-client-server-architecture)

[Simplicity Meets IoT: A Hackathon Project](https://motherduck.com/blog/simplifying-iot-analytics-motherduck/#simplicity-meets-iot-a-hackathon-project)

[The Future is Simpler Than We Think](https://motherduck.com/blog/simplifying-iot-analytics-motherduck/#the-future-is-simpler-than-we-think)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Vector Technologies for AI: Extending Your Existing Data Stack](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fvectordbvsvectorengine_2683697a32.png&w=3840&q=75)](https://motherduck.com/blog/vector-technologies-ai-data-stack/)

[2025/03/28 - Simon Späti](https://motherduck.com/blog/vector-technologies-ai-data-stack/)

### [Vector Technologies for AI: Extending Your Existing Data Stack](https://motherduck.com/blog/vector-technologies-ai-data-stack)

Understand when to use a vector database and how it differs from vector search engines.

[![Prompting? That’s so 2024. Welcome to Quack-to-SQL.](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fquacktosql_blog_2cff2b4afe.png&w=3840&q=75)](https://motherduck.com/blog/quacktosql/)

[2025/04/01 - MotherDuck team](https://motherduck.com/blog/quacktosql/)

### [Prompting? That’s so 2024. Welcome to Quack-to-SQL.](https://motherduck.com/blog/quacktosql)

Quack to SQL — our first AI model that understands duck sounds and translates them into queries.

[View all](https://motherduck.com/blog/)

Authorization Response