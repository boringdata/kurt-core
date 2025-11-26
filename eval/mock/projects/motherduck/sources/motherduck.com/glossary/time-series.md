---
title: time-series
content_type: tutorial
source_url: https://motherduck.com/glossary/time-series
indexed_at: '2025-11-25T20:02:48.480270'
content_hash: b93a6b3deb0dd5dc
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# Time Series Data Analysis

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

A time series is a sequence of data points collected and ordered chronologically at regular intervals. In the context of data analysis and engineering, time series data often represents measurements or observations of a particular phenomenon over time, such as stock prices, temperature readings, or website traffic. Time series data is characterized by its temporal nature, where the order and spacing of data points are crucial for understanding trends, patterns, and seasonality.

## Use Cases for Time-Series Data Analysis

**1\. Trend analysis:** Identifying long-term patterns or directions in the data.

**2\. Seasonality detection:** Recognizing recurring patterns at fixed intervals.

**3\. Forecasting:** Predicting future values based on historical data.

When working with time series data in DuckDB, you can leverage built-in functions like `date_trunc()` for grouping data into specific time intervals and window functions for calculating moving averages or cumulative sums.

### Forecasting example chart

![Post Image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fforecast_graph_0ede5ca8a2.svg&w=3840&q=75)

## Moving Average Window Query

Here's a window function for computing 7-day moving average of daily sales.

### Animation

![Post Image](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fwindow_function_e3e77e310a.svg&w=3840&q=75)

### SQL Query

```sql
Copy code

SELECT
    date,
    sales,
    AVG(sales) OVER (
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_avg
FROM daily_sales
ORDER BY date;
```

Time series data is commonly used in various fields, including finance, meteorology, economics, and IoT applications. While specialized time series databases like [InfluxDB](https://www.influxdata.com/) or [TimescaleDB](https://www.timescale.com/) exist for this type of data, many types of time series queries and analyses can be done very efficiently in DuckDB.

## Examples of DuckDB for time-series data

The _DuckDB in Action_ book, published by Manning (available as a [Free PDF Download](https://motherduck.com/duckdb-book-brief/)), uses a sample data set of power generation data. The authors have published some great [time-series queries](https://duckdbsnippets.com/snippets/148/duckdb-in-action-examples-from-chapters-3-and-4-having-fun-with-power-production-measurements) as a DuckDB Snippet.

The Evidence team has also published [SQL Prophet](https://github.com/evidence-dev/sql-prophet) showing time-series forecasting with DuckDB and evidence.

Authorization Response