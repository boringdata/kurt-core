---
title: pushing-geo-boundaries-with-motherduck-geobase
content_type: blog
source_url: https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase
indexed_at: '2025-11-25T19:58:39.029978'
content_hash: edb0b8caa3dfccaf
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Pushing the Boundaries of Geo Data with MotherDuck and Geobase!

2024/07/03 - 4 min read

BY

[Saqib Rasul](https://motherduck.com/authors/saqib-rasul/)

In this post, we will demonstrate how [Geobase](https://geobase.app/) and MotherDuck can work together to create previously impossible applications! MotherDuck handles online analytical processing (OLAP) queries efficiently, while Geobase excels at spatial-temporal queries for movement analytics.

With this integration, all API calls are routed through Geobase, enabling stored procedures to generate vector tiles on the front end seamlessly, providing a straightforward solution for developers and businesses.

![Demo video](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_3_ef68bbed2a.gif&w=3840&q=75)

## Use Case: The Danish Straits' Impact on World Trade and Shipping

Over 80% of the volume of international trade in goods is transported by sea. For Western Europe, most of this volume passes through the Danish Straits. Like road transport networks, this trade moves from the main trade routes to ports and from there into channels and rivers.

This region is home to some of the largest offshore energy farms, such as the Lillgrund Wind Farm. It also hosts major engineering projects like the Oresund Bridge.

The raw ship traffic data for this region of international waters is available on the Danish Maritime Authority’s website as monthly CSV extracts. We wanted to use Geobase and MotherDuck to bring this data to life!
Once the data was visualized, we discovered things we never knew existed, like [maintenance ships working at the offshore wind farm from 7 AM to 3 PM](https://youtu.be/6FzQL0-lMa0) or ship captains' [preference to take certain routes over others](https://youtu.be/QRE_zIIx1EI). These are all very human stories hidden within the data.

The [Ship Tracks site is now live](https://shiptracks.vercel.app/) so that you can discover more patterns and stories in the data.

## How we Built This

MotherDuck and Geobase were instrumental in visualizing the movement of around 5,000 ships over a 24-hour period in the Danish Straits. This visualization highlights the density of ships and their common paths. This would not have been possible without Geobase!

![Embedded demo](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage2_aee787316c.gif&w=3840&q=75)

## Getting Started

Getting started with Geobase and MotherDuck is straightforward. Users can leverage the integration to create compelling geospatial applications and visualizations without managing their servers. The integration offers a practical and efficient solution for developers and businesses looking to harness the power of large datasets in the geospatial industry.

![Architecture diagram](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage4_f42fed96d7.png&w=3840&q=75)
The figure above outlines how MotherDuck and the Geobase platform integrate.

**1\. MotherDuck (powered by DuckDB):**

- Offers a data warehouse service that extends DuckDB to the cloud
- Securely connects to the Geobase platform

**2\. Geobase Platform:**

- Handles both external ('big data' at cloud scale) and internal tables
- Uses stored functions for business logic

**3\. Vector Tiles API:**

- Processes data into vector tiles
- Includes a caching mechanism for efficiency

**4\. Applications:**

- Web, mobile, and VR applications access vector tiles and API functions from the Geobase platform to visualize and interact with the data

![Ships moving](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_20697e8d32.gif&w=3840&q=75)

## Geobase and MotherDuck overview

Geobase and MotherDuck have key features that are highly complementary:
![Overview table](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ftable_52097d413e.png&w=3840&q=75)

## Integration Benefits

The Geobase and MotherDuck integration offers several advantages. MotherDuck excels at running OLAP queries, making it ideal for data analysis at cloud scale. Geobase is particularly strong in handling the spatial-temporal queries required for movement analytics in the geospatial industry. It also supports H3 integration for efficient spatial indexing. Combining these capabilities allows API calls through Geobase to MotherDuck. Geobase can also process the data to create vector tiles in response to the front end, thus allowing visualization of large datasets. It's all possible without touching the server!

## Additional Use Cases

This integration supports various practical applications, such as real-time maritime activity analysis, global trade insights, and event impact assessment. For example, it can monitor and analyze vessel movements in real time, track performance at major ports, and evaluate the impact of events like natural disasters or geopolitical conflicts on maritime activities. Of course, the maritime industry is just one of a dozen other industries that create, store & analyze, and build upon geospatial data. These capabilities enable governments, researchers, and businesses to make informed decisions based on comprehensive and timely data.

## Conclusion

Our example is just one highlight of the available tools and functionality in Geobase and MotherDuck, which offer greater possibilities, such as identifying high-density areas, spotting stationary ships, tracking individual ship trajectories, and investigating anomalous ship behavior.

As we launch Geobase, we will educate our community on using these tools better and improving the know-how needed to create such powerful applications.

### TABLE OF CONTENTS

[Use Case: The Danish Straits' Impact on World Trade and Shipping](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase/#use-case-the-danish-straits-impact-on-world-trade-and-shipping)

[How we Built This](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase/#how-we-built-this)

[Getting Started](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase/#getting-started)

[Geobase and MotherDuck overview](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase/#geobase-and-motherduck-overview)

[Integration Benefits](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase/#integration-benefits)

[Additional Use Cases](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase/#additional-use-cases)

[Conclusion](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase/#conclusion)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Search in DuckDB: Integrating Full Text and Embedding Methods](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FSearch_Using_Duck_DB_series_3_of_3_265a610479.png&w=3840&q=75)](https://motherduck.com/blog/search-using-duckdb-part-3/)

[2024/06/20 - Adithya Krishnan](https://motherduck.com/blog/search-using-duckdb-part-3/)

### [Search in DuckDB: Integrating Full Text and Embedding Methods](https://motherduck.com/blog/search-using-duckdb-part-3)

Explore search methods with DuckDB using Full-Text-Search and embeddings in a hybrid search engine fully accessible using SQL

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response