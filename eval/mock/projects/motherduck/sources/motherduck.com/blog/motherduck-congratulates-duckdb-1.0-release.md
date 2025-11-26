---
title: motherduck-congratulates-duckdb-1.0-release
content_type: blog
source_url: https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release
indexed_at: '2025-11-25T19:57:46.857822'
content_hash: 5a700d9ff7bfada6
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Congratulations to DuckDB Labs On Reaching 1.0!

2024/06/03 - 4 min read

BY
MotherDuck team

Earlier today, [DuckDB released version 1.0](https://duckdb.org/2024/06/03/announcing-duckdb-100), marking a key maturity milestone for the nimble yet powerful analytics database quickly taking over the world. MotherDuck would like to _quackgradulate_ DuckDB and extend our gratitude for all their hard work and support (and enabling all the duck puns)!

## Why DuckDB?

For database nerds, [there’s much to love about DuckDB](https://motherduck.com/duckdb-book-brief/) — [performance](https://thenewstack.io/duckdb-in-process-python-analytics-for-not-quite-big-data/), [innovation velocity](https://motherduck.com/blog/six-reasons-duckdb-slaps/), [versatility](https://duckdb.org/faq.html#why-call-it-duckdb), [ease of use](https://www.nikolasgoebel.com/2024/05/28/duckdb-doesnt-need-data.html), [rich and user-friendly SQL](https://duckdb.org/2024/03/01/sql-gymnastics.html), and [extreme portability](https://duckdb.org/why_duckdb.html#portable). Thanks to DuckDB, analytics can run virtually anywhere, liberated from the shackles of complex and expensive distributed systems. As an embedded database, it’s the perfect ‘Lego’ building block that can snap into any process just by linking in a library.

When we first learned about DuckDB two years ago, we loved it so much that we decided to start a company to turn it into a serverless cloud data warehouse. While in retrospect, this seems like an obvious duck to bet on, at the time, DuckDB was relatively unknown outside of database enthusiast and academic circles. But you could tell, even then, that they were onto something — the elegance of the design and the fervent enthusiasm of their growing user base set it apart from other databases. Moreover, their philosophy about what actually matters in data management systems deeply resonated with us at MotherDuck.

This turned out to be a prophetic choice. In the two years since we started working together, DuckDB has consistently moved up the rankings in the [DB Engines list](https://db-engines.com/en/ranking%5D). They’ve gone from thousands of monthly downloads to millions. And they’ve gone from being the database nobody has heard of to the one everyone is talking about.

![DB Engines growth chart](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_f6daf71258.png&w=3840&q=75)

With DuckDB as the key building block, MotherDuck is a [complete set of Legos](https://www.lego.com/en-us/product/millennium-falcon-75192?gclid=CjwKCAjwjeuyBhBuEiwAJ3vuoU4Ue7BPvmrfhnovXtGvA-5kp27nHkdJs9LXUCaPZjCUCrewdkOiyRoCnuQQAvD_BwE&ef_id=CjwKCAjwjeuyBhBuEiwAJ3vuoU4Ue7BPvmrfhnovXtGvA-5kp27nHkdJs9LXUCaPZjCUCrewdkOiyRoCnuQQAvD_BwE:G:s&s_kwcid=AL!790!3!!!!x!!!19930801844!&cmp=KAC-INI-GOOGUS-GO-US_GL-EN-RE-SP-BUY-CREATE-MB_ALWAYS_ON-SHOP-BP-PMAX-ALL-CIDNA00000-PMAX-MEDIUM_PRIORITY&gad_source=1), purpose-made for data teams, analytics application developers, and DuckDB users looking to supercharge and extend their favorite database to the cloud.

## DuckDB Labs, Thank You!

When we first talked to [Hannes](https://hannes.muehleisen.org/) and [Mark](https://mytherin.github.io/) about bringing DuckDB to the cloud, they were cautiously supportive of the idea. Since then, we’ve built a great working relationship with the DuckDB Labs team to help achieve our shared vision of DuckDB running everywhere. We’ve also created a pioneering model for building a commercial business without stifling open-source independence.

We at MotherDuck are extending DuckDB beyond its embedded confines by offering [serverless delivery](https://motherduck.com/product/), [secure sharing](https://motherduck.com/docs/key-tasks/managing-shared-motherduck-database/) and [access control](https://motherduck.com/docs/authenticating-to-motherduck/), [durable managed storage](https://motherduck.com/docs/architecture-and-capabilities/), [hybrid/dual query execution](https://motherduck.com/cidr-paper/), [a WebAssembly (Wasm) SDK](https://motherduck.com/blog/building-data-applications-with-motherduck/), and more.

Crucially, thanks to the [extensibility hooks](https://duckdb.org/docs/extensions/overview.html) DuckDB provides, MotherDuck has been able to run standard DuckDB under the hood.

As DuckDB marched towards its 1.0 release, we saw DuckDB Labs’ hard work firsthand to production-proof DuckDB. We appreciate the hardening, fuzzing, refactoring, and testing that has made for an impressively stable, flexible, and semantically rich data management system. Frankly, many of MotherDuck’s recent improvements, including version independence and multi-statement transactions, were made possible by DuckDB Labs’ collaborative efforts.

We could not have picked a better database to work with or a better group of passionate database professionals to partner with. To Hannes, Mark, and the rest of DuckDB Labs, we appreciate your continuous support, determination, and excellence.

We look forward to celebrating 2.0 and beyond with you!

## DuckDB 1.0 and MotherDuck

Today’s release also marks the first simultaneous launch of MotherDuck with a new DuckDB version. MotherDuck already supports DuckDB 1.0; if you run a query via MotherDuck, it will run on the latest DuckDB version. What makes this possible is **Version Independence**, a feature we quietly enabled a few weeks ago that decouples clients from the version of DuckDB that we run on our servers.

When DuckDB ships a new version, we can upgrade all the MotherDuck servers to run it in the cloud. Users don’t need to do anything; they’ll get access to improved performance and bug fixes. While users will need to upgrade their clients to access new features, they can now do so at their convenience.

## PS: Something BIG is Coming Soon

At MotherDuck, we have also been busy, and we have some exciting news to share with you very soon.

Stay tuned!

Meanwhile, if you’re in San Francisco tonight, **June 3rd, at 6:00 pm**, [celebrate with us at our party at 111 Minna](https://motherducking-party-snowflake-summit.eventbrite.com/)… [we’ll run it back on Tuesday, June 11th](https://motherducking-party-data-ai-summit.eventbrite.com/)!

## Take Flight with MotherDuck

### Cloud SQL Analytics Without the Overhead

If you haven’t tried MotherDuck, [take flight with a 30-day trial of the Standard Plan](https://motherduck.com/) or paddle [Free Forever for small projects](https://motherduck.com/product/pricing/).

### TABLE OF CONTENTS

[Why DuckDB?](https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release#why-duckdb)

[DuckDB Labs, Thank You!](https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release#duckdb-labs-thank-you)

[DuckDB 1.0 and MotherDuck](https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release#duckdb-10-and-motherduck)

[PS: Something BIG is Coming Soon](https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release#ps-something-big-is-coming-soon)

[Take Flight with MotherDuck](https://motherduck.com/blog/motherduck-congratulates-duckdb-1.0-release#take-flight-with-motherduck)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![How we Saved 95% on Log Processing with Bacalhau and MotherDuck](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FBacalhau_blog_e9a1602bb1.png&w=3840&q=75)](https://motherduck.com/blog/log-processing-savings-bacalhau-motherduck/)

[2024/05/08 - Sean M. Tracey](https://motherduck.com/blog/log-processing-savings-bacalhau-motherduck/)

### [How we Saved 95% on Log Processing with Bacalhau and MotherDuck](https://motherduck.com/blog/log-processing-savings-bacalhau-motherduck)

We stopped sifting our log data and started generating speedy logging insights to realize 95% in cost savings by pre-processing logs with Bacalhau and MotherDuck. How is that even possible? Let's walk through a step-by-step overview together.

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response