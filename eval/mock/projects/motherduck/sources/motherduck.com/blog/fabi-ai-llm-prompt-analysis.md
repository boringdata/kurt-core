---
title: fabi-ai-llm-prompt-analysis
content_type: tutorial
source_url: https://motherduck.com/blog/fabi-ai-llm-prompt-analysis
indexed_at: '2025-11-25T19:56:41.341258'
content_hash: 7e96974266e7d2ef
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# How to build an interactive, shareable sentiment analysis dashboard with MotherDuck & Fabi.ai

2025/02/12 - 12 min read

BY

[Marc Dupuis](https://motherduck.com/authors/Marc-D/)

Text analysis presents unique challenges for businesses trying to understand customer feedback. Analyzing survey responses or product reviews can improve your customer experience. But, at the same time, extracting insights from unstructured text data is complex and time-consuming.

Large Language Models (LLMs) and [Small Language Models](https://motherduck.com/blog/sql-llm-prompt-function-gpt-models/) (SMLs) excel at this task. However, integrating them into real-time, business-ready dashboards requires careful consideration of performance, cost, and usability.

Thankfully, MotherDuck is uniquely well-suited for this task for two reasons:

1. It’s a **highly-performant, cost-effective data warehouse** designed for analytics use cases.
2. It’s **the only data warehouse with a built-in language model that can take in arbitrary prompts** to enrich and manipulate data on the fly

Adding on, [Fabi.ai](https://www.fabi.ai/)–an AI data analytics platform with SQL, Python, and AI support– [perfectly complements MotherDuck](https://motherduck.com/ecosystem/fabi/). Fabi.ai provides the fastest way in the market to go from raw data to interactive, shareable reports.

This tutorial will show you how to use MotherDuck's prompt() function and vector embeddings, along with [Fabi.ai's visualizations](https://medium.com/fabi-ai/the-future-of-ai-data-visualization-9bec3d8c6074). We'll label data for sentiment analysis and create an interactive dashboard to improve your customer experience.

## **What we’ll build: An interactive sentiment analysis dashboard**

By the end of this article, you’ll know how to build an end-to-end sentiment analysis process, including:

- A **MotherDuck query that analyzes a free-form review field** and categorizes reviews as “Positive”, “Neutral”, or “Negative.”
- An **interactive dashboard that shows reviews and insights** based on review sentiment and product category.
- **Dynamic filtering capabilities** for product categories and sentiment types.
- **A semantic search function using vector embeddings** for intelligent review discovery.
- **An automated refresh system** to keep your analysis current.

To see the end result in action, check out our video:

How to build a sentiment analysis dashboard using MotherDuck & Fabi.ai - YouTube

[Photo image of Fabi.ai: AI data analysis platform](https://www.youtube.com/channel/UCMv7ZPxYL9SYo2lbKTUMtlg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

Fabi.ai: AI data analysis platform

760 subscribers

[How to build a sentiment analysis dashboard using MotherDuck & Fabi.ai](https://www.youtube.com/watch?v=rGKvdLUxS6c)

Fabi.ai: AI data analysis platform

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

Full screen is unavailable. [Learn More](https://support.google.com/youtube/answer/6276924)

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=rGKvdLUxS6c&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 17:32

•Live

•

## **What is sentiment analysis, and what makes it challenging?**

[Sentiment analysis](https://www.ibm.com/think/topics/sentiment-analysis) is a technique in natural language processing that identifies and categorizes opinions or emotions expressed in text. It checks if the sentiment is positive, negative, or neutral and is often used to analyze customer feedback, social media, or reviews. This helps businesses and researchers understand public sentiment and make data-driven decisions about their products. Sentiment analysis is also a powerful tool for customer success and marketing teams because it can help them identify issues with their services or products, and understand what customers and users like about their offerings.

In our example, sentiment analysis means categorizing customer product reviews into “Positive”, “Neutral,” or “Negative” categories.

Traditional sentiment analysis methods, [like rule-based systems](https://www.analyticsvidhya.com/blog/2021/06/rule-based-sentiment-analysis-in-python/) and ML models, often struggle with context, sarcasm, and adapting to new domains. Rule-based approaches rely on lexicons. But they often fail with nuanced language, while ML methods require extensive labeled data and feature engineering. This limits their generalizability. For example, a review that says “I wanted to love this product but in the end I regretted it” is clearly negative. A human reader would easily glean that. But traditional sentiment analysis methods might misclassify it because of the word “love.”

Language models overcome these challenges. They can understand context, handle subtleties like sarcasm, and generalize across domains. Pretrained on diverse text from sources rich in emotions and sarcasm (comment sections, we’re looking at you), these language models easily capture nuanced sentiment, adapt to new domains, and support multilingual analysis with minimal additional training. All of which make them highly effective for sentiment analysis tasks.

## **Meet prompt(): MotherDuck’s built-in small language model**

In the second half of 2024, [MotherDuck introduced a powerful new prompt() function](https://motherduck.com/blog/sql-llm-prompt-function-gpt-models/). Prompt() lets you use language models directly in your MotherDuck queries.

Here’s a simple example:

```sql
Copy code

SELECT prompt('summarize my text: ' || my_text) as summary FROM my_table;
```

This query summarizes text in a “my\_text” field and inserts it into a “summary” field in the results.

Prompt() leverages OpenAI's [GPT-4o mini](https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/) and [GPT-4o](https://openai.com/index/hello-gpt-4o/) models trained specifically for MotherDuck’s use case and is optimized for cost and performance. It’s well suited for extraction from unstructured fields in your MotherDuck tables.

## **Instructions: How to build a sentiment analysis dashboard with MotherDuck and Fabi.ai**

OK, it’s time to get into our example: Building our sentiment analysis dashboard. It will extract the sentiment from customer product reviews for a fictional company, Superdope, which sells fashion apparel. We’ll use that information to build a product review dashboard that you can [share with your customer success and marketing teams.](https://www.fabi.ai/use-cases/collaboration)

We’ll complete this in a few steps:

1. **Use prompt() in MotherDuck to prepare the data** and extract sentiment from a review text field.
2. Query the review and sentiment data in Fabi.ai and then build and extract the insights.
3. Build a dashboard from your Fabi.ai [Smartbook](https://www.fabi.ai/product/smartbooks) and publish the dashboard.

### Environment requirements

Before we get started, here are the technical requirements you’ll need going into this example:

- **A MotherDuck account with access to prompt() and embedding() functions.** These are part of the Standard plan.
- Some **text data in a CSV file.**
- **A Fabi.ai account for dashboard creation.** You can use the Free Tier of the product for this.
- Basic SQL knowledge.
- Basic Python knowledge.

### **1\. Create our sentiment analysis pipeline**

This example will use synthetic data for our fictional company, which you can download yourself [here](https://docs.google.com/spreadsheets/d/1ivpayqKOzJbSMD3PZz-NirXGGxRJUbypmnRsWswrfFQ/edit?gid=32410012#gid=32410012) if you’d like to follow along exactly. Otherwise, you can simply ask your favorite AI to generate some data for you with the following fields:

- **product\_category:** Categories of products (e.g. shoes, t-shirts, swimwear)
- **review:** A text field containing some review data ranging from positive to negative
- **rating:** A score from 0 to 10

Once you have your data, go ahead and [upload it to your MotherDuck instance](https://motherduck.com/docs/getting-started/e2e-tutorial/#loading-your-dataset).

#### Using prompt() to create derivative fields

Once your data is loaded into your database, **check that it’s there**. Next, we’ll **generate two fields: A** **sentiment** **field,** which will simply be “Positive”, “Neutral” or “Negative”, and **a keywords field,** which contains keywords from the review.

Using prompt():

```sql
Copy code

SELECT
  product_category as category,
  review,
  rating,
  prompt('Classify sentiment as "Positive", "Negative", "Neutral". Just use those simple terms: ' || Review ) as sentiment,
  prompt('Extract keywords from review as a comma separated list: ' || Review ) as keywords
FROM my_db.main.superdope_product_reviews;
```

Your results should have the sentiment in the **sentiment** field. This prompt worked for us, but you may need to tune it a little bit to get the results you want. For example, when I first didn’t specify “Just use those simple terms” it was using “Neutral sentiment” as a category. You may also want to consider some simple evals and errors when building this in production in the event that the AI decides to behave a bit differently.

### **2\. Analyze your data in Fabi.ai**

Now that we have our data loaded in MotherDuck and our query in hand, let’s conduct our analysis in Fabi.ai. We’ll create a table and a pie chart with some filters so your stakeholders can adjust the view on their own.

**Follow these steps:**

**Step 1: Log in to [Fabi.ai](https://app.fabi.ai/) and create your account**

Go to [https://app.fabi.ai/](https://app.fabi.ai/) and log in with your corporate Gmail account.

**Step 2: Connect MotherDuck to Fabi.ai**

When you create your account, the system will prompt you to connect your data source.. Simply follow those steps and enter your [MotherDuck access token](https://docs.fabi.ai/integrations_and_connectors/motherduck). Or, in a blank Smartbook in the [Schema browser, click on the “Add Data Source” option on the left hand side and](https://docs.fabi.ai/getting_started/connect_data_sources) follow those same steps.

**Step 3: Query the data**

In a blank Smartbook, create a new SQL cell and copy/paste the SQL query we wrote above. Run the cell. You should see the results in the output. Note: This data is now cached as a pandas DataFrame. This is important for the following steps.

![motherduck_query.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fmotherduck_query_fad6b5a2e5.png&w=3840&q=75)

**Step 4: Chain a new SQL cell and create filters**

In this step, we’re going to query the DataFrame generated by the SQL cell. Under the first SQL cell, create another new SQL cell and query the DataFrame:

```sql
Copy code

    select * from dataframe1
```

This step may seem redundant, but it helps when creating filters. Since **dataframe1** is now cached, we can create dynamic filters based on the values in the result.

In your second SQL cell, we can adjust the query to add a dynamic variable:

```sql
Copy code

select *
from dataframe1
where sentiment in {{sentiment}}
```

Now let’s create the filter for **sentiment**. Above the second SQL cell, click “Insert a new cell” and create a **Filters & Inputs** of type **Pick List**. Follow the steps using the following parameters:

- **Input Name**: sentiment
- **Options Type:** dynamic
- **Dataframe**: dataframe1
- **Column**: sentiment
- **Allow multiple selections**: True

In our example, we added two filters, but this is what you should now see (below). If you change the filter or rerun the cell, it will pick up the values from the dropdown. You can create [many more types of filters and inputs in Fabi.ai](https://docs.fabi.ai/analysis_and_reporting/filters_and_inputs).

![filtered_dataframe.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ffiltered_dataframe_1e6f6c1cca.png&w=3840&q=75)

**Step 5: Create a pie chart**

Finally, let’s create a pie chart. It will show the distribution of sentiment for the filtered DataFrame.

At the bottom of the Smartbook, insert a new Python cell. Use Plotly to create a pie chart with **dataframe2** (the DataFrame generated by your second SQL cell):

```python
Copy code

import plotly.express as px

sentiment_counts = dataframe2['sentiment'].value_counts()

# Create a dictionary to map sentiments to specific colors
color_map = {'Positive': '#A5D6A7', 'Negative': '#FF8A80', 'Neutral': '#BCAAA4'}
colors = [color_map[sentiment] for sentiment in sentiment_counts.index]

fig = px.pie(values=sentiment_counts.values,
             names=sentiment_counts.index,
             width=800,
             height=450,
             color_discrete_sequence=colors)

fig.update_layout(title='Distribution of Review Sentiments')
fig.show()
```

Run that cell, and there you have it! Your pie chart will dynamically adjust as you change the filters above.

![sentiment_pie_chart.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsentiment_pie_chart_6451fc6d35.png&w=3840&q=75)

_**Pro-tip:** Fabi.ai has an integrated AI assistant that can write both SQL and Python and understands the full context of your Smartbook. Rather than writing the code manually, [you can simply ask the AI](https://www.fabi.ai/blog/fabi-ai-january-product-updates)._

### **3\. Build and publish the report and share with stakeholders**

Congrats, you’ve successfully categorized product review sentiment using MotherDuck! We’ve also built a basic sentiment analysis. Now we need to convert this to a [shareable report](https://www.fabi.ai/use-cases/reporting) for your teammates.

In the top header of the Smartbook, click “Report.” This will take you to the report building staging area. There, you can add, remove, or rearrange elements as you wish. In our case, you can remove the first SQL cell output. It's a duplicate of the second one but without the filter. In the right-hand configuration pane, you can schedule this report to refresh as well.

When you’re ready to publish this, click **Publish** in the right hand panel, which will bring you to the report.

And that’s it! Now you can share this URL with your coworkers. They’ll be able to slice and dice product reviews by sentiment on their own.

![fabi_sentiment_dashboard.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ffabi_sentiment_dashboard_e9e1041412.png&w=3840&q=75)

### **Bonus: Use MotherDuck’s vector embedding for advanced review search**

If you’re building a sentiment analysis report, you may also want to let your users search reviews by content. Keyword and term matching using things like Regex or even fuzzy matching can be quite limiting. Say, for example, you want to search for reviews that mention “great quality.” It would be great if that search could return a review that says “The materials were top notch,” which is clearly a commentary on the quality.

MotherDuck’s [vector embedding](https://motherduck.com/blog/sql-embeddings-for-semantic-meaning-in-text-and-rag/) can offer a quick and easy way to build a clever search engine.

In the same Smartbook we created above, create a new SQL cell and add the following MotherDuck query:

```sql
Copy code

WITH embedded_reviews AS (
  SELECT
    product_category AS category,
    review,
    rating,
    embedding(review) AS review_embedding
  FROM my_db.main.superdope_product_reviews
),
search_query AS (
  SELECT embedding('great quality') AS query_embedding
)
SELECT
  er.category,
  er.review,
  er.rating,
  array_cosine_similarity(er.review_embedding, sq.query_embedding) AS similarity_score
FROM embedded_reviews er, search_query sq
ORDER BY similarity_score DESC
```

The embedding() function will create an embedding for each review. It does this as a new column called **review\_embedding** in the CTE. Then we use cosine similarity to match that embedding with the embedding for the string ‘great quality’.

Now, to create a search function for your users in the dashboard, replace the ‘great quality’ string with a parameter:

```sql
Copy code

WITH embedded_reviews AS (
  SELECT
    product_category AS category,
    review,
    rating,
    embedding(review) AS review_embedding
  FROM my_db.main.superdope_product_reviews
),
search_query AS (
  SELECT embedding('{{search_term}}') AS query_embedding
)
SELECT
  er.category,
  er.review,
  er.rating,
  array_cosine_similarity(er.review_embedding, sq.query_embedding) AS similarity_score
FROM embedded_reviews er, search_query sq
ORDER BY similarity_score DESC
LIMIT 10
```

For this to run, we’ll create a new input above this cell like we did previously for the filter. Select “Insert a new cell” above the SQL cell and select **Text**. Call the input “search\_term” and insert some default value. After creating this input, you can search for any term in it. It will then perform a semantic search on the review field.

![Screenshot 2025-02-10 at 1.47.14 PM.png](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2025_02_10_at_1_47_14_PM_af9cdd1ee8.png&w=3840&q=75)

## **Further learning: Customizing our sentiment analysis**

A few final, quick tips and thoughts to take your analysis to the next level:

- **Prompt tuning**: You may need to play around with the prompt a bit to make sure it’s giving you the results you want reliably. Smaller models are powerful but may need a bit more supervision than larger models. It’s also best to keep the prompt short and precise. As a best practice, consider adding some basic checks and error handling or evals. In our example here, if the AI doesn’t return exactly “Positive”, “Neutral”, or “Negative”, that should be identified and handled gracefully.
- **Advanced visualization**: This tutorial uses a simple bar chart. But, using Plotly and Python, you can customize your Fabi.ai report to your heart’s content. Have some fun exploring creative ways to show off your data!
- **Precomputing vector embedding**: If you know the field you want to perform a semantic search in, consider precomputing the vector embedding directly in MotherDuck to improve performance.
- **DuckDB caching**: Not only does Fabi.ai integrate with MotherDuck, but it also uses DuckDB as part of its caching layer. When we created the second SQL cell, it referenced the DataFrame from the first SQL query output. That data was being stored in DuckDB, which means queries on Python DataFrames have all the benefits of DuckDB.

## **Next steps**

With that, you’re now a sentiment analysis expert! This tutorial explored how to use MotherDuck’s native prompt() function to parse out natural language on the fly and leverage Fabi.ai to build an interactive, shareable report for your customer success and marketing teams. This is a great way to stay on top of reviews and improve your customer experience.

Check out the [full tutorial walkthrough](https://www.youtube.com/watch?v=rGKvdLUxS6c), or [get started with your own data in MotherDuck](https://auth.motherduck.com/login?state=hKFo2SBQU0tMQi1pUVhVTnJYaUNULUN2M2hMc0xlalREQ0p2QaFupWxvZ2luo3RpZNkgcXd3Tjd4SU9WV08wdmpaMW53UkRXYXpkQmd0UzcxNzOjY2lk2SBiemEzS1dRcHhSQUZsVGxSRlhVbzI5QU9nOXhEN3pjcA&client=bza3KWQpxRAFlTlRFXUo29AOg9xD7zcp&protocol=oauth2&scope=openid%20profile%20email&auth_flow=signup&redirect_uri=https://app.motherduck.com&response_type=code&response_mode=query&nonce=ZWdvTENSWW0xOUF1ZjU4cHZKZ3Zxemw2ZDM1Sk8xSV9zYVBvY3oyYXRuWg%3D%3D&code_challenge=2SIt5KtrDuTtutwEGkEOp76WLmSc4ccTAQ4I1-jXgD0&code_challenge_method=S256&auth0Client=eyJuYW1lIjoiYXV0aDAtcmVhY3QiLCJ2ZXJzaW9uIjoiMi4yLjQifQ%3D%3D) today.

### TABLE OF CONTENTS

[What we’ll build: An interactive sentiment analysis dashboard](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/#what-well-build-an-interactive-sentiment-analysis-dashboard)

[What is sentiment analysis, and what makes it challenging?](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/#what-is-sentiment-analysis-and-what-makes-it-challenging)

[Meet prompt(): MotherDuck’s built-in small language model](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/#meet-prompt-motherducks-built-in-small-language-model)

[Instructions: How to build a sentiment analysis dashboard with MotherDuck and Fabi.ai](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/#instructions-how-to-build-a-sentiment-analysis-dashboard-with-motherduck-and-fabiai)

[Further learning: Customizing our sentiment analysis](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/#further-learning-customizing-our-sentiment-analysis)

[Next steps](https://motherduck.com/blog/fabi-ai-llm-prompt-analysis/#next-steps)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Why CSV Files Won’t Die and How DuckDB Conquers Them](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fcsvwontdie_1_9a8f8b85b5.png&w=3840&q=75)](https://motherduck.com/blog/csv-files-persist-duckdb-solution/)

[2025/02/04 - Mehdi Ouazza](https://motherduck.com/blog/csv-files-persist-duckdb-solution/)

### [Why CSV Files Won’t Die and How DuckDB Conquers Them](https://motherduck.com/blog/csv-files-persist-duckdb-solution)

Learn how you can pragmatically use DuckDB to parse any CSVs

[![MotherDuck Now Supports DuckDB 1.2: Faster, Friendlier, Better Performance](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_1_2_ea12029200.png&w=3840&q=75)](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw/)

[2025/02/05 - Sheila Sitaram](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw/)

### [MotherDuck Now Supports DuckDB 1.2: Faster, Friendlier, Better Performance](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw)

DuckDB 1.2 has launched, with improvements in performance, the SQL experience, CSV handling, and scalability - all fully supported in MotherDuck!

[View all](https://motherduck.com/blog/)

Authorization Response