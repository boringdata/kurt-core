---
title: why-learn-sql-in-2024
content_type: tutorial
source_url: https://motherduck.com/blog/why-learn-sql-in-2024
indexed_at: '2025-11-25T19:58:11.647304'
content_hash: 11a1c230f187468e
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Why You Should Learn SQL in 2024

2024/01/31 - 4 min read

BY
David Neal

Throughout human history, every advancement or achievement has been driven by our ability to capture, store, and share information. Business, government, education, healthcare, research, agriculture, and every other sector rely on information, or data, for decision-making, growth, and success. The demand for collecting and analyzing data will only continue to grow.

More than ever, organizations collect raw data from internal and external sources. An organization might mine that data to answer questions and gain insight using reporting applications, dashboards, charts, maps, and other tools. However, there’s still much work to be done to get that raw data into those tools, or there may be valuable information those tools can miss.

## SQL is an Essential Skill

SQL, which stands for Structured Query Language, is a computer language created for the purpose of manipulating sets of data. SQL can be used to filter, transform, and join data together. SQL is typically used for data sets stored as rows and columns, similar to a spreadsheet. The container that holds and organizes these data sets is called a database.

Since its creation in the 1970s, SQL has become the standard for analyzing data. In Stack Overflow’s [2023 survey](https://survey.stackoverflow.co/2023/#section-most-popular-technologies-programming-scripting-and-markup-languages), SQL is ranked #3 among languages used by professional programmers.

For every organization that relies on data (arguably every organization), SQL is the indispensable skill they need to get the most value out of their data. Many modern business data tools support SQL, making SQL a valuable skill, even if you aren’t the person responsible for creating and managing databases.

## SQL is a Portable Skill

To query or manipulate data with SQL, you write statements using keywords like “SELECT” and “FROM.” This SQL syntax has been standardized by ANSI and is ISO-certified. That means out of the hundreds of databases and data tools available today that support SQL, the core syntax remains the same.

Some databases and tools may extend that syntax with specialized operators, commands, or functions. However, once you learn the basics of SQL, you can leverage that knowledge wherever you go!

## SQL is an Accessible Skill

Basic SQL syntax is very readable, almost sentence-like. SQL syntax describes how data should be retrieved or operated upon. Take the following query, for example.

```sql
Copy code

SELECT first_name, last_name, date_of_hire
FROM employees
WHERE date_of_hire > '2018-12-31'
ORDER BY date_of_hire, last_name;
```

The keywords used in the previous syntax are SELECT, FROM, WHERE, and ORDER BY. These do not have to be capitalized, but many people capitalize them by convention.

- **SELECT** specifies which pieces of information, known as columns, to include in the results. In this example, the query asks for the first name, last name, and date each employee was hired. There may be other columns in the same data set, but only these three will be returned in the results.
- **FROM** specifies the name of the data source similar to the name of a spreadsheet. It's usually a table in the database but it could be another type of data source.
- **WHERE** is used to filter the data. In this example, the WHERE instructs the database to only return the employees who were hired after December 31, 2018.
- **ORDER BY** specifies how the results should be sorted. This example instructs the data should be sorted first by the date of hire, and then by the employee’s last name.

## Learning SQL is Easier with DuckDB and MotherDuck

The best way to learn SQL is hands-on, experimenting with the syntax and seeing how changes to the syntax affect the results. This means you need access to a database that contains some data to query. Traditionally, corporate databases have been off-limits to casual learners, hosted databases have been too expensive, and most free open-source databases have not been practical to set up and maintain.

[DuckDB](https://duckdb.org/) is a lightweight application for analyzing data with SQL on your local computer. It can read all kinds of data formats so you can start querying data right away.

[MotherDuck](https://motherduck.com/) takes all the goodness of DuckDB, stirs in more features, and lets you run SQL using only your Web browser. As soon as you create and log in to your [free MotherDuck account](https://app.motherduck.com/?auth_flow=signup), you can start querying the included [sample data](https://motherduck.com/docs/getting-started/e2e-tutorial). There’s even a built-in [SQL syntax checker](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/) that will suggest and fix your syntax should you make any mistakes!

## Make 2024 the Year You Learn SQL

SQL is an accessible, ubiquitous, and valuable language you can learn in 2024. It’s a marketable skill that practically every organization needs. To start your learning journey, check out the following!

- [MotherDuck tutorial](https://motherduck.com/docs/getting-started/e2e-tutorial)
- [Friendly SQL with DuckDB](https://www.youtube.com/watch?v=Rao5Hlir6Y8) “Quack & Code” livestream video
- [Friendlier SQL with DuckDB](https://duckdb.org/2022/05/04/friendlier-sql.html)

### TABLE OF CONTENTS

[SQL is an Essential Skill](https://motherduck.com/blog/why-learn-sql-in-2024/#sql-is-an-essential-skill)

[SQL is a Portable Skill](https://motherduck.com/blog/why-learn-sql-in-2024/#sql-is-a-portable-skill)

[SQL is an Accessible Skill](https://motherduck.com/blog/why-learn-sql-in-2024/#sql-is-an-accessible-skill)

[Learning SQL is Easier with DuckDB and MotherDuck](https://motherduck.com/blog/why-learn-sql-in-2024/#learning-sql-is-easier-with-duckdb-and-motherduck)

[Make 2024 the Year You Learn SQL](https://motherduck.com/blog/why-learn-sql-in-2024/#make-2024-the-year-you-learn-sql)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: January 2024](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fjanuary_2024_d1e35e2c15.jpg&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2024/)

[2024/01/30 - Ryan Boyd](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2024/)

### [This Month in the DuckDB Ecosystem: January 2024](https://motherduck.com/blog/duckdb-ecosystem-newsletter-january-2024)

DuckDB Monthly January: Featuring Mihai Bojin & Marcelo Cenerino , top content, and upcoming events!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response