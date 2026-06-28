# UI Tokens

Design tokens for SEO Autopilot frontend. All colors, typography, spacing, and component values extracted from the delivered design. Use these exact values throughout the frontend codebase — never hardcode colors or use non-standard values in components.

---

## How to Use

The frontend uses vanilla CSS with custom properties defined in `css/style.css`. All design tokens are declared as CSS custom properties on `:root`. Use `var(--token-name)` to reference them throughout the application.

```css
/* Correct — uses CSS variables */
background: var(--color-surface);
color: var(--color-text-primary);
border: 1px solid var(--color-border);

/* Never — hardcoded hex values in component files */
background: #F6F7FB;
color: #0F2747;
```

---

## CSS Custom Properties — Complete Definition

```css
:root {
  /* ── Page and surface backgrounds ── */
  --color-background: #f4f6f9;
  --color-surface: #ffffff;
  --color-surface-secondary: #f8fafc;
  --color-surface-muted: #f1f5f9;

  /* ── Brand — Navy + Blue ── */
  --color-brand-navy: #0f2747;
  --color-brand-navy-light: #1a3a5c;
  --color-brand-blue: #2563eb;
  --color-brand-blue-light: #dbeafe;
  --color-brand-blue-muted: #eff6ff;

  /* ── Borders ── */
  --color-border: #e2e8f0;
  --color-border-light: #f1f5f9;

  /* ── Text ── */
  --color-text-primary: #0f172a;
  --color-text-secondary: #475569;
  --color-text-muted: #94a3b8;
  --color-text-inverse: #ffffff;

  /* ── Semantic ── */
  --color-success: #16a34a;
  --color-success-light: #dcfce7;
  --color-success-muted: #f0fdf4;
  --color-warning: #f59e0b;
  --color-warning-light: #fef3c7;
  --color-warning-muted: #fffbeb;
  --color-error: #dc2626;
  --color-error-light: #fee2e2;
  --color-error-muted: #fef2f2;
  --color-info: #2563eb;
  --color-info-light: #dbeafe;
  --color-info-muted: #eff6ff;

  /* ── Shadows ── */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);

  /* ── Border radius ── */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* ── Typography ── */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* ── Spacing ── */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
  --space-16: 64px;
}
```

---

## Color Usage Guide

### Page Layout

| Element           | Token                        |
| ----------------- | ---------------------------- |
| Page background   | `var(--color-background)`    |
| Card / surface    | `var(--color-surface)`       |
| Secondary surface | `var(--color-surface-secondary)` |
| Muted surface     | `var(--color-surface-muted)` |
| Default border    | `var(--color-border)`        |

### Brand Colors

| Element                | Token                         |
| ---------------------- | ----------------------------- |
| Primary button         | `var(--color-brand-navy)`     |
| Primary button hover   | `var(--color-brand-navy-light)` |
| Accent links, highlights | `var(--color-brand-blue)`    |
| Light badge background | `var(--color-brand-blue-light)` |
| Subtle background      | `var(--color-brand-blue-muted)` |

### Typography

| Element                | Token                          |
| ---------------------- | ------------------------------ |
| Headings, body text    | `var(--color-text-primary)`    |
| Secondary text, labels | `var(--color-text-secondary)`  |
| Placeholder, muted     | `var(--color-text-muted)`      |
| Text on dark           | `var(--color-text-inverse)`    |

### Semantic Colors

| Context   | Background Token                   | Text Token                   |
| --------- | ---------------------------------- | ---------------------------- |
| Success   | `var(--color-success-light)`       | `var(--color-success)`       |
| Warning   | `var(--color-warning-light)`       | `var(--color-warning)`       |
| Error     | `var(--color-error-light)`         | `var(--color-error)`         |
| Info      | `var(--color-info-light)`          | `var(--color-info)`          |

---

## Typography

| Element              | Size    | Weight | Line height | Color token                 |
| -------------------- | ------- | ------ | ----------- | --------------------------- |
| Hero title           | 36px    | 700    | 44px        | `var(--color-text-primary)` |
| Section heading      | 24px    | 600    | 32px        | `var(--color-text-primary)` |
| Card title           | 18px    | 600    | 24px        | `var(--color-text-primary)` |
| Body text            | 15px    | 400    | 24px        | `var(--color-text-primary)` |
| Body small           | 14px    | 400    | 20px        | `var(--color-text-secondary)` |
| Label / tag text     | 13px    | 500    | 18px        | `var(--color-text-secondary)` |
| Muted / timestamp    | 12px    | 400    | 16px        | `var(--color-text-muted)`   |
| Code                 | 14px    | 400    | 20px        | monospace family            |

Font family: **Inter** (body), **JetBrains Mono** (code).

---

## Component Tokens

### Cards

```
background: var(--color-surface)
border: 1px solid var(--color-border)
border-radius: var(--radius-xl) (16px)
padding: var(--space-6) (24px)
box-shadow: var(--shadow-sm)
```

### Buttons — Primary

```
background: var(--color-brand-navy)
color: var(--color-text-inverse)
border-radius: var(--radius-md) (8px)
padding: 10px 20px
font-size: 14px
font-weight: 500
hover: background var(--color-brand-navy-light)
```

### Buttons — Secondary

```
background: var(--color-surface)
border: 1px solid var(--color-border)
color: var(--color-text-primary)
border-radius: var(--radius-md) (8px)
padding: 10px 20px
```

### Input Fields

```
background: var(--color-surface)
border: 1px solid var(--color-border)
border-radius: var(--radius-md) (8px)
padding: 10px 14px
font-size: 14px
color: var(--color-text-primary)
placeholder: var(--color-text-muted)
focus: border-color var(--color-brand-blue), ring
```

### Badges / Tags

```
border-radius: var(--radius-full)
padding: 2px 10px
font-size: 12px
font-weight: 500
```

### Code Blocks

```
background: var(--color-surface-muted)
border: 1px solid var(--color-border)
border-radius: var(--radius-md)
padding: var(--space-4)
font-family: var(--font-mono)
font-size: 14px
```

---

## DOCX Tokens (Python — Not CSS)

These tokens apply to `python-docx` output only. They are defined as constants in the DOCX builder files.

| Token  | Hex         | Usage                            |
| ------ | ----------- | --------------------------------- |
| NAVY   | `#0F2747`   | Cover background, section headers |
| ACCENT | `#2563EB`   | Sub-headings, emphasis            |
| DARK   | `#1E293B`   | Body text                         |
| BODY   | `#334155`   | Secondary text                    |
| WHITE  | `#FFFFFF`   | Text on dark backgrounds          |
| GREEN  | `#16A34A`   | Positive metrics, gains           |
| AMBER  | `#F59E0B`   | Warnings, attention needed        |
| RED    | `#DC2626`   | Critical issues, losses           |
| TEAL   | `#14B8A6`   | Accent highlights                 |
| GRAY   | `#94A3B8`   | Muted text, secondary labels      |

Font: Calibri, 10pt body.

---

## Invariants

- Never use hex values directly in CSS — always use `var(--token-name)`
- Font is Inter for body, loaded via Google Fonts CDN
- Never use raw Tailwind-like utility classes — this is vanilla CSS
- `--color-brand-navy` (#0F2747) is the only navy — never deviate
- `--color-brand-blue` (#2563EB) is the only accent blue — never generic blue
- All borders default to `--color-border` (#E2E8F0)
- DOCX and CSS tokens are separate — never mix python-docx RGBColor values with CSS custom properties
