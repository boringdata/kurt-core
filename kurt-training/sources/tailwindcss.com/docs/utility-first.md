---
title: Styling with utility classes - Core concepts
url: https://tailwindcss.com/docs/styling-with-utility-classes
hostname: tailwindcss.com
description: Building complex components from a constrained set of primitive utilities.
sitename: Tailwindcss
date: 2025-01-01
---
Core concepts

Building complex components from a constrained set of primitive utilities.

You style things with Tailwind by combining many single-purpose presentational classes *(utility classes)* directly in your markup:

For example, in the UI above we've used:

`flex`

, `shrink-0`

, and `p-6`

) to control the overall layout`max-w-sm`

and `mx-auto`

) to constrain the card width and center it horizontally`bg-white`

, `rounded-xl`

, and `shadow-lg`

) to style the card's appearance`size-12`

) to set the width and height of the logo image`gap-x-4`

) to handle the spacing between the logo and the text`text-xl`

, `text-black`

, `font-medium`

, etc.) to style the card textStyling things this way contradicts a lot of traditional best practices, but once you try it you'll quickly notice some really important benefits:

These benefits make a big difference on small projects, but they are even more valuable for teams working on long-running projects at scale.

A common reaction to this approach is wondering, “isn’t this just inline styles?” and in some ways it is — you’re applying styles directly to elements instead of assigning them a class name and then styling that class.

But using utility classes has many important advantages over inline styles, for example:

This component is fully responsive and includes a button with hover and active styles, and is built entirely with utility classes:

To style an element on states like hover or focus, prefix any utility with the state you want to target, for example `hover:bg-sky-700`

:

Hover over this button to see the background color change

These prefixes are called [variants](https://tailwindcss.com/docs/hover-focus-and-other-states) in Tailwind, and they only apply the styles from a utility class when the condition for that variant matches.

Here's what the generated CSS looks like for the `hover:bg-sky-700`

class:

`.hover\:bg-sky-700 { &:hover { background-color: var(--color-sky-700); }}`


Notice how this class does nothing *unless* the element is hovered? Its *only* job is to provide hover styles — nothing else.

This is different from how you'd write traditional CSS, where a single class would usually provide the styles for many states:

`<button class="btn">Save changes</button><style> .btn { background-color: var(--color-sky-500); &:hover { background-color: var(--color-sky-700); } }</style>`


You can even stack variants in Tailwind to apply a utility when multiple conditions match, like combining `hover:`

and `disabled:`


`<button class="bg-sky-500 disabled:hover:bg-sky-500 ...">Save changes</button>`


Learn more in the documentation styling elements on [hover, focus, and other states](https://tailwindcss.com/docs/hover-focus-and-other-states).

Just like hover and focus states, you can style elements at different breakpoints by prefixing any utility with the breakpoint where you want that style to apply:

Resize this example to see the layout change

In the example above, the `sm:`

prefix makes sure that `grid-cols-3`

only triggers at the `sm`

breakpoint and above, which is 40rem out of the box:

`.sm\:grid-cols-3 { @media (width >= 40rem) { grid-template-columns: repeat(3, minmax(0, 1fr)); }}`


Learn more in the [responsive design](https://tailwindcss.com/docs/responsive-design) documentation.

Styling an element in dark mode is just a matter of adding the `dark:`

prefix to any utility you want to apply when dark mode is active:

Just like with hover states or media queries, the important thing to understand is that a single utility class will never include *both* the light and dark styles — you style things in dark mode by using multiple classes, one for the light mode styles and another for the dark mode styles.

`.dark\:bg-gray-800 { @media (prefers-color-scheme: dark) { background-color: var(--color-gray-800); }}`


Learn more in the [dark mode](https://tailwindcss.com/docs/dark-mode) documentation.

A lot of the time with Tailwind you'll even use multiple classes to build up the value for a single CSS property, for example adding multiple filters to an element:

`<div class="blur-sm grayscale"> <!-- ... --></div>`


Both of these effects rely on the `filter`

property in CSS, so Tailwind uses CSS variables to make it possible to compose these effects together:

`.blur-sm { --tw-blur: blur(var(--blur-sm)); filter: var(--tw-blur,) var(--tw-brightness,) var(--tw-grayscale,);}.grayscale { --tw-grayscale: grayscale(100%); filter: var(--tw-blur,) var(--tw-brightness,) var(--tw-grayscale,);}`


The generated CSS above is slightly simplified, but the trick here is that each utility sets a CSS variable just for the effect it's meant to apply. Then the `filter`

property looks at all of these variables, falling back to nothing if the variable hasn't been set.

Tailwind uses this same approach for [gradients](https://tailwindcss.com/docs/background-image#adding-a-linear-gradient), [shadow colors](https://tailwindcss.com/docs/box-shadow#setting-the-shadow-color), [transforms](https://tailwindcss.com/docs/translate), and more.

Many utilities in Tailwind are driven by [theme variables](https://tailwindcss.com/docs/theme), like `bg-blue-500`

, `text-xl`

, and `shadow-md`

, which map to your underlying color palette, type scale, and shadows.

When you need to use a one-off value outside of your theme, use the special square bracket syntax for specifying arbitrary values:

`<button class="bg-[#316ff6] ..."> Sign in with Facebook</button>`


This can be useful for one-off colors outside of your color palette *(like the Facebook blue above)*, but also when you need a complex custom value like a very specific grid:

`<div class="grid grid-cols-[24rem_2.5rem_minmax(0,1fr)]"> <!-- ... --></div>`


It's also useful when you need to use CSS features like `calc()`

, even if you are using your theme values:

`<div class="max-h-[calc(100dvh-(--spacing(6)))]"> <!-- ... --></div>`


There's even a syntax for generating completely arbitrary CSS including an arbitrary property name, which can be useful for setting CSS variables:

`<div class="[--gutter-width:1rem] lg:[--gutter-width:2rem]"> <!-- ... --></div>`


Learn more in the documentation on [using arbitrary values](https://tailwindcss.com/docs/adding-custom-styles#using-arbitrary-values).

Tailwind CSS isn't one big static stylesheet like you might be used to with other CSS frameworks — it generates the CSS needed based on the classes you're actually using when you compile your CSS.

It does this by scanning all of the files in your project looking for any symbol that looks like it could be a class name:

`export default function Button({ size, children }) { let sizeClasses = { md: "px-4 py-2 rounded-md text-base", lg: "px-5 py-3 rounded-lg text-lg", }[size]; return ( <button type="button" className={`font-bold ${sizeClasses}`}> {children} </button> );}`


After it's found all of the potential classes, Tailwind generates the CSS for each one and compiles it all into one stylesheet of just the styles you actually need.

Since the CSS is generated based on the class name, Tailwind can recognize classes using arbitrary values like `bg-[#316ff6]`

and generate the necessary CSS, even when the value isn't part of your theme.

Learn more about how this works in [detecting classes in source files](https://tailwindcss.com/docs/detecting-classes-in-source-files).

Sometimes you need to style an element under a combination of conditions, for example in dark mode, at a specific breakpoint, when hovered, and when the element has a specific data attribute.

Here's an example of what that looks like with Tailwind:

`<button class="dark:lg:data-current:hover:bg-indigo-600 ..."> <!-- ... --></button>`


`@media (prefers-color-scheme: dark) and (width >= 64rem) { button[data-current]:hover { background-color: var(--color-indigo-600); }}`


Tailwind also supports things like `group-hover`

, which let you style an element when a specific parent is hovered:

`<a href="#" class="group rounded-lg p-8"> <!-- ... --> <span class="group-hover:underline">Read more…</span></a>`


`@media (hover: hover) { a:hover span { text-decoration-line: underline; }}`


This `group-*`

syntax works with other variants too, like `group-focus`

, `group-active`

, and [many more](https://tailwindcss.com/docs/hover-focus-and-other-states#styling-based-on-parent-state).

For really complex scenarios *(especially when styling HTML you don't control)*, Tailwind supports [arbitrary variants](https://tailwindcss.com/docs/adding-custom-styles#arbitrary-variants) which let you write any selector you want, directly in a class name:

`<div class="[&>[data-active]+span]:text-blue-600 ..."> <span data-active><!-- ... --></span> <span>This text will be blue</span></div>`


`div > [data-active] + span { color: var(--color-blue-600);}`


Inline styles are still very useful in Tailwind CSS projects, particularly when a value is coming from a dynamic source like a database or API:

`export function BrandedButton({ buttonColor, textColor, children }) { return ( <button style={{ backgroundColor: buttonColor, color: textColor, }} className="rounded-md px-3 py-1.5 font-medium" > {children} </button> );}`


You might also reach for an inline style for very complicated arbitrary values that are difficult to read when formatted as a class name:

`<div class="grid-[2fr_max(0,var(--gutter-width))_calc(var(--gutter-width)+10px)]"><div style="grid-template-columns: 2fr max(0, var(--gutter-width)) calc(var(--gutter-width) + 10px)"> <!-- ... --></div>`


Another useful pattern is setting CSS variables based on dynamic sources using inline styles, then referencing those variables with utility classes:

`export function BrandedButton({ buttonColor, buttonColorHover, textColor, children }) { return ( <button style={{ "--bg-color": buttonColor, "--bg-color-hover": buttonColorHover, "--text-color": textColor, }} className="bg-(--bg-color) text-(--text-color) hover:bg-(--bg-color-hover) ..." > {children} </button> );}`


When you build entire projects with just utility classes, you'll inevitably find yourself repeating certain patterns to recreate the same design in different places.

For example, here the utility classes for each avatar image are repeated five separate times:

Don't panic! In practice this isn't the problem you might be worried it is, and the strategies for dealing with it are things you already do every day.

A lot of the time a design element that shows up more than once in the rendered page is only actually authored once because the actual markup is rendered in a loop.

For example, the duplicate avatars at the beginning of this guide would almost certainly be rendered in a loop in a real project:

When elements are rendered in a loop like this, the actual class list is only written once so there's no actual duplication problem to solve.

When duplication is localized to a group of elements in a single file, the easiest way to deal with it is to use [multi-cursor editing](https://code.visualstudio.com/docs/editor/codebasics#_multiple-selections-multicursor) to quickly select and edit the class list for each element at once:

You'd be surprised at how often this ends up being the best solution. If you can quickly edit all of the duplicated class lists simultaneously, there's no benefit to introducing any additional abstraction.

If you need to reuse some styles across multiple files, the best strategy is to create a *component* if you're using a front-end framework like React, Svelte, or Vue, or a *template partial* if you're using a templating language like Blade, ERB, Twig, or Nunjucks.

Now you can use this component in as many places as you like, while still having a single source of truth for the styles so they can easily be updated together in one place.

If you're using a templating language like ERB or Twig instead of something like React or Vue, creating a template partial for something as small as a button can feel like overkill compared to a simple CSS class like `btn`

.

While it's highly recommended that you create proper template partials for more complex components, writing some custom CSS is totally fine when a template partial feels heavy-handed.

Here's what a `btn-primary`

class might look like, using [theme variables](https://tailwindcss.com/docs/theme#with-custom-css) to keep the design consistent:

Again though, for anything that's more complicated than just a single HTML element, we highly recommend using template partials so the styles and structure can be encapsulated in one place.

When you add two classes that target the same CSS property, the class that appears later in the stylesheet wins. So in this example, the element will receive `display: grid`

even though `flex`

comes last in the actual `class`

attribute:

`<div class="grid flex"> <!-- ... --></div>`


`.flex { display: flex;}.grid { display: grid;}`


In general, you should just never add two conflicting classes to the same element — only ever add the one you actually want to take effect:

`export function Example({ gridLayout }) { return <div className={gridLayout ? "grid" : "flex"}>{/* ... */}</div>;}`


Using component-based libraries like React or Vue, this often means exposing specific props for styling customizations instead of letting consumers add extra classes from outside of a component, since those styles will often conflict.

When you really need to force a specific utility class to take effect and have no other means of managing the specificity, you can add `!`

to the end of the class name to make all of the declarations `!important`

:

`<div class="bg-teal-500 bg-red-500!"> <!-- ... --></div>`


`.bg-red-500\! { background-color: var(--color-red-500) !important;}.bg-teal-500 { background-color: var(--color-teal-500);}`


If you're adding Tailwind to a project that has existing complex CSS with high specificity rules, you can use the `important`

flag when importing Tailwind to mark *all* utilities as `!important`

:

`@import "tailwindcss" important;`


`@layer utilities { .flex { display: flex !important; } .gap-4 { gap: 1rem !important; } .underline { text-decoration-line: underline !important; }}`


If your project has class names that conflict with Tailwind CSS utilities, you can prefix all Tailwind-generated classes and CSS variables using the `prefix`

option:

`@import "tailwindcss" prefix(tw);`


`@layer theme { :root { --tw-color-red-500: oklch(0.637 0.237 25.331); }}@layer utilities { .tw\:text-red-500 { color: var(--tw-color-red-500); }}`