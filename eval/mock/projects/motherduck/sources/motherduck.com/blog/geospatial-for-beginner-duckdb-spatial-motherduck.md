---
title: geospatial-for-beginner-duckdb-spatial-motherduck
content_type: tutorial
source_url: https://motherduck.com/blog/geospatial-for-beginner-duckdb-spatial-motherduck
indexed_at: '2025-11-25T19:56:18.105407'
content_hash: a0b7a80589f4a5e8
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# A Beginner’s Guide to Geospatial with DuckDB Spatial and MotherDuck

2025/02/26 - 22 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

Geospatial data is everywhere in modern analytics. Consider this scenario: you're a data analyst at a growing restaurant chain, and your CEO asks, "Where should we open our next location?"

This seemingly simple question requires analyzing competitor locations, population density, traffic patterns, and demographics—all spatial data. Traditionally, answering this question would require expensive GIS (Geographic Information Systems) software or complex database setups. Today, DuckDB offers a simpler, more accessible approach for data engineers to tackle spatial problems without specialized infrastructure.

This article explores how DuckDB's spatial capabilities can transform complex geographic analysis into simple SQL queries, including hands-on spatial queries with the Foursquare dataset.

### What is GIS or Geospatial?

[GIS](https://en.wikipedia.org/wiki/Geographic_information_system) is a specialized data infrastructure that handles geographic datasets, supporting spatial indexing, topology rules, and coordinate systems for location-based data processing and analysis. Geospatial is the broader domain encompassing all geographic data types (vector, raster), spatial relationships, and coordinate-based information that can be integrated into data pipelines and warehouses for location-aware analytics.

NOTE: Difference between Geospatial and GIS
In this article, we talk about geospatial applications and GIS-specific tools. You may have heard both and didn't know how they relate. To clarify, here is a short description of their difference. **Geospatial** refers to all aspects of location-based data and geographic relationships. Meanwhile, **GIS** (Geographic Information Systems) is the specific technology stack used to capture, analyze, and visualize this spatial data. Think of geospatial as the broader domain of geographic information, with **GIS being the toolkit** used to work with it.

## Why Geospatial Processing Matters

When I first worked with GIS and geospatial data, I was always confused—why do we need it? Can't we use Postgres or MySQL? What are these different layers (WMS, WFS, etc.) and all these formats? What's the difference between polygons and multi-polygons? When do we use a point? What is the coordinate system for points, longitude, and latitude?

GIS and maps are [challenging](https://observablehq.com/blog/maps-and-data-visualization-with-fil-riviere), and there is a lot to cover. In this article, I will briefly introduce geospatial and GIS tools, explain why we need them, and showcase their ubiquitous use.

### Limitations of Relational Databases

First, why do we need geospatial capabilities? Can't we just use Postgres or any relational database? Yes, there's an extension for Postgres, such as [PostGIS](https://postgis.net/). But why the extension, and why not plain Postgres?

Geospatial technology is helpful for maps to quickly find the nearest points or all within a region (e.g., State), see the closest neighbors, or assess a radius for a spreading virus. A relational database without a geospatial data type can't do it fast enough. We mainly work with **points, LineString, Polygon**, and **MultiPolygon**. Geospatial formats and data types help optimize these use cases and do it much faster.

Points are usually longitude and latitude, and polygons are arrays of points. Matching these isn't as trivial as it sounds.

### Common Applications of GIS and Geospatial Analysis

If you haven't encountered geographical data, it may be because you don't have a customer-facing application. You quickly end up creating a map when showcasing world data to people.

Why is this? Besides the time/date dimension, **geography is probably the second most used dimension**. We want to know where our sales are coming from, where our next repair shop is, or if we need to deliver a product. You need to visually show that on a map for better understanding, or it most often happens in the background. Calculating the fastest way to deliver the parts is not something you need to visualize; it is just a calculation.

### SQL-joins vs Spatial-Joins

Why can't we use SQL joins?

Because geospatial data usually resides in a different format. It's not your typical `varchar`, `number`, or `date`. It's stored in specialized **geometric data type** representing spatial objects like `POINT(x y)`, `LINESTRING`, and `POLYGON`. PostGIS, for example, introduces the GEOMETRY and GEOGRAPHY data types, which can store more complex spatial information:

![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgeo_01_5e4650cbb6.png&w=3840&q=75)
Visualized geometric data types \| Image from [Querying spatial data](https://devjef.wordpress.com/2012/11/03/querying-spatial-data-the-basics/)

- Points (locations like stores, cities)
- MultiPoints (Trees, Poles, Hydrant)
- LineStrings (roads, rivers)
- MultiLineString (Road, River, Railway)
- Polygons (boundaries, service areas)
- MultiPolygons (multiple areas like voting districts)
- Collections of these geometries

"Normal" joins won't work. Instead, we use spatial joins. Although they're called joins, they are unlike relational database joins, intersecting data from two tables based on a matching column. Imagine a virtual map where space is divided into grids and tiles and only compared to items that could potentially intersect.

Besides, spatial operations are **much faster**; they are indexed differently (instead of B-Tree, they use spatial indexes (like [R-trees](https://en.wikipedia.org/wiki/R-tree) or [GIST indexes](https://www.postgresql.org/docs/8.1/gist.html) in PostGIS) that can handle multi-dimensional data). These indexes organize data differently and optimize for geometric operations, e.g., based on the spatial location and features such as proximity.

This is done with so-called " [Minimum Bounding Rectangles (MBR)](https://en.wikipedia.org/wiki/Minimum_bounding_rectangle)" where each geometry gets a simple rectangular "bounding box". This bounding boxing is much simpler than the original, potentially very complex geometry, making it faster and easier to check for overlaps/intersections. The index stores the tree structure into bounding boxes, dividing space into progressively smaller rectangles and grouping nearby geometries. The database can then quickly eliminate large areas of non-matching geometries, making spatial queries more efficient for geographic operations than SQL joins can be.

While SQL joins excel at matching exact values or ranges, they are not built to handle the complexities of geometric relationships and spatial operations.

NOTE: Spatial Index vs SQL Join
With a data set, say, 1 million customer points and 100,000 territory polygons, a traditional SQL join would need to check every point against every polygon. That's `1M × 100K = 100 billion` comparisons, each requiring complex geometric calculations.
In contrast, with a **spatial index** in place, searching for a single point in New York would first check which high-level grid cell contains the point and only examine polygons in that cell and adjacent cells (maybe 5–10 polygons instead of 100,000). For these few potential matches, only then do the exact geometry calculations.

Instead of 100 billion computations, spatial indexing may only need to look up 1M grid cells, each lookup comparing against nearby polygons (~10 instead of 100K). Thus, the total would be **~10 million** instead of **100 billion**.

As the above example shows, dividing space into cells makes a lot of sense in terms of efficiency, and that's one main reason why these spatial data types and operations exist.

### Geospatial Data Formats and Core Operations

Geospatial data comes in various formats besides specialized geometric types. CSV and Parquet can contain geographic information but lack native spatial support. [GeoJSON](https://geojson.org/) and [GeoParquet](https://geoparquet.org/) are file formats designed for geospatial encoding of common data types like **Points** (locations), **LineStrings** (paths), **Polygons** (areas), and **MultiPolygons** (region collections). [WKT (Well-Known Text)](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry) and [WKB (Well-Known Binary)](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry#Well-known_binary) provide standardized formats for storing and exchanging spatial data between systems.

[Coordinate reference systems (CRS)](https://en.wikipedia.org/wiki/Spatial_reference_system) are crucial in defining how locations on Earth's curved surface map to 2D coordinates and having a system to reference spatially. Web mapping services like [WMS](https://en.wikipedia.org/wiki/Web_Map_Service) (images), [WFS](https://en.wikipedia.org/wiki/Web_Feature_Service) (vectors), [WCS](https://en.wikipedia.org/wiki/Web_Coverage_Service) (coverages), and [WPS](https://en.wikipedia.org/wiki/Web_Processing_Service) (processes) allow interoperability.

Other common **spatial operations** include checking whether one geometry contains, intersects, or is within a distance of another. These are all optimized by spatial indexes for fast performance.

As you can see, there's a lot more, but in this article, we want to examine actual use cases and how DuckDB and MotherDuck can help us.

### Business Use Cases

But what are actual business use cases? When should we use GIS or geospatial operation? Geospatial data powers daily applications, from food delivery services and real estate sites to insurance risk assessment.

Businesses use spatial analysis to optimize store locations, delivery routes, and customer targeting. Apps like **[Foursquare](https://foursquare.com/)** leverage location data for personalized recommendations and business insights, while **[Strava](https://www.strava.com/)** uses GPS data to create interactive maps and foster fitness communities (to name two). Geospatial visualizations on dashboards and interactive maps in notebooks are key for analyzing location-based trends in data space.

Other examples are:

- Finding all restaurants within walking distance (0.5km) of subway stations
- Analyzing delivery coverage areas for a service
- Identifying potential new store locations based on competitor locations
- Creating trade areas based on drive time

## Today, The Modern GIS Stack

Shifting to technology and the different libraries, concluding a so-called **GIS landscape**. What are parts of it, you might ask? Matt Forrest shared his modern GIS stack, and it looks like this:
![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgeo_01_01_18a660fb64.png&w=3840&q=75)[The modern geospatial analysis stack](https://academy.carto.com/working-with-geospatial-data/the-modern-geospatial-analysis-stack) by Carto. If you like video format, Matt made a [YouTube video](https://www.youtube.com/watch?v=2WOXQ4JdKaw).

As you might recognize, there are some similarities to the Modern Data Stack or data engineering landscape. Most notable are Airflow, Airbyte in the ingestion, dbt in the transformation, and DuckDB, MotherDuck in storage.

But what are the other tools? Understanding that there are different buckets is essential without going into too much detail. For example, **applications** such as [deck.gl](https://deck.gl/) and [map.libre](https://github.com/maplibre/maplibre-gl-js) are essential tools to visualize data on a map interactively. **Data science** tools are mostly notebooks and utilities to work with the data, whereas **GIS** tools are powerful tools to support the discussed features of geospatial that don't come with regular databases or tools.

For data engineers, geospatial **data sources** are similar to regular data sources like APIs and databases and formats like CSV files; the difference is that the data comes with **location information** that needs special handling. Map APIs, for example, don't just give you all the data at once - they serve it in tiles based on what area and zoom level you're looking at. When you pull data from sources like OpenStreetMap or satellite imagery, you're not just getting rows and columns of data but also shapes (like points, lines, and polygons) that show where things are on Earth. These shapes must be handled carefully throughout your data pipeline to ensure you don't lose their spatial meaning.

### Traditional GIS Solutions and Their Limitations

So why would you need DuckDB for GIS? In the past, you needed very expensive tools for doing GIS applications, tools like [ArcGIS](https://www.arcgis.com/), [QGIS](https://qgis.org/) and others. These tools obviously do much more, but it added a high barrier to getting started.

Another option, as mentioned above, was using PostgreSQL instance with PostGIS for spatial queries, along with a few Python scripts to handle data ingestion and transformation—since PostgreSQL isn’t optimized for analytical workloads.

With DuckDB, all your data preparation, integration, and analysis are consolidated into a single database. Spatial support is just an extension away, allowing you to perform complex geospatial queries without the overhead of managing a database server.

### DuckDB's Built-in Geospatial Capabilities

What capabilities does DuckDB exactly bring you might ask? DuckDB offers extensive [Spatial Functions](https://duckdb.org/docs/stable/core_extensions/spatial/overview.html) that are out of the box.

It also comes with [GDAL Based `COPY` Function](https://duckdb.org/docs/stable/core_extensions/spatial/gdal) that allows reading and writing spatial data from a variety of geospatial vector file formats—ingesting or importing geospatial file formats through the `ST_Read` function and exporting DuckDB tables to different geospatial vector formats through a GDAL-based `COPY` function.

An example from the [docs](https://duckdb.org/docs/stable/core_extensions/spatial/gdal) showcases how to export to a [GeoJSON](https://geojson.org/) file with generated bounding boxes from a DuckDB table:

```sql
Copy code

COPY ⟨table⟩ TO 'some/file/path/filename.geojson'
WITH (FORMAT GDAL, DRIVER 'GeoJSON', LAYER_CREATION_OPTIONS 'WRITE_BBOX=YES');
```

NOTE: What is GDAL? [GDAL](https://gdal.org/en/latest/) is primarily a transformation library that helps you read, convert, and process different types of location-based data (like satellite images or map files). While it can be used in ingestion pipelines, its main strength is transforming data between different spatial formats and coordinate systems, ensuring the geographic information stays accurate throughout your data pipeline.

So, what are we doing next when we have a GeoJSON export? Let's explore some hands-on examples.

## Geospatial in Action

In this chapter, we get hands-on and see how we work with Geospatial in DuckDB and MotherDuck. MotherDuck extends DuckDB's [analytical capabilities](https://motherduck.com/product/) with serverless, collaborative features for scaling SQL and geospatial workloads.

### Converting Coordinates to Addresses (REST)

First, let's start with a handy yet powerful use case converting longitude and latitude coordinates to cities or addresses, all within the comfort of SQL.

Imagine you have longitude/latitude in your dataset but no address; you could simply install the [DuckDB HTTP Client Extension](https://duckdb.org/community_extensions/extensions/http_client.html):

```bash
Copy code

❯ duckdb
D INSTALL http_client FROM community;
D LOAD http_client;
```

And with the below query, we can GET-request [OpenStreetMap](https://motherduck.com/blog/geospatial-for-beginner-duckdb-spatial-motherduck/www.openstreetmap.org) with the address with a SQL query:

```sql
Copy code

WITH nominatim_request AS (
      SELECT http_get(
        'https://nominatim.openstreetmap.org/reverse',
        headers => MAP {
          'User-Agent': 'DuckDB-Demo/1.0', -- Required by Nominatim ToS
          'Accept': 'application/json'
        },
        params => MAP {
          'format': 'json',
          'lat': '47.3769',
          'lon': '8.5417'
        }
      ) AS response
    )
    SELECT
      (response->>'status')::INT AS status,
       json_extract_string(response->>'body', '$.display_name') AS address,
      json_extract_string(response->>'body', '$.address.city') AS city,
      json_extract_string(response->>'body', '$.address.country') AS country
    FROM nominatim_request;
```

As you can see, the coordinates that I copied from Google Maps in Zurich belong to this address:

```sql
Copy code

┌────────┬──────────────────────────────────────────────────────────────────────────────────────────────────┬─────────┬────────────────────────────────┐
│ status │                                             address                                              │  city   │            country             │
│ int32  │                                             varchar                                              │ varchar │            varchar             │
├────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼─────────┼────────────────────────────────┤
│    200 │ Bahnhofquai, City, Altstadt, Zürich, Bezirk Zürich, Zürich, 8001, Schweiz/Suisse/Svizzera/Svizra │ Zürich  │ Schweiz/Suisse/Svizzera/Svizra │
└────────┴──────────────────────────────────────────────────────────────────────────────────────────────────┴─────────┴────────────────────────────────┘
```

Another use case was presented at the DuckCon, with an upcoming Extension called Airport. See the example from the [Airport for DuckDB Letting DuckDB take Apache Arrow Flights by DuckDB](https://youtu.be/-AfgEiE2kaI?feature=shared&t=532).

These extensions integrate geocoding directly into SQL queries in DuckDB, making it accessible through standard SQL syntax. The vectorized approach can efficiently handle batch operations, unlike traditional one-by-one geocoding requests.

### Foursquare

Shifting to the [released](https://docs.foursquare.com/data-products/docs/access-fsq-os-places) dataset of Foursquare OS Places. It is an interesting dataset because they have a lot of location-based data types, making it an excellent example for a showcase.

As the dataset is on [Huggingface](https://huggingface.co/datasets/foursquare/fsq-os-places), we can directly query it with the `hf://` interface of DuckDB:

```sql
Copy code

D select count(*) from read_parquet('hf://datasets/foursquare/fsq-os-places/release/dt=2025-01-10/places/parquet/*.parquet');
100% ▕████████████████████████████████████████████████████████████▏
┌──────────────┐
│ count_star() │
│    int64     │
├──────────────┤
│    104588312 │
└──────────────┘
```

INFO: Local DuckDB vs. MotherDuck
Interestingly, if we do that locally, the `count(*)` ran in `9.012281` seconds (my internet connection).
If I ran the same query on [MotherDuck UI](https://app.motherduck.com/) in `1.8`.
![query performance comparison](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgeo_02_779a38f4c9.png&w=3840&q=75)

This is also relevant when you create databases, as shown below. Instead of manually uploading them, we can directly make them through `hf://`.

#### Creating a Database in MotherDuck

Instead of downloading the full 11.05 GB locally (`aws s3 cp --no-sign s3://fsq-os-places-us-east-1/release/dt=2025-02-06/places/parquet . --recursive`), we can simply create a database over the network using the power of MotherDuck with:

```sql
Copy code

CREATE TABLE fsq_os_places AS
select * from read_parquet('hf://datasets/foursquare/fsq-os-places/release/dt=2025-01-10/places/parquet/*.parquet')
```

INFO: Foursquare Dataset shared as DuckDB Database on MotherDuck
This database is now available on MotherDuck as a shared Database. You can use it with `ATTACH 'md:_share/foursquare/0cbf467d-03b0-449e-863a-ce17975d2c0b'`
In the further details, I will use this database and you can follow along executing the same queries with that shared database. Find more details on [MotherDuck Docs](https://motherduck.com/docs/getting-started/sample-data-queries/foursquare/).

Now we can simply use the data from everywhere with MotherDuck in a shared Notebook or locally with:

```bash
Copy code

❯ duckdb
v1.2.0 5f5512b827
Enter ".help" for usage hints.
D ATTACH 'md:_share/foursquare/0cbf467d-03b0-449e-863a-ce17975d2c0b';
D show all databases;
┌─────────────┬─────────────┬──────────────────┬────────────────────────────────────────────────────────────┐
│    alias    │ is_attached │       type       │                    fully_qualified_name                    │
│   varchar   │   boolean   │     varchar      │                          varchar                           │
├─────────────┼─────────────┼──────────────────┼────────────────────────────────────────────────────────────┤
│ bsky        │ true        │ motherduck       │ md:bsky                                                    │
│ foursquare  │ true        │ motherduck       │ md:foursquare                                              │
└─────────────┴─────────────┴──────────────────┴────────────────────────────────────────────────────────────┘
D use foursquare;
D show tables;
┌───────────────────┐
│       name        │
│      varchar      │
├───────────────────┤
│ fsq_os_categories │
│ fsq_os_places     │
└───────────────────┘
```

We can check the data types with `describe fsq_os_places;` or check on [Places OS Data Schemas](https://docs.foursquare.com/data-products/docs/places-os-data-schema). If we check locally, we see that we have some geometric data:

```sql
Copy code

D describe fsq_os_places;
┌─────────────────────┬────────────────────────────────────────────────────────────┬─────────┬─────────┬─────────┬─────────┐
│     column_name     │                        column_type                         │  null   │   key   │ default │  extra  │
│       varchar       │                          varchar                           │ varchar │ varchar │ varchar │ varchar │
├─────────────────────┼────────────────────────────────────────────────────────────┼─────────┼─────────┼─────────┼─────────┤
│ fsq_place_id        │ VARCHAR                                                    │ YES     │         │         │         │
│ name                │ VARCHAR                                                    │ YES     │         │         │         │
│ latitude            │ DOUBLE                                                     │ YES     │         │         │         │
│ longitude           │ DOUBLE                                                     │ YES     │         │         │         │
│ address             │ VARCHAR                                                    │ YES     │         │         │         │
│ locality            │ VARCHAR                                                    │ YES     │         │         │         │
│ region              │ VARCHAR                                                    │ YES     │         │         │         │
...
│ geom                │ GEOMETRY                                                   │ YES     │         │         │         │
│ bbox                │ STRUCT(xmin DOUBLE, ymin DOUBLE, xmax DOUBLE, ymax DOUBLE) │ YES     │         │         │         │
```

#### Highest Chocolate Store Density in Swiss Cities

As the data contains Chocolate stores and I'm from Switzerland, the land of chocolate 😉, I was interested in the city with the most significant store density. We can do that with this data and DuckDB.

Let's first check the data and query all the cities with the 20 most entries:

```sql
Copy code

D select locality, count(*) from fsq_os_places where country = 'CH' group by locality order by 2 desc limit 20;
┌──────────────┬──────────────┐
│   locality   │ count_star() │
│   varchar    │    int64     │
├──────────────┼──────────────┤
│              │        84228 │
│ Zürich       │        32488 │
│ Basel        │        11975 │
│ Bern         │        11256 │
│ Genève       │        11083 │
│ Lausanne     │         9161 │
│ Luzern       │         6343 │
│ Winterthur   │         6058 │
│ St. Gallen   │         4807 │
│ Zurich       │         4497 │
│ Lugano       │         4027 │
│ Zug          │         3849 │
│ Geneva       │         2938 │
│ Chur         │         2611 │
│ Fribourg     │         2426 │
│ Thun         │         2383 │
│ Schaffhausen │         2288 │
│ Sion         │         2280 │
│ Aarau        │         2234 │
│ Carouge      │         2188 │
├──────────────┴──────────────┤
│ 20 rows           2 columns │
└─────────────────────────────┘
```

Secondly, we need the `category_id` for chocolate stores. We find these in the metadata table that comes with this dataset `fsq_os_categories`:

```sql
Copy code

D select distinct category_label, category_name, category_id  from fsq_os_categories  where lower(category_label) like '%chocolate%';
┌─────────────────────────────────────────────────────┬─────────────────┬──────────────────────────┐
│                   category_label                    │  category_name  │       category_id        │
│                       varchar                       │     varchar     │         varchar          │
├─────────────────────────────────────────────────────┼─────────────────┼──────────────────────────┤
│ Retail > Food and Beverage Retail > Chocolate Store │ Chocolate Store │ 52f2ab2ebcbc57f1066b8b31 │
└─────────────────────────────────────────────────────┴─────────────────┴──────────────────────────┘
```

Next, let's install and activate the spatial extensions:

```sql
Copy code

INSTALL spatial;
LOAD spatial;
```

As with the above city data, I chose the biggest cities in Switzerland—Zurich, Geneva, Bern, Basel, and Luzern—and checked the highest density of chocolate stores.

The query has three major queries: it defines city centers and their bounding boxes to speed up spatial queries by pre-filtering coordinates (not needed); second, it identifies chocolate stores within a 5km radius of each city center using spatial functions and category filtering; and third, it calculates store density per square kilometer and lists the three closest chocolate stores to each city center:

```sql
Copy code

WITH city_centers AS (
  SELECT * FROM (
    VALUES
      ('Zurich', ST_Point(8.5417, 47.3769), 8.5417-0.05, 8.5417+0.05, 47.3769-0.05, 47.3769+0.05),
      ('Geneva', ST_Point(6.1432, 46.2044), 6.1432-0.05, 6.1432+0.05, 46.2044-0.05, 46.2044+0.05),
      ('Bern', ST_Point(7.4474, 46.9480), 7.4474-0.05, 7.4474+0.05, 46.9480-0.05, 46.9480+0.05),
      ('Basel', ST_Point(7.5886, 47.5596), 7.5886-0.05, 7.5886+0.05, 47.5596-0.05, 47.5596+0.05),
      ('Luzern', ST_Point(8.3093, 47.0505), 8.3093-0.05, 8.3093+0.05, 47.0505-0.05, 47.0505+0.05),
  ) AS cities(city_name, center, lon_min, lon_max, lat_min, lat_max)
),
stores_by_city AS (
  SELECT
    c.city_name,
    p.name as store_name,
    ROUND(ST_Distance_Spheroid(
      ST_Point(p.longitude, p.latitude),
      c.center
    )::numeric, 2) as distance_from_center
  FROM fsq_os_places p
  CROSS JOIN city_centers c
  WHERE
	  ---unnest and filter by chocolate category
     array_contains(fsq_category_ids, '52f2ab2ebcbc57f1066b8b31')
    AND country = 'CH' --filter by metadata too to speed up
    AND p.longitude BETWEEN c.lon_min AND c.lon_max
    AND p.latitude BETWEEN c.lat_min AND c.lat_max
    AND ST_Distance_Spheroid(ST_Point(p.longitude, p.latitude), c.center) <= 5000
)
SELECT
  s.city_name,
  COUNT(*) as total_stores,
  -- Calculate stores per km² (area of 5km radius circle is π*5² ≈ 78.54 km²)
  ROUND(COUNT(*)::numeric / 78.54, 2) as stores_per_km2,
  (
    SELECT STRING_AGG(store_name, ', ')
    FROM (
      SELECT store_name
      FROM stores_by_city s2
      WHERE s2.city_name = s.city_name
      ORDER BY distance_from_center
      LIMIT 3
    )
  ) as closest_stores
FROM stores_by_city s
GROUP BY city_name
ORDER BY total_stores DESC;
```

The result looks like this:
![image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgeo_04_95f8656023.png&w=3840&q=75)

It is interesting to know that Geneva has 42 chocolate stores, which is 0.53 stores per km. If the data quality is correct, this is quite impressive. Geneva has a higher density of chocolate stores than Zurich and Basel. Unfortunately, my favorite city, Bern, is last in this measurement 🙂.

In the next step, you could visualize this on a map, but more on it and its libraries later in "Data Visualization".

TIP: Sign Up for Free
If you'd like to try this use case, [sign up](https://app.motherduck.com/) for free and start using the UI or any DuckDB-specific features.
To authenticate, you'll need to [get an access token](https://motherduck.com/docs/key-tasks/authenticating-and-connecting-to-motherduck/authenticating-to-motherduck/#authentication-using-an-access-token) initially and set it as an environment variable under `motherduck_token`. Then use `ATTACH 'md:'` to see all your databases.

#### Finding Store Clusters around Switzerland

Another common example is to build clusters. For example, store clusters allow us to identify retail hotspots where multiple businesses are located extremely close to each other. This analysis is particularly valuable for urban planners studying commercial density, real estate investors looking for high-traffic locations, or businesses seeking to understand competitive proximity. These micro-clusters often indicate shopping arcades, malls, or historic commercial districts where businesses benefit from shared foot traffic.

First, we install the spatial extension again (in case you haven't run it above):

```sql
Copy code

INSTALL spatial;
LOAD spatial;
```

The below query selects clusters of shops within a 2km radius of Biel, Switzerland, where neighboring businesses are located within 2 meters of each other, identifying extremely close commercial pairings that likely share walls or entrances:

```sql
Copy code

WITH base_location AS (
  SELECT
    ST_Point(7.2474174805428335, 47.13673837848461) as center  -- Biel, Switzerland
),
nearby_stores AS (
SELECT
    fsq_place_id,
    name,
    longitude,
    latitude,
    ST_Point(longitude, latitude) as location,
    -- Calculate distance in meters
    ROUND(ST_Distance_Spheroid(
        ST_Point(longitude, latitude),
        base_location.center
    )::numeric, 2) as distance_meters
FROM fsq_os_places, base_location
WHERE date_closed IS NULL
    -- Use bounding box for initial filtering
    AND longitude BETWEEN 7.0 AND 7.5
    AND latitude BETWEEN 46.9 AND 47.3
    -- Then apply precise distance filter
    AND ST_Distance_Spheroid(
        ST_Point(longitude, latitude),
        base_location.center
    ) <= 2000  -- 2km radius
)
 SELECT
  a.name as store1, CAST(a.latitude AS VARCHAR) || ', ' || CAST(a.longitude AS VARCHAR) as location,
  b.name as store2, CAST(b.latitude AS VARCHAR) || ', ' || CAST(b.longitude AS VARCHAR) as location,
  ROUND(ST_Distance(a.location, b.location), 2) as distance_meters
FROM nearby_stores a
JOIN nearby_stores b
  ON a.fsq_place_id < b.fsq_place_id
  AND ST_DWithin(a.location, b.location, 2)  -- Looking for stores within Xm of each other
ORDER BY distance_meters
LIMIT 20000;
```

The query employs a two-step spatial filtering process for efficiency: first using simple bounding box coordinates (longitude BETWEEN 7.0 AND 7.5) as a coarse filter, then applying the more computationally expensive `ST_Distance_Spheroid` function only on that filtered subset.

This approach significantly reduces processing time. The self-join with `a.fsq_place_id < b.fsq_place_id` ensures each pair is counted only once, while `ST_DWithin` efficiently identifies stores within the 2-meter proximity threshold without calculating exact distances until the final display.

This data lets you do many more use cases. I encourage you to play around with it yourself. We have shared the database on MotherDuck, so you can easily query it with DuckDB via `duckdb` and attach all databases with `ATTACH 'md:'` , or use [MotherDuck UI](https://app.motherduck.com/) and attach from there.

INFO: Fun Fact
DuckDB's Excel support was initially developed as part of the spatial extension before being separated in version 1.2. This highlights how the spatial extension serves as a format conversion utility, supporting numerous data formats beyond just traditional GIS files.

## Data Visualizations

Lastly, we explore data visualization. Before we explore libraries, check out Mehdi's fantastic showcase for visualizing data in Python Notebook using Lonboard in [this video](https://youtu.be/OuCY7_DzCTA?feature=shared), including the notebook shared on [Google Collab](https://colab.research.google.com/drive/1GNUJXYC2L-gTqD6x1Q7x8z7b9Gd5X4vV?usp=sharing).

Below are some of the most powerful and well-known Python libraries for visualizing geospatial data. The list should serve as an overview to navigate the space:

- **[Folium](https://python-visualization.github.io/folium/)**: Python wrapper for Leaflet.js that creates interactive maps with minimal code
- **[GeoPandas](https://geopandas.org/)**: Extends pandas to work with geospatial data and includes basic plotting capabilities
- **[Datashader](https://datashader.org/)**: Renders even the largest datasets accurately as images
- [Deck.gl](https://deck.gl/) Python wrappers, a GPU-powered framework for visual exploratory data analysis of large datasets.

  - **[PyDeck](https://pydeck.gl/)** : High-scale spatial rendering in Python, powered by deck.gl.
  - **[Lonboard](https://github.com/developmentseed/lonboard)**: library for fast, interactive geospatial vector data visualization in Jupyter.
- **[MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js)**: Interactive vector tile maps in the browser.
- **[HoloViews](https://holoviews.org/)** with **[GeoViews](https://geoviews.org/)**: High-level tools for easy visualization of complex data.
- **[Cartopy](https://scitools.org.uk/cartopy/docs/latest/)**: Specialized library for cartographic projections and geospatial visualization
- **[ipyleaflet](https://github.com/jupyter-widgets/ipyleaflet)**: Interactive maps in Jupyter notebooks
- **[Contextily](https://contextily.readthedocs.io/)**: Adds basemaps from web tile services to [matplotlib](https://matplotlib.org/) or GeoPandas plots.
- **[Seaborn](https://seaborn.pydata.org/)**: While not geospatial-specific, it can be combined with matplotlib for statistical visualizations on maps.
- Plots and chart libraries that include maps and geospatial capabilities:
  - **[Plotly](https://plotly.com/python/)**: Creates interactive visualizations, including maps with scattergeo, choropleth, and densitymapbox
  - **[Bokeh](https://bokeh.org/)**: Interactive visualization library with geospatial capabilities

NOTE: Everything About Maps and Data Visualization Is Hard.
A **quick reminder**: Everything is hard. That’s the thing with data visualization. You have to understand the data. You have to understand the context. You have to understand the technique. You have to be an artist. You have to understand composition and color theory. All of these are hard in a practical way and in a theoretical way— [Fil Rivière on We can always talk about maps](https://observablehq.com/blog/maps-and-data-visualization-with-fil-riviere)

## DuckDB & MotherDuck as a Single Tool for Your GIS Stack

You've seen how DuckDB can be helpful for geospatial work, especially with its extensions. It provides a quick and efficient way to analyze and work with location data, particularly when combined with notebooks for exploring and visualizing maps.

Beyond its optimization for analytical workloads, DuckDB's [versatile data processing](https://motherduck.com/blog/duckdb-enterprise-5-key-categories/) integrates seamlessly with modern data platforms. In many use cases, unifying storage and processing eliminates the need for separate spatial servers. MotherDuck extends these capabilities further, providing a scalable, collaborative backend that grows with your data needs.

Working with spatial data presents unique challenges, particularly when handling large polygon datasets. Our Foursquare example demonstrates that performance depends on having the right query strategy—using appropriate spatial joins and filtering by metadata when possible.

DuckDB showcases its strength through its simple yet powerful architecture. Whether running in-browser to minimize network latency or deploying as a MotherDuck instance for enterprise-scale applications, it reduces infrastructure complexity while maintaining performance.

Geospatial analysis powers countless daily applications—from delivery services to store locators—often invisibly enhancing our digital experiences. With DuckDB, this analytical power becomes accessible to every data engineer, democratizing capabilities once reserved for GIS specialists.

* * *

Further Reads/Videos and great examples:

- [Pushing the Boundaries of Geo Data with MotherDuck and Geobase! - MotherDuck Blog](https://motherduck.com/blog/pushing-geo-boundaries-with-motherduck-geobase/)
- [DuckDB Spatial](https://www.youtube.com/watch?v=hoyQnP8CiXE): Supercharged Geospatial SQL (GeoPython 2024)
- [Geospatial DuckDB](https://tech.marksblogg.com/duckdb-geospatial-gis.html): Practical guide to handling geospatial data in DuckDB with performance optimizations
- [Is DuckDB the Secret to Unlocking Your GIS Potential?](https://www.youtube.com/watch?v=OuCY7_DzCTA&t=10s)
- [Spatial data management with DuckDB ft. MattForrest](https://www.youtube.com/watch?v=roXhkcs0Cug) and [Geospatial Data Lakes! Maps from Motherduck (duckdb)](https://youtu.be/360BDapl4Hk?feature=shared)

### TABLE OF CONTENTS

[Why Geospatial Processing Matters](https://motherduck.com/blog/geospatial-for-beginner-duckdb-spatial-motherduck/#why-geospatial-processing-matters)

[Today, The Modern GIS Stack](https://motherduck.com/blog/geospatial-for-beginner-duckdb-spatial-motherduck/#today-the-modern-gis-stack)

[Geospatial in Action](https://motherduck.com/blog/geospatial-for-beginner-duckdb-spatial-motherduck/#geospatial-in-action)

[Data Visualizations](https://motherduck.com/blog/geospatial-for-beginner-duckdb-spatial-motherduck/#data-visualizations)

[DuckDB & MotherDuck as a Single Tool for Your GIS Stack](https://motherduck.com/blog/geospatial-for-beginner-duckdb-spatial-motherduck/#duckdb-motherduck-as-a-single-tool-for-your-gis-stack)

!['DuckDB In Action' book cover](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fduckdb-book-full-cover.68e4f598.png&w=3840&q=75)

Get your free book!

E-mail

Subscribe to other MotherDuck news

Submit

Free Book!

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![DuckDB Ecosystem: September 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_3_72ab709f58.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

[2025/09/09 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

### [DuckDB Ecosystem: September 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025)

DuckDB Monthly #33: DuckDB 58× faster spatial joins, pg\_duckdb 1.0, and 79% Snowflake cost savings

[![MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Feu_launch_blog_b165ff2751.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-in-europe/)

[2025/09/24 - Garrett O'Brien, Sheila Sitaram](https://motherduck.com/blog/motherduck-in-europe/)

### [MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/blog/motherduck-in-europe)

Serverless analytics built on DuckDB, running entirely in the EU.

[View all](https://motherduck.com/blog/)

Authorization Response