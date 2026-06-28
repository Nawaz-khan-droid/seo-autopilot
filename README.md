---
title: Seo-Autopilot
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# SEO Autopilot — Multi-Client SEO Report Generator

Automated DOCX report generation for monthly SEO deliverables. Produces two files per client:
- **Client-facing Monthly SEO Report** (15 cards — off-page, on-page, technical)
- **Internal Action Plan** (9 cards — sprint-ready task breakdown)

## Quick Start

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set at minimum:

```env
GROQ_API_KEY=your_groq_key_here
```

Generate sample reports for Beautiful India:

```bash
python scripts/gen_llm_report.py
```

Output is written to `output/` as timestamped DOCX files.

## Report Structure

### Client Report (15 cards)

| Card | Section | Content |
|------|---------|---------|
| 1 | Cover | Agency name, client, period |
| 2 | Executive Dashboard | KPI snapshot + insight bullets |
| 3 | GSC Performance | Clicks/impressions comparison |
| 4 | Search Visibility & Brand Rankings | Keyword distribution chart + table |
| 5 | Top Performing Keywords | Winners with gain analysis |
| 6 | Keywords Needing Attention | Losers with recovery actions |
| 7 | Press Coverage & Regional Visibility | Media rankings (Forbes, Vogue, etc.) |
| 8 | Local SEO — GMB | GMB keyword tracking + insights |
| 9 | Off-Page SEO Activities | Bookmarking, image/video submissions |
| 10 | SEO Activities Performed | All tasks categorised |
| 11 | Core Web Vitals | CWV scores + optimisation notes |
| 12 | Technical SEO Health | Audit results + issues list |
| 13 | Recommendations & Strategy | Priority breakdown (P0–P2) |
| 14 | Action Plan by Team | Team assignments with priorities |
| 15 | Summary & Next Steps | Key priorities for next period |

### Action Plan (9 cards)

| Card | Content |
|------|---------|
| 1 | Cover |
| 2 | Task Landscape |
| 3–6 | Team-specific tasks (SEO, Dev, Content, Local, Off-Page) |
| 7 | Priority Matrix (P0–P3) |
| 8 | Technical Specifications (LCP, INP, CLS) |
| 9 | Advisor Summary |

## Key Features

- **Zero hallucinated data** — Every metric uses an `Evidence<T>` wrapper with source and timestamp
- **Client context module** — Pre-researched profiles prevent the LLM from inventing keywords or business type
- **Balanced coverage** — Off-page (GMB, link building, PR), on-page (rankings, content), and technical (CWV, site health)
- **Explanatory narrative** — Every section includes client-facing bullet points that translate numbers into business impact
- **Separate files** — Client report is clean of technical detail; action plan has CWV specs, advisor notes, and sprint planning

## Configuration

Key environment variables (see `.env.example` for full list):

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Yes | LLM for report narratives (Llama 3 70B) |
| `GROQ_MODEL` | No | Default: `llama-3.3-70b-versatile` |
| `TAVILY_API_KEY` | No | Auto-research new clients (falls back to hardcoded profiles) |

## Adding a New Client

1. Add client context to `report/client_context.py` `CLIENT_PROFILES` dict
2. Add keyword data to `CLIENT_KEYWORDS` in the same file
3. Update sample data in `scripts/gen_llm_report.py` `build_sample_facts()`
4. Run `python scripts/gen_llm_report.py` to regenerate

## Dependencies

- `python-docx` — DOCX report builder
- `matplotlib` — Charts (distribution, PSI comparison)
- `groq` / `tavily-python` — LLM and client research APIs

See `requirements.txt` for full list.

## Project Structure

```
├── report/                    # Report builders
│   ├── docx_report.py         # Client-facing DOCX (15 cards)
│   ├── docx_action_plan.py    # Internal action plan DOCX (9 cards)
│   ├── client_context.py      # Pre-researched client profiles
│   ├── client_research.py     # Tavily auto-research module
│   ├── facts.py               # ReportFacts data structures
│   ├── llm_report_generator.py # LLM prompt + generation
│   ├── charts.py              # Matplotlib chart functions
│   └── evidence.py            # Evidence<T> wrapper
├── scripts/
│   ├── gen_llm_report.py      # Sample report generator (Beautiful India)
│   └── run_report_generator.py # CLI wrapper
├── config/
│   └── settings.py            # Env var loading
├── output/                    # Generated deliverables
├── .env.example               # Environment template
└── requirements.txt           # Python dependencies
```
