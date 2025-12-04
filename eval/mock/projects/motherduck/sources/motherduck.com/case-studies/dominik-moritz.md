---
title: dominik-moritz
content_type: tutorial
source_url: https://motherduck.com/case-studies/dominik-moritz
indexed_at: '2025-11-25T20:02:32.559062'
content_hash: acc878c938bc34f3
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO CASE STUDIES](https://motherduck.com/case-studies/)

# How Mosaic by Dominik Moritz Achieved Interactive Browser Visualization of 18 Million Data Points

With MotherDuck, it only took an hour to get an app up and running, which was pretty cool. It uses 18 million rows of data, but once it’s loaded, we have all this interactivity right on the website. And since it's all coming from MotherDuck, we can create a shareable snapshot of our data that others can attach to and query.

![Dominik Moritz's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdominik_berlin_f8a31170af.jpg&w=3840&q=75)

Dominik Moritz

Professor

[![Dominik Moritz company logo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FCarnegie_Mellon_University_wordmark_svg_0a953fa401.png&w=3840&q=75)](https://www.cmu.edu/)

Mosaic is an extensible framework that leverages a database (usually DuckDB) for scalable processing, which allows for linking data visualizations, tables, input widgets, and other data-driven components. This framework is ideal for managing data-intensive applications and visualizations, enabling users to interactively visualize and explore millions, or even billions, of data points. Charts typically update with interactive frame rates, which is only possible because of Mosaic's optimizations and some nice features of DuckDB, which MotherDuck enhances.

MotherDuck is a great option for building analytics applications in the browser because it allows us to offload computation to a server when needed. I was able to build a [Mosaic demo](https://github.com/domoritz/mosaic-motherduck) in just one evening, which allowed me to explore 18 million data points from the [Gaia dataset](https://gea.esac.esa.int/archive/) in my web browser. Although the dataset isn't massive, it's incredible that I can work with it without having to download it locally.

While [Mosaic](https://idl.cs.washington.edu/papers/mosaic/) coordinates and optimizes queries and creates client-side data cube indexes for fast updates, many of its performance benefits directly result from DuckDB's efficiency. For example, DuckDB's columnar, vectorized execution makes it easier to run these optimized queries on only the necessary columns, resulting in faster execution. Another advantage of DuckDB is its relatively compact binary. This makes it a great target to compile and run entirely in the browser using WebAssembly, allowing us to run the queries closer to the user and avoid slow network roundtrips. **Even short delays in linked interactive charts can frustrate users and hinder exploration, which has been shown to reduce the number and quality of insights discovered.** DuckDB in the browser gives us short latencies over much larger datasets than what was previously possible in a browser.

Yet, sometimes, datasets are too large for the browser. Luckily, Mosaic can call a remote DuckDB server to execute expensive queries. However, we also have to pay the latency to the remote server for queries over small data cube indexes that Mosaic uses to optimize interactions. This is where MotherDuck's hybrid execution architecture can give us a huge boost in performance!

![1.5-tier architecture](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2F1_5_architecture_f73f2c95b2.png&w=3840&q=75)

**With MotherDuck, we can run queries in a hybrid fashion across a local DuckDB instance and the MotherDuck server.** MotherDuck can create an execution plan to optimize whether to run queries locally on DuckDB or remotely on the server based on query complexity and the location of the data. Large datasets can stay on the server, while small indexes can stay local and close to the user. Because the same database is embedded locally and in the cloud, MotherDuck gives us the option to process data closer to the source. If we typically run expensive queries using our full data set, we can instead run these queries closer to the data while avoiding the need to manage and move data manually.

**And best of all, building on MotherDuck means I don't have to manage the server myself. Everything works transparently.**

## Build insanely interactive data apps

_If you’re interested in building applications with the [MotherDuck WebAssembly (Wasm) SDK](https://motherduck.com/product/app-developers#webassembly-wasm-sdk), please [connect with us](mailto:support@motherduck.com) or [join the community](https://slack.motherduck.com/?__hstc=122295063.e2be54004ac93dc71fb3e430d552098c.1710193754866.1712184786165.1712238924378.84&__hssc=122295063.1.1712238924378&__hsfp=1717932986) \- we’d love to learn more about your use case and what you’re building!_

Authorization Response