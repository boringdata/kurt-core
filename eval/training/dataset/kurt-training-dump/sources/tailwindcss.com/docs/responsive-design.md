---
title: Responsive design - Core concepts
url: https://tailwindcss.com/docs/responsive-design
hostname: tailwindcss.com
description: Using responsive utility variants to build adaptive user interfaces.
sitename: Tailwindcss
date: 2025-01-01
---
Core concepts

Using responsive utility variants to build adaptive user interfaces.

Every utility class in Tailwind can be applied conditionally at different breakpoints, which makes it a piece of cake to build complex responsive interfaces without ever leaving your HTML.

First, make sure you've added the [viewport meta tag](https://developer.mozilla.org/en-US/docs/Web/HTML/Viewport_meta_tag) to the `<head>`

of your document:

`<meta name="viewport" content="width=device-width, initial-scale=1.0" />`


Then to add a utility but only have it take effect at a certain breakpoint, all you need to do is prefix the utility with the breakpoint name, followed by the `:`

character:

`<!-- Width of 16 by default, 32 on medium screens, and 48 on large screens --><img class="w-16 md:w-32 lg:w-48" src="..." />`


There are five breakpoints by default, inspired by common device resolutions:

| Breakpoint prefix | Minimum width | CSS |
|---|---|---|
`sm` | 40rem (640px) | `@media (width >= 40rem) { ... }` |
`md` | 48rem (768px) | `@media (width >= 48rem) { ... }` |
`lg` | 64rem (1024px) | `@media (width >= 64rem) { ... }` |
`xl` | 80rem (1280px) | `@media (width >= 80rem) { ... }` |
`2xl` | 96rem (1536px) | `@media (width >= 96rem) { ... }` |

This works for **every utility class in the framework**, which means you can change literally anything at a given breakpoint — even things like letter spacing or cursor styles.

Here's a simple example of a marketing page component that uses a stacked layout on small screens, and a side-by-side layout on larger screens:

Here's how the example above works:

`div`

is `display: block`

, but by adding the `md:flex`

utility, it becomes `display: flex`

on medium screens and larger.`md:shrink-0`

to prevent shrinking on medium screens and larger. Technically we could have just used `shrink-0`

since it would do nothing on smaller screens, but since it only matters on `md`

screens, it's a good idea to make that clear in the class name.`md:h-full md:w-48`

.We've only used one breakpoint in this example, but you could easily customize this component at other sizes using the `sm`

, `lg`

, `xl`

, or `2xl`

responsive prefixes as well.

Tailwind uses a mobile-first breakpoint system, similar to what you might be used to in other frameworks like Bootstrap.

What this means is that unprefixed utilities (like `uppercase`

) take effect on all screen sizes, while prefixed utilities (like `md:uppercase`

) only take effect at the specified breakpoint *and above*.

Where this approach surprises people most often is that to style something for mobile, you need to use the unprefixed version of a utility, not the `sm:`

prefixed version. Don't think of `sm:`

as meaning "on small screens", think of it as "at the small *breakpoint*".

Don't use `sm:`

to target mobile devices

`<!-- This will only center text on screens 640px and wider, not on small screens --><div class="sm:text-center"></div>`


Use unprefixed utilities to target mobile, and override them at larger breakpoints

`<!-- This will center text on mobile, and left align it on screens 640px and wider --><div class="text-center sm:text-left"></div>`


For this reason, it's often a good idea to implement the mobile layout for a design first, then layer on any changes that make sense for `sm`

screens, followed by `md`

screens, etc.

By default, styles applied by rules like `md:flex`

will apply at that breakpoint and stay applied at larger breakpoints.

If you'd like to apply a utility *only* when a specific breakpoint range is active, stack a responsive variant like `md`

with a `max-*`

variant to limit that style to a specific range:

`<div class="md:max-xl:flex"> <!-- ... --></div>`


Tailwind generates a corresponding `max-*`

variant for each breakpoint, so out of the box the following variants are available:

| Variant | Media query |
|---|---|
`max-sm` | `@media (width < 40rem) { ... }` |
`max-md` | `@media (width < 48rem) { ... }` |
`max-lg` | `@media (width < 64rem) { ... }` |
`max-xl` | `@media (width < 80rem) { ... }` |
`max-2xl` | `@media (width < 96rem) { ... }` |

To target a single breakpoint, target the range for that breakpoint by stacking a responsive variant like `md`

with the `max-*`

variant for the next breakpoint:

`<div class="md:max-lg:flex"> <!-- ... --></div>`


Read about [targeting breakpoint ranges](https://tailwindcss.com#targeting-a-breakpoint-range) to learn more.

Use the `--breakpoint-*`

theme variables to customize your breakpoints:

`@import "tailwindcss";@theme { --breakpoint-xs: 30rem; --breakpoint-2xl: 100rem; --breakpoint-3xl: 120rem;}`


This updates the `2xl`

breakpoint to use `100rem`

instead of the default `96rem`

, and creates new `xs`

and `3xl`

breakpoints that can be used in your markup:

`<div class="grid xs:grid-cols-2 3xl:grid-cols-6"> <!-- ... --></div>`


Note that it's important to always use the same unit for defining your breakpoints or the generated utilities may be sorted in an unexpected order, causing breakpoint classes to override each other in unexpected ways.

Tailwind uses `rem`

for the default breakpoints, so if you are adding additional breakpoints to the defaults, make sure you use `rem`

as well.

Learn more about customizing your theme in the [theme documentation](https://tailwindcss.com/docs/theme).

To remove a default breakpoint, reset its value to the `initial`

keyword:

`@import "tailwindcss";@theme { --breakpoint-2xl: initial;}`


You can also reset all of the default breakpoints using `--breakpoint-*: initial`

, then define all of your breakpoints from scratch:

`@import "tailwindcss";@theme { --breakpoint-*: initial; --breakpoint-tablet: 40rem; --breakpoint-laptop: 64rem; --breakpoint-desktop: 80rem;}`


Learn more removing default theme values in the [theme documentation](https://tailwindcss.com/docs/theme).

If you need to use a one-off breakpoint that doesn’t make sense to include in your theme, use the `min`

or `max`

variants to generate a custom breakpoint on the fly using any arbitrary value.

`<div class="max-[600px]:bg-sky-300 min-[320px]:text-center"> <!-- ... --></div>`


Learn more about arbitrary value support in the [arbitrary values](https://tailwindcss.com/docs/adding-custom-styles#using-arbitrary-values) documentation.

[Container queries](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_queries) are a modern CSS feature that let you style something based on the size of a parent element instead of the size of the entire viewport. They let you build components that are a lot more portable and reusable because they can change based on the actual space available for that component.

Use the `@container`

class to mark an element as a container, then use variants like `@sm`

and `@md`

to style child elements based on the size of the container:

`<div class="@container"> <div class="flex flex-col @md:flex-row"> <!-- ... --> </div></div>`


Just like breakpoint variants, container queries are mobile-first in Tailwind CSS and apply at the target container size and up.

Use variants like `@max-sm`

and `@max-md`

to apply a style below a specific container size:

`<div class="@container"> <div class="flex flex-row @max-md:flex-col"> <!-- ... --> </div></div>`


Stack a regular container query variant with a max-width container query variant to target a specific range:

`<div class="@container"> <div class="flex flex-row @sm:@max-md:flex-col"> <!-- ... --> </div></div>`


For complex designs that use multiple nested containers, you can name containers using `@container/{name}`

and target specific containers with variants like `@sm/{name}`

and `@md/{name}`

:

`<div class="@container/main"> <!-- ... --> <div class="flex flex-row @sm/main:flex-col"> <!-- ... --> </div></div>`


This makes it possible to style something based on the size of a distant container, rather than just the nearest container.

Use the `--container-*`

theme variables to customize your container sizes:

`@import "tailwindcss";@theme { --container-8xl: 96rem;}`


This adds a new `8xl`

container query variant that can be used in your markup:

`<div class="@container"> <div class="flex flex-col @8xl:flex-row"> <!-- ... --> </div></div>`


Learn more about customizing your theme in the [theme documentation](https://tailwindcss.com/docs/theme).

Use variants like `@min-[475px]`

and `@max-[960px]`

for one-off container query sizes you don't want to add to your theme:

`<div class="@container"> <div class="flex flex-col @min-[475px]:flex-row"> <!-- ... --> </div></div>`


Use [container query length units](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_queries#container_query_length_units) like `cqw`

as arbitrary values in other utility classes to reference the container size:

`<div class="@container"> <div class="w-[50cqw]"> <!-- ... --> </div></div>`


By default, Tailwind includes container sizes ranging from 16rem *(256px)* to 80rem *(1280px)*:

| Variant | Minimum width | CSS |
|---|---|---|
`@3xs` | 16rem (256px) | `@container (width >= 16rem) { … }` |
`@2xs` | 18rem (288px) | `@container (width >= 18rem) { … }` |
`@xs` | 20rem (320px) | `@container (width >= 20rem) { … }` |
`@sm` | 24rem (384px) | `@container (width >= 24rem) { … }` |
`@md` | 28rem (448px) | `@container (width >= 28rem) { … }` |
`@lg` | 32rem (512px) | `@container (width >= 32rem) { … }` |
`@xl` | 36rem (576px) | `@container (width >= 36rem) { … }` |
`@2xl` | 42rem (672px) | `@container (width >= 42rem) { … }` |
`@3xl` | 48rem (768px) | `@container (width >= 48rem) { … }` |
`@4xl` | 56rem (896px) | `@container (width >= 56rem) { … }` |
`@5xl` | 64rem (1024px) | `@container (width >= 64rem) { … }` |
`@6xl` | 72rem (1152px) | `@container (width >= 72rem) { … }` |
`@7xl` | 80rem (1280px) | `@container (width >= 80rem) { … }` |