---
title: duckdb-tutorial-for-beginners
content_type: tutorial
source_url: https://motherduck.com/videos/duckdb-tutorial-for-beginners
indexed_at: '2025-11-25T20:44:13.531470'
content_hash: e15dc0df3360da35
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

DuckDB Tutorial For Beginners In 12 min - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[DuckDB Tutorial For Beginners In 12 min](https://www.youtube.com/watch?v=ZX5FdqzGT1E)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

More videos

## More videos

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Why am I seeing this?](https://support.google.com/youtube/answer/9004474?hl=en)

[Watch on](https://www.youtube.com/watch?v=ZX5FdqzGT1E&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 11:26

•Live

•

YouTubeTutorial

# DuckDB Tutorial For Beginners

2023/04/04

Imagine a world where the efficiency of database management meets the simplicity of in-process analytics. Sounds like a data analyst's dream, doesn't it? In the fast-paced era of big data, professionals often grapple with the trade-off between powerful analytics and ease of use. A staggering 80% of data scientists report spending a significant portion of their time on data preparation rather than analysis—highlighting a critical need for more efficient tools.

Enter DuckDB, an in-process SQL OLAP database engineered for analytical tasks. This article promises a deep dive into DuckDB, shedding light on its unique capability to blend database efficiency with straightforward management. Readers will embark on a journey through DuckDB's installation process, explore its core features, and apply its functionalities to real-world data analytics scenarios. Expect to uncover how DuckDB stands out in the world of data analytics, making it a compelling choice for developers and data analysts alike.

Are you ready to explore how DuckDB can revolutionize your data analytics workflow? Let's delve into the intricacies of this powerful database system.

## Introduction to DuckDB - A Deep Dive into the In-Process SQL OLAP Database

DuckDB emerges as a beacon of innovation in the database management landscape. As an in-process SQL OLAP database, it is specifically tailored for analytical tasks, offering a unique blend of performance and simplicity. Unlike conventional databases that demand extensive setup and management, DuckDB simplifies data analysis by running directly within user applications. This in-process nature eliminates the need for separate server processes, dramatically reducing overhead and streamlining data operations.

The allure of DuckDB lies in its seamless integration and ease of management. Developers and data analysts, often burdened by the complexity of database configuration and maintenance, will find solace in DuckDB's straightforward approach. Without sacrificing database efficiency, DuckDB enables immediate access to powerful analytics, directly within the application environment.

This unparalleled combination of efficiency and ease positions DuckDB as a valuable tool in the arsenal of any data professional. Whether conducting complex queries, performing large-scale aggregations, or managing data with precision, DuckDB offers a robust solution that caters to the dynamic needs of modern data analytics.

In setting the stage for a comprehensive exploration of DuckDB, we highlight its potential to redefine data management and analysis. For developers seeking to harness the power of SQL analytics without the overhead of traditional databases, and for data analysts aiming to expedite data preparation and dive deeper into analysis, DuckDB presents an enticing proposition.

As we venture further into the capabilities and practical applications of DuckDB, keep in mind this singular objective: to empower you with a tool that simplifies your data tasks while amplifying your analytical capabilities.

## Setting Up DuckDB - Step-by-Step Installation Guide

DuckDB's installation process is a testament to its design philosophy: making powerful data analytics accessible to everyone. Whether you're navigating through the setup on Windows, macOS, or Linux, DuckDB ensures a smooth and efficient installation process. This guide will walk you through the steps required to get DuckDB up and running on your machine, including the use of Homebrew for macOS users, highlighting the ease with which you can start leveraging DuckDB for your data analysis needs.

**Windows:**

1. **Download the DuckDB binary** suitable for Windows from the official DuckDB releases page.
2. **Extract the downloaded archive** to your desired location.
3. To make the DuckDB Command Line Interface (CLI) easily accessible, **add the binary's folder to your system's PATH** environment variable. This step enables you to launch DuckDB from the command prompt without having to navigate to the binary's directory.

**macOS:**

- For macOS users, the process is simplified through the use of **Homebrew**, a popular package manager. If you have Homebrew installed, setting up DuckDB is as simple as opening a terminal and running:


```
Copy code


brew install duckdb
```


This command not only downloads DuckDB but also ensures that the CLI is directly accessible from the terminal. Homebrew handles the PATH configuration automatically, streamlining the installation process.

**Linux:**

1. Similar to Windows, **start by downloading the DuckDB binary** for Linux from the official releases page.
2. **Extract the archive** to a directory of your choosing.
3. **Add the binary's directory to your PATH** environment variable to make the DuckDB CLI globally accessible from any terminal session.

For users across all operating systems, ensuring that the DuckDB CLI is directly accessible from the terminal or command prompt is a crucial step. It not only simplifies the workflow but also allows for quick experimentation and exploration of DuckDB's features.

After installation, you can verify that DuckDB is correctly set up by opening a terminal or command prompt and entering:

```
Copy code

duckdb
```

If the installation was successful, this command will launch the DuckDB CLI, presenting you with a prompt where you can start executing SQL commands directly.

This guide serves as a practical walkthrough for setting up DuckDB, designed to get you from installation to experimentation in minimal time. With DuckDB installed, you’re now poised to explore its robust features, from in-memory processing to persistent storage, and begin your journey into efficient data analysis.

## DuckDB Workflow and Features - An Overview

DuckDB emerges as a potent SQL OLAP database, engineered with a keen focus on analytical tasks. Its architecture harmoniously blends the speed of in-memory processing with the resilience and durability of persistent storage, establishing a versatile environment for data analysis.

**In-Memory Processing:** At its core, DuckDB thrives on an in-memory processing model. This framework ensures rapid query execution, pivotal for interactive analytics where response time is critical. Unlike traditional databases that may rely solely on disk-based operations, DuckDB's in-memory prowess allows for swift data manipulation and exploration, significantly enhancing the user experience.

**Switching to Persistent Storage:** DuckDB distinguishes itself with the seamless transition from in-memory to persistent storage. This capability is not just about data durability; it's about offering flexibility. Users can start with in-memory datasets for quick, ad-hoc analysis and then, with minimal effort, migrate these datasets to a persistent format. This dual-mode operation caters to a broad spectrum of analytical needs, from transient exploratory tasks to long-term data storage requirements.

**Custom File Format:** The foundation of DuckDB's efficient data storage and retrieval is its custom file format. This format employs a compressed columnar storage mechanism, which is a game-changer for large-scale aggregations. By storing data in columns rather than rows, DuckDB can achieve higher compression rates, reduce I/O operations, and expedite analytical queries, especially those involving aggregations across vast datasets.

**SQL Capabilities and the 'FROM FIRST' Syntax:** DuckDB not only excels in data storage and processing but also shines in its SQL capabilities. A notable feature is the support for the 'FROM FIRST' syntax. This innovation simplifies the SQL query structure, allowing users to fetch all columns of a dataset without the verbose `SELECT * FROM` command. Such enhancements in query simplicity empower both novice and experienced users to interact with data more efficiently, making DuckDB an attractive tool for a wide array of analytical projects.

In essence, DuckDB's architecture and features are meticulously designed to cater to the modern data analyst's needs. By balancing in-memory speed with the reliability of persistent storage and enhancing SQL interaction, DuckDB stands out as a robust solution for complex data analytics tasks.

## Interacting with Data in DuckDB - From Import to Analysis

The journey from data import to insightful analysis in DuckDB unfolds with remarkable simplicity and efficiency, a testament to its design catered towards empowering analytics. This section delves into the steps involved in importing data from CSV and Parquet files, creating tables, and exporting data. We will navigate through these processes using a real-world dataset from Kaggle, examining DuckDB's analytical capabilities in action.

**Step 1: Importing Data**

Importing data into DuckDB is straightforward, whether from CSV or Parquet files. For CSV files, DuckDB offers the `READ_CSV_AUTO` command, which automatically infers the schema of the file. This functionality eliminates the need for manual schema definition, accelerating the data import process. For Parquet files, known for their efficiency in storing large, columnar data, DuckDB provides seamless integration, allowing direct queries on Parquet-stored data without the need for explicit loading or conversion.

**Example:**

- **CSV Import:**`READ_CSV_AUTO('path/to/your/file.csv')` automatically detects and applies the correct data types for each column.
- **Parquet Import:** Directly query a Parquet file using `SELECT * FROM 'path/to/your/file.parquet'`.

**Step 2: Creating Tables**

After importing data, creating a table is essential for performing further operations like queries and aggregations. DuckDB simplifies this process with commands that allow for the creation of tables directly from imported data. This step is crucial for structuring the data in a way that optimizes query performance and enables more complex analytical tasks.

**Example:**

- `CREATE TABLE your_table AS SELECT * FROM READ_CSV_AUTO('path/to/your/file.csv')`

**Step 3: Querying and Analyzing Data**

With the data imported and tables created, the next step is to unleash DuckDB's analytical power. DuckDB's SQL engine supports a wide array of functions and operators, making it adept at handling complex analytical queries. From simple aggregations to sophisticated analytical functions, DuckDB provides the tools necessary for deep data analysis.

**Example:**

Consider a dataset from Kaggle detailing Netflix viewing trends. A query to find the most popular show during a specific period might look like this:

- `SELECT show_name, COUNT(*) AS view_count FROM netflix_data WHERE view_date BETWEEN '2020-03-01' AND '2020-04-30' GROUP BY show_name ORDER BY view_count DESC LIMIT 1;`

This query would return the most-watched show on Netflix during the first lockdown phase of the COVID-19 pandemic, showcasing DuckDB's ability to handle real-world analytical questions efficiently.

**Step 4: Exporting Data**

After analysis, exporting data for further use or reporting is often necessary. DuckDB supports exporting data to various formats, including CSV and Parquet, allowing for easy integration with other tools and platforms.

**Example:**

- **CSV Export:**`COPY (SELECT * FROM your_table) TO 'path/to/export/file.csv' WITH (FORMAT CSV)`
- **Parquet Export:**`COPY (SELECT * FROM your_table) TO 'path/to/export/file.parquet' (FORMAT PARQUET)`

Through these steps, DuckDB demonstrates its suitability for a wide range of data analytics projects. From importing to analyzing and finally exporting data, DuckDB streamlines the workflow, making it accessible for users with varying levels of expertise. The hands-on example with the Kaggle dataset not only illustrates DuckDB's analytical prowess but also highlights its practical application in answering real-world questions. DuckDB's ability to handle diverse data types and complex queries, all while maintaining high performance, underscores its value as a tool in the modern data analyst's toolkit.

## Extensions and Customization in DuckDB - Enhancing Functionality

DuckDB's architecture not only excels in delivering high-performance analytics but also shines in its extensibility and customization capabilities. A pivotal feature of DuckDB is its robust support for extensions, which significantly broadens its functionality and adaptability to specific use cases. This flexibility allows users to enhance the core capabilities of DuckDB, making it a versatile tool for a wide array of data tasks.

**Core Extensions: An Overview**

Among the myriad of extensions available, the HTTP FS extension stands out for its utility in reading and writing remote files. This extension exemplifies DuckDB's commitment to addressing modern data engineering challenges, enabling seamless access to data stored across various cloud platforms. Such functionality is crucial for organizations leveraging cloud storage solutions like AWS S3 or Google Cloud Storage, facilitating direct interactions with data without the need for intermediary steps.

**Installing Extensions**

The process of enriching DuckDB with additional capabilities through extensions is straightforward:

1. **Identify the Extension:** Start by exploring the available extensions. For instance, the HTTP FS extension caters to the need for handling remote files.
2. **Installation Command:** Use the `INSTALL` command followed by the name of the extension, such as `INSTALL 'http_fs';` This command fetches and installs the extension, integrating it with DuckDB.

**Loading Extensions**

Once installed, loading the extension into your current DuckDB session is the next step:

- **Load Command:** Execute the `LOAD` command with the extension name, like `LOAD 'http_fs';` This action makes the functionalities of the extension available for use.

**Practical Application**

Consider the scenario where a data analyst needs to access a dataset stored on AWS S3. With the HTTP FS extension, DuckDB can directly query this remote data, streamlining the workflow significantly. This capability eliminates the need for downloading large datasets to local storage before analysis, thereby optimizing both time and resource utilization.

**Customization for Project Requirements**

The true power of DuckDB's extensions lies in their potential for customization. Users can tailor the database to their specific project needs, whether it involves working with unique data formats, integrating with cloud services, or enhancing analytical functions. This level of customization ensures that DuckDB remains a relevant and powerful tool, regardless of the evolving data landscape.

- **Explore and Utilize:** Users are encouraged to explore the vast library of DuckDB extensions. Experimentation and integration of these extensions can lead to improved efficiency, novel analytical capabilities, and solutions perfectly adapted to unique project requirements.

DuckDB's support for extensions is a testament to its design philosophy—combining the efficiency and power of a traditional database with the flexibility and user-friendliness of modern data tools. By leveraging these extensions, users can significantly enhance DuckDB's functionality, adapting it to meet and exceed project demands. Whether it's through the integration of remote file systems or the addition of custom analytical functions, DuckDB's extensibility ensures it remains a potent tool in the data analyst's arsenal.

## Practical Use Case: Analyzing Netflix Viewing Trends with DuckDB

The COVID-19 pandemic, a period marked by lockdowns and social distancing, saw a significant shift in entertainment consumption patterns. With millions confined to their homes, streaming platforms, especially Netflix, experienced unprecedented viewership. DuckDB, with its agile data processing capabilities, presents an ideal solution for analyzing these shifting trends. This section delves into a practical application of DuckDB by examining the top-viewed Netflix shows during the lockdown, illustrating the database's prowess in handling real-world data analytics.

**Step 1: Data Import**

The initial phase involves importing the Netflix viewership dataset into DuckDB. The dataset, sourced from Kaggle, encompasses the United States' daily top 10 TV shows and movies on Netflix from March 2020 to March 2022. Utilizing DuckDB's `READ_CSV_AUTO` command makes the import process seamless, automatically inferring the schema of the dataset. This simplicity accelerates the setup, allowing analysts to focus on the analysis rather than the preliminaries of data preparation.

**Step 2: Query Execution**

With the data imported, the next step involves crafting SQL queries to dissect the viewership patterns. DuckDB's efficient in-memory processing shines here, enabling rapid execution of complex queries. Analysts might seek to identify the longest-standing shows in the top 10, necessitating aggregation and sorting operations. DuckDB's SQL capabilities, particularly its support for the `FROM FIRST` syntax, simplify these tasks, making the data more accessible for analysis.

**Step 3: Unveiling Insights**

The execution of these queries yields intriguing insights into the viewing habits during the lockdown. For example, findings might reveal a dominance of children's programming in the top ranks, suggesting a high demand for family-friendly content as parents sought to entertain their children during the lockdown. Such insights not only inform content strategy but also offer a glimpse into societal behaviors in unprecedented times.

**Step 4: Exporting Data**

After gleaning insights, DuckDB facilitates the export of results for further analysis or presentation. Whether the preference is for CSV, Parquet, or another format, DuckDB's export capabilities ensure that the data is easily sharable and ready for any next steps, from reporting to more in-depth analysis with other tools.

**Demonstrating DuckDB's Efficacy**

This practical use case underscores DuckDB's suitability for data analytics projects, from the ease of importing and querying data to the efficient extraction of insights. The analysis of Netflix viewing trends during the COVID-19 lockdown not only showcases the database's technical prowess but also highlights its potential to drive valuable business decisions. Through this example, DuckDB proves itself as a powerful tool in the data analyst's toolkit, capable of turning vast datasets into actionable knowledge.

...SHOW MORE

## Related Videos

[!["Is DuckDB the Secret to Unlocking Your GIS Potential?" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmaxresdefault_1_c988e40ed0.jpg&w=3840&q=75)\\
\\
14:49](https://motherduck.com/videos/is-duckdb-the-secret-to-unlocking-your-gis-potential/)

[2024-08-29](https://motherduck.com/videos/is-duckdb-the-secret-to-unlocking-your-gis-potential/)

### [Is DuckDB the Secret to Unlocking Your GIS Potential?](https://motherduck.com/videos/is-duckdb-the-secret-to-unlocking-your-gis-potential)

In this video, ‪Mehdi walks you through the basics of working with geospatial data and introduces the DuckDB spatial extension. By the end, you will create your own heatmap using DuckDB, Python, and MotherDuck for sharing and scalability.

YouTube

Tutorial

[!["DuckDB & dataviz | End-To-End Data Engineering Project (3/3)" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fvideo_ta_Pzc2_EE_Eo_23e0b0a9d0.jpg&w=3840&q=75)\\
\\
0:21:46](https://motherduck.com/videos/duckdb-dataviz-end-to-end-data-engineering-project-33/)

[2024-06-27](https://motherduck.com/videos/duckdb-dataviz-end-to-end-data-engineering-project-33/)

### [DuckDB & dataviz \| End-To-End Data Engineering Project (3/3)](https://motherduck.com/videos/duckdb-dataviz-end-to-end-data-engineering-project-33)

In this part 3 of the project, @mehdio explores how to build a Dashboard with Evidence using MotherDuck/DuckDb as a data source.

YouTube

BI & Visualization

Tutorial

[!["DuckDB & dbt | End-To-End Data Engineering Project (2/3)" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fvideo_Spf_EQQXBGMQ_ae19000d3a.jpg&w=3840&q=75)\\
\\
0:37:25](https://motherduck.com/videos/duckdb-dbt-end-to-end-data-engineering-project-23/)

[2024-03-01](https://motherduck.com/videos/duckdb-dbt-end-to-end-data-engineering-project-23/)

### [DuckDB & dbt \| End-To-End Data Engineering Project (2/3)](https://motherduck.com/videos/duckdb-dbt-end-to-end-data-engineering-project-23)

@mehdio is taking you to part 2 of this end-to-end data engineering project series: transform data using dbt and DuckDB! You will be leveraging all the in-memory capabilities of DuckDB to smooth your development process and deployment to t

YouTube

Data Pipelines

dbt

Tutorial

Ecosystem

[View all](https://motherduck.com/videos/)

Authorization Response