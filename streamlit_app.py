import streamlit as st
from enum import Enum
from typing import TypedDict

st.set_page_config(page_title="SEO Automation Pipeline", page_icon="🔍", layout="wide")
st.markdown("""
<style>
.card { border:1px solid #e5e7eb; border-radius:12px; padding:20px; margin-bottom:16px; background:white; transition:all .2s }
.card:hover { box-shadow:0 4px 20px rgba(0,0,0,.08); transform:translateY(-2px) }
.metric { text-align:center; padding:4px 0 }
.phase-badge { display:inline-flex; align-items:center; gap:6px; padding:4px 12px; border-radius:20px; font-size:13px; font-weight:600 }
.cat-badge { display:inline-flex; align-items:center; gap:4px; padding:2px 10px; border-radius:4px; font-size:11px; font-weight:500 }
.score-bar { display:flex; align-items:center; gap:8px; margin:4px 0 }
.score-track { flex:1; height:6px; background:#f1f5f9; border-radius:3px; overflow:hidden }
.score-fill { height:100%; border-radius:3px; transition:width .5s }
.tag { display:inline-block; padding:2px 8px; border-radius:12px; font-size:10px; background:#f1f5f9; color:#64748b; margin:2px }
.effort-badge { display:inline-flex; align-items:center; gap:4px; padding:2px 10px; border-radius:12px; font-size:11px }
.priority-badge { font-size:10px; font-weight:600; padding:2px 10px; border-radius:12px }
div[data-testid="stExpander"] { border:1px solid #e5e7eb; border-radius:12px; margin-bottom:12px }
div[data-testid="stExpander"] > details { padding:0 }
div[data-testid="stExpander"] > details > summary { padding:16px 20px; border-radius:12px }
</style>
""", unsafe_allow_html=True)

PHASE_CONFIG = {
    "empathize": {"label": "Empathize", "desc": "Understand pain points", "color": "#e11d48", "bg": "#fff1f2", "border": "#fecdd3", "emoji": "🔍"},
    "define": {"label": "Define", "desc": "Frame core problems", "color": "#d97706", "bg": "#fffbeb", "border": "#fde68a", "emoji": "🎯"},
    "ideate": {"label": "Ideate", "desc": "Generate solutions", "color": "#059669", "bg": "#ecfdf5", "border": "#a7f3d0", "emoji": "💡"},
    "prototype": {"label": "Prototype", "desc": "Build solutions", "color": "#0891b2", "bg": "#ecfeff", "border": "#a5f3fc", "emoji": "⚙️"},
    "test": {"label": "Test", "desc": "Validate & iterate", "color": "#7c3aed", "bg": "#f5f3ff", "border": "#ddd6fe", "emoji": "📊"},
}

CATEGORY_CONFIG = {
    "keyword-intelligence": {"label": "Keyword Intelligence", "color": "#ea580c", "bg": "#fff7ed"},
    "content-automation": {"label": "Content Automation", "color": "#059669", "bg": "#ecfdf5"},
    "technical-seo": {"label": "Technical SEO", "color": "#0891b2", "bg": "#ecfeff"},
    "link-building": {"label": "Link Building", "color": "#db2777", "bg": "#fdf2f8"},
    "analytics-reporting": {"label": "Analytics & Reporting", "color": "#7c3aed", "bg": "#f5f3ff"},
    "local-seo": {"label": "Local SEO", "color": "#0d9488", "bg": "#f0fdfa"},
    "workflow-orchestration": {"label": "Workflow Orchestration", "color": "#64748b", "bg": "#f8fafc"},
    "ai-strategy": {"label": "AI-Powered Strategy", "color": "#a21caf", "bg": "#fdf4ff"},
}

EFFORT_CONFIG = {"low": {"label": "Low", "color": "#059669", "bg": "#ecfdf5", "icon": "⚡"},
                 "medium": {"label": "Medium", "color": "#d97706", "bg": "#fffbeb", "icon": "📈"},
                 "high": {"label": "High", "color": "#ea580c", "bg": "#fff7ed", "icon": "🔧"},
                 "enterprise": {"label": "Enterprise", "color": "#e11d48", "bg": "#fff1f2", "icon": "⚠️"}}

PRIORITY_CONFIG = {"critical": {"label": "Critical", "css": "background:#e11d48;color:white"},
                   "high": {"label": "High", "css": "background:#ea580c;color:white"},
                   "medium": {"label": "Medium", "css": "background:#f59e0b;color:white"},
                   "low": {"label": "Low", "css": "background:#e5e7eb;color:#374151"}}

IDEAS = [
    {"id":"em-001","title":"AI Client Profiler","tagline":"Auto-generate comprehensive client SEO profiles from their website and industry data","description":"An automated system that scans a new client's website, industry landscape, and competitive environment to produce a detailed SEO profile.","benefits":["Reduce client onboarding from 2 days to 30 min","Eliminate human error","Standardize client evaluation","Impress with data-rich first impressions"],"phase":"empathize","category":"workflow-orchestration","impactScore":9,"feasibilityScore":8,"effort":"high","timeline":"6-8 weeks","priority":"high","tags":["onboarding","automation","AI"]},
    {"id":"em-002","title":"Competitor Intelligence Radar","tagline":"360-degree automated competitor monitoring with strategic gap detection","description":"A continuous competitor intelligence system that monitors competitor SEO strategies in real-time.","benefits":["Never miss competitor moves","Identify content gaps","Save hours on competitive analysis","Enable proactive strategy"],"phase":"empathize","category":"ai-strategy","impactScore":9,"feasibilityScore":7,"effort":"high","timeline":"8-10 weeks","priority":"high","tags":["competitors","monitoring","intelligence"]},
    {"id":"em-003","title":"Search Intent Analyzer","tagline":"Classify and map search intent at scale using NLP and SERP analysis","description":"Automatically classify thousands of keywords by search intent using SERP feature analysis and NLP.","benefits":["Intent mapping for 1000s of keywords","Detect intent shifts early","Align content with user needs","Identify under-served intents"],"phase":"empathize","category":"keyword-intelligence","impactScore":8,"feasibilityScore":7,"effort":"medium","timeline":"4-6 weeks","priority":"high","tags":["intent","keywords","NLP"]},
    {"id":"df-001","title":"SEO Opportunity Scorer","tagline":"Data-driven opportunity prioritization that replaces gut feeling with quantified impact","description":"An intelligent scoring system evaluating every SEO opportunity against multiple dimensions.","benefits":["Eliminate subjective debates","Focus on highest-ROI activities","Transparent scoring","Dynamic re-prioritization"],"phase":"define","category":"workflow-orchestration","impactScore":10,"feasibilityScore":8,"effort":"medium","timeline":"4-5 weeks","priority":"critical","tags":["prioritization","scoring","ROI"]},
    {"id":"df-002","title":"Technical Debt Quantifier","tagline":"Measure, track, and prioritize technical SEO debt with financial impact estimation","description":"Automatically crawl client websites, detect technical SEO issues, classify by severity and business impact.","benefits":["Quantify SEO issues in revenue terms","Prioritize by business impact","Track debt reduction over time","Build ROI justification"],"phase":"define","category":"technical-seo","impactScore":8,"feasibilityScore":7,"effort":"high","timeline":"6-8 weeks","priority":"high","tags":["technical-seo","debt","ROI"]},
    {"id":"df-003","title":"Content Gap Heatmap","tagline":"Visual heatmap revealing content gaps between your clients and their competitors","description":"Maps the entire topical landscape for a niche and identifies where competitors have content but your client doesn't.","benefits":["See full content opportunity landscape","Identify high-priority gaps","Visual format for client presentations","Prevent duplicate content"],"phase":"define","category":"content-automation","impactScore":8,"feasibilityScore":7,"effort":"medium","timeline":"5-6 weeks","priority":"high","tags":["content-gap","visualization","competitors"]},
    {"id":"id-001","title":"AI Keyword Cluster Engine","tagline":"Transform thousands of keywords into strategic topic clusters with AI-powered grouping","description":"Feed any keyword list and the system automatically groups them into topical clusters using NLP.","benefits":["Turn keywords into content plans","Identify pillar page opportunities","Build topical authority","Save 10+ hrs per client"],"phase":"ideate","category":"keyword-intelligence","impactScore":10,"feasibilityScore":8,"effort":"medium","timeline":"4-6 weeks","priority":"critical","tags":["keywords","clustering","NLP"]},
    {"id":"id-002","title":"Predictive Content Calendar","tagline":"AI-generated content calendar that anticipates seasonal trends and keyword demand","description":"Analyzes historical search trends, seasonal patterns, and competitor publishing to suggest the optimal content plan.","benefits":["Publish ahead of trend peaks","Never miss seasonal opportunities","Balance evergreen and trending","Save planning time"],"phase":"ideate","category":"content-automation","impactScore":9,"feasibilityScore":7,"effort":"medium","timeline":"5-7 weeks","priority":"high","tags":["calendar","forecasting","seasonal"]},
    {"id":"id-003","title":"SERP Feature Opportunity Scanner","tagline":"Detect and prioritize SERP feature opportunities across your entire keyword portfolio","description":"Automatically scan tracked keywords to identify which SERP features are available and winnable.","benefits":["Capture more SERP real estate","Prioritize snippet opportunities","Get optimization steps per feature","Track wins and losses"],"phase":"ideate","category":"keyword-intelligence","impactScore":8,"feasibilityScore":8,"effort":"medium","timeline":"4-5 weeks","priority":"high","tags":["SERP","featured-snippets","opportunities"]},
    {"id":"id-004","title":"Automated Internal Link Graph","tagline":"AI-powered internal linking strategy with visual graph and automated recommendations","description":"Build a complete internal link graph, analyze link equity, identify orphan pages.","benefits":["Maximize link equity","Eliminate orphan pages","Improve topical authority","Visualize architecture"],"phase":"ideate","category":"technical-seo","impactScore":9,"feasibilityScore":7,"effort":"high","timeline":"6-8 weeks","priority":"medium","tags":["internal-links","graph","architecture"]},
    {"id":"id-005","title":"AI Review Responder","tagline":"Brand-voice-aware automated responses to Google Business Profile reviews","description":"Monitors GBP reviews and generates contextually appropriate responses matching brand voice.","benefits":["Respond within 1 hour","Consistent brand voice","Free up staff time","Improve local ranking signals"],"phase":"ideate","category":"local-seo","impactScore":7,"feasibilityScore":9,"effort":"low","timeline":"2-3 weeks","priority":"medium","tags":["reviews","local-seo","AI"]},
    {"id":"id-006","title":"Voice Search Optimizer","tagline":"Identify and optimize for conversational queries and voice search opportunities","description":"Automatically identify voice search query opportunities and generate FAQ schema.","benefits":["Capture voice search traffic","Win Featured Snippets","Build FAQ at scale","Future-proof strategy"],"phase":"ideate","category":"keyword-intelligence","impactScore":7,"feasibilityScore":8,"effort":"low","timeline":"3-4 weeks","priority":"medium","tags":["voice-search","FAQ","schema"]},
    {"id":"pt-001","title":"Real-Time Site Health Monitor","tagline":"Continuous website health monitoring with instant alerts and self-healing recommendations","description":"24/7 monitoring of critical SEO health metrics with instant Slack/email alerts.","benefits":["Fix issues within minutes","Prevent revenue loss","Replace reactive troubleshooting","Reduce firefighting 80%"],"phase":"prototype","category":"technical-seo","impactScore":10,"feasibilityScore":9,"effort":"medium","timeline":"5-7 weeks","priority":"critical","tags":["monitoring","alerts","health"]},
    {"id":"pt-002","title":"AI Content Brief Generator","tagline":"Generate comprehensive, SEO-optimized content briefs in seconds with AI intelligence","description":"Transform a keyword into a complete content brief with search intent analysis and outline.","benefits":["Cut planning time 80%","Optimize before writing","Standardize quality","Enable junior writers"],"phase":"prototype","category":"content-automation","impactScore":10,"feasibilityScore":9,"effort":"medium","timeline":"4-6 weeks","priority":"critical","tags":["content","briefs","AI","writing"]},
    {"id":"pt-003","title":"Automated Outreach Engine","tagline":"Multi-channel link building outreach with personalization at scale","description":"Automated outreach that finds prospects, generates personalized emails, and tracks responses.","benefits":["Scale outreach 10x","Personalization at scale","Automated follow-ups","Track ROI precisely"],"phase":"prototype","category":"link-building","impactScore":9,"feasibilityScore":7,"effort":"high","timeline":"8-10 weeks","priority":"high","tags":["outreach","link-building","email"]},
    {"id":"pt-004","title":"Schema Markup Auto-Generator","tagline":"Automatically detect, generate, validate, and deploy structured data markup","description":"Analyze pages to determine the right schema type and auto-generate JSON-LD.","benefits":["Implement schema site-wide","100% validity guarantee","Auto-maintain as content changes","Increase rich result eligibility"],"phase":"prototype","category":"technical-seo","impactScore":8,"feasibilityScore":9,"effort":"medium","timeline":"4-6 weeks","priority":"high","tags":["schema","structured-data","JSON-LD"]},
    {"id":"pt-005","title":"Core Web Vitals Auto-Optimizer","tagline":"Detect, diagnose, and auto-fix Core Web Vitals issues with intelligent recommendations","description":"Monitor CWV across all client sites and generate specific fix recommendations.","benefits":["Prevent ranking regressions","Reduce LCP 30-50%","Zero-effort monitoring","Pass CWV assessment"],"phase":"prototype","category":"technical-seo","impactScore":9,"feasibilityScore":8,"effort":"high","timeline":"6-8 weeks","priority":"high","tags":["core-web-vitals","performance","LCP"]},
    {"id":"pt-006","title":"Citation Consistency Monitor","tagline":"Monitor NAP consistency across 100+ directories with automated correction workflows","description":"Automatically monitor NAP consistency across all major directories for every client location.","benefits":["Perfect NAP consistency","Prevent ranking drops","Manage 100+ locations","Save hours per location/month"],"phase":"prototype","category":"local-seo","impactScore":7,"feasibilityScore":8,"effort":"medium","timeline":"5-6 weeks","priority":"medium","tags":["citations","NAP","local-seo"]},
    {"id":"ts-001","title":"Automated ROI Attribution Engine","tagline":"Multi-touch attribution model that proves SEO's revenue contribution","description":"Track the complete customer journey from organic search to conversion with multi-touch attribution.","benefits":["Prove SEO ROI with data","Reduce client churn","Identify top revenue drivers","Build investment cases"],"phase":"test","category":"analytics-reporting","impactScore":10,"feasibilityScore":7,"effort":"high","timeline":"8-10 weeks","priority":"critical","tags":["attribution","ROI","revenue"]},
    {"id":"ts-002","title":"Predictive Traffic Forecaster","tagline":"ML-based organic traffic forecasting with confidence intervals and scenario planning","description":"Forecasts organic traffic 3-12 months ahead based on historical data and planned activities.","benefits":["Set data-driven forecasts","Identify performance gaps","Plan resource allocation","Proactively address declines"],"phase":"test","category":"analytics-reporting","impactScore":8,"feasibilityScore":6,"effort":"high","timeline":"8-12 weeks","priority":"medium","tags":["forecasting","ML","prediction"]},
    {"id":"ts-003","title":"Client Report Automator","tagline":"Generate professional, customizable client reports automatically on any schedule","description":"Automatically generate white-label SEO reports with custom branding and AI summaries.","benefits":["Save 8+ hrs per client/month","Consistent professional reporting","AI translates tech to business","Customizable templates"],"phase":"test","category":"analytics-reporting","impactScore":9,"feasibilityScore":9,"effort":"medium","timeline":"5-7 weeks","priority":"critical","tags":["reporting","automation","white-label"]},
    {"id":"ts-004","title":"Algorithm Update Impact Analyzer","tagline":"Instantly measure ranking and traffic impact of Google algorithm updates","description":"Automatically correlate ranking/traffic changes with known Google algorithm updates.","benefits":["Know impact immediately","Reduce panic response","Data-driven recovery","Historical vulnerability analysis"],"phase":"test","category":"ai-strategy","impactScore":8,"feasibilityScore":7,"effort":"medium","timeline":"5-7 weeks","priority":"high","tags":["algorithm-updates","monitoring"]},
    {"id":"ts-005","title":"SEO A/B Testing Platform","tagline":"Scientifically test SEO changes with controlled experiments and statistical significance","description":"Split URLs into control/variant groups and measure ranking/traffic differences with significance.","benefits":["Data-driven decisions","Quantify change impact","Build confidence","Reduce risk"],"phase":"test","category":"workflow-orchestration","impactScore":9,"feasibilityScore":5,"effort":"enterprise","timeline":"12-16 weeks","priority":"low","tags":["A/B-testing","experimentation"]},
    {"id":"cc-001","title":"Central SEO Orchestrator","tagline":"Unified command center that coordinates all SEO automation tools and workflows","description":"Central dashboard integrating all SEO automation tools with unified view and workflow coordination.","benefits":["Single pane of glass","Eliminate context switching","Coordinated workflows","Scale from 10 to 100+ clients"],"phase":"prototype","category":"workflow-orchestration","impactScore":10,"feasibilityScore":6,"effort":"enterprise","timeline":"16-24 weeks","priority":"high","tags":["orchestration","dashboard","integration"]},
    {"id":"cc-002","title":"Lost Link Recovery System","tagline":"Detect lost backlinks in real-time and trigger automated recovery outreach","description":"Continuously monitor backlinks to detect removal, classify loss, and trigger recovery.","benefits":["Prevent authority decay","Recover high-value links","Automated recovery","Track link health"],"phase":"test","category":"link-building","impactScore":8,"feasibilityScore":7,"effort":"medium","timeline":"5-7 weeks","priority":"medium","tags":["backlinks","recovery","monitoring"]},
    {"id":"cc-003","title":"Content Decay Detector","tagline":"Monitor existing content for performance decline and trigger refresh workflows","description":"Track published content for signs of decay and automatically trigger refresh workflows.","benefits":["Maintain rankings over time","Catch decay before traffic loss","Trigger optimal refresh timing","Maximize content ROI"],"phase":"test","category":"content-automation","impactScore":8,"feasibilityScore":8,"effort":"medium","timeline":"4-6 weeks","priority":"high","tags":["content-decay","refresh","monitoring"]},
]

st.title("🔍 SEO Automation Pipeline")
st.markdown("**25 automation ideas** organized by Design Thinking methodology across **8 SEO workflow categories**. Score, prioritize, and plan your agency's automation roadmap.")

if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = set()
if "phase_filter" not in st.session_state:
    st.session_state.phase_filter = "all"
if "category_filter" not in st.session_state:
    st.session_state.category_filter = "all"

def toggle_detail(idea_id):
    if idea_id in st.session_state.selected_ids:
        st.session_state.selected_ids.discard(idea_id)
    else:
        st.session_state.selected_ids.add(idea_id)

col1, col2 = st.columns([2, 1])
with col1:
    phases = ["all"] + list(PHASE_CONFIG.keys())
    phase_labels = ["All Phases"] + [f"{PHASE_CONFIG[p]['emoji']} {PHASE_CONFIG[p]['label']}" for p in list(PHASE_CONFIG.keys())]
    phase_map = dict(zip(phase_labels, phases))
    selected_phase_label = st.selectbox("Filter by Phase", phase_labels, label_visibility="collapsed")
    st.session_state.phase_filter = phase_map[selected_phase_label]
with col2:
    cats = ["all"] + list(CATEGORY_CONFIG.keys())
    cat_labels = ["All Categories"] + [CATEGORY_CONFIG[c]["label"] for c in list(CATEGORY_CONFIG.keys())]
    cat_map = dict(zip(cat_labels, cats))
    selected_cat_label = st.selectbox("Filter by Category", cat_labels, label_visibility="collapsed")
    st.session_state.category_filter = cat_map[selected_cat_label]

filtered = [i for i in IDEAS
            if (st.session_state.phase_filter == "all" or i["phase"] == st.session_state.phase_filter)
            and (st.session_state.category_filter == "all" or i["category"] == st.session_state.category_filter)]

st.markdown(f"<p style='color:#64748b;font-size:14px'>Showing {len(filtered)} of {len(IDEAS)} ideas</p>", unsafe_allow_html=True)

for idea in filtered:
    ph = PHASE_CONFIG[idea["phase"]]
    cat = CATEGORY_CONFIG[idea["category"]]
    ef = EFFORT_CONFIG[idea["effort"]]
    pr = PRIORITY_CONFIG[idea["priority"]]
    is_expanded = idea["id"] in st.session_state.selected_ids

    phase_css = f"background:{ph['bg']};color:{ph['color']};border:1px solid {ph['border']}"
    cat_css = f"background:{cat['bg']};color:{cat['color']}"
    effort_css = f"background:{ef['bg']};color:{ef['color']}"
    priority_css = pr["css"]

    with st.expander(f"**{idea['title']}** — {idea['tagline']}", expanded=is_expanded):
        meta = f"""
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
            <span class="phase-badge" style="{phase_css}">{ph['emoji']} {ph['label']}</span>
            <span class="cat-badge" style="{cat_css}">{cat['label']}</span>
            <span class="effort-badge" style="{effort_css}">{ef['icon']} {ef['label']}</span>
            <span style="font-size:11px;color:#64748b">⏱ {idea['timeline']}</span>
            <span class="priority-badge" style="{priority_css}">{pr['label']}</span>
        </div>
        """
        st.markdown(meta, unsafe_allow_html=True)
        st.markdown(f"<p style='color:#374151;line-height:1.6'>{idea['description']}</p>", unsafe_allow_html=True)

        sc1, sc2, sc3 = st.columns([1, 1, 1])
        with sc1:
            st.markdown(f"<div class='metric'><div style='font-size:24px;font-weight:700;color:#059669'>{idea['impactScore']}/10</div><div style='font-size:11px;color:#64748b'>Impact Score</div></div>", unsafe_allow_html=True)
        with sc2:
            st.markdown(f"<div class='metric'><div style='font-size:24px;font-weight:700;color:#0891b2'>{idea['feasibilityScore']}/10</div><div style='font-size:11px;color:#64748b'>Feasibility</div></div>", unsafe_allow_html=True)
        with sc3:
            st.markdown(f"<div class='metric'><div style='font-size:14px;font-weight:600;color:#374151'>⏱ {idea['timeline']}</div><div style='font-size:11px;color:#64748b'>Timeline</div></div>", unsafe_allow_html=True)

        if idea.get("benefits"):
            st.markdown("**✅ Key Benefits**")
            for b in idea["benefits"]:
                st.markdown(f"- {b}")

        if idea.get("tags"):
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in idea["tags"])
            st.markdown(f"**Tags:** {tags_html}", unsafe_allow_html=True)

st.markdown("""
<div style='text-align:center;margin-top:48px;padding:32px;border-radius:12px;background:linear-gradient(135deg,#0f172a,#1e293b);color:white'>
    <h3 style='margin:0 0 8px;font-size:18px'>🚀 Ready to Build Your Automation Pipeline?</h3>
    <p style='color:#94a3b8;font-size:14px;margin:0'>Score. Prioritize. Build. Transform your agency's SEO operations.</p>
</div>
""", unsafe_allow_html=True)
