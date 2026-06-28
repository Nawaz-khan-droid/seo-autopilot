# SEO Action Planner — Knowledge Framework

Reference taxonomy and decision heuristics for generating client-specific
SEO action plans. This is a body of knowledge — not a set of instructions
on how to output. Use these guidelines to reason about what actions are
appropriate given the client's data.

---

## Priority Levels

| Level | Meaning | Cadence |
|-------|---------|---------|
| P0 | Fire — blocking, critical issue | This week |
| P1 | High — significant impact | Next sprint |
| P2 | Medium — valuable but not urgent | This sprint |
| P3 | Low — nice to have, backlog | Backlog |

---

## Team Assignments

| Team | Scope |
|------|-------|
| Dev | Technical SEO, Core Web Vitals, site performance, schema, sitemap/robots |
| Content | On-page copy, meta descriptions, thin content, blog posts, keyword content gaps |
| SEO | Rankings, internal linking, keyword strategy, SERP features, cannibalisation |
| Local | Google Business Profile, reviews, NAP consistency, local citations |
| Off-Page | Backlinks, digital PR, guest posting, DA/authority building |

---

## Technical SEO Heuristics (Dev team)

| Signal | Threshold | Priority |
|--------|-----------|----------|
| LCP | > 4.0s | P0 |
| LCP | 2.5 — 4.0s | P1 |
| INP | > 350ms | P1 |
| INP | 200 — 350ms | P2 |
| CLS | > 0.25 | P1 |
| CLS | 0.1 — 0.25 | P2 |
| Render-blocking resources | > 1000ms | P1 |
| Render-blocking resources | 500 — 1000ms | P2 |
| Mobile PSI score | < 50 | P0 |
| Mobile PSI score | 50 — 80 | P1 |
| Missing H1 tags | > 0 pages | P1 |
| Missing meta descriptions | > 0 pages | P1 |
| Missing alt text | > 0 images | P2 |
| Broken links (4xx/5xx) | Any | P1 |
| Broken links (many) | 5+ | P0 |
| No schema detected | — | P2 |
| No sitemap.xml | — | P1 |
| No robots.txt | — | P1 |
| No HTTPS | — | P0 |

---

## Rankings & Keyword Heuristics (SEO team)

| Signal | Action | Priority |
|--------|--------|----------|
| Dropped 5+ positions | Recovery audit + content refresh | P1 |
| Position 4-10 dropped | Content refresh | P1 |
| Position 11-20 | Internal linking, content gap fill | P2 |
| AI Overview present | Optimise for AIO visibility | P2 |
| PAA present | Create PAA-targeted content | P2 |
| High-volume, not indexed | Investigation + index request | P1 |
| Position 4-15 + high volume | Content optimisation push | P1 |
| Position 21+ with volume | Topic cluster / pillar page | P2 |

---

## Content Heuristics (Content team)

| Signal | Action | Priority |
|--------|--------|----------|
| Thin pages (< 300 words) | Expand to 500+ words | P2 |
| Missing meta descriptions (any count) | Write unique descriptions per page | P1 |
| Dropped rankings from content gaps | Recovery content | P1 |
| Keyword cluster opportunity | Topical authority pillar | P3 |

---

## Local SEO Heuristics (Local team)

| Signal | Action | Priority |
|--------|--------|----------|
| No GBP posts in 30+ days | Start weekly posting cadence | P1 |
| Review count < 10 | Review generation campaign | P1 |
| NAP inconsistency detected | Fix across all platforms | P1 |
| Average rating < 3.5 | Reputation management plan | P1 |
| Map pack not present | Local audit + GBP optimisation | P2 |

---

## Authority & Off-Page Heuristics (Off-Page team)

| Signal | Action | Priority |
|--------|--------|----------|
| DA stagnant or declining | Digital PR push | P2 |
| No new dofollow links this period | Guest post / outreach campaign | P2 |
| Referring domains < 30 | Directory + guest post plan | P2 |
| Competitor backlink gap identified | Gap analysis + targeted outreach | P2 |

---

## Anti-Hallucination Guardrails

- If a data field is absent, null, `"N/A"`, or `"—"`, do not reference its category in any action.
- If `local_seo` is missing entirely, do not generate local actions.
- If KPI change data is absent, do not generate trend-based actions.
- If `rankings` array is empty, do not generate ranking actions.
- If `backlinks.top_backlinks` or `ref_domains` is absent, do not generate off-page actions.
- Each action must cite at least one concrete data point from the input JSON.
