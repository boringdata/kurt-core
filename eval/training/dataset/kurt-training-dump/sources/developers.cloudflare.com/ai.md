---
title: Build AI Applications · Use cases · Cloudflare use cases
url: https://developers.cloudflare.com/use-cases/ai/
hostname: cloudflare.com
description: Build and deploy ambitious AI applications to Cloudflare's global network.
sitename: Cloudflare Docs
date: 2025-08-19
---
# Build AI Applications

Build and deploy ambitious AI applications to Cloudflare's global network.

Diagrams, design patterns, and detailed best practices to help you generate solutions with Cloudflare products.


Ingesting BigQuery Data into Workers AI

You can connect a Cloudflare Worker to get data from Google BigQuery and pass it to Workers AI, to run AI Models, powered by serverless GPUs.


Multi-vendor AI observability and control

By shifting features such as rate limiting, caching, and error handling to the proxy layer, organizations can apply unified configurations across services and inference service providers.


Composable AI architecture

The architecture diagram illustrates how AI applications can be built end-to-end on Cloudflare, or single services can be integrated with external infrastructure and services.


Content-based asset creation

AI systems combine text-generation and text-to-image models to create visual content from text. They generate prompts, moderate content, and produce images for various applications.


Retrieval Augmented Generation (RAG)

RAG combines retrieval with generative models for better text. It uses external knowledge to create factual, relevant responses, improving coherence and accuracy in NLP tasks like chatbots.


Automatic captioning for video uploads

By integrating automatic speech recognition technology into video platforms, content creators, publishers, and distributors can reach a broader audience, including individuals with hearing impairments or those who prefer to consume content in different languages.

-
[Gamertown Customer Support Assistant: ↗](https://github.com/craigsdennis/gamertown-workers-ai-vectorize)A RAG based AI Chat app that uses Vectorize to access video game data for employees of Gamertown. -
[LoRA News Summarizer: ↗](https://github.com/elizabethsiegle/cf-ai-lora-news-summarizer)This application uses Cloudflare Workers AI, Streamlit, and Beautiful Soup to summarize input news article URLs in a variety of tones. -
[shrty.dev: ↗](https://github.com/craigsdennis/shorty-dot-dev)A URL shortener that makes use of KV and Workers Analytics Engine. The admin interface uses Function Calling. Go Shorty! -
[Fanfic Generator: ↗](https://github.com/elizabethsiegle/star-wars-fanfic-generator-streamlit-astra-cf)This application uses Cloudflare Workers AI, Streamlit, and AstraDB to generate personal scifi fanfiction. -
[Homie - Home Automation using Function Calling: ↗](https://github.com/craigsdennis/lightbulb-moment-tool-calling)A home automation tool that uses AI Function calling to change the color of lightbulbs in your home. -
[Hackathon Helper: ↗](https://github.com/craigsdennis/hackathon-helper-workers-ai)A series of starters for Hackathons. Get building quicker! Python, Streamlit, Workers, and Pages starters for all your AI needs! -
[NBA Finals Polling and Predictor: ↗](https://github.com/elizabethsiegle/nbafinals-cloudflare-ai-hono-durable-objects)This stateful polling application uses Cloudflare Workers AI, Cloudflare Pages, Cloudflare Durable Objects, and Hono to keep track of users' votes for different basketball teams and generates personal predictions for the series. -
[Multimodal AI Translator: ↗](https://github.com/elizabethsiegle/cfworkers-ai-translate)This application uses Cloudflare Workers AI to perform multimodal translation of languages via audio and text in the browser. -
[Floor is Llava: ↗](https://github.com/craigsdennis/floor-is-llava-workers-ai)This is an example repo to explore using the AI Vision model Llava hosted on Cloudflare Workers AI. This is a SvelteKit app hosted on Pages. -
[Workers AI Object Detector: ↗](https://github.com/elizabethsiegle/cf-workers-ai-obj-detection-webcam)Detect objects from a webcam in a Cloudflare Worker web app with detr-resnet-50 hosted on Cloudflare using Cloudflare Workers AI. -
[Comically Bad Art Generation: ↗](https://github.com/craigsdennis/comically-bad-art-workers-ai-streamlit)This app uses the wonderful Python UI Framework Streamlit and Cloudflare Workers AI. -
[Whatever-ify: ↗](https://github.com/craigsdennis/whatever-ify-workers-ai)Turn yourself into...whatever. Take a photo, get a description, generate a scene and character, then generate an image based on that calendar. -
[Phoney AI: ↗](https://github.com/craigsdennis/phoney-ai)This application uses Cloudflare Workers AI, Twilio, and AssemblyAI. Your phone is an input and output device. -
[Image Model Streamlit starters: ↗](https://github.com/craigsdennis/image-model-streamlit-workers-ai)Collection of Streamlit applications that are making use of Cloudflare Workers AI. -
[Vanilla JavaScript Chat Application using Cloudflare Workers AI: ↗](https://github.com/craigsdennis/vanilla-chat-workers-ai)A web based chat interface built on Cloudflare Pages that allows for exploring Text Generation models on Cloudflare Workers AI. Design is built using tailwind.

Step-by-step guides to help you build and learn.


Create and secure an AI agent wrapper using AI Gateway and Zero Trust

This tutorial explains how to use Cloudflare AI Gateway and Zero Trust to create a functional and secure website wrapper for an AI agent.


Whisper-large-v3-turbo with Cloudflare Workers AI

Learn how to transcribe large audio files using Workers AI.


Llama 3.2 11B Vision Instruct model on Cloudflare Workers AI

Learn how to use the Llama 3.2 11B Vision Instruct model on Cloudflare Workers AI.


Store and Catalog AI Generated Images with R2 (Part 3)

In the final part of the AI Image Playground series, Kristian teaches how to utilize Cloudflare's R2 object storage.


Build a Retrieval Augmented Generation (RAG) AI

Build your first AI app with Cloudflare AI. This guide uses Workers AI, Vectorize, D1, and Cloudflare Workers.


Using BigQuery with Workers AI

Learn how to ingest data stored outside of Cloudflare as an input to Workers AI models.


Add New AI Models to your Playground (Part 2)

In part 2, Kristian expands upon the existing environment built in part 1, by showing you how to integrate new AI models and introduce new parameters that allow you to customize how images are generated.


Build an AI Image Generator Playground (Part 1)

The new flux models on Workers AI are our most powerful text-to-image AI models yet. Using Workers AI, you can get access to the best models in the industry without having to worry about inference, ops, or deployment.


How to Build an Image Generator using Workers AI

Learn how to build an image generator using Workers AI.


Explore Workers AI Models Using a Jupyter Notebook

This Jupyter notebook explores various models (including Whisper, Distilled BERT, LLaVA, and Meta Llama 3) using Python and the requests library.


Create a fine-tuned OpenAI model with R2

In this tutorial, you will use the OpenAI API and Cloudflare R2 to create a fine-tuned model.


Fine Tune Models With AutoTrain from HuggingFace

Fine-tuning AI models with LoRA adapters on Workers AI allows adding custom training data, like for LLM finetuning.


Explore Code Generation Using DeepSeek Coder Models

Explore how you can use AI models to generate code and work more efficiently.


Choose the Right Text Generation Model

There's a wide range of text generation models available through Workers AI. In an effort to aid you in your journey of finding the right model, this notebook will help you get to know your options in a speed dating type of scenario.


Deploy a Worker that connects to OpenAI via AI Gateway

Learn how to deploy a Worker that makes calls to OpenAI through AI Gateway


OpenAI GPT function calling with JavaScript and Cloudflare Workers

Build a project that leverages OpenAI's function calling feature, available in OpenAI's latest Chat Completions API models.

Explore case studies on [AI companies building on Cloudflare ↗](https://workers.cloudflare.com/built-with/collections/ai-workers/).

Examples ready to copy and paste.

## Was this helpful?

-
**Resources** -
[API](https://developers.cloudflare.com/api/) -
[New to Cloudflare?](https://developers.cloudflare.com/fundamentals/) -
[Directory](https://developers.cloudflare.com/directory/) -
[Sponsorships](https://developers.cloudflare.com/sponsorships/) -
[Open Source](https://github.com/cloudflare)

-
**Support** -
[Help Center](https://support.cloudflare.com/) -
[System Status](https://www.cloudflarestatus.com/) -
[Compliance](https://www.cloudflare.com/trust-hub/compliance-resources/) -
[GDPR](https://www.cloudflare.com/trust-hub/gdpr/)

-
**Company** -
[cloudflare.com](https://www.cloudflare.com/) -
[Our team](https://www.cloudflare.com/people/) -
[Careers](https://www.cloudflare.com/careers/)

- © 2025 Cloudflare, Inc.
-
[Privacy Policy](https://www.cloudflare.com/privacypolicy/) -
[Terms of Use](https://www.cloudflare.com/website-terms/) -
[Report Security Issues](https://www.cloudflare.com/disclosure/) -
[Trademark](https://www.cloudflare.com/trademark/) -