---
title: unstructured-analysis-tensorlake-motherduck
content_type: tutorial
source_url: https://motherduck.com/blog/unstructured-analysis-tensorlake-motherduck
indexed_at: '2025-11-25T19:56:55.292194'
content_hash: 593499625c424057
has_code_examples: true
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Unstructured Document Analysis with Tensorlake and MotherDuck

2025/11/19 - 6 min read

BY

[Diptanu Gon Choudhury](https://motherduck.com/authors/diptanu-gon-choudhury/)

Most business-critical data is trapped in PDFs, including SEC filings, contracts, invoices, and reports that contain valuable data but can't be queried directly with SQL. Until now.

Tensorlake cracks open the wide world of documents, turning verbose text into structured data with 91-98% accuracy. Combined with MotherDuck’s serverless data warehouse, data teams can instantly query complex documents using friendly, familiar SQL. [Tensorlake](https://tensorlake.ai/) is a unified runtime for data-centric agents, workflows, with a best-in-class document ingestion API. Companies like [Sixt](https://www.sixt.com/) and [BindHQ](https://www.bindhq.com/) use Tensorlake to power critical business workflows and agentic applications.

Tensorlake's state-of-the-art document ingestion, combined with MotherDuck's serverless analytics, creates a powerful platform for extracting insights from unstructured data. In a recent benchmark, Tensorlake delivers best-in-class accuracy for document processing, [achieving a 91.7% F1 score](https://docs.tensorlake.ai/document-ingestion/benchmarks) on complex JSON extraction–outperforming Azure, Textract, Gemini, and open-source document AI tools.

![Structured output accuracy score.](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fimage1_1470311d27.png&w=3840&q=75)

## **Tutorial: AI Risk Analysis**

Let’s try a simple example for extracting and querying data from unstructured documents with a very in-vogue topic: AI risk. AI-related risk is fundamentally reshaping global economic outlooks. Specifically, how are publicly traded companies talking about the risks of AI to _their businesses_?

We can start to answer this question by reading SEC filings, but most of the data within is unstructured and inaccessible. Let’s use Tensorlake and MotherDuck to extract, classify, and analyze this data using Python and SQL.

In this tutorial, we'll walk you through a complete workflow: classifying pages in SEC filings that discuss AI risks, extracting structured data, loading it into MotherDuck, and querying trends across companies —all with just a few lines of code.

You can follow along using the [Colab notebook here](https://colab.research.google.com/drive/1CljRj5TCral2LHIuBLJOxy_mMLdbjFi3?usp=sharing), where you’ll find all the code required for this tutorial. You’ll also need a [Tensorlake API key](https://www.google.com/url?q=https%3A%2F%2Ftlake.link%2Fcloud) and a [MotherDuck token](https://motherduck.com/docs/key-tasks/authenticating-and-connecting-to-motherduck/authenticating-to-motherduck/), both of which you can obtain as part of the products’ free plans.

![Query result set.](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fimage2_a271c04e17.png&w=3840&q=75)

### First, source SEC filings for relevant NYSE companies

Before we can analyze AI risks, we need the source documents. We'll start by collecting SEC filings from major NYSE-listed companies. The 10-K (annual) and 10-Q (quarterly) reports describe a company’s financial performance and operations, including key risk factors.

Follow along in the [Colab notebook](https://colab.research.google.com/drive/1CljRj5TCral2LHIuBLJOxy_mMLdbjFi3?usp=sharing) for an example.

### Classify pages where AI risks are mentioned

SEC filings can be hundreds of pages long, but AI risks are typically only discussed in a few specific sections where companies disclose material risks, including emerging concerns around AI. Rather than processing entire documents, we'll use Tensorlake's semantic page classification to find pages mentioning AI-related risks. This saves processing time and tokens, and ensures we're extracting data from the most relevant content.

We'll define a classification schema that looks for risk factor pages, then run it across all our SEC filings to build a map of where AI risks appear in each document.

```py
Copy code

sec_filings = [] # URLs of SEC Filings PDFs

# Create a PageClassConfig object to describe classfication rules
page_classifications = [\
  PageClassConfig(\
    name="risk_factors",\
    description="Pages that contain risk factors related to AI."\
  )\
]

# Call Tensorlake Page Classification API
for file_url in sec_filings:
  parse_id = doc_ai.classify(
    file_url=file_url,
    page_classifications=page_classifications
  )

  result = doc_ai.wait_for_completion(parse_id=parse_id)

  # Save the page numbers where AI risk factors are for each file
  for page_class in result.page_classes:
    if(page_class.page_class == "risk_factors"):
    	document_ai_risk_pages[file_url] = page_class.page_numbers
```

### Extract AI risk factors from each document

With the right pages identified, it's time to extract structured data. We'll define a schema that captures risk category, description, severity, and citation, then let Tensorlake's Document Ingestion API turn risk disclosures into queryable JSON.

```py
Copy code

# Define our data schema
class AIRiskMention(BaseModel):
    """Individual AI-related risk mention"""
    risk_category: str = Field(
        description="Category: Operational, Regulatory, Competitive, Ethical, Security, Liability"
    )
    risk_description: str = Field(description="Description of the AI risk")
    severity_indicator: Optional[str] = Field(None, description="Severity level if mentioned")
    citation: str = Field(description="Page reference")

class AIRiskExtraction(BaseModel):
    """Complete AI risk data from a filing"""
    company_name: str
    ticker: str
    filing_type: str
    filing_date: str
    fiscal_year: str
    fiscal_quarter: Optional[str] = None
    ai_risk_mentioned: bool
    ai_risk_mentions: List[AIRiskMention] = []
    num_ai_risk_mentions: int = 0
    ai_strategy_mentioned: bool = False
    ai_investment_mentioned: bool = False
    ai_competition_mentioned: bool = False
    regulatory_ai_risk: bool = False

doc_ai = DocumentAI()

results = {}

for file_url, page_numbers in document_ai_risk_pages.items():
  print(f"File URL: {file_url}")
  page_number_str_list = ",".join(str(i) for i in page_numbers)
  print(f"Page Numbers: {page_number_str_list}")

  result = doc_ai.parse_and_wait(
      file=file_url,
      page_range=page_number_str_list,
      structured_extraction_options=[\
          StructuredExtractionOptions(\
              schema_name="AIRiskExtraction",\
              json_schema=AIRiskExtraction\
          )\
      ]
  )
  results[file_url] = result

  # Save results to a json file
  filename = os.path.basename(file_url).replace('.pdf', '.json')
  with open(json_filename, 'w') as f:
    json.dump(result.structured_data[0].data, f, indent=2, default=str)
```

### Load structured data into MotherDuck

Now we have structured JSON for each company's AI risks. Let's load this data into MotherDuck's serverless warehouse. Once it's in MotherDuck, we can query across all companies using SQL.

```py
Copy code

# Load into MotherDuck
con = duckdb.connect('md:ai_risk_analytics')

for filename in json_files:
    # Load JSON
    with open(filename, 'r') as f:
        data = json.load(f)

    # Convert ai_risk_mentions to JSON string
    data['ai_risk_mentions'] = json.dumps(data.get('ai_risk_mentions', []))
```

### Analyze with SQL

With our data in MotherDuck, we can run SQL queries to uncover patterns across companies. Which risk categories are most common? How do tech giants describe operational AI risks differently from financial services firms? Let's explore.

For example, you can extract risk category distribution across all companies with a single query:

```py
Copy code

risk_categories = con.execute("""
    WITH parsed_risks AS (
        SELECT
            company_name,
            unnest(CAST(json(ai_risk_mentions) AS JSON[])) as risk_item
        FROM ai_risk_factors.ai_risk_filings
    )
    SELECT
        risk_item->>'risk_category' as risk_category,
        COUNT(*) as total_mentions,
        COUNT(DISTINCT company_name) as companies_mentioning
    FROM parsed_risks
    WHERE risk_item->>'risk_category' IS NOT NULL
    GROUP BY risk_category
    ORDER BY total_mentions DESC
""").fetchdf()

print(risk_categories)
```

With this query, you get output like:

![Query result set.](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fimage4_9bec91c6a0.png&w=3840&q=75)

Or, query operational risks to see how different companies frame execution challenges:

```py
Copy code

# Query: Extract one operational AI risk per company
operational_risks = con.execute("""
    WITH parsed_risks AS (
        SELECT
            company_name,
            ticker,
            unnest(CAST(json(ai_risk_mentions) AS JSON[])) as risk_item
        FROM ai_risk_factors.ai_risk_filings
    ),
    operational_only AS (
        SELECT
            company_name,
            ticker,
            risk_item->>'risk_description' as risk_description,
            risk_item->>'citation' as citation
        FROM parsed_risks
        WHERE risk_item->>'risk_category' = 'Operational'
    )
    SELECT
        company_name,
        ticker,
        risk_description,
        citation
    FROM operational_only
    ORDER BY company_name
""").fetchdf()

print(operational_risks)
```

The query will return output like:

![Query result set.](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fimage2_a271c04e17.png&w=3840&q=75)

## In conclusion

Most of the effort in document analytics is getting the data into a database. Critical business information in financial services, logistics, and other industries still lives inside documents. Once that information is reliably extracted into a structured form, the analytics layer becomes dramatically simpler.

Document extraction, however, requires more than OCR - namely, page classification, layout understanding, and schema-driven structured extraction. Tensorlake’s Document Ingestion API bundles these capabilities into a single API.

Once the data is structured, DuckDB makes analysis effortless. Its query engine allows analytics queries over semi-structured JSON from documents using familiar SQL, and MotherDuck’s serverless architecture scales that to large workloads instantly.

Together, Tensorlake and MotherDuck turn unstructured documents into analytics-ready datasets. Beyond PDFs, Tensorlake also ingests Word, HTML, PowerPoint, and Excel files, unlocking even more enterprise data sources for DuckDB’s ecosystem.

### TABLE OF CONTENTS

[Tutorial: AI Risk Analysis](https://motherduck.com/blog/unstructured-analysis-tensorlake-motherduck/#tutorial-ai-risk-analysis)

[In conclusion](https://motherduck.com/blog/unstructured-analysis-tensorlake-motherduck/#in-conclusion)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![DuckDB Ecosystem: November 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_36d7966f34.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025/)

[2025/11/12 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025/)

### [DuckDB Ecosystem: November 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025)

DuckDB Monthly #35: DuckDB extensions, DuckLake, DataFrame, and more!

[![Small Data SF 2025: the Recap!](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Fsmall_data_sf_2025_f373154984.png&w=3840&q=75)](https://motherduck.com/blog/small-data-sf-recap-2025/)

[2025/11/14 - Garrett O'Brien](https://motherduck.com/blog/small-data-sf-recap-2025/)

### [Small Data SF 2025: the Recap!](https://motherduck.com/blog/small-data-sf-recap-2025)

Dive into a recap of the world's hottest efficiency-themed data conference, Small Data SF!

[View all](https://motherduck.com/blog/)

Authorization Response