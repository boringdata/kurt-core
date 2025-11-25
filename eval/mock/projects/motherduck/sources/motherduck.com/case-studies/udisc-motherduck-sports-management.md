---
title: udisc-motherduck-sports-management
content_type: case_study
source_url: https://motherduck.com/case-studies/udisc-motherduck-sports-management
indexed_at: '2025-11-25T20:02:37.757695'
content_hash: af78437aa21ba6d9
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO CASE STUDIES](https://motherduck.com/case-studies/)

# From minutes to seconds: How UDisc Transformed Disc Golf Analytics with MotherDuck

MotherDuck solves all sorts of really hard problems for us so that we can just focus on building UDisc. It’s a big unlock not only for our business but also for disc golf as a sport. We’re just scratching the surface right now of what’s possible.

![Josh Lichti's photo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fudisc_josh_49a3d44e14.jpeg&w=3840&q=75)

Josh Lichti

Co-Founder & CEO

[![Josh Lichti company logo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fu_disc_logo_95b92cceda.png&w=3840&q=75)](https://udisc.com/)

UDisc is the leading mobile app to help disc golfers explore over 16,000 courses worldwide, keep score with friends, track personal game stats, find events, and more.

At UDisc, **MotherDuck has been essential** to fulfilling our mission to empower more people to play disc golf worldwide. What began as a simple course directory in 2012 blossomed over time into the full-fledged UDisc mobile app. While usage was steady in the early years, disc golf exploded in popularity during the pandemic, and the resulting data grew even faster. Part of our mission is to provide local stakeholders with data that showcases the positive impact of disc golf in their community, but as UDisc grew, wrangling and sharing that data became almost impossibly difficult. That’s when we found MotherDuck.

We use MongoDB for our transactional database, but generating our annual usage reports was a messy process that took forever. As a bootstrapped startup, our overall database size isn’t all that large, but MongoDB was unsuitable for analytics even just once a year. The real challenge came when we created a course stats dashboard for our local volunteer ambassadors. Our first version only included basic stats and was limited to 30 days’ worth of data, otherwise it would have slowed down our database. But as course ambassadors kept asking for more data, we knew there was no way we could keep up with the rising number of ad hoc analytics queries using just MongoDB.

In our quest for an effective user dashboard, we tried everything: ClickHouse, Snowflake, Databricks, BigQuery and even Postgres. Many of these big solutions were too expensive and too complex for our use case. As an employee-owned startup, we needed a solution that was simple and cost-effective. In spring 2024, we found MotherDuck after learning that [Hex](https://hex.tech/) (part of our dashboard front-end) used DuckDB themselves. The fact that MotherDuck is based on the open source DuckDB engine was also an attractive feature for us.

In our POC, **a typical query in MotherDuck took 5 seconds**, and in Postgres, it still wasn’t complete after 2 minutes. Likewise, our fully-optimized dbt job in Postgres took 6 hours, and that’s not counting any indexing work, which was often required even if the query only changed slightly. **The same optimized dbt job in MotherDuck took only 30 minutes.** We immediately implemented MotherDuck into our course stats dashboard, and our local ambassadors were able to load the lifetime history of a given course along with all of its stats and charts in just a few seconds. This sort of request was just not even possible before using MotherDuck.

Ultimately, MotherDuck made it easy for our team to analyze and surface our existing data both internally and externally. Whereas our annual usage report used to require several 1-hour scripts, **we can now gather all the year’s stats in a couple of seconds**. Furthermore, our course dashboards empower local ambassadors with tons of analytics data, including a self-serve function for ad hoc queries.

![Chart in Course Dashboard](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_bff13a355a.png&w=3840&q=75)

Looking ahead, we now have better internal insights to help us figure out what we need to fix, improve, or build going forward. In the future, we want to use [DuckDB Spatial](https://motherduck.com/blog/geospatial-for-beginner-duckdb-spatial-motherduck/) and GPS tracking to analyze and improve how players navigate a course, and we hope to integrate weather data one day as well. UDisc has 90% of the market share for disc golf apps, so our high quality data gives us a near-complete picture of how the sport is growing—and all of that’s been made possible through MotherDuck.

## UDisc's Data Stack

- MotherDuck
- Hex
- Dagster
- dbt
- Node.js API to MotherDuck
- React
- Remix web framework ( [https://remix.run/](https://remix.run/))
- CloudFlare

Authorization Response