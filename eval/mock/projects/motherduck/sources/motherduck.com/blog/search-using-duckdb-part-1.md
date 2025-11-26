---
title: search-using-duckdb-part-1
content_type: blog
source_url: https://motherduck.com/blog/search-using-duckdb-part-1
indexed_at: '2025-11-25T19:58:08.945929'
content_hash: d463f99a94522509
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Building Vector Search in DuckDB

2024/04/19 - 7 min read

BY

[Adithya Krishnan](https://motherduck.com/authors/adithya-krishnan/)

Many of today’s analytical tasks involve textual data, such as product reviews for an e-commerce store. These tasks include, but are not limited to, classification, clustering, and similarity comparison. They are performed primarily using vector embedding representations of the textual data to enable vector search capabilities.

DuckDB provides the [Array](https://duckdb.org/docs/sql/data_types/array.html) and [List](https://duckdb.org/docs/sql/data_types/list.html) data types, which can be used to store and process vector embeddings in DuckDB or MotherDuck to enable vector search. In the first of three blogs in this series, we will explore similarity comparison to learn how to use vector embeddings in DuckDB. We’ll cover vector embeddings, cosine similarity, and embeddings-based vector search.

## What is Vector Search?

In the world of Natural Language Processing (NLP), Vector Embeddings, or vector search, refer to the numerical representations of textual data. These embeddings transform words, phrases, or even entire documents into vectors of real numbers, that capture word relationships and semantic meaning of the textual data. Representing text as vector embeddings enables the possibility of applying mathematical operations such as similarity comparison, clustering, and classification. Let's look at an example to understand this further.

Here are vector embeddings for four words using a simple vector embeddings model:

![image 1](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_1_db24a6389f.png&w=3840&q=75)

Note: The above vector embeddings were generated using the [mixedbread-ai/mxbai-embed-large-v1](https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1) model. Since this model generates embeddings of size 1024, the vectors were reduced to 2 dimensions using PCA so that they can be plotted and discussed. Also, the decimals of the embeddings and the following similarity scores were rounded to 2 places for simplicity.

Visualizing them on a graph gives us:

![graph visualization](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_4d6fb99e3d.png&w=3840&q=75)

From our semantic knowledge we know that the words "dog" and "bark" are related similarly to how "cat" and "meow" are. At first glance, we see the words "dog" and "bark" on one side of the x-axis, with "cat" and "meow" on the other. To quantitatively analyze these word relationships, we would have to use a metric like cosine similarity.

## What is Cosine Similarity?

Cosine Similarity is a metric for calculating the semantic similarity of vector embeddings. It is also commonly used in the semantic retrieval of information. We calculate it by taking the [dot product](https://simple.wikipedia.org/wiki/Dot_product#:~:text=In%20mathematics%2C%20the%20dot%20product,used%20to%20designate%20this%20operation.) of the two normalized vectors.

- A value of 1 for this metric indicates that the two vectors are identical
- A value of 0 means they are independent (orthogonal)
- A value of -1 indicates that they are diametrically opposed (opposites)

Outlined below, we have the cosine of the word pairs listed:

![image 2](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_2_569c19d0b8.png&w=3840&q=75)

By comparing the cosine("dog", "meow") with cosine("cat", "bark"), we can infer that "meow" is almost the opposite of "dog" and the same for "cat" and "bark." Of the words we have, we see that "dog" relates most to "bark," and "cat" relates most to "meow." Interestingly enough, although "meow" and "bark" are opposites, "dog" and "cat" are not. Perhaps this model captures the commonality that they are both domesticated animals and pets that are also very cute. 😆

## DuckDB's Array Type and Cosine Similarity Function

Since version 0.10, DuckDB has provided the `ARRAY` type to store fixed-sized arrays that are perfect for storing vector embeddings. This means that all the fields in the ARRAY type column have the same length and the same underlying type. To initialize a table with this data type, you would need to specify the data type of each element in the array followed by square brackets with the array size; for example, `FLOAT[2]` would initialize an array of size 2 with each element being a FLOAT.

Let's look at how to implement the above data into a table:

```sql
Copy code

CREATE TABLE word_embeddings (word VARCHAR, embedding FLOAT[2]);
INSERT INTO word_embeddings
VALUES ("dog", [ 0.23, 0.37]),
       ("cat", [-0.27, 0.29]),
       ("bark", [ 0.35, -0.02]),
       ("meow", [-0.32, -0.09]);
```

This gives us a table with the words and their vector embeddings. DuckDB also provides a function `array_cosine_similarity(array1, array2)` to calculate the cosine similarity metric between 2 vectors.

For the above table, let’s calculate the cosine similarity metric for the word pairs:

```vbnet
Copy code

SELECT x.word as word_1,
       y.word as word_2,
       array_cosine_similarity(x.embedding, y.embedding) AS similarity_metric
FROM word_embeddings AS x
CROSS JOIN word_embeddings AS y
WHERE word_1 > word_2
ORDER BY similarity_metric DESC;
```

This gives us the same results as the above section:

![image 3](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_3_2cf8ec8c90.png&w=3840&q=75)

Note: Until DuckDB v 0.10.0, the data type `LIST` which is for storing variable sized arrays, could also be used for storing embeddings. For which you'd use the function `list_cosine_similarity`.

## How does Embedding-based Retrieval work to enable Vector Search?

The core idea behind embedding-based retrieval is to represent both query input and the items in a dataset as vector embeddings in a high-dimensional space, such that the semantic similarity is reflected when ranking the cosine similarity metric between the query and items. So, by ranking the items in the dataset based on the cosine similarity with the given query, the top score ranking items are most relevant. Let's look at this using a [movie dataset from Kaggle](https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset?resource=download).

The dataset has titles and overviews of movies, for which I've calculated the vector embeddings of the title and the overview by using the [mxbai-embed-large-v1](https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1) model with the [sentence-transformers](https://www.sbert.net/) package.

![image 4](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_4_8299fc0412.png&w=3840&q=75)

Now, let's say I want to search for a movie that is very similar to this description: `a movie about a warrior fighting for his community`. To retrieve relevant movies, let's calculate an embedding of the description and search it against embeddings of the items in the dataset.

### Similarity with Title Embeddings

The following SQL query implements the similarity retrieval of the embedding of the description above against the title embeddings. The query calculates the cosine similarity, and orders the entries in descending order and picks the top 5 items. We see that the titles of these items contain the word warrior.

```vbnet
Copy code

SELECT title, overview
    FROM (
        SELECT *, array_cosine_similarity(title_embeddings, [0.7058067321777344, -0.0012793205678462982, -0.08653011173009872...]) AS score
        FROM movies_embeddings
    ) sq
    WHERE score IS NOT NULL
    ORDER BY score DESC LIMIT 5;
```

![image 5](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_5_8bef57dd51.png&w=3840&q=75)

### Similarity with Overview Embeddings

When running the similarity retrieval of the embedding of the description above against the overview embeddings, the results are completely different as they match the overview. This is due to the overview attribute for each movie containing more and different words that relate to the movie than the title. The overview embeddings would be more semantically similar to the movie description embedding than the the title which are sometimes not very descriptive of the movie itself.

![image 6](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_6_81d38fbd94.png&w=3840&q=75)

### Similarity with a Composite of the Embeddings

Since we have 2 embeddings in our dataset, we can calculate a composite of them by summing up both scores and rank it based on the sum.

```vbnet
Copy code

SELECT title, overview
    FROM (
        SELECT *,
        array_cosine_similarity(title_embeddings, [0.7058067321777344, ...]) AS score_1,
        array_cosine_similarity(overview_embeddings, [0.7058067321777344, ...]) AS score_2
        FROM movies_embeddings
    ) sq
    WHERE score_1 IS NOT NULL AND score_2 IS NOT NULL
    ORDER BY score_1+score_2 DESC LIMIT 5;
```

This time around, we get a different result that's somewhat similar to the first one.

![image 7](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage_7_43209e1948.png&w=3840&q=75)

## Conclusion

The depth and richness of information contained in textual data makes it very valuable. With vector embeddings, by translating language into a mathematical space, we enable a multitude of operations that provide an opportunity to extract and transform the information stored in it, thereby unlocking vector search functionality.

DuckDB, with its efficient processing capabilities and user-friendly SQL interface, eases the process of working with vector embeddings. Whether you’re performing similarity searches, clustering, or executing any other vector-based operation, DuckDB provides a seamless bridge to execute analytical experiments closer to your textual data.

These features are directly available in [MotherDuck](https://motherduck.com/product/) to enable you to store and analyze textual data at scale.

### TABLE OF CONTENTS

[What is Vector Search?](https://motherduck.com/blog/search-using-duckdb-part-1/#what-is-vector-search)

[What is Cosine Similarity?](https://motherduck.com/blog/search-using-duckdb-part-1/#what-is-cosine-similarity)

[DuckDB's Array Type and Cosine Similarity Function](https://motherduck.com/blog/search-using-duckdb-part-1/#duckdbs-array-type-and-cosine-similarity-function)

[How does Embedding-based Retrieval work to enable Vector Search?](https://motherduck.com/blog/search-using-duckdb-part-1/#how-does-embedding-based-retrieval-work-to-enable-vector-search)

[Conclusion](https://motherduck.com/blog/search-using-duckdb-part-1/#conclusion)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: March 2024](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ffebruary_2024_896d875c5b.jpg&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-march-2024/)

[2024/03/28 - Mehdi Ouazza](https://motherduck.com/blog/duckdb-ecosystem-newsletter-march-2024/)

### [This Month in the DuckDB Ecosystem: March 2024](https://motherduck.com/blog/duckdb-ecosystem-newsletter-march-2024)

DuckDB Monthly: Matt Forrest, end-to-end data projects, DuckCon lightning talks videos and more!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response