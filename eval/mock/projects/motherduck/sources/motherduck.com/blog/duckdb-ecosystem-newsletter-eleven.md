---
title: duckdb-ecosystem-newsletter-eleven
content_type: reference
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-eleven
indexed_at: '2025-11-25T19:58:03.543775'
content_hash: 3a1eb24fef42ad70
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# This Month in the DuckDB Ecosystem: October 2023

2023/10/30 - 4 min read

BY

[Marcos Ortiz](https://motherduck.com/authors/marcos-ortiz/)

## Hey, friend 👋

It’s [Marcos](https://www.linkedin.com/in/mlortiz) again, aka “ _DuckDB News Reporter_” with another issue of “This Month in the DuckDB Ecosystem for October 2023.

As always we share here, this is a two-way conversation: if you have any feedback on this newsletter, feel free to send us an email to [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

## Featured Community Member

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FTed_Conbeer_f35ebe5faf.png%3Fupdated_at%3D2023-10-30T14%3A31%3A32.569Z&w=3840&q=75)

### Ted Conbeer

Ted Conbeer is a mechanical engineer turned management consultant, who eventually became an analytics engineer and startup executive and advisor. But don't be misled by the latter title; he's also a prolific contributor to open-source coding!

In 2021, he created [sqlfmt](https://sqlfmt.com/), an autoformatter for dbt SQL, which has been downloaded over 1,500,000 times. By 2023, he went on to develop [harlequin](https://harlequin.sh/), a terminal-based SQL IDE for DuckDB. If you're aiming to enhance your DuckDB development experience, giving harlequin a try is highly recommended!

You can connect with Ted on [GitHub](https://github.com/tconbeer), [X](https://twitter.com/tedconbeer), or [LinkedIn](https://www.linkedin.com/in/tedconbeer/).

## Top DuckDB Links this Month

* * *

### [DuckDB’s CSV sniffer](https://duckdb.org/2023/10/27/csv-sniffer.html)

Whether we like it or not, CSV files are here to stay. The DuckDB team understands this well, which is why they've significantly enhanced their CSV reader. It now detects CSV dialect options, identifies column types, and even bypasses corrupt data. [Pedro Holanda](https://twitter.com/holanda_pe?lang=en) guides us through these latest updates.

### [DuckDB — Data Processing in Python Without Pains](https://medium.com/@trung.ngvan/duckdb-data-processing-in-python-without-pains-bf201e36e875)

While DuckDB is renowned for its impressive SQL interfaces, it's not as well-known in the Python community. However, this blog by [Trung Nguyen](https://medium.com/@trung.ngvan), demonstrates how it can accelerate and enhance workflows based on Pandas.

### [NPLG 10.5.23: A New Way to Monetize Open Source (MotherDuck)](https://notoriousplg.substack.com/p/nplg-10523-a-new-way-to-monetize)

A very interesting conversation between [Tino Tereshko](https://www.linkedin.com/in/valentinotereshko/) (VP of Product at MotherDuck) and [Zachary Dewitt](https://www.linkedin.com/in/zachary-dewitt-a5a8b816/) (Partner at Wing VC)

### [Transforming Data Engineering: A Deep Dive into dbt with DuckDB](https://blog.det.life/transforming-data-engineering-a-deep-dive-into-dbt-with-duckdb-ddd3a0c1e0c2)

Are you interested in the combination of dbt and DuckDB? Well, [Felix Gutierrez](https://www.linkedin.com/in/felixgutierrezmorales/) gave us a very good introduction to the topic in this article

### [DuckDB for Spatial Data Management](https://www.youtube.com/playlist?list=PLAxJ4-o7ZoPeXzIjOJx3vBF0ftKlcYH9J)

If you are interested on this topic, you must watch the course that [Quisheng Wu](https://www.linkedin.com/in/giswqs/) (an Associate Professor of the University of Tennessee) taught about it. It’s on YouTube

### [DuckDB extensions for AWS Lambda](https://extensions.quacking.cloud/)

[Tobias Müller](https://www.linkedin.com/in/tobiasmuellerlg/) created this very cool project in order to run DuckDB on AWS Lambda

### [Analyst mulls data collection for socioeconomic development](https://thenationonlineng.net/analyst-mulls-data-collection-for-socioeconomic-development/)

DuckDB can be very advantages for governemtn focused innitiaves, and this articles shares the perspective of a Nigerian called [Oluwajuwon Ogunseye](https://www.linkedin.com/in/oluwajuwon-micheal/) talking precisely about it. Now, there is further development for it: he announced a challenge called [#30DaysofDuckDBChallenge](https://www.linkedin.com/feed/update/urn:li:activity:7121802182789652480/?updateEntityUrn=urn%3Ali%3Afs_updateV2%3A%28urn%3Ali%3Aactivity%3A7121802182789652480%2CFEED_DETAIL%2CEMPTY%2CDEFAULT%2Cfalse%29) to get more people excited about it.

### [Building an IoT Platform Using Modern Data Stack — Part 1](https://medium.com/datamatiks/building-an-iot-platform-using-modern-data-stack-part-1-02c5460e3f6c)

A good example of a end-to-end project done by [Niño Francisco Liwa](https://medium.com/@nifrali?source=---two_column_layout_sidebar----------------------------------) using DuckDB, FastAPI, Prefect & Streamlit. This involves using public dataset from telemetry sensors provided by Brisbane City Council.

### [Unleashing the Power of DuckDB for Interactive SQL Notebooks](https://www.youtube.com/watch?v=60OrHvauWTg)

This a video talk where [Rik Bauwens](https://www.linkedin.com/in/rikbauwens/) walked us through how they implemented neat features into [Datacamp’s](https://www.datacamp.com/) notebook interface using DuckDB.

## Upcoming events

### [Webinar: Semantic Layers with Cube and MotherDuck + DuckDB](https://cube.dev/events/cube-duckdb-motherduck)

**1 November 2023 \| Online 🌐**

The Cube and MotherDuck teams are hosting a webinar on how to use Cube's semantic layer \[access control, pre-aggregates\] with MotherDuck and DuckDB.

### [Scale By the Bay \| In Process Analytical Data Management with DuckDB](https://www.scale.bythebay.io/post/alex-monahan-in-process-analytical-data-management-with-duckdb)

**13-15th November 2023 \| Oakland 🇺🇲**

Discover DuckDB with Alex Monahan’s talk: Learn about this innovative analytical data management system that seamlessly integrates with languages like Python, R, Java, and more. Find out how DuckDB enhances data workflows with fast, efficient operations and automatic parallelization. Join us for an insightful talk on the power of DuckDB!

### [MotherDuck / DuckDB User Meetup DE November 2023 Edition](https://www.eventbrite.com/e/motherduck-duckdb-user-meetup-de-november-2023-edition-2-tickets-742532794577)

**20th November 2023 \| Berlin 🇩🇪**

MotherDuck is happy to announce the second MotherDuck/DuckDB meetup in Berlin!. Talk about DuckDB, MotherDuck and all the things data! C﻿o-creator of DuckDB Hannes Mühleisen will join us, and Michael Hunger author of "DuckDB in action" will give a talk!
I﻿f you want to quack a talk, feel free to reach out to [events@motherduck.com](mailto:events@motherduck.com) or submit your proposition in [sessionize](https://sessionize.com/md-duckdb-meetup).

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-eleven/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-eleven/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-eleven/#top-duckdb-links-this-month)

[Upcoming events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-eleven/#upcoming-events)

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

[![Exploring StackOverflow with DuckDB on MotherDuck (Part 2)](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FPART_2_38a52220c4.png&w=3840&q=75)](https://motherduck.com/blog/exploring-stackoverflow-with-duckdb-on-motherduck-2/)

[2023/10/02 - Michael Hunger](https://motherduck.com/blog/exploring-stackoverflow-with-duckdb-on-motherduck-2/)

### [Exploring StackOverflow with DuckDB on MotherDuck (Part 2)](https://motherduck.com/blog/exploring-stackoverflow-with-duckdb-on-motherduck-2)

Exploring StackOverflow with DuckDB on MotherDuck (Part 2)

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response