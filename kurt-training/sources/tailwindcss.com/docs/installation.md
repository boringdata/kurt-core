---
title: Installing with Vite - Installation
url: https://tailwindcss.com/docs/installation/using-vite
hostname: tailwindcss.com
description: Integrate Tailwind CSS with frameworks like Laravel, SvelteKit, React Router, and SolidJS.
sitename: Tailwind CSS
date: 2025-01-01
---
Installation

Tailwind CSS works by scanning all of your HTML files, JavaScript components, and any other templates for class names, generating the corresponding styles and then writing them to a static CSS file.

It's fast, flexible, and reliable — with zero-runtime.

Installing Tailwind CSS as a Vite plugin is the most seamless way to integrate it with frameworks like Laravel, SvelteKit, React Router, Nuxt, and SolidJS.

Start by creating a new Vite project if you don’t have one set up already. The most common approach is to use [Create Vite](https://vite.dev/guide/#scaffolding-your-first-vite-project).

`npm create vite@latest my-projectcd my-project`


Install `tailwindcss`

and `@tailwindcss/vite`

via npm.

`npm install tailwindcss @tailwindcss/vite`


Add the `@tailwindcss/vite`

plugin to your Vite configuration.

`import { defineConfig } from 'vite'import tailwindcss from '@tailwindcss/vite'export default defineConfig({ plugins: [ tailwindcss(), ],})`


Add an `@import`

to your CSS file that imports Tailwind CSS.

`@import "tailwindcss";`


Run your build process with `npm run dev`

or whatever command is configured in your `package.json`

file.

`npm run dev`


Make sure your compiled CSS is included in the `<head>`

*(your framework might handle this for you)*, then start using Tailwind’s utility classes to style your content.

`<!doctype html><html><head> <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0"> <link href="/src/style.css" rel="stylesheet"></head><body> <h1 class="text-3xl font-bold underline"> Hello world! </h1></body></html>`