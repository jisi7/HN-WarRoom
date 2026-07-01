#!/usr/bin/env python3
"""
Holistic Nutrition Content Agent v5
Firecrawl + DataForSEO + Claude → Best keyword gap → Article → Shopify → Library
Fixes: realistic images (FLUX Dev), correct article URLs, image upload retry
"""

import os, json, random, requests, datetime, base64, io, re, time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from anthropic import Anthropic

# ── CONFIG ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL        = "https://ykzkivpcojjzmbbnuewj.supabase.co"
SUPABASE_KEY        = os.environ.get("SUPABASE_KEY", "")
ZAPIER_WEBHOOK      = os.environ.get("ZAPIER_WEBHOOK", "")
ZAPIER_LIBRARY_HOOK = os.environ.get("ZAPIER_LIBRARY_HOOK", "")
YOUTUBE_API_KEY     = os.environ.get("YOUTUBE_API_KEY", "")
REPLICATE_API_KEY   = os.environ.get("REPLICATE_API_KEY", "")
CLOUDINARY_CLOUD    = os.environ.get("CLOUDINARY_CLOUD", "")
CLOUDINARY_API_KEY  = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_SECRET   = os.environ.get("CLOUDINARY_SECRET", "")
FIRECRAWL_API_KEY   = os.environ.get("FIRECRAWL_API_KEY", "")
DATAFORSEO_LOGIN    = os.environ.get("DATAFORSEO_LOGIN", "")
DATAFORSEO_PASSWORD = os.environ.get("DATAFORSEO_PASSWORD", "")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# ── BRAND ─────────────────────────────────────────────────────────────────────
HN_BROWN    = "#A3988B"
HN_CREAM    = "#E8E3DC"
HN_CHARCOAL = "#2C2A27"
HN_GREEN    = "#048142"
HN_RED      = "#D2042D"
HN_BLUE     = "#24418F"
HN_AMBER    = "#C8893A"

PRODUCT_MAP = {
    "creatine": {
        "name":     "Micronized Creatine Monohydrate",
        "url":      "https://holisticnutrition.us/products/creatine-monohydrate",
        "color":    HN_RED,
        "category": "Physical Performance",
        "cta":      "Holistic Nutrition's Micronized Creatine Monohydrate is formulated to the standard outlined in this brief — single-ingredient, micronized, third-party tested.",
        "cta_url":  "https://holisticnutrition.us/products/creatine-monohydrate"
    },
    "focase": {
        "name":     "Focase Cognition Support",
        "url":      "https://holisticnutrition.us/products/focase",
        "color":    HN_BLUE,
        "category": "Cognitive Performance",
        "cta":      "Focase 2.0 combines L-Tyrosine, Ashwagandha, Alpha-GPC, L-Theanine, Phosphatidylserine, Rhodiola, Omega-3s, methylated B-vitamins, Vitamin D3, Caffeine, and BioPerine at clinically informed doses.",
        "cta_url":  "https://holisticnutrition.us/products/focase"
    },
    "vitamin_d": {
        "name":     "Vitamin D3 + K2",
        "url":      "https://holisticnutrition.us/products/vitamin-d3-k2",
        "color":    HN_AMBER,
        "category": "Foundational Health and Longevity",
        "cta":      "Holistic Nutrition's Vitamin D3 + K2 pairs D3 with MK-7, calcium, and BioPerine — addressing the full absorption mechanism reviewed here.",
        "cta_url":  "https://holisticnutrition.us/products/vitamin-d3-k2"
    },
    "general": {
        "name":     "Holistic Nutrition",
        "url":      "https://holisticnutrition.us",
        "color":    HN_BROWN,
        "category": "Research Briefs",
        "cta":      "Explore Holistic Nutrition's research-driven supplement lineup.",
        "cta_url":  "https://holisticnutrition.us"
    }
}

FOCASE_2_FORMULA = """
Focase 2.0 (per serving, 30 servings):
Vitamin D3 50mcg, B6 (P5P) 5mg, Folate (5-MTHF) 460mcg, B12 (Methylcobalamin) 25mcg,
Omega-3 Fish Oil 1000mg, L-Tyrosine 400mg, Ashwagandha (KSM-66) 250mg,
Alpha-GPC 50% 200mg, L-Theanine 200mg, Phosphatidylserine 20% 200mg,
Rhodiola (3% Rosavins) 150mg, Caffeine 75mg, BioPerine 7mg.
NO Lion's Mane. Sweetened with Stevia + Thaumatin only.
"""

# ── PHOTO PROMPT STYLE ────────────────────────────────────────────────────────
# Real-world subjects FLUX Dev can photograph realistically.
PHOTO_STYLE = (
    "Ultra-wide panoramic banner, 3:1 aspect ratio. "
    "Shot on a full-frame camera with a 50mm lens. "
    "Natural studio or outdoor light. "
    "Photorealistic — looks like a real photograph, not digital art, not CGI, not illustrated. "
    "Clean minimal composition. "
    "No text, no product bottles, no logos, no people's faces."
)

PRODUCT_PHOTO_SUBJECTS = {
    "creatine": [
        "overhead view of a white ceramic scoop of fine white crystalline powder on a clean white surface",
        "close-up of muscular forearm gripping a stainless steel pull-up bar, natural gym lighting",
        "glass of clear water with fine white powder dissolving, macro lens, clean white background",
        "top view of athletic track lane lines stretching to the horizon, early morning golden light",
        "hands of an athlete wrapping wrist tape before lifting, clean gym background",
        "close-up of white powder being scooped with a matte black spoon on white marble"
    ],
    "focase": [
        "overhead shot of a clean wooden desk with an open notebook, single pen, morning window light",
        "close-up of hands typing on a keyboard with coffee beside them, warm office light",
        "bright minimal workspace corner — white desk, green plant, soft morning light through window",
        "top-down view of open book pages with small glass of water and clean white surface",
        "a focused person writing notes in a notebook at a bright cafe window, bokeh background",
        "minimal desk setup with a laptop, clean notepad, and a single espresso cup, morning light"
    ],
    "vitamin_d": [
        "aerial view of a person standing in bright midday sunlight on a white sand beach",
        "close-up of sunlight streaming through a window onto a wooden table with a glass of water",
        "macro shot of small amber gel capsules on a clean white marble surface",
        "sunlight breaking through forest canopy onto a green moss floor, rays visible",
        "person's bare arm resting in bright natural sunlight on a light concrete surface",
        "wide shot of golden wheat field under a bright blue sky at midday"
    ],
    "general": [
        "overhead flat lay of scientific journals, a glass of water, and a clean notebook on white",
        "close-up of a researcher's hands turning pages of a printed study under lab lighting",
        "minimal lab bench with clean glass beakers and morning light through large windows",
        "top-down view of assorted natural ingredients arranged cleanly on white surface",
        "side view of a person reviewing data on a laptop screen, clean bright room"
    ]
}

SEED_KEYWORDS = {
    "creatine": [
        "creatine in coffee", "creatine for brain health cognitive performance",
        "creatine monohydrate benefits evidence", "creatine monohydrate vegetarian",
        "creatine and taurine", "creatine or protein which is better",
        "creatine and protein powder stack", "best tasteless creatine powder",
        "creatine loading phase necessary", "creatine for women evidence",
        "creatine timing pre vs post workout", "creatine water retention truth",
        "creatine safety long term", "creatine for endurance athletes",
        "micronized creatine bioavailability", "creatine sleep quality",
        "creatine for beginners complete guide", "creatine and intermittent fasting",
        "creatine hair loss myth evidence", "creatine kidney health research"
    ],
    "focase": [
        "supplements for focus and concentration without crash",
        "how to get rid of brain fog nutrition", "memory health supplements evidence",
        "brain healthy supplements research", "nootropic stack evidence based",
        "alpha gpc cognitive benefits dosing", "ashwagandha cortisol stress evidence",
        "l-theanine caffeine synergy ratio", "phosphatidylserine memory research",
        "rhodiola rosea fatigue evidence", "l-tyrosine focus dopamine mechanism",
        "adaptogens stress response clinical", "cognitive decline prevention supplements",
        "best supplements marathon training focus", "working memory improvement supplements",
        "mental fatigue supplements evidence", "vitamin d brain health cognition",
        "omega 3 cognitive performance", "methylcobalamin b12 brain benefits",
        "bioperine absorption nootropics"
    ],
    "vitamin_d": [
        "vitamin d brain health depression", "immune health supplements evidence",
        "vitamin d deficiency symptoms indoor lifestyle", "vitamin d3 vs d2 clinical evidence",
        "vitamin k2 mk7 calcium arterial", "vitamin d bone density research",
        "vitamin d testosterone evidence", "vitamin d sleep quality research",
        "vitamin d cardiovascular health", "vitamin d optimal levels testing",
        "vitamin d dosing protocol evidence", "bioperine fat soluble vitamin absorption",
        "vitamin d autoimmune disease research", "vitamin d athletes performance",
        "calcium supplementation evidence", "vitamin d insulin sensitivity",
        "vitamin d and magnesium absorption", "heart health supplements evidence",
        "adrenal health supplements", "elderberry immune support evidence"
    ],
    "general": [
        "longevity supplements evidence based", "supplement third party testing importance",
        "bioavailability supplement forms guide", "supplement label reading guide",
        "anti inflammatory supplements evidence", "gut health performance supplements",
        "sleep optimization supplements research", "recovery supplements evidence",
        "supplement stack for longevity", "nutrient deficiency modern diet",
        "best supplements for biohackers", "holistic health optimization science",
        "supplements and vitamins evidence", "vegan supplements complete guide",
        "turmeric health supplements evidence"
    ]
}

COMPETITORS = [
    {"url": "https://examine.com/supplements/", "name": "Examine.com"},
    {"url": "https://www.healthline.com/nutrition", "name": "Healthline"},
    {"url": "https://www.verywellhealth.com/supplements-4846521", "name": "Verywell"},
    {"url": "https://www.thorne.com/take-5-daily", "name": "Thorne Blog"}
]

ARTICLE_SYSTEM_PROMPT = """You are the lead research writer for Holistic Nutrition — a science-driven supplement company positioned as the closest thing in the supplement industry to a biotech research institution.

BRAND VOICE:
- Authoritative, precise, educational — never cold, never hype-driven
- Write like a researcher who wants the reader to understand their own biology
- Cite evidence clearly. Acknowledge limitations honestly.
- Never use motivational language, wellness speak, or marketing filler
- Every article must be completely self-contained

FORMATTING:
- Mix developed paragraphs (3-5 sentences) with selective bullet points
- Never more than 3 consecutive long paragraphs without a visual break
- Bullets for: comparisons, dosing protocols, population guidance, key findings
- Paragraphs for: mechanisms, background, nuanced analysis

ARTICLE STRUCTURE:
1. Title — research brief style, clinically grounded, SEO-optimized for the target keyword
2. Opening quote — real peer-reviewed study or named researcher
3. Introduction — 2 paragraphs establishing why this topic matters
4. What is [X]? — 2-3 paragraphs, zero prior knowledge assumed
5. What is [X] Used For? — prose + bullets covering primary documented uses
6. Evidence and Mechanisms — core science with citations [1][2][3]
7. Clinical Considerations — subpopulations with H3 subheadings and bullets
8. How to Choose [X] — 3-5 bullet selection criteria
9. Conclusion — 1-2 paragraphs
10. References — AMA format

REQUIRED VISUALS:
- At least ONE pull quote blockquote with key stat
- At least ONE HTML comparison/summary table
- Bullets in at least 3 sections
- H3 subheadings in Clinical Considerations

HTML: <h2>, <h3>, <p>, <ul><li>, <blockquote>, <table>
Health claims: "supports", "associated with", "may help", "evidence suggests"
Length: 1800-2400 words
CRITICAL: Never use backslashes in HTML. No escape sequences in JSON strings.

OUTPUT — ONLY valid JSON:
{
  "title": "...",
  "photo_subject": "Describe ONE simple real-world subject to photograph — a physical object or scene. Keep it concrete and photographable. Examples: 'close-up of white creatine powder in a ceramic scoop on white marble', 'sunlight streaming through a window onto a wooden desk', 'athlete gripping a pull-up bar in a clean gym'. No molecular descriptions, no diagrams, no abstract concepts.",
  "meta_title": "... max 55 chars",
  "meta_description": "... max 150 chars",
  "opening_quote": {"text": "...", "source": "..."},
  "sections": [
    {"heading": "Introduction", "html": "<p>...</p>"},
    {"heading": "What is [X]?", "html": "<p>...</p>"},
    {"heading": "What is [X] Used For?", "html": "<p>...</p><ul><li>...</li></ul>"},
    {"heading": "Evidence and Mechanisms", "html": "<p>...</p><blockquote>...</blockquote>"},
    {"heading": "Clinical Considerations", "html": "<h3>...</h3><p>...</p><ul><li>...</li></ul>"},
    {"heading": "How to Choose [X]", "html": "<ul><li>...</li></ul>"},
    {"heading": "Conclusion", "html": "<p>...</p>"}
  ],
  "chart": {
    "type": "bar", "title": "...", "subtitle": "Source: Author et al., Journal, Year",
    "labels": ["...", "..."], "values": [0.0, 0.0],
    "value_suffix": "%", "color_highlight_index": 0
  },
  "youtube_query": "...",
  "references": ["[1] ...", "[2] ..."],
  "word_count": 0
}

Return ONLY valid JSON. No markdown. No preamble."""

# ── SUPABASE ──────────────────────────────────────────────────────────────────
def sb(method, path, **kwargs):
    if not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_KEY is empty — set the GitHub Actions secret to a valid "
            "Supabase service_role / secret key."
        )
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    r = getattr(requests, method)(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, **kwargs)
    # Fail loudly instead of silently swallowing. A bad key, expired token, or RLS
    # block used to return {} here — so the agent kept running, published, and
    # exited 0 while nothing reached Supabase. Surface it instead.
    if r.status_code >= 400:
        raise RuntimeError(
            f"Supabase {method.upper()} /{path} failed [{r.status_code}]: {r.text[:300]}"
        )
    if r.status_code == 204 or not r.text:
        return []
    try:    return r.json()
    except: return r.text

def get_published_topics():
    rows = sb("get", "articles", params={"status": "eq.published", "select": "keyword,title", "limit": "500"})
    if not isinstance(rows, list): return []
    topics = []
    for r in rows:
        if r.get("keyword"): topics.append(r["keyword"].lower().strip())
        if r.get("title"):   topics.append(r["title"].lower().strip())
    return topics

def get_product_performance():
    """Per-product score multiplier from real GA4 results (the `performance` table,
    populated by analytics_agent.py). Sales-weighted: revenue and conversions count
    most, engagement second. Returns {} when there's no data yet, so this is a safe
    no-op until analytics starts flowing. Best product gets ~1.35x, others scale down
    toward 1.0 — a deliberate nudge toward what converts, not a hard override."""
    MAX_BOOST = 1.35
    try:
        rows = sb("get", "performance", params={
            "select": "engagement_rate,conversions,revenue,articles(product)", "limit": "5000"})
    except Exception as e:
        print(f"  [warn] performance read failed (no boost applied): {e}")
        return {}
    if not isinstance(rows, list) or not rows:
        return {}
    agg = {}
    for r in rows:
        prod = (r.get("articles") or {}).get("product")
        if not prod:
            continue
        a = agg.setdefault(prod, {"rev": 0.0, "conv": 0.0, "eng": 0.0, "n": 0})
        a["rev"]  += float(r.get("revenue") or 0)
        a["conv"] += float(r.get("conversions") or 0)
        a["eng"]  += float(r.get("engagement_rate") or 0)
        a["n"]    += 1
    signal = {p: a["rev"] * 1.0 + a["conv"] * 25.0 + (a["eng"] / a["n"] if a["n"] else 0) * 50.0
              for p, a in agg.items()}
    if not signal:
        return {}
    lo, hi = min(signal.values()), max(signal.values())
    if hi <= lo:
        return {}
    return {p: 1.0 + (s - lo) / (hi - lo) * (MAX_BOOST - 1.0) for p, s in signal.items()}

def get_cached_competitor_topics():
    try:
        rows = sb("get", "agent_runs", params={
            "agent_name": "eq.Firecrawl Scraper",
            "status": "eq.completed",
            "order": "completed_at.desc",
            "limit": "1"
        })
    except Exception as e:
        print(f"  [warn] competitor cache read failed: {e}")
        return None, None
    if not isinstance(rows, list) or not rows:
        return None, None
    last_run = rows[0].get("completed_at", "")
    if last_run:
        try:
            last_dt  = datetime.datetime.fromisoformat(last_run.replace("Z", "").replace("+00:00", ""))
            days_ago = (datetime.datetime.utcnow() - last_dt).days
            if days_ago < 7:
                cached = json.loads(rows[0].get("message", "{}"))
                return cached.get("topics", []), days_ago
        except: pass
    return None, None

def cache_competitor_topics(topics):
    try:
        sb("post", "agent_runs", json={
            "agent_name":    "Firecrawl Scraper",
            "status":        "completed",
            "message":       json.dumps({"topics": topics}),
            "completed_at":  datetime.datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"  [warn] competitor cache write failed: {e}")

def log_run(status, message, articles=0, errors=None, duration=None):
    # Best-effort: a logging failure must never crash a run that already published.
    try:
        sb("post", "agent_runs", json={
            "agent_name":         "Content Agent v5",
            "status":             status,
            "message":            message,
            "articles_processed": articles,
            "errors":             errors,
            "duration_seconds":   duration,
            "completed_at":       datetime.datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"  [warn] log_run failed: {e}")

def insert_article(data):
    rows = sb("post", "articles", json=data)
    return rows[0] if isinstance(rows, list) and rows else None

def update_article(aid, data):
    sb("patch", f"articles?id=eq.{aid}", json=data)

# ── FIRECRAWL ─────────────────────────────────────────────────────────────────
def scrape_competitor_topics():
    print("  [Firecrawl] Scraping competitor sites...")
    if not FIRECRAWL_API_KEY:
        print("  [Firecrawl] No API key — skipping")
        return []

    all_topics = []
    headers    = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}

    for competitor in COMPETITORS:
        try:
            print(f"  [Firecrawl] Scraping {competitor['name']}...")
            r    = requests.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers=headers,
                json={"url": competitor["url"], "formats": ["markdown"],
                      "onlyMainContent": True, "waitFor": 2000},
                timeout=30
            )
            data = r.json()
            if data.get("success"):
                content = data.get("data", {}).get("markdown", "")
                for line in content.split("\n"):
                    line = line.strip()
                    for match in re.findall(r'\[([^\]]+)\]\(', line):
                        if 10 < len(match) < 150:
                            all_topics.append({"title": match.strip(), "source": competitor["name"]})
                    if line.startswith("#") and len(line) > 15:
                        clean = re.sub(r'^#+\s*', '', line).strip()
                        if clean:
                            all_topics.append({"title": clean, "source": competitor["name"]})
            else:
                print(f"  [Firecrawl] {competitor['name']} failed: {data.get('error', 'unknown')}")
            time.sleep(1)
        except Exception as e:
            print(f"  [Firecrawl] {competitor['name']} error: {e}")

    print(f"  [Firecrawl] Scraped {len(all_topics)} competitor topics")
    return all_topics

# ── DATAFORSEO ────────────────────────────────────────────────────────────────
def get_search_volumes(keywords):
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD or not keywords:
        print("  [DataForSEO] Skipping — no credentials or keywords")
        return {}
    print(f"  [DataForSEO] Checking volume for {len(keywords)} keywords...")
    try:
        auth    = base64.b64encode(f"{DATAFORSEO_LOGIN}:{DATAFORSEO_PASSWORD}".encode()).decode()
        payload = [{"keywords": keywords[:100], "location_code": 2840, "language_code": "en",
                    "include_serp_info": False}]
        r       = requests.post(
            "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json=payload, timeout=30
        )
        result  = r.json()
        volumes = {}
        if result.get("status_code") == 20000:
            for task in result.get("tasks", []):
                for item in (task.get("result", []) or []):
                    kw = item.get("keyword", "")
                    volumes[kw] = {
                        "volume":      item.get("search_volume", 0) or 0,
                        "cpc":         item.get("cpc", 0) or 0,
                        "competition": item.get("competition_index", 0) or 0
                    }
        print(f"  [DataForSEO] Got data for {len(volumes)} keywords")
        return volumes
    except Exception as e:
        print(f"  [DataForSEO] Error: {e}")
        return {}

# ── KEYWORD SELECTION ─────────────────────────────────────────────────────────
# ── TOPIC DEDUP ───────────────────────────────────────────────────────────────
# Generic SEO/filler words to ignore when comparing topics, so "Alpha-GPC ...
# Clinical Review" and "Alpha-GPC ... Evidence-Based Guidelines" are recognized
# as the SAME topic (they share the meaningful tokens alpha/gpc/cognitive/dosing).
_STOP = {
    "the","and","for","with","without","what","how","why","best","top","your","you","are","that","this",
    "vs","versus","than","from","into","based","evidence","clinical","complete","comprehensive",
    "research","studies","study","analysis","review","protocol","protocols","science","scientific",
    "explained","actually","shows","guidelines","comparing","comparison","overview","ultimate","guide",
}

def _topic_tokens(text):
    # Keep normal words (>2 chars) AND short alphanumeric supplement codes like
    # d3, d2, k2, b6, b12, q10 — dropping these blinded dedup to the difference
    # between "Vitamin D3 vs D2" and every reworded clone of it (8 shipped in a row
    # before this fix), since after stopwords the only shared word was "vitamin".
    toks = set()
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if w in _STOP:
            continue
        if len(w) > 2 or any(ch.isdigit() for ch in w):
            toks.add(w)
    return toks

def _is_dup_topic(candidate, published_texts):
    """True if `candidate` covers essentially the same subject as something already
    published. Compares meaningful-token overlap rather than exact substrings, which
    is what let near-identical titles slip through before."""
    c = _topic_tokens(candidate)
    if not c:
        return False
    for p in published_texts:
        pt = _topic_tokens(p)
        if not pt:
            continue
        shared = c & pt
        if len(shared) >= 3 or (len(shared) >= 2 and len(shared) / min(len(c), len(pt)) >= 0.66):
            return True
    return False

def pick_best_keyword():
    print("\n  [Keyword] Starting competitive keyword research...")

    published = get_published_topics()
    print(f"  [Keyword] {len(published)} topics already published")

    perf_boost = get_product_performance()
    if perf_boost:
        ranked = sorted(perf_boost.items(), key=lambda kv: kv[1], reverse=True)
        print("  [Keyword] Performance boost by product: " +
              ", ".join(f"{p}×{b:.2f}" for p, b in ranked))

    competitor_topics, cache_age = get_cached_competitor_topics()
    if competitor_topics:
        print(f"  [Keyword] Using cached competitor data ({cache_age} days old, {len(competitor_topics)} topics)")
    else:
        print("  [Keyword] Cache expired — scraping competitors...")
        competitor_topics = scrape_competitor_topics()
        if competitor_topics:
            cache_competitor_topics(competitor_topics)

    candidates = []
    for product, keywords in SEED_KEYWORDS.items():
        for kw in keywords:
            if not _is_dup_topic(kw, published):
                candidates.append({"keyword": kw, "product": product})

    if not candidates:
        print("  [Keyword] All seed topics covered — generating fresh keywords...")
        fresh = generate_fresh_keywords(published)
        candidates = [c for c in fresh if not _is_dup_topic(c.get("keyword", ""), published)]

    print(f"  [Keyword] {len(candidates)} non-duplicate candidates available")

    volumes = get_search_volumes([c["keyword"] for c in candidates[:50]])

    scored = []
    for c in candidates[:50]:
        kw   = c["keyword"]
        vol  = volumes.get(kw, {}).get("volume", 0)
        comp = volumes.get(kw, {}).get("competition", 100)
        cpc  = volumes.get(kw, {}).get("cpc", 0)
        if vol == 0: vol = 500
        score = (vol * 0.4) + (cpc * 100) + ((100 - comp) * 10)
        if c["product"] in ["focase", "creatine", "vitamin_d"]:
            score *= 1.3
        # Nudge toward products that actually convert (from GA4 performance data).
        score *= perf_boost.get(c["product"], 1.0)
        scored.append({**c, "volume": vol, "competition": comp, "cpc": cpc, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = scored[:15]

    print("  [Keyword] Claude selecting best keyword...")
    competitor_summary = ""
    if competitor_topics:
        sample = competitor_topics[:30]
        competitor_summary = "Competitor content:\n" + "\n".join(
            f"- {t['title']} ({t['source']})" for t in sample
        )

    candidates_str = "\n".join(
        f"- '{c['keyword']}' | product: {c['product']} | vol: {c['volume']}/mo | score: {int(c['score'])}"
        for c in top_candidates
    )

    published_sample = "\n".join(f"- {p}" for p in published[:60])

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        messages=[{"role": "user", "content": f"""You are the SEO strategist for Holistic Nutrition — selling:
1. Micronized Creatine Monohydrate (physical performance)
2. Focase 2.0 (cognitive performance nootropic)
3. Vitamin D3 + K2 (foundational health/longevity)

Brand: closest thing in supplements to a biotech research institution.
Audience: biohackers, athletes, health-conscious professionals 30-55.

Already published — do NOT pick anything on the same TOPIC as any of these
(even with different wording, angle, or sub-title — we want a genuinely new subject):
{published_sample}

Top candidates:
{candidates_str}

{competitor_summary}

Pick the single best keyword for today. Consider commercial intent, volume vs competition, topic clusters, and month: {datetime.datetime.utcnow().strftime('%B %Y')}.

Return ONLY JSON:
{{"keyword": "exact keyword", "product": "creatine|focase|vitamin_d|general", "reasoning": "one sentence", "estimated_monthly_searches": 0}}"""}]
    )

    raw = msg.content[0].text.strip()
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    def first_fresh():
        """Highest-scored candidate whose topic isn't already published."""
        for c in scored:
            if not _is_dup_topic(c["keyword"], published):
                return c["keyword"], c["product"]
        return None

    try:
        result  = json.loads(raw.strip())
        kw      = result["keyword"]
        product = result["product"]
        # Guard: if Claude still picked a near-duplicate of a published article,
        # override it with the best genuinely-new candidate.
        if _is_dup_topic(kw, published):
            alt = first_fresh()
            if alt:
                print(f"  [Keyword] '{kw}' duplicates a published topic — overriding with '{alt[0]}'")
                return alt
            print(f"  [Keyword] '{kw}' looks duplicate but no fresh alternative found — proceeding")
        print(f"  [Keyword] Selected: '{kw}' ({product})")
        print(f"  [Keyword] Reasoning: {result.get('reasoning', '')}")
        return kw, product
    except Exception as e:
        print(f"  [Keyword] Parse error: {e} — using best fresh scored candidate")
        alt = first_fresh()
        if alt:
            return alt
        top = scored[0] if scored else {"keyword": "creatine monohydrate benefits", "product": "creatine"}
        return top["keyword"], top["product"]

def generate_fresh_keywords(published):
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": f"""Generate 20 new SEO keywords for a supplement brand selling creatine monohydrate, a nootropic blend (Focase), and Vitamin D3+K2.

Already covered:
{chr(10).join(f'- {p}' for p in published[:30])}

Focus on long-tail research questions, ingredient deep-dives, comparisons, population-specific guides, myth-busting.

Return ONLY JSON array:
[{{"keyword": "...", "product": "creatine|focase|vitamin_d|general"}}]"""}]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    try:    return json.loads(raw.strip())
    except: return [{"keyword": "creatine monohydrate complete guide", "product": "creatine"}]

# ── GENERATE ARTICLE ──────────────────────────────────────────────────────────
def generate_article(keyword, product):
    print(f"  [Claude] Writing article: '{keyword}'")
    prod       = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    focase_ctx = f"\n\nFOCASE FORMULA:\n{FOCASE_2_FORMULA}" if product == "focase" else ""

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=5000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content":
            f'Write a Holistic Nutrition research brief targeting: "{keyword}"\n\n'
            f'SEO goal: rank for "{keyword}" and related variants.\n'
            f'Product CTA: conclude with criteria aligning with {prod["name"]}.{focase_ctx}\n\n'
            f'Return ONLY valid JSON.'
        }]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)

    def safe_parse(text):
        for fn in [
            lambda t: json.loads(t),
            lambda t: json.loads(re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', t)),
            lambda t: json.loads(t[t.index('{'):t.rindex('}')+1])
        ]:
            try: return fn(text)
            except: pass
        return None

    result = safe_parse(raw.strip())
    if result: return result

    print("  [Claude] JSON failed — requesting rewrite...")
    fix = client.messages.create(
        model="claude-sonnet-4-5", max_tokens=6000,
        system="Return ONLY valid JSON. No markdown. No preamble.",
        messages=[{"role": "user", "content": "Fix this JSON:\n\n" + raw[:8000]}]
    )
    fixed = fix.content[0].text.strip()
    fixed = re.sub(r'^```[a-z]*\n?', '', fixed)
    fixed = re.sub(r'\n?```$', '', fixed)
    result = safe_parse(fixed.strip())
    if result: return result
    raise ValueError("Could not parse article JSON")

# ── BUILD PHOTO PROMPT ────────────────────────────────────────────────────────
def build_photo_prompt(article, product):
    """Combine article photo_subject with FLUX Dev style. Falls back to curated list if abstract."""
    subject = (article.get("photo_subject") or "").strip()

    bad_signals = ["molecular", "cross-section", "cellular", "atomic", "microscop",
                   "diagram", "illustration", "abstract", "symbolic", "visualization"]
    if not subject or any(sig in subject.lower() for sig in bad_signals):
        subjects = PRODUCT_PHOTO_SUBJECTS.get(product, PRODUCT_PHOTO_SUBJECTS["general"])
        subject  = random.choice(subjects)
        print(f"  [Image] Using curated subject: {subject}")
    else:
        print(f"  [Image] Using article subject: {subject}")

    return f"{subject}. {PHOTO_STYLE}"

# ── IMAGE ─────────────────────────────────────────────────────────────────────
def upload_to_cloudinary(image_bytes, ext="webp"):
    if not all([CLOUDINARY_CLOUD, CLOUDINARY_API_KEY, CLOUDINARY_SECRET]): return None
    try:
        import hashlib
        ts  = str(int(time.time()))
        pid = f"hn-articles/article-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        sig = hashlib.sha1(f"public_id={pid}&timestamp={ts}{CLOUDINARY_SECRET}".encode()).hexdigest()
        r   = requests.post(
            f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD}/image/upload",
            data={"api_key": CLOUDINARY_API_KEY, "timestamp": ts, "public_id": pid, "signature": sig},
            files={"file": (f"image.{ext}", image_bytes, f"image/{ext}")},
            timeout=60
        )
        url = r.json().get("secure_url")
        if url: print(f"  [Cloudinary] {url}")
        return url
    except Exception as e:
        print(f"  [Cloudinary] Error: {e}")
        return None

def generate_hero_image(article, product):
    """Generate hero image using FLUX Dev with a real-world photo prompt."""
    print("  [Image] Generating hero image with FLUX Dev...")
    prod         = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    color        = prod["color"]
    photo_prompt = build_photo_prompt(article, product)

    if REPLICATE_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {REPLICATE_API_KEY}",
                "Content-Type":  "application/json",
                "Prefer":        "wait"
            }

            # FLUX Dev — more realistic than Schnell, better prompt adherence
            r = requests.post(
                "https://api.replicate.com/v1/models/black-forest-labs/flux-dev/predictions",
                headers=headers,
                json={"input": {
                    "prompt":              photo_prompt,
                    "width":               1500,
                    "height":              500,
                    "num_outputs":         1,
                    "output_format":       "webp",
                    "output_quality":      90,
                    "guidance":            3.5,
                    "num_inference_steps": 28,
                    "go_fast":             False
                }},
                timeout=180
            )
            result = r.json()
            print(f"  [FLUX Dev] Status: {result.get('status', 'unknown')}")

            if result.get("status") not in ["succeeded", "failed", "canceled"]:
                poll_url = result.get("urls", {}).get("get")
                if poll_url:
                    for _ in range(60):
                        time.sleep(4)
                        result = requests.get(
                            poll_url, headers={"Authorization": f"Bearer {REPLICATE_API_KEY}"}
                        ).json()
                        print(f"  [FLUX Dev] Polling: {result.get('status', '...')}")
                        if result.get("status") in ["succeeded", "failed", "canceled"]: break

            if result.get("status") == "succeeded":
                output  = result.get("output")
                img_url = output[0] if isinstance(output, list) else output
                print(f"  [FLUX Dev] Success: {img_url}")
                img_r = requests.get(img_url, timeout=30)
                if img_r.status_code == 200:
                    cdn = upload_to_cloudinary(img_r.content, "webp")
                    if cdn: return cdn, cdn
                    print("  [Cloudinary] Retrying upload...")
                    time.sleep(3)
                    cdn = upload_to_cloudinary(img_r.content, "webp")
                    if cdn: return cdn, cdn
                    print("  [Image] Using Replicate URL as fallback (may expire)")
                    return img_url, img_url

            print(f"  [FLUX Dev] Failed: {result.get('error', 'unknown')}")
        except Exception as e:
            print(f"  [FLUX Dev] Error: {e}")

    # SVG fallback
    print("  [Image] Using SVG fallback")
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="500">'
        f'<rect width="1500" height="500" fill="{HN_CREAM}"/>'
        f'<rect width="6" height="500" fill="{color}"/>'
        f'<text x="28" y="38" font-family="Georgia,serif" font-size="11" '
        f'fill="{HN_CHARCOAL}" opacity="0.5" letter-spacing="5">HOLISTIC NUTRITION RESEARCH BRIEF</text>'
        f'</svg>'
    )
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}", svg

# ── CHART ─────────────────────────────────────────────────────────────────────
def generate_chart(chart_data, product):
    labels = chart_data.get("labels", [])
    values = chart_data.get("values", [])
    if not labels or not values: return None

    prod   = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    color  = prod["color"]
    hi_idx = chart_data.get("color_highlight_index", 0)
    suffix = chart_data.get("value_suffix", "")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor("#FAFAF8")
    ax.set_facecolor("#FAFAF8")

    bar_colors = [color if i == hi_idx else HN_BROWN + "99" for i in range(len(labels))]
    bars = ax.bar(labels, values, color=bar_colors, width=0.55, zorder=3)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.02,
                f"{val}{suffix}", ha='center', va='bottom',
                fontsize=11, fontweight='600', color=HN_CHARCOAL)

    ax.set_title(chart_data.get("title", ""), fontsize=13, fontweight='500',
                 color=HN_CHARCOAL, pad=16)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color("#d4cec6")
    ax.spines['bottom'].set_color("#d4cec6")
    ax.yaxis.grid(True, color="#e8e3dc", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    if chart_data.get("subtitle"):
        fig.text(0.5, -0.02, chart_data["subtitle"], ha='center',
                 fontsize=8, color="#9a9590", style='italic')

    fig.text(0.98, 0.02, "holisticnutrition.us", ha='right', fontsize=7, color="#b0a89f")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor="#FAFAF8")
    plt.close()
    buf.seek(0)
    return f"data:image/png;base64,{base64.b64encode(buf.read()).decode()}"

# ── YOUTUBE ───────────────────────────────────────────────────────────────────
def find_youtube_video(query):
    if not YOUTUBE_API_KEY: return None
    try:
        r     = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": query, "type": "video",
                    "maxResults": 3, "key": YOUTUBE_API_KEY},
            timeout=10
        )
        items = r.json().get("items", [])
        if not items: return None
        item   = items[0]
        vid_id = item["id"]["videoId"]
        title  = item["snippet"]["title"]
        ch     = item["snippet"]["channelTitle"]
        return {"embed_html": (
            f'<div style="margin:2rem 0;">'
            f'<p style="font-size:12px;color:#7a7570;margin-bottom:8px;'
            f'text-transform:uppercase;letter-spacing:0.06em;">Related Research</p>'
            f'<div style="position:relative;padding-bottom:56.25%;height:0;'
            f'overflow:hidden;border-radius:8px;">'
            f'<iframe style="position:absolute;top:0;left:0;width:100%;height:100%;" '
            f'src="https://www.youtube.com/embed/{vid_id}" frameborder="0" allowfullscreen></iframe>'
            f'</div>'
            f'<p style="font-size:11px;color:#9a9590;margin-top:6px;">{title} — {ch}</p>'
            f'</div>'
        )}
    except: return None

# ── ASSEMBLE HTML ─────────────────────────────────────────────────────────────
def assemble_html(article, hero_uri, chart_b64, youtube, product):
    prod  = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    color = prod["color"]
    parts = []

    # Suppress Shopify's auto-rendered tags/date line above article body
    parts.append(
        '<style>'
        '.article__tags, .article-template__tags, .article__meta, '
        '.article-template__meta, .article__date, .blog-post__meta, '
        '.blog-article__meta, .article-meta { display: none !important; }'
        '</style>'
    )

    parts.append(
        f'<div style="margin:0 0 36px 0;border-radius:10px;overflow:hidden;">'
        f'<img src="{hero_uri}" alt="{article["title"]}" '
        f'style="width:100%;aspect-ratio:3/1;object-fit:cover;display:block;"/>'
        f'</div>'
    )

    q = article.get("opening_quote", {})
    if q.get("text"):
        parts.append(
            f'<blockquote style="border-left:4px solid {color};padding:16px 24px;'
            f'margin:0 0 32px;background:#faf9f7;border-radius:0 8px 8px 0;">'
            f'<p style="font-size:18px;line-height:1.6;color:#2C2A27;font-style:italic;margin:0 0 8px;">'
            f'"{q["text"]}"</p>'
            f'<cite style="font-size:12px;color:#7a7570;font-style:normal;">'
            f'{q.get("source","")}</cite>'
            f'</blockquote>'
        )

    parts.append(f'''<style>
.hn-article blockquote{{border-left:4px solid {color};background:#faf9f7;padding:20px 24px;margin:28px 0;border-radius:0 8px 8px 0;font-size:17px;line-height:1.6;color:#2C2A27;font-style:italic;}}
.hn-article table{{width:100%;border-collapse:collapse;margin:24px 0;font-size:14px;}}
.hn-article th{{background:{color};color:white;padding:10px 14px;text-align:left;font-weight:500;}}
.hn-article td{{padding:9px 14px;border-bottom:1px solid #e8e3dc;color:#2C2A27;}}
.hn-article tr:nth-child(even) td{{background:#faf9f7;}}
.hn-article ul{{padding-left:20px;margin:12px 0;}}
.hn-article li{{margin-bottom:6px;line-height:1.65;color:#2C2A27;}}
.hn-article h3{{font-size:18px;font-weight:500;color:#2C2A27;margin:28px 0 10px;}}
</style><div class="hn-article">''')

    chart_inserted = False
    for sec in article.get("sections", []):
        heading = sec.get("heading", "")
        html    = sec.get("html", "")
        if heading and heading.lower() != "introduction":
            parts.append(
                f'<h2 style="font-size:22px;font-weight:500;color:#2C2A27;'
                f'margin:40px 0 16px;padding-bottom:8px;border-bottom:1px solid #e8e3dc;">'
                f'{heading}</h2>'
            )
        parts.append(html)
        if not chart_inserted and chart_b64 and "evidence" in heading.lower():
            parts.append(
                f'<div style="margin:28px 0;">'
                f'<img src="{chart_b64}" alt="Study data chart" '
                f'style="width:100%;max-width:720px;display:block;margin:0 auto;border-radius:8px;"/>'
                f'</div>'
            )
            chart_inserted = True
        if youtube and youtube.get("embed_html") and "clinical" in heading.lower():
            parts.append(youtube["embed_html"])

    parts.append("</div>")

    # Rotating CTA button copy — A/B test across articles
    # Track which variant converts in Shopify analytics / UTM params
    prod_short = {"creatine": "Creatine", "focase": "Focase", "vitamin_d": "D3+K2", "general": "Holistic Nutrition"}.get(product, "Holistic Nutrition")
    CTA_VARIANTS = [
        ("Shop Now", "?utm_source=blog&utm_content=cta_shop_now"),
        (f"See Our {prod_short} Formula", "?utm_source=blog&utm_content=cta_see_formula"),
        (f"Try {prod_short}", "?utm_source=blog&utm_content=cta_try_product"),
        ("Learn More", "?utm_source=blog&utm_content=cta_learn_more"),
    ]
    btn_label, btn_utm = random.choice(CTA_VARIANTS)

    parts.append(
        f'<div style="margin:48px 0 32px;padding:28px 32px;background:#faf9f7;'
        f'border-radius:12px;border:1px solid #e8e3dc;border-left:4px solid {color};">'
        f'<p style="margin:0 0 16px;font-size:15px;color:#2C2A27;line-height:1.7;">'
        f'{prod["cta"]}</p>'
        f'<a href="{prod["cta_url"]}{btn_utm}" style="display:inline-block;background:{color};'
        f'color:white;padding:11px 24px;border-radius:6px;text-decoration:none;'
        f'font-size:13px;font-weight:500;letter-spacing:0.02em;">{btn_label} &#x2192;</a>'
        f'</div>'
    )

    parts.append(
        f'<div style="margin:24px 0;padding:16px 20px;background:#f5f3f0;'
        f'border-radius:8px;border:1px solid #e8e3dc;">'
        f'<p style="margin:0;font-size:12px;color:#7a7570;line-height:1.6;">'
        f'This article is part of the '
        f'<a href="https://holisticnutrition.us/pages/research-library" '
        f'style="color:{color};text-decoration:none;font-weight:500;">'
        f'Holistic Nutrition Research Library</a>. '
        f'Browse all research briefs and ingredient factsheets.</p>'
        f'</div>'
    )

    refs = article.get("references", [])
    if refs:
        parts.append(
            f'<div style="margin-top:48px;padding-top:24px;border-top:1px solid #e8e3dc;">'
            f'<h2 style="font-size:14px;font-weight:500;color:#7a7570;'
            f'text-transform:uppercase;letter-spacing:0.08em;margin:0 0 16px;">References</h2>'
            + "".join(
                f'<p style="font-size:12px;color:#7a7570;margin:4px 0;line-height:1.6;">{r}</p>'
                for r in refs
            )
            + '</div>'
        )

    return "\n".join(parts)

# ── NOTIFY LIBRARY ────────────────────────────────────────────────────────────
def notify_library(title, article_url, category):
    if not ZAPIER_LIBRARY_HOOK:
        print("  [Library] No webhook — skipping")
        return
    try:
        r = requests.post(ZAPIER_LIBRARY_HOOK, json={
            "article_title":  title,
            "article_url":    article_url,
            "category":       category,
            "published_date": datetime.datetime.utcnow().strftime("%B %d, %Y")
        }, timeout=30)
        print(f"  [Library] Status: {r.status_code}")
    except Exception as e:
        print(f"  [Library] Error: {e}")

# ── PUBLISH ───────────────────────────────────────────────────────────────────
def publish(title, body_html, keyword, product, meta_title, meta_description):
    print("  [Zapier] Publishing to Shopify...")
    r = requests.post(ZAPIER_WEBHOOK, json={
        "title":            title,
        "body_html":        body_html,
        "tags":             f"{product}, holistic nutrition, research brief, {keyword[:50]}",
        "meta_title":       meta_title,
        "meta_description": meta_description,
        "published":        True,
        "keyword":          keyword
    }, timeout=30)
    print(f"  [Zapier] Status: {r.status_code}")
    try:    return r.json()
    except: return {"status": r.status_code}

# ── MAIN ──────────────────────────────────────────────────────────────────────
def run():
    start = datetime.datetime.utcnow()
    print(f"\n{'='*65}")
    print(f"  HN CONTENT AGENT v5 — {start.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  FLUX Dev + Firecrawl + DataForSEO + Claude Autonomous")
    print(f"{'='*65}")

    # Preflight — confirm Supabase access BEFORE generating or publishing anything.
    # The agent's dedup memory lives in Supabase (get_published_topics). If we can't
    # reach it, abort loudly here rather than publish near-duplicate articles to the
    # live blog with no record of them. This makes a bad SUPABASE_KEY a red workflow.
    print("\n  Preflight — checking Supabase access...")
    try:
        seen = get_published_topics()
        print(f"    Supabase OK — {len(seen)} published topics visible for dedup")
    except Exception as e:
        print(f"\n  FATAL: cannot reach Supabase — aborting before publish.")
        print(f"  Fix the SUPABASE_KEY GitHub Actions secret (valid service_role key).")
        print(f"  Detail: {e}")
        raise

    print("\n  Step 0 — Competitive keyword research...")
    keyword, product = pick_best_keyword()

    print(f"\n  Keyword : {keyword}")
    print(f"  Product : {product}")

    rec = insert_article({
        "title":   f"Drafting — {keyword}",
        "keyword": keyword,
        "product": product,
        "status":  "draft"
    })
    aid = rec["id"] if rec else None

    try:
        print("\n  Step 1/5 — Generating article...")
        art = generate_article(keyword, product)
        print(f"    Title : {art['title']}")
        print(f"    Words : {art.get('word_count', '?')}")

        print("\n  Step 2/5 — Creating hero image (FLUX Dev)...")
        hero_uri, _ = generate_hero_image(art, product)

        print("\n  Step 3/5 — Rendering chart...")
        chart_b64 = generate_chart(art["chart"], product) if art.get("chart") else None

        print("\n  Step 4/5 — Finding YouTube video...")
        yt = find_youtube_video(art["youtube_query"]) if art.get("youtube_query") else None

        print("\n  Step 5/5 — Assembling and publishing...")
        body_html = assemble_html(art, hero_uri, chart_b64, yt, product)
        result    = publish(
            art["title"], body_html, keyword, product,
            art.get("meta_title", art["title"][:55]),
            art.get("meta_description", "")
        )

        title_slug  = re.sub(r'[^a-z0-9]+', '-', art["title"].lower()).strip('-')
        shopify_url = None
        if isinstance(result, dict):
            candidate = result.get("url") or result.get("shopify_url") or result.get("blog_url")
            if candidate and "research-library" not in candidate and "holisticnutrition.us" in candidate:
                shopify_url = candidate
        if not shopify_url:
            shopify_url = f"https://holisticnutrition.us/blogs/research-studies/{title_slug}"

        print(f"  [URL] {shopify_url}")

        if aid:
            update_article(aid, {
                "title":            art["title"],
                "keyword":          keyword,
                "meta_title":       art.get("meta_title", ""),
                "meta_description": art.get("meta_description", ""),
                "word_count":       art.get("word_count", 0),
                "status":           "published",
                "published_at":     datetime.datetime.utcnow().isoformat(),
                "shopify_url":      shopify_url
            })

        prod_data = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
        notify_library(art["title"], shopify_url, prod_data["category"])

        duration = int((datetime.datetime.utcnow() - start).total_seconds())
        log_run("completed", f"Published: {art['title']}", 1, duration=duration)

        print(f"\n{'='*65}")
        print(f"  PUBLISHED : {art['title']}")
        print(f"  Keyword   : {keyword}")
        print(f"  Product   : {product}")
        print(f"  Duration  : {duration}s")
        print(f"  URL       : {shopify_url}")
        print(f"{'='*65}\n")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        # Don't let a follow-up Supabase failure mask the original error.
        try:
            if aid: update_article(aid, {"status": "failed", "keyword": keyword})
        except Exception as e2:
            print(f"  [warn] could not mark article failed: {e2}")
        log_run("failed", str(e), 0, errors=str(e))  # already best-effort
        raise

if __name__ == "__main__":
    run()
