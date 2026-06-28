# UI Rules

Concise rules for building the SEO Autopilot frontend. Design is vanilla HTML/CSS/JS — no framework. These rules cover the most important patterns and constraints to keep the UI consistent.

---

## Font

Import Inter via Google Fonts CDN in the `<head>` of `index.html`.

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
```

Never use a system font as the primary font. Inter is the only body font.

---

## Layout

- Page max-width: 1200px, centered with `margin: 0 auto`
- Main content padding: 32px on all sides on desktop, 16px on mobile
- Gap between page sections: 32px
- Header height: 64px, full width, white background, box-shadow
- All pages use top navbar only — no sidebar, no drawer

---

## Navbar

Three nav items: Home, Generate, API Docs.

- Active item: `color: #0F2747`, font-weight 600
- Inactive item: `color: #475569`, font-weight 500
- Active state indicated by underline or color change — not both
- Navbar always white background, full viewport width, `box-shadow: var(--shadow-sm)`

---

## Cards

Every content section lives in a card.

```
background: #FFFFFF
border: 1px solid #E2E8F0
border-radius: 16px
padding: 24px
box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05)
```

Never use colored card backgrounds — always white. Color goes inside cards via badges, bars, and text, never on the card surface itself.

---

## Typography Hierarchy

Three levels used consistently throughout:

**Section headings** — card titles, page section titles

```
font-size: 24px
font-weight: 600
color: #0F172A
line-height: 32px
```

**Body / primary content text**

```
font-size: 15px
font-weight: 400
color: #0F172A
line-height: 24px
```

**Secondary / muted text** — labels, timestamps, subtitles

```
font-size: 14px
font-weight: 400
color: #475569
line-height: 20px
```

Hero title on landing page uses 36px / weight 700 / color #0F172A.

---

## Badges / Tags

All badges use `border-radius: 9999px` (pill shape).

```
padding: 2px 10px
font-size: 12px
font-weight: 500
```

Colour by context:

| Context         | Background               | Text              |
| --------------- | ------------------------ | ----------------- |
| Success / Gain  | `var(--color-success-light)` | `var(--color-success)` |
| Warning / Loss  | `var(--color-warning-light)` | `var(--color-warning)` |
| Error / Issue   | `var(--color-error-light)`   | `var(--color-error)` |
| Info / Neutral  | `var(--color-info-light)`    | `var(--color-info)` |

---

## Buttons

**Primary button:**

```
background: #0F2747
color: #FFFFFF
border-radius: 8px
padding: 10px 20px
font-size: 14px
font-weight: 500
hover: background #1A3A5C
```

**Secondary button:**

```
background: #FFFFFF
border: 1px solid #E2E8F0
color: #0F172A
border-radius: 8px
padding: 10px 20px
hover: background #F8FAFC
```

---

## Form Inputs

```
background: #FFFFFF
border: 1px solid #E2E8F0
border-radius: 8px
padding: 10px 14px
font-size: 14px
color: #0F172A
placeholder color: #94A3B8
focus: border-color #2563EB, ring
```

---

## Report Preview (Frontend)

The mock report preview uses an accordion-style layout, not a paginated view.

- Each section is a collapsible card with a heading and toggle arrow
- Tables inside preview have full width, striped rows on hover
- Charts are rendered as mock SVG placeholders (not real matplotlib images)
- Action plan preview mirrors the same accordion pattern

---

## Code Blocks

API documentation code examples use:

```
background: #F1F5F9
border: 1px solid #E2E8F0
border-radius: 8px
padding: 16px
font-family: 'JetBrains Mono', 'Fira Code', monospace
font-size: 14px
```

Copy button appears on hover at top-right of code block.

---

## Empty States

Every section that can be empty must have an empty state. Keep it minimal:

- Short descriptive text in `color: #94A3B8`
- Optional icon above text
- CTA button if there's a logical next action

---

## Mobile Breakpoint

At `max-width: 768px`:

- Padding reduces to 16px
- Cards stack vertically (no multi-column layouts)
- Buttons become full width
- Navbar items condense to hamburger menu (if needed)
- Font sizes remain the same — no mobile-specific size reduction

---

## Do Nots

- Never use hex values directly in component files — use CSS variables only
- Never add gradients to card backgrounds
- Never use more than one font weight in a single UI element
- Never show raw error messages to users — always show human readable text
- Never use `position: fixed` for UI elements — use normal flow layout
- Never use `!important` in CSS — specificity should be sufficient
- Never import external CSS frameworks (Tailwind, Bootstrap, etc.) — vanilla CSS only
