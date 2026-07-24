---
description: "Clean, modern minimalist styling for AirAssist frontend (CSS Modules only)."
applyTo: "frontend/**"
---

# Frontend Style Guide — Clean Minimalist

Applies to every file under `frontend/`. When creating or editing UI, produce a clean, minimalist aesthetic in the spirit of Linear / Vercel / Stripe docs: generous whitespace, subtle borders, muted neutrals, one accent color, sans-serif system fonts.

## Non-negotiables

- **CSS Modules only.** No Tailwind, no styled-components, no headless UI libs, no `clsx`. Style with `styles.name` from a co-located `.module.css`.
- **Use design tokens** from `frontend/src/styles/tokens.css` (defined below). Never hardcode colors, spacing, radii, or shadows in a component's module. Raw hex values in a `.module.css` file are a bug.
- **No new dependencies** for styling or icons unless the user explicitly asks.
- **Preserve accessibility.** Every interactive element needs a visible `:focus-visible` ring; every input needs a `<label>`; keep color contrast ≥ 4.5:1 for body text.

## Design tokens (source of truth)

The workspace has a token file at [frontend/src/styles/tokens.css](frontend/src/styles/tokens.css) imported once from `main.tsx`. Every module CSS file uses these variables:

```css
/* Reference — do not duplicate in component modules */
:root {
  /* Neutrals — cool gray scale */
  --color-bg:        #fafafa;   /* page background */
  --color-surface:   #ffffff;   /* card/section background */
  --color-border:    #e5e7eb;   /* hairline borders */
  --color-border-strong: #d1d5db;
  --color-text:      #111827;   /* body text */
  --color-text-muted:#6b7280;   /* helper text, labels */
  --color-text-subtle:#9ca3af;  /* placeholder, disabled */

  /* Accent — single blue */
  --color-accent:    #2563eb;
  --color-accent-hover: #1d4ed8;
  --color-accent-soft: #eff6ff;

  /* Semantic */
  --color-danger:    #dc2626;
  --color-danger-soft:#fef2f2;
  --color-success:   #059669;
  --color-success-soft:#ecfdf5;

  /* Spacing scale (4px base) */
  --space-1: 0.25rem; --space-2: 0.5rem;  --space-3: 0.75rem;
  --space-4: 1rem;    --space-5: 1.25rem; --space-6: 1.5rem;
  --space-8: 2rem;    --space-10: 2.5rem; --space-12: 3rem;

  /* Radius */
  --radius-sm: 4px; --radius-md: 6px; --radius-lg: 10px;

  /* Shadows — subtle, single-layer */
  --shadow-sm: 0 1px 2px rgba(17, 24, 39, 0.04);
  --shadow-md: 0 4px 12px rgba(17, 24, 39, 0.06);

  /* Type */
  --font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI",
               Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-size-xs:  0.75rem;   --font-size-sm: 0.875rem;
  --font-size-md:  1rem;      --font-size-lg: 1.125rem;
  --font-size-xl:  1.25rem;   --font-size-2xl: 1.5rem;

  /* Motion */
  --transition-fast: 120ms cubic-bezier(0.16, 1, 0.3, 1);
  --transition-base: 200ms cubic-bezier(0.16, 1, 0.3, 1);
}
```

If `frontend/src/styles/tokens.css` does not exist yet, create it with the exact block above and import it as the **first** import in [frontend/src/main.tsx](frontend/src/main.tsx). Do not put tokens anywhere else.

## Layout & spacing

- Page wrappers: `max-width: 720px` centered with `margin-inline: auto` and `padding-inline: var(--space-6)`.
- Sections/cards: `background: var(--color-surface)`, `border: 1px solid var(--color-border)`, `border-radius: var(--radius-lg)`, `padding: var(--space-6)`, `margin-bottom: var(--space-5)`, `box-shadow: var(--shadow-sm)`. No heavier shadows on flat surfaces.
- Vertical rhythm: pick spacing from the 4-px scale. Never use raw pixel values like `13px` or `1.1rem`.
- Grid layouts: `display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-3) var(--space-5);` for form field pairs; collapse to a single column below 640px via `@media (max-width: 640px)`.

## Typography

- `font-family: var(--font-sans)` on `body`; every heading + text inherits.
- `h1` = `var(--font-size-2xl)`, weight `600`, letter-spacing `-0.01em`.
- `h2` (section headings) = `var(--font-size-lg)`, weight `600`, `margin: 0 0 var(--space-4)`.
- Labels: `var(--font-size-sm)`, weight `500`, `color: var(--color-text-muted)`.
- Body: `var(--font-size-md)`, `line-height: 1.55`.
- Helper/counter text: `var(--font-size-xs)`, `color: var(--color-text-muted)`.

## Form controls

- All `<input>`, `<select>`, `<textarea>` share one base look:
  - `padding: var(--space-2) var(--space-3);`
  - `border: 1px solid var(--color-border-strong);`
  - `border-radius: var(--radius-md);`
  - `background: var(--color-surface);`
  - `font: inherit; color: var(--color-text);`
  - `transition: border-color var(--transition-fast), box-shadow var(--transition-fast);`
  - Focus: `outline: none; border-color: var(--color-accent); box-shadow: 0 0 0 3px var(--color-accent-soft);`
  - Disabled: `background: var(--color-bg); color: var(--color-text-subtle); cursor: not-allowed;`
  - Invalid (`aria-invalid="true"`): `border-color: var(--color-danger); box-shadow: 0 0 0 3px var(--color-danger-soft);`
- Buttons — primary:
  - `background: var(--color-accent); color: #fff; border: none;`
  - `padding: var(--space-3) var(--space-5); border-radius: var(--radius-md);`
  - `font-weight: 500; cursor: pointer;`
  - Hover: `background: var(--color-accent-hover);`
  - Disabled: `opacity: 0.5; cursor: not-allowed;`
- Buttons — secondary/ghost: `background: transparent; color: var(--color-text); border: 1px solid var(--color-border-strong);` with the same padding/radius.
- Error messages (`.error` in `sections.module.css` and friends): `color: var(--color-danger); font-size: var(--font-size-xs); margin-top: var(--space-1);`.

## Banners & inline states

- Info banner: `background: var(--color-accent-soft); color: var(--color-accent-hover); border: 1px solid var(--color-accent);`
- Error banner: `background: var(--color-danger-soft); color: var(--color-danger); border: 1px solid var(--color-danger);`
- Success banner: `background: var(--color-success-soft); color: var(--color-success); border: 1px solid var(--color-success);`
- All banners: `padding: var(--space-3) var(--space-4); border-radius: var(--radius-md); font-size: var(--font-size-sm);`

## Do / Don't

- ✅ Import tokens once in `main.tsx`; consume via `var(--token)` in every module CSS.
- ✅ Use `border` for separation; use `box-shadow: var(--shadow-sm)` sparingly and only on cards.
- ✅ Give every interactive element a `:focus-visible` state using the accent color ring.
- ✅ Use `rem` for spacing/typography; use `px` only for border widths.
- ❌ Do not use gradients, glassmorphism, or blur effects.
- ❌ Do not add multiple accent colors — one blue accent only.
- ❌ Do not add drop shadows heavier than `--shadow-md`.
- ❌ Do not use raw hex codes inside component `.module.css` files. If you need a color that isn't a token, add a token first.
- ❌ Do not add animations longer than `--transition-base` or non-motion-safe transitions.

## When modernizing existing files

If you touch a component whose module CSS still uses raw hex values (e.g. `#0d47a1`, `#fdecea`), migrate those declarations to the equivalent tokens as part of your edit. Don't create parallel styles — replace, don't add.

## When creating a new component

1. Create `ComponentName.module.css` next to `ComponentName.tsx`.
2. Import it as `import styles from "./ComponentName.module.css"`.
3. First lines of the module should only reference tokens — if you can't express the design without a raw value, stop and add a token first.
4. Every state (`hover`, `:focus-visible`, `:disabled`, `[aria-invalid]`, error message) must be covered before the component is considered done.
