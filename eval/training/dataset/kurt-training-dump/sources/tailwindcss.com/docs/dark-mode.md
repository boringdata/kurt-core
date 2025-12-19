---
title: Dark mode - Core concepts
url: https://tailwindcss.com/docs/dark-mode
hostname: tailwindcss.com
description: Using variants to style your site in dark mode.
sitename: Tailwindcss
date: 2025-01-01
---
Core concepts

Using variants to style your site in dark mode.

Now that dark mode is a first-class feature of many operating systems, it's becoming more and more common to design a dark version of your website to go along with the default design.

To make this as easy as possible, Tailwind includes a `dark`

variant that lets you style your site differently when dark mode is enabled:

By default this uses the `prefers-color-scheme`

CSS media feature, but you can also build sites that support [toggling dark mode manually](https://tailwindcss.com#toggling-dark-mode-manually) by overriding the dark variant.

If you want your dark theme to be driven by a CSS selector instead of the `prefers-color-scheme`

media query, override the `dark`

variant to use your custom selector:

`@import "tailwindcss";@custom-variant dark (&:where(.dark, .dark *));`


Now instead of `dark:*`

utilities being applied based on `prefers-color-scheme`

, they will be applied whenever the `dark`

class is present earlier in the HTML tree:

`<html class="dark"> <body> <div class="bg-white dark:bg-black"> <!-- ... --> </div> </body></html>`


How you add the `dark`

class to the `html`

element is up to you, but a common approach is to use a bit of JavaScript that updates the `class`

attribute and syncs that preference to somewhere like `localStorage`

.

To use a data attribute instead of a class to activate dark mode, just override the `dark`

variant with an attribute selector instead:

`@import "tailwindcss";@custom-variant dark (&:where([data-theme=dark], [data-theme=dark] *));`


Now dark mode utilities will be applied whenever the `data-theme`

attribute is set to `dark`

somewhere up the tree:

`<html data-theme="dark"> <body> <div class="bg-white dark:bg-black"> <!-- ... --> </div> </body></html>`


To build three-way theme toggles that support light mode, dark mode, and your system theme, use a custom dark mode selector and the [ window.matchMedia() API](https://developer.mozilla.org/en-US/docs/Web/API/Window/matchMedia) to detect the system theme and update the

`html`

element when needed.Here's a simple example of how you can support light mode, dark mode, as well as respecting the operating system preference:

`// On page load or when changing themes, best to add inline in `head` to avoid FOUCdocument.documentElement.classList.toggle( "dark", localStorage.theme === "dark" || (!("theme" in localStorage) && window.matchMedia("(prefers-color-scheme: dark)").matches),);// Whenever the user explicitly chooses light modelocalStorage.theme = "light";// Whenever the user explicitly chooses dark modelocalStorage.theme = "dark";// Whenever the user explicitly chooses to respect the OS preferencelocalStorage.removeItem("theme");`


Again you can manage this however you like, even storing the preference server-side in a database and rendering the class on the server — it's totally up to you.