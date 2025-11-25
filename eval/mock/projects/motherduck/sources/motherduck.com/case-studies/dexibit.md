---
title: dexibit
content_type: case_study
source_url: https://motherduck.com/case-studies/dexibit
indexed_at: '2025-11-25T20:02:54.590039'
content_hash: 7efd79f834a83868
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO CASE STUDIES](https://motherduck.com/case-studies/)

# How Dexibit Unlocked Lightning-Fast Analytics and New Browser-Based Analytics

MotherDuck’s innovative approach to managing data and providing easy-to-use tooling has allowed us to expand our application use cases (e.g., getting data into the client's browser) and offer more value to our customers.

![Ravi Chandra's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fravi_chandra_photo_7db3a4c457.jpg&w=3840&q=75)

Ravi Chandra

Chief Technology Officer

[![Ravi Chandra company logo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdexibit_logo_2d070ff8e3.png&w=3840&q=75)](https://dexibit.com/)

Dexibit provides out-of-the-box analytics and insights solutions to power world-class visitor experiences.

**We adopted MotherDuck as an alternative to traditional data warehousing** to meet our need for efficient analytical queries. We were already using DuckDB, so adding MotherDuck using the same SQL dialect enabled us to seamlessly expand our services to our customers both now and into the future.

Traditionally, we've relied on Postgres, which is flexible but not designed for analytical operations. Now, with MotherDuck and DuckDB, we know that we don't have to worry about performance. In that way, we're driving at it differently.

Moving our production workloads to MotherDuck seemed relatively low-risk since we could experiment with it first. **It was fairly easy to shift from Postgres to MotherDuck thanks to the federation capabilities, and the SQL was very similar.**

Our customers need an interactive dashboard experience, so we really love the performance we get with MotherDuck. It is super fast, and our customers love it. And when we're talking super fast, we're talking about analytical load times being just a few seconds when running many ad hoc queries at once. And that is great when you compare that to alternative solutions.

We get the traditional capabilities with MotherDuck, but one of the great things though is the variety of tools that are provided so we get to do things differently. Using [shares](https://motherduck.com/docs/key-tasks/managing-shared-motherduck-database/), we can create an instance per customer easily as opposed to Postgres, where it’s a hassle to create and manage that many instances. **We've now got these new levers for performance scaling because we can split and store the data and query efficiently as needed.** If we need to handle a load spike or a huge amount of queries, we can spin up more ducklings on demand. Whereas with the traditional data warehouse type approach (Postgres or Snowflake), we've had to just get a bigger box wholesale and then, it was not easy to get a smaller one. As we expand our usage on MotherDuck, our possible use cases for our end customers are expanding.

We are confident we have chosen an innovative partner in the data space who influences our growth with these emergent use cases for our product. If we went with Snowflake, we wouldn't have the option of thinking about getting data into our client's browsers. If we stayed with Postgres, we wouldn't have the option of just connecting to a share.

**With MotherDuck working to solve amazing problems through data, our behaviors have changed because we know we don't have to pay enormous costs every time we run a query, so we've got almost limitless performance.**

Partnering with MotherDuck has brought us endless possibilities as we continue to innovate and grow to provide our customer insights to inspire decisions toward building amazing visitor experiences.

## Build insanely interactive data apps

_If you’re interested in building applications with the [MotherDuck WebAssembly (Wasm) SDK](https://motherduck.com/product/app-developers#webassembly-wasm-sdk), please [connect with us](mailto:support@motherduck.com) or [join the community](https://slack.motherduck.com/?__hstc=122295063.e2be54004ac93dc71fb3e430d552098c.1710193754866.1712184786165.1712238924378.84&__hssc=122295063.1.1712238924378&__hsfp=1717932986) \- we’d love to learn more about your use case and what you’re building!_

Authorization Response