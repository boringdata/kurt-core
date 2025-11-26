---
title: is-bi-too-big-for-small-data
content_type: blog
source_url: https://motherduck.com/videos/is-bi-too-big-for-small-data
indexed_at: '2025-11-25T20:44:25.574735'
content_hash: 1f918cf796cdc13a
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

Is BI Too Big for Small Data? - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Is BI Too Big for Small Data?](https://www.youtube.com/watch?v=3JCLWGCaam8)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=3JCLWGCaam8&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 17:04

•Live

•

YouTubeBI & Visualization

# Is BI Too Big for Small Data?

2024/11/17

If you’ve ever sat through a demo for a [Business Intelligence](https://en.wikipedia.org/wiki/Business_intelligence) (BI) tool, you know the story. A key metric on a dashboard suddenly dips. An "intrepid analyst" dives in, slicing and dicing the data with a few clicks. They join a few tables, write a few queries, and— _voila!_—they uncover a previously unimagined insight that saves the day.

As [Benn Stancil](https://www.linkedin.com/in/benn-stancil/), founder of the BI tool [Mode](https://mode.com/), explained in a recent talk, "This sells! This story actually really works." It’s the narrative that built a multi-billion dollar industry. But Stancil, who has given this demo hundreds of times, reveals the conflict at the heart of the BI world: the story sells, but for most companies, **it doesn't actually work.**

If this narrative were true, why are so many teams unhappy with their BI tools? Why do our dashboards become "trashboards" that nobody uses? The answer, according to Stancil, is that the entire "intrepid analyst" fantasy is built on a lie. Not a malicious lie, but a foundational misunderstanding of the data most of us actually have. It’s the Big Data Lie.

## The Myth of "Data is the New Oil"

To understand why the story fails, we have to go back to the early 2010s, when the "big data" hype train left the station at full speed. A series of iconic stories cemented a powerful idea in our collective consciousness: that data, like oil, is a raw material just waiting to be drilled into to produce immense value. We heard how [Target’s data science team used purchasing data to predict a teenage girl’s pregnancy](https://www.forbes.com/sites/kashmirhill/2012/02/16/how-target-figured-out-a-teen-girl-was-pregnant-before-her-father-did/), suggesting data had prophetic powers. We saw it in [Moneyball](https://en.wikipedia.org/wiki/Moneyball:_The_Art_of_Winning_an_Unfair_Game), where the Oakland Athletic's used decades of historical baseball data to build a winning team on a shoestring budget. We witnessed it when Nate Silver, hailed as a "witch," [predicted the 2012 US election](https://www.theguardian.com/world/2012/nov/07/nate-silver-election-forecasts-right) with stunning accuracy by analyzing millions of polling records. And we learned it from Facebook, which data-scienced its way to the magic ["7 friends in 10 days"](https://andrewchen.com/my-quora-answer-to-how-do-you-find-insights-like-facebooks-7-friends-in-10-days-to-grow-your-product-faster/) formula for growth.

These examples, and the ["Data Scientist: Sexiest Job of the 21st Century"](https://hbr.org/2012/10/data-scientist-the-sexiest-job-of-the-21st-century) headlines that followed, created a powerful belief system. Stancil summarizes it perfectly: "A lot of people came to very much believe that data just contains value... And all it takes is us to have the right tools to get that insight out." This belief spawned a generation of tools promising to "unlock the power of your data." The problem? The premise was flawed for most of us from the start.

Target had $73 billion in revenue. The Moneyball team had nearly 12 million historical at-bats. Nate Silver had 650 million votes. Facebook had over a billion users.

As Stancil states bluntly, "This is big data." Most of us don't have that. We have a few thousand customers, not a billion users. Our charts don't look like the smooth, predictable curves from a dataset of millions. They look like this:

When faced with a chart like this, you don't "slice and dice." You don't "drill down." As Stancil hilariously puts it, "You squint at it and you're like, **it's up-ish.**" This is the disconnect. We were promised a treasure map, but we got a squiggly line and a shrug.

So if the heroic "big data" playbook is a fantasy for most of us, what are we supposed to do? If our reality is more "up-ish" than insightful, it's clear we need a different approach—a new playbook designed not for finding treasure in petabytes, but for finding meaning in ambiguity.

## A New Playbook for the "Small Data" Reality

If the old playbook is broken, what does the new one look like? Stancil proposes a new set of principles for finding value in the "up-ish" reality that most of us live in. This new playbook shifts the focus from heroic exploration to pragmatic interpretation.

### Principle 1: Shift from Exploration to Interpretation

"The hard part is not creating this chart," Stancil argues. "The hard part is interpreting it."

Most BI tools are built for exploration. They give you endless options to filter, pivot, and visualize. But when your data is sparse, these features don't lead to clarity; they just create more confusing charts. The real bottleneck isn't getting the data; it's figuring out what, if anything, it means. Stancil's insight is that **"interpretation of data is often a lot harder than exploration."**

This is where speed and interactivity become critical. To interpret an ambiguous chart, you need to form and test hypotheses rapidly. _Is this dip because of the holiday? Let me pull last year's data. Is it a specific user segment? Let me filter by plan type. Is it a bug? Let me look at error logs from the same period._

If each query takes minutes to run, you lose your train of thought. The friction of waiting kills the iterative cycle of questioning that is essential for interpretation. When you can test ideas as fast as you can think of them, you shrink the gap between question and answer, making the hard work of interpretation just a little bit easier.

### Principle 2: Embrace Unscalable Work

This might sound like heresy to data professionals, but it’s Stancil’s most powerful point. He tells the story of a friend tasked with analyzing the sentiment of articles on a specific topic. She started building a complex AI model, only to realize there were just _seven_ articles.

"Why am I building a tool to look at seven articles?" Stancil asks. **"Go read them."** It takes 20 minutes and yields a far richer understanding than any model could. This "unscalable" approach is incredibly effective for customer data. Instead of trying to find trends across thousands of users in a noisy dataset, go look at the raw activity of a _single_ user.

With a tool like MotherDuck, you don't need a complex pipeline to do this. You can query your raw event data directly to "read the story" of an individual user's journey. For example, let's say you want to understand what your most active user from the last week was actually doing.

```sql
Copy code

-- Stancil's point: Sometimes the best insight comes from looking at one customer.
-- With MotherDuck, you don't need a complex pipeline to do this.
-- Just query your raw data directly.

-- First, find our most active user this week
WITH user_activity AS (
    SELECT
        user_id,
        COUNT(event_id) AS event_count
    FROM events
    WHERE event_timestamp >= NOW() - INTERVAL '7 day'
    GROUP BY 1
    ORDER BY 2 DESC
    LIMIT 1
)
-- Now, let's pull their entire event stream to "read the story" of their session
SELECT
    e.event_timestamp,
    e.event_type,
    e.properties
FROM events e
JOIN user_activity ua ON e.user_id = ua.user_id
ORDER BY e.event_timestamp;
```

The result of this query isn't a high-level chart; it's a narrative. You can see every click, every page view, every action this power user took, step-by-step. This is the "unscalable" insight Stancil talks about. It doesn't tell you what _all_ users are doing, but it gives you a deep, qualitative understanding of what an engaged user's journey _looks like_. That's often far more valuable than another "up-ish" chart.

### Principle 3: Honestly Assess Your Data's Scale

Stancil's final piece of advice is to be honest about the scale of your data. Don't use a "big data" sledgehammer for a "small data" nail. Big data problems are real, and they require big data tools like [Snowflake](https://www.snowflake.com/) or [BigQuery](https://cloud.google.com/bigquery?hl=en). If you're managing petabytes of data for a global enterprise, those are the right tools for the job.

But MotherDuck and [DuckDB](https://duckdb.org/) were built for the other 99% of us. We excel in the vast space _below_ that massive threshold, where most companies operate and where the challenges are different. It's not about wrangling petabytes; it's about getting fast, reliable insights from datasets that fit on your laptop or a modest server. It's about using the right tool for the job.

## Conclusion: Embrace Your "Up-ish" Data

The "big data" dream set an unrealistic expectation for many of us. We were told our data was a gold mine, and we felt like failures when we couldn't find the gold. Benn Stancil's message is a liberating one: your data isn't the problem. The "small data" reality isn't a failure; it just requires a different, more pragmatic approach.

Stop chasing the "intrepid analyst" fantasy and start embracing the messy, ambiguous, "up-ish" world you actually live in. Shift your focus from exploration to interpretation, embrace the unscalable work of looking at individual examples, and choose tools built for the scale of data you actually have. The best way to begin is to try a more direct, interpretation-focused approach yourself. You can start with a local [DuckDB](https://duckdb.org/) instance or sign up for a free [MotherDuck](https://motherduck.com/) account and see what stories your "small data" can tell.

...SHOW MORE

## Related Videos

[!["Can DuckDB replace your data stack?" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FCan_Duck_DB_Replace_Your_Data_Stack_Mother_Duck_Co_Founder_Ryan_Boyd_3_56_screenshot_70e18322ec.png&w=3840&q=75)\\
\\
60:00](https://motherduck.com/videos/can-duckdb-replace-your-data-stack/)

[2025-10-23](https://motherduck.com/videos/can-duckdb-replace-your-data-stack/)

### [Can DuckDB replace your data stack?](https://motherduck.com/videos/can-duckdb-replace-your-data-stack)

MotherDuck co-founder Ryan Boyd joins the Super Data Brothers show to talk about all things DuckDB, MotherDuck, AI agents/LLMs, hypertenancy and more.

YouTube

BI & Visualization

AI, ML and LLMs

Interview

[!["AI Powered BI: Can LLMs REALLY Generate Your Dashboards? ft. Michael Driscoll" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_1123cd92b9.jpg&w=3840&q=75)](https://motherduck.com/videos/ai-powered-bi-can-llms-really-generate-your-dashboards-ft-michael-driscoll/)

[2025-05-20](https://motherduck.com/videos/ai-powered-bi-can-llms-really-generate-your-dashboards-ft-michael-driscoll/)

### [AI Powered BI: Can LLMs REALLY Generate Your Dashboards? ft. Michael Driscoll](https://motherduck.com/videos/ai-powered-bi-can-llms-really-generate-your-dashboards-ft-michael-driscoll)

Discover how business intelligence is evolving from drag-and-drop tools to code-based, AI-powered workflows—leveraging LLMs, DuckDB, and local development for faster, more flexible analytics.

YouTube

AI, ML and LLMs

BI & Visualization

[!["A duck in the hand is worth two in the cloud" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FA_Duck_in_the_Hand_f9ac52885a.png&w=3840&q=75)\\
\\
33:49](https://motherduck.com/videos/a-duck-in-the-hand-is-worth-two-in-the-cloud/)

[2024-11-08](https://motherduck.com/videos/a-duck-in-the-hand-is-worth-two-in-the-cloud/)

### [A duck in the hand is worth two in the cloud](https://motherduck.com/videos/a-duck-in-the-hand-is-worth-two-in-the-cloud)

What if I told you that you could complete a JSON parse and extract task on your laptop before a distributed compute cluster even finishes booting up?

YouTube

BI & Visualization

AI, ML and LLMs

SQL

Python

Talk

[View all](https://motherduck.com/videos/)

Authorization Response