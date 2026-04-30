#!/usr/bin/env python3
"""
Holistic Nutrition Content Agent v2
Keyword → Research Brief → Brand Image → Chart → YouTube → Shopify → Supabase
"""

import os, json, random, requests, datetime, base64, io, re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from anthropic import Anthropic

# ── CONFIG ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL      = "https://ykzkivpcojjzmbbnuewj.supabase.co"
SUPABASE_KEY      = os.environ.get("SUPABASE_KEY", "")
ZAPIER_WEBHOOK    = os.environ.get("ZAPIER_WEBHOOK", "")
YOUTUBE_API_KEY   = os.environ.get("YOUTUBE_API_KEY", "")  # optional — add later

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# HN Brand Colors
HN_BROWN   = "#A3988B"
HN_CREAM   = "#E8E3DC"
HN_CHARCOAL= "#2C2A27"
HN_GREEN   = "#048142"
HN_RED     = "#D2042D"
HN_BLUE    = "#24418F"
HN_AMBER   = "#C8893A"
HN_GOLD    = "#C9A84C"

PRODUCT_MAP = {
    "creatine": {
        "name": "Micronized Creatine Monohydrate",
        "url":  "https://holisticnutrition.us/products/creatine-monohydrate",
        "color": HN_RED,
        "cta":  "Holistic Nutrition's Micronized Creatine Monohydrate is formulated to the standard outlined in this brief — single-ingredient, micronized, third-party tested.",
        "cta_url": "https://holisticnutrition.us/products/creatine-monohydrate"
    },
    "focase": {
        "name": "Focase Cognition Support",
        "url":  "https://holisticnutrition.us/products/focase",
        "color": HN_BLUE,
        "cta":  "Focase is Holistic Nutrition's cognitive performance formula — combining the ingredients reviewed in this brief at clinically informed doses.",
        "cta_url": "https://holisticnutrition.us/products/focase"
    },
    "vitamin_d": {
        "name": "Vitamin D3 + K2",
        "url":  "https://holisticnutrition.us/products/vitamin-d3-k2",
        "color": HN_AMBER,
        "cta":  "Holistic Nutrition's Vitamin D3 + K2 pairs D3 with MK-7, calcium, and BioPerine — addressing the full mechanism reviewed here.",
        "cta_url": "https://holisticnutrition.us/products/vitamin-d3-k2"
    },
    "general": {
        "name": "Holistic Nutrition",
        "url":  "https://holisticnutrition.us",
        "color": HN_BROWN,
        "cta":  "Explore Holistic Nutrition's research-driven supplement lineup.",
        "cta_url": "https://holisticnutrition.us"
    }
}

# ── ARTICLE SYSTEM PROMPT ────────────────────────────────────────────────────
ARTICLE_SYSTEM_PROMPT = """You are the lead research writer for Holistic Nutrition — a science-driven supplement company positioned as the closest thing in the supplement industry to a biotech research institution.

BRAND VOICE:
- Authoritative, precise, educational — never cold, never hype-driven
- Write like a researcher who genuinely wants the reader to understand their own biology
- Confident without arrogance. State what evidence supports clearly and cite it. Acknowledge limitations honestly.
- Never use motivational language, wellness speak, or marketing filler
- Respect the reader's intelligence — explain mechanisms within fully developed paragraphs

ARTICLE STRUCTURE (follow exactly, in this order):
1. Title — research brief style, specific and clinically grounded, not clickbait
2. Opening quote — from a real peer-reviewed study, institution, or named researcher that establishes the stakes
3. Introduction — 2-3 developed paragraphs: the problem, why it matters, what this brief covers
4. What is [X] — foundational section explaining the compound, mechanism, or condition
5. Evidence & Mechanisms — the core science with inline citations [1] [2] [3]
6. Clinical Considerations — practical application broken into relevant subpopulations or use cases
7. Conclusion — synthesizes findings, establishes selection criteria naturally without being promotional
8. [CTA_PLACEHOLDER]
9. References — AMA format numbered list

FORMATTING RULES:
- Fully developed paragraphs only — never single or two-sentence standalone paragraphs
- Inline citations as bracketed numbers [1] [2] — never author-year in body text
- No emojis, no bullet points in article body, no callout boxes, no "in plain terms" labels
- Section headings as plain text (will be wrapped in <h2> tags)
- Minimum 1400 words, target 1800-2200 words
- Health claims must use compliant language: "supports", "associated with", "may help", "evidence suggests" — never "treats", "cures", "prevents"

CHART DATA — include this section in your JSON:
Identify ONE key quantitative finding from the research that would visualize well as a simple bar or comparison chart. Provide the data needed to render it.

YOUTUBE SEARCH — include this section in your JSON:
Suggest ONE specific YouTube search query that would surface a high-quality educational video (researcher, physician, or academic lecture) relevant to this topic. Not a product review, not a supplement brand video.

OUTPUT — return ONLY a valid JSON object with exactly these fields:
{
  "title": "...",
  "photo_prompt": "Cinematic editorial photograph, natural earth tones, [specific scene relevant to article topic]. Warm amber and cream palette, intentional atmospheric lighting, no lab coats, no product bottles, no text.",
  "meta_title": "... max 55 chars",
  "meta_description": "... max 150 chars",
  "opening_quote": { "text": "...", "source": "..." },
  "sections": [
    { "heading": "Introduction", "html": "<p>...</p><p>...</p>" },
    { "heading": "What is X", "html": "<p>...</p>" },
    { "heading": "Evidence and Mechanisms", "html": "<p>...</p>" },
    { "heading": "Clinical Considerations", "html": "<p>...</p>" },
    { "heading": "Conclusion", "html": "<p>...</p>" }
  ],
  "chart": {
    "type": "bar",
    "title": "Chart title here",
    "subtitle": "Source: Author et al., Journal, Year",
    "labels": ["Label 1", "Label 2", "Label 3"],
    "values": [0.0, 0.0, 0.0],
    "value_suffix": "%",
    "color_highlight_index": 0
  },
  "youtube_query": "specific search query here",
  "references": ["[1] Author et al. Title. Journal. Year;Vol:Pages.", "..."],
  "word_count": 0
}

Return ONLY valid JSON. No markdown fences. No preamble. No explanation."""

# ── SUPABASE ─────────────────────────────────────────────────────────────────
def sb(method, path, **kwargs):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    r = getattr(requests, method)(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, **kwargs)
    try: return r.json()
    except: return {}

def get_next_keyword():
    rows = sb("get", "keywords", params={
        "status": "eq.queued",
        "order": "priority.asc,created_at.asc",
        "limit": "5"
    })
    if not rows: return None
    return random.choice(rows[:min(3, len(rows))])

def mark_keyword(kid, status):
    sb("patch", f"keywords?id=eq.{kid}", json={"status": status})

def log_run(status, message, articles=0, errors=None, duration=None):
    sb("post", "agent_runs", json={
        "agent_name": "Content Agent",
        "status": status,
        "message": message,
        "articles_processed": articles,
        "errors": errors,
        "duration_seconds": duration,
        "completed_at": datetime.datetime.utcnow().isoformat()
    })

def insert_article(data):
    rows = sb("post", "articles", json=data)
    return rows[0] if isinstance(rows, list) and rows else None

def update_article(aid, data):
    sb("patch", f"articles?id=eq.{aid}", json=data)

# ── GENERATE ARTICLE ─────────────────────────────────────────────────────────
def generate_article(keyword, product):
    print(f"  [Claude] Writing article for: '{keyword}'")
    prod = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=5000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f'Write a Holistic Nutrition research brief on: "{keyword}"\n\nProduct context: conclude with criteria that align with {prod["name"]}.\n\nReturn ONLY valid JSON.'
        }]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    return json.loads(raw.strip())

# ── GENERATE IMAGE (Claude vision + base64) ───────────────────────────────────
def generate_hero_image(photo_prompt, product):
    """
    Generate a branded hero image using Claude's image generation capability.
    Falls back to a styled SVG placeholder if generation unavailable.
    """
    print(f"  [Image] Generating hero image...")
    prod = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    color = prod["color"]

    # Create a high-quality SVG placeholder branded to HN
    # (Replace this with FLUX/DALL-E API call when you add those keys)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="600" viewBox="0 0 1200 600">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{HN_CREAM};stop-opacity:1"/>
      <stop offset="60%" style="stop-color:#d4cec6;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:{HN_BROWN};stop-opacity:0.4"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{color};stop-opacity:0.15"/>
      <stop offset="100%" style="stop-color:{color};stop-opacity:0"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="600" fill="url(#bg)"/>
  <rect width="1200" height="600" fill="url(#accent)"/>
  <rect x="0" y="0" width="6" height="600" fill="{color}"/>
  <rect x="0" y="560" width="1200" height="2" fill="{HN_BROWN}" opacity="0.3"/>
  <text x="60" y="80" font-family="Georgia, serif" font-size="11" fill="{HN_CHARCOAL}" opacity="0.5" letter-spacing="4">HOLISTIC NUTRITION · RESEARCH BRIEF</text>
  <text x="60" y="200" font-family="Georgia, serif" font-size="42" fill="{HN_CHARCOAL}" font-weight="400" opacity="0.9">Science you can take.</text>
  <text x="60" y="580" font-family="Georgia, serif" font-size="10" fill="{HN_CHARCOAL}" opacity="0.4">holisticnutrition.us</text>
  <circle cx="950" cy="300" r="180" fill="{color}" opacity="0.06"/>
  <circle cx="1050" cy="150" r="80" fill="{HN_GOLD}" opacity="0.08"/>
</svg>"""

    # Encode SVG as base64 data URI
    svg_b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{svg_b64}", svg

# ── GENERATE CHART ────────────────────────────────────────────────────────────
def generate_chart(chart_data, product):
    """Render a branded matplotlib chart and return as base64 PNG."""
    print(f"  [Chart] Rendering: {chart_data.get('title','chart')}")
    prod   = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    color  = prod["color"]
    labels = chart_data.get("labels", [])
    values = chart_data.get("values", [])
    hi_idx = chart_data.get("color_highlight_index", 0)
    suffix = chart_data.get("value_suffix", "")

    if not labels or not values:
        return None

    fig, ax = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor("#FAFAF8")
    ax.set_facecolor("#FAFAF8")

    bar_colors = [color if i == hi_idx else HN_BROWN + "99" for i in range(len(labels))]
    bars = ax.bar(labels, values, color=bar_colors, width=0.55, zorder=3)

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + max(values)*0.02,
                f"{val}{suffix}",
                ha='center', va='bottom',
                fontsize=11, fontweight='600',
                color=HN_CHARCOAL, fontfamily='DejaVu Sans')

    # Styling
    ax.set_title(chart_data.get("title", ""), fontsize=13, fontweight='500',
                 color=HN_CHARCOAL, pad=16, fontfamily='DejaVu Sans')
    ax.set_ylabel(f"Value ({suffix})" if suffix else "Value",
                  fontsize=9, color="#7a7570")
    ax.tick_params(colors=HN_CHARCOAL, labelsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color("#d4cec6")
    ax.spines['bottom'].set_color("#d4cec6")
    ax.yaxis.grid(True, color="#e8e3dc", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    subtitle = chart_data.get("subtitle", "")
    if subtitle:
        fig.text(0.5, -0.02, subtitle, ha='center', fontsize=8,
                 color="#9a9590", style='italic')

    # HN watermark
    fig.text(0.98, 0.02, "holisticnutrition.us",
             ha='right', fontsize=7, color="#b0a89f")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return f"data:image/png;base64,{b64}"

# ── YOUTUBE SEARCH ────────────────────────────────────────────────────────────
def find_youtube_video(query):
    """Search YouTube for a relevant educational video."""
    print(f"  [YouTube] Searching: '{query}'")
    if not YOUTUBE_API_KEY:
        # Fallback: construct a search URL without API
        encoded = requests.utils.quote(query)
        return {
            "search_url": f"https://www.youtube.com/results?search_query={encoded}",
            "embed_html": None,
            "note": "Add YOUTUBE_API_KEY to enable auto-embedding"
        }
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 3,
                "videoDuration": "medium",
                "key": YOUTUBE_API_KEY
            },
            timeout=10
        )
        items = r.json().get("items", [])
        if not items:
            return None
        # Pick first result
        item    = items[0]
        vid_id  = item["id"]["videoId"]
        title   = item["snippet"]["title"]
        channel = item["snippet"]["channelTitle"]
        return {
            "video_id": vid_id,
            "title": title,
            "channel": channel,
            "embed_html": f'<div style="margin:2rem 0;"><p style="font-size:12px;color:#7a7570;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.06em;">Related Research</p><div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:8px;"><iframe style="position:absolute;top:0;left:0;width:100%;height:100%;" src="https://www.youtube.com/embed/{vid_id}" frameborder="0" allowfullscreen></iframe></div><p style="font-size:11px;color:#9a9590;margin-top:6px;">{title} — {channel}</p></div>'
        }
    except Exception as e:
        print(f"    YouTube error: {e}")
        return None

# ── ASSEMBLE HTML ─────────────────────────────────────────────────────────────
def assemble_html(article, hero_img_uri, chart_b64, youtube, product):
    prod = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    color = prod["color"]
    parts = []

    # Hero image
    parts.append(f'<div style="margin:-20px -20px 32px -20px;"><img src="{hero_img_uri}" alt="{article["title"]}" style="width:100%;height:400px;object-fit:cover;display:block;"/></div>')

    # Opening quote
    q = article.get("opening_quote", {})
    if q.get("text"):
        parts.append(f'''<blockquote style="border-left:4px solid {color};padding:16px 24px;margin:0 0 32px;background:#faf9f7;border-radius:0 8px 8px 0;">
<p style="font-size:18px;line-height:1.6;color:#2C2A27;font-style:italic;margin:0 0 8px;">"{q["text"]}"</p>
<cite style="font-size:12px;color:#7a7570;font-style:normal;">{q.get("source","")}</cite>
</blockquote>''')

    # Sections
    sections = article.get("sections", [])
    chart_inserted = False
    for i, sec in enumerate(sections):
        heading = sec.get("heading", "")
        html    = sec.get("html", "")
        if heading and heading.lower() != "introduction":
            parts.append(f'<h2 style="font-size:22px;font-weight:500;color:#2C2A27;margin:40px 0 16px;padding-bottom:8px;border-bottom:1px solid #e8e3dc;">{heading}</h2>')
        parts.append(html)
        # Insert chart after Evidence section
        if not chart_inserted and chart_b64 and "evidence" in heading.lower():
            parts.append(f'<div style="margin:28px 0;"><img src="{chart_b64}" alt="Study data chart" style="width:100%;max-width:720px;display:block;margin:0 auto;border-radius:8px;"/></div>')
            chart_inserted = True
        # Insert YouTube after Clinical section
        if youtube and youtube.get("embed_html") and "clinical" in heading.lower():
            parts.append(youtube["embed_html"])

    # CTA
    parts.append(f'''<div style="margin:48px 0 32px;padding:28px 32px;background:#faf9f7;border-radius:12px;border:1px solid #e8e3dc;border-left:4px solid {color};">
<p style="margin:0 0 12px;font-size:15px;color:#2C2A27;line-height:1.7;">{prod["cta"]}</p>
<a href="{prod["cta_url"]}" style="display:inline-block;background:{color};color:white;padding:10px 22px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:500;">View the product →</a>
</div>''')

    # References
    refs = article.get("references", [])
    if refs:
        ref_html = "".join(f'<p style="font-size:12px;color:#7a7570;margin:4px 0;line-height:1.6;">{r}</p>' for r in refs)
        parts.append(f'<div style="margin-top:48px;padding-top:24px;border-top:1px solid #e8e3dc;"><h2 style="font-size:14px;font-weight:500;color:#7a7570;text-transform:uppercase;letter-spacing:0.08em;margin:0 0 16px;">References</h2>{ref_html}</div>')

    return "\n".join(parts)

# ── PUBLISH TO SHOPIFY VIA ZAPIER ─────────────────────────────────────────────
def publish(title, body_html, keyword, product, meta_title, meta_description):
    print(f"  [Zapier] Publishing to Shopify...")
    payload = {
        "title":            title,
        "body_html":        body_html,
        "tags":             f"{product}, holistic nutrition, research brief",
        "meta_title":       meta_title,
        "meta_description": meta_description,
        "published":        True,
        "keyword":          keyword
    }
    r = requests.post(ZAPIER_WEBHOOK, json=payload, timeout=30)
    print(f"  [Zapier] Status: {r.status_code}")
    try:    return r.json()
    except: return {"status": r.status_code}

# ── MAIN ──────────────────────────────────────────────────────────────────────
def run():
    start = datetime.datetime.utcnow()
    print(f"\n{'='*65}")
    print(f"  HN CONTENT AGENT — {start.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*65}")

    kw_row = get_next_keyword()
    if not kw_row:
        print("  No queued keywords. Exiting.")
        log_run("completed", "No queued keywords available")
        return

    keyword = kw_row["keyword"]
    product = kw_row.get("product", "general")
    kid     = kw_row["id"]
    print(f"\n  Keyword : {keyword}")
    print(f"  Product : {product}")

    mark_keyword(kid, "in_progress")

    rec = insert_article({
        "title":   f"Drafting — {keyword}",
        "keyword": keyword,
        "product": product,
        "status":  "draft"
    })
    aid = rec["id"] if rec else None

    try:
        # 1. Generate article JSON
        print("\n  Step 1/5 — Generating article...")
        art = generate_article(keyword, product)
        print(f"    Title : {art['title']}")
        print(f"    Words : {art.get('word_count', '?')}")

        # 2. Generate hero image
        print("\n  Step 2/5 — Creating hero image...")
        hero_uri, _ = generate_hero_image(art.get("photo_prompt", ""), product)

        # 3. Generate chart
        print("\n  Step 3/5 — Rendering chart...")
        chart_b64 = None
        if art.get("chart"):
            chart_b64 = generate_chart(art["chart"], product)

        # 4. Find YouTube video
        print("\n  Step 4/5 — Finding YouTube video...")
        yt = None
        if art.get("youtube_query"):
            yt = find_youtube_video(art["youtube_query"])

        # 5. Assemble + publish
        print("\n  Step 5/5 — Assembling and publishing...")
        body_html = assemble_html(art, hero_uri, chart_b64, yt, product)

        result = publish(
            title=art["title"],
            body_html=body_html,
            keyword=keyword,
            product=product,
            meta_title=art.get("meta_title", art["title"][:55]),
            meta_description=art.get("meta_description", "")
        )

        shopify_url = result.get("url") or result.get("shopify_url") if isinstance(result, dict) else None

        if aid:
            update_article(aid, {
                "title":            art["title"],
                "meta_title":       art.get("meta_title", ""),
                "meta_description": art.get("meta_description", ""),
                "word_count":       art.get("word_count", 0),
                "status":           "published",
                "published_at":     datetime.datetime.utcnow().isoformat(),
                "shopify_url":      shopify_url
            })

        mark_keyword(kid, "published")
        duration = int((datetime.datetime.utcnow() - start).total_seconds())
        log_run("completed", f"Published: {art['title']}", 1, duration=duration)

        print(f"\n{'='*65}")
        print(f"  ✓ PUBLISHED: {art['title']}")
        print(f"  Duration  : {duration}s")
        if shopify_url: print(f"  URL       : {shopify_url}")
        print(f"{'='*65}\n")

    except Exception as e:
        print(f"\n  ✗ ERROR: {e}")
        if aid: update_article(aid, {"status": "failed"})
        mark_keyword(kid, "queued")
        log_run("failed", str(e), 0, errors=str(e))
        raise

if __name__ == "__main__":
    run()
