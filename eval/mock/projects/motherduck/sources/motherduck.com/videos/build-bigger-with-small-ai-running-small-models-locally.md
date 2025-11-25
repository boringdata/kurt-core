---
title: build-bigger-with-small-ai-running-small-models-locally
content_type: tutorial
source_url: https://motherduck.com/videos/build-bigger-with-small-ai-running-small-models-locally
indexed_at: '2025-11-25T20:44:51.068401'
content_hash: c9266e506d33a8bd
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

Build Bigger With Small Ai: Running Small Models Locally - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Build Bigger With Small Ai: Running Small Models Locally](https://www.youtube.com/watch?v=P-55pV6ss3k)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Why am I seeing this?](https://support.google.com/youtube/answer/9004474?hl=en)

[Watch on](https://www.youtube.com/watch?v=P-55pV6ss3k&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 21:56

•Live

•

YouTube

# Build Bigger With Small Ai: Running Small Models Locally

2024/09/24

## What Are Small AI Models?

Small AI models are compact versions of large language models that can run on ordinary hardware like laptops or even phones. While cloud-based models from providers like OpenAI or Anthropic typically have hundreds of billions or even trillions of parameters, small models range from 0.5 to 70 billion parameters and are only a few gigabytes in size.

These models share the same underlying architecture and research foundations as their larger counterparts - they're based on the transformer architecture that powers most modern AI systems. The key difference is their size, which makes them practical for local deployment without expensive GPU clusters.

## Why Small Models Matter for Local Development

### Faster Performance Through Local Execution

Running models locally provides surprising speed advantages. Small models execute faster due to their reduced parameter count - since transformer compute time scales quadratically with parameters, a model with 1 billion parameters runs dramatically faster than one with hundreds of billions. Additionally, eliminating network round trips means zero latency for API calls, making the entire inference process remarkably quick.

### Data Privacy and Freedom to Experiment

Local models keep data on your machine, eliminating concerns about sharing sensitive information with cloud providers. This isn't just about privacy paranoia - it liberates developers to experiment freely without worrying about security controls, approval processes, or compliance requirements. Teams can prototype and test ideas without the friction of corporate security reviews.

### Cost Structure Benefits

While local models aren't free (you still need hardware), they avoid the per-token pricing of cloud APIs. Modern hardware is increasingly optimized for AI workloads - Intel claims 100 million AI-capable computers will ship within a year, and Apple Silicon dedicates roughly a third of its chip area to neural processing. This hardware investment pays dividends across all your AI experiments without ongoing API costs.

## Getting Started with Ollama

Ollama provides an easy way to run these models locally. Here's a simple example using Python:

```python
Copy code

import ollama

# Chat with a model
response = ollama.chat(model='llama3.1', messages=[\
    {'role': 'user', 'content': 'What is DuckDB? Keep it to two sentences.'}\
])
```

The models run entirely on your local machine, providing responses as fast or faster than cloud providers. Popular models include:

- Llama 3.1 from Meta
- Gemma from Google
- Phi from Microsoft Research
- Qwen 2.5 from Alibaba

## Combining Small Models with Local Data

### Retrieval Augmented Generation (RAG)

Small models excel when combined with existing factual data through a technique called Retrieval Augmented Generation. Since smaller models may hallucinate when asked about specific facts, RAG compensates by providing relevant data snippets at runtime.

The process involves:

1. Pre-processing your data into a vector store
2. When queried, retrieving relevant data snippets
3. Augmenting the model's prompt with this factual information
4. Getting accurate responses grounded in your actual data

Tools like LlamaIndex and LangChain simplify implementing RAG patterns, allowing models to answer questions about your specific datasets accurately.

### Tool Calling and Small Agents

A newer capability enables models to decide when and how to fetch data themselves through "tool calling." Instead of pre-building all the plumbing to connect data sources, the model can:

- Analyze what information it needs
- Write and execute database queries
- Interpret results in context
- Provide natural language responses

For example, newer models like Qwen 2.5 Coder can write SQL queries against DuckDB databases, execute them, and interpret the results - all based on natural language prompts.

## Practical Use Cases

### Internal Tooling and Back Office Applications

The most successful deployments start with internal tools rather than customer-facing applications:

- IT help desk automation
- Security questionnaire processing
- Data engineering and reporting tasks
- Engineering productivity tools for issue management and code review

### Combining Small and Large Models

Small models don't replace cloud-scale models entirely. Like hot and cold data storage, you can use small models for most queries and escalate to larger models when needed. Apple and Microsoft already use this hybrid approach in their AI products.

## The Future is Small and Local

Open source models are rapidly improving, with performance gaps between small and large models shrinking. New models emerge weekly with better capabilities, specialized functions, and permissive licenses. Combined with hardware improvements specifically targeting AI workloads, local model deployment is becoming increasingly practical for production use cases.

The ecosystem around small models continues to expand, with thousands of fine-tuned variants available for specific tasks. As these models improve and hardware accelerates, the ability to run powerful AI locally transforms from a nice-to-have into a competitive advantage for development teams.

...SHOW MORE

## Related Videos

[!["Data-based: Going Beyond the Dataframe" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FData_based_f32745b461.png&w=3840&q=75)](https://motherduck.com/videos/going-beyond-the-dataframe/)

[2025-11-20](https://motherduck.com/videos/going-beyond-the-dataframe/)

### [Data-based: Going Beyond the Dataframe](https://motherduck.com/videos/going-beyond-the-dataframe)

Learn how to turbocharge your Python data work using DuckDB and MotherDuck with Pandas. We walk through performance comparisons, exploratory data analysis on bigger datasets, and an end-to-end ML feature engineering pipeline.

Webinar

Python

AI, ML and LLMs

[!["Empowering Data Teams: Smarter AI Workflows with Hex & MotherDuck" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FHex_Webinar_778e3959e4.png&w=3840&q=75)](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck/)

[2025-11-14](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck/)

### [Empowering Data Teams: Smarter AI Workflows with Hex & MotherDuck](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck)

AI isn't here to replace data work, it's here to make it better. Watch this webinar to see how Hex and MotherDuck build AI workflows that prioritize context, iteration, and real-world impact.

Webinar

AI, ML and LLMs

[!["Lies, Damn Lies, and Benchmarks" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FLies_Damn_Lies_and_Benchmarks_Thumbnail_404db1bf46.png&w=3840&q=75)](https://motherduck.com/videos/lies-damn-lies-and-benchmarks/)

[2025-10-31](https://motherduck.com/videos/lies-damn-lies-and-benchmarks/)

### [Lies, Damn Lies, and Benchmarks](https://motherduck.com/videos/lies-damn-lies-and-benchmarks)

Why do database benchmarks so often mislead? MotherDuck CEO Jordan Tigani discusses the pitfalls of performance benchmarking, lessons from BigQuery, and why your own workload is the only benchmark that truly matters.

Stream

Interview

[View all](https://motherduck.com/videos/)

Authorization Response