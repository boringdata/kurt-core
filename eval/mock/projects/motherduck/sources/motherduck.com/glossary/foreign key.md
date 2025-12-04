---
title: 'DuckDB Data Engineering Glossary: foreign key'
content_type: reference
description: Making analytics ducking awesome with DuckDB. Start using DuckDB in the
  cloud for free today.
published_date: '2024-10-30T00:00:00'
source_url: https://motherduck.com/glossary/foreign key
indexed_at: '2025-11-25T20:02:06.728099'
content_hash: 04f3ba9282c63e18
has_code_examples: true
---

# foreign key

[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)

## Definition

A foreign key is a column or set of columns in a database table that creates a link between data in two tables. It acts as a reference to a primary key in another table, maintaining referential integrity in a relational database. Think of it like a cross-reference that ensures data consistency - if you have an `order_id`

column in a customer orders table, you want to make sure it always points to a valid order in your orders table.

## Implementation

In DuckDB and other databases, you define a foreign key as part of your table creation using the `FOREIGN KEY`

constraint. This tells the database to enforce the relationship between tables by preventing invalid references. Here's an example:

Copy code

```
CREATE TABLE orders (
id INTEGER PRIMARY KEY,
total DECIMAL(10,2)
);
CREATE TABLE order_items (
id INTEGER PRIMARY KEY,
order_id INTEGER,
product_name VARCHAR(100),
quantity INTEGER,
FOREIGN KEY (order_id) REFERENCES orders(id)
);
```


In this example, `order_id`

in the `order_items`

table is a foreign key that references the `id`

column in the `orders`

table. DuckDB will prevent you from:

- Inserting an order item with an
`order_id`

that doesn't exist in the`orders`

table - Deleting an order from
`orders`

if there are still items referencing it in`order_items`


## Composite Foreign Keys

You can also create foreign keys that reference multiple columns, known as composite foreign keys:

Copy code

```
CREATE TABLE locations (
country_code CHAR(2),
region_code CHAR(2),
city VARCHAR(100),
PRIMARY KEY (country_code, region_code)
);
CREATE TABLE stores (
id INTEGER PRIMARY KEY,
country_code CHAR(2),
region_code CHAR(2),
address VARCHAR(200),
FOREIGN KEY (country_code, region_code)
REFERENCES locations(country_code, region_code)
);
```


## Performance Considerations

Foreign keys automatically create an index on the referencing columns in DuckDB, which can help with query performance when joining tables. However, they also add overhead during data modifications since the database must check referential integrity with each insert or update.