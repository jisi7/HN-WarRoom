#!/usr/bin/env python3
"""
Holistic Nutrition Content Agent v2
Keyword → Research Brief → Brand Image → Chart → YouTube → Shopify → Supabase → Library Update
"""

import os, json, random, requests, datetime, base64, io, re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from anthropic import Anthropic

# ── CONFIG ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY    = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL         = "https://ykzkivpcojjzmbbnuewj.supabase.co"
SUPABASE_KEY         = os.environ.get("SUPABASE_KEY", "")
ZAPIER_WEBHOOK       = os.environ.get("ZAPIER_WEBHOOK", "")
ZAPIER_LIBRARY_HOOK  = os.environ.get("ZAPIER_LIBRARY_HOOK", "")
YOUTUBE_API_KEY      = os.environ.get("YOUTUBE_API_KEY", "")
REPLICATE_API_KEY    = os.environ.get("REPLICATE_API_KEY", "")
SHOPIFY_TOKEN        = os.environ.get("SHOPIFY_TOKEN", "")
SHOPIFY_STORE        = os.environ.get("SHOPIFY_STORE", "natures-premier.myshopify.com")
CLOUDINARY_CLOUD     = os.environ.get("CLOUDINARY_CLOUD", "")
CLOUDINARY_API_KEY   = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_SECRET    = os.environ.get("CLOUDINARY_SECRET", "")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# HN Brand Colors
HN_BROWN    = "#A3988B"
HN_CREAM    = "#E8E3DC"
HN_CHARCOAL = "#2C2A27"
HN_GREEN    = "#048142"
HN_RED      = "#D2042D"
HN_BLUE     = "#24418F"
HN_AMBER    = "#C8893A"
HN_GOLD     = "#C9A84C"

PRODUCT_MAP = {
    "creatine": {
        "name":      "Micronized Creatine Monohydrate",
        "url":       "https://holisticnutrition.us/products/creatine-monohydrate",
        "color":     HN_RED,
        "category":  "Physical Performance",
        "cta":       "Holistic Nutrition's Micronized Creatine Monohydrate is formulated to the standard outlined in this brief — single-ingredient, micronized, third-party tested.",
        "cta_url":   "https://holisticnutrition.us/products/creatine-monohydrate"
    },
    "focase": {
        "name":      "Focase Cognition Support",
        "url":       "https://holisticnutrition.us/products/focase",
        "color":     HN_BLUE,
        "category":  "Cognitive Performance",
        "cta":       "Focase is Holistic Nutrition's cognitive performance formula — combining the ingredients reviewed in this brief at clinically informed doses. Focase 2.0 contains L-Tyrosine, Ashwagandha, Alpha-GPC, L-Theanine, Phosphatidylserine, Rhodiola, Omega-3s, methylated B-vitamins (B6 as P5P, Folate as 5-MTHF, B12 as Methylcobalamin), Vitamin D3, Caffeine, and BioPerine.",
        "cta_url":   "https://holisticnutrition.us/products/focase"
    },
    "vitamin_d": {
        "name":      "Vitamin D3 + K2",
        "url":       "https://holisticnutrition.us/products/vitamin-d3-k2",
        "color":     HN_AMBER,
        "category":  "Foundational Health and Longevity",
        "cta":       "Holistic Nutrition's Vitamin D3 + K2 pairs D3 with MK-7, calcium, and BioPerine — addressing the full mechanism reviewed here.",
        "cta_url":   "https://holisticnutrition.us/products/vitamin-d3-k2"
    },
    "general": {
        "name":      "Holistic Nutrition",
        "url":       "https://holisticnutrition.us",
        "color":     HN_BROWN,
        "category":  "Research Briefs",
        "cta":       "Explore Holistic Nutrition's research-driven supplement lineup.",
        "cta_url":   "https://holisticnutrition.us"
    }
}

# ── FOCASE 2.0 FORMULA ───────────────────────────────────────────────────────
FOCASE_2_FORMULA = """
Focase 2.0 — Supplement Facts (Serving Size: ~1 Scoop / 4.1g, 30 Servings)

Active Ingredients per serving:
- Vitamin D3 (as Cholecalciferol): 50mcg (2,000 IU)
- Vitamin B6 (as Pyridoxal-5-Phosphate): 5mg
- Folate (as 5-Methyltetrahydrofolate Calcium): 460mcg DFE
- Vitamin B12 (as Methylcobalamin): 25mcg
- Omega-3 Fish Oil Powder (Omega 3-6-9 Fatty Acid): 1,000mg
- L-Tyrosine: 400mg
- Ashwagandha Powder (Withania somnifera, Root): 250mg
- Alpha GPC 50% (L-Alpha-glyceryl phosphorylcholine): 200mg
- L-Theanine: 200mg
- Phosphatidylserine Powder 20%: 200mg
- Rhodiola Root Powder (Rhodiola rosea L., Root) [std to 3% Rosavins, 1% Salidrosides]: 150mg
- Caffeine Anhydrous: 75mg
- Black Pepper Fruit Extract 95% (Piper nigrum): 7mg

Other Ingredients: Natural Flavors, Malic Acid, Silica, Stevia Leaf Extract, Thaumatin Protein

Formula notes:
- Uses active/methylated B vitamin forms (P5P, Methylcobalamin, Methylfolate)
- Caffeine:L-Theanine ratio 75:200mg (clinically studied calm-focus ratio)
- BioPerine enhances absorption of fat-soluble nutrients
- NO Lion's Mane in current formula
- Sweetened with Stevia + Thaumatin, no artificial sweeteners
"""

# ── ARTICLE SYSTEM PROMPT ────────────────────────────────────────────────────
ARTICLE_SYSTEM_PROMPT = """You are the lead research writer for Holistic Nutrition — a science-driven supplement company positioned as the closest thing in the supplement industry to a biotech research institution.

BRAND VOICE:
- Authoritative, precise, educational — never cold, never hype-driven
- Write like a researcher who genuinely wants the reader to understand their own biology
- Confident without arrogance. State what evidence supports clearly and cite it. Acknowledge limitations honestly.
- Never use motivational language, wellness speak, or marketing filler
- Respect the reader's intelligence but make every article self-contained — never assume prior knowledge

CRITICAL FORMATTING PHILOSOPHY:
Every article must be readable by both a PhD and a first-time supplement buyer. Achieve this by:
- Mixing developed paragraphs (3-5 sentences) with selective bullet points where lists genuinely aid clarity
- Never writing more than 3 consecutive long paragraphs without a visual break (subheading, bullet list, or pull quote)
- Using bullet points for: ingredient comparisons, dosing protocols, population-specific guidance, key study findings
- Using paragraphs for: mechanism explanations, contextual background, nuanced analysis
- Each article must be completely self-contained — a new reader learns everything they need without reading previous articles

ARTICLE STRUCTURE (follow exactly, in this order):
1. Title — research brief style, specific and clinically grounded, not clickbait
2. Opening quote — from a real peer-reviewed study, institution, or named researcher
3. Introduction — 2 paragraphs establishing why this topic matters right now
4. What is [X]? — foundational section, 2-3 paragraphs, assumes zero prior knowledge
5. What is [X] used for? — practical applications section using a mix of prose and bullet points
6. Evidence and Mechanisms — core science with inline citations [1] [2] [3]
7. Clinical Considerations — practical guidance broken into subpopulations with H3 subheadings
8. How to Choose [X] — selection criteria (3-5 bullets)
9. Conclusion — 1-2 paragraphs
10. [CTA_PLACEHOLDER]
11. References — AMA format numbered list

VISUAL ELEMENTS:
- At least ONE pull quote block per article
- At least ONE comparison or summary table in HTML
- Bullet points in at least 3 sections
- Subheadings within Clinical Considerations

HTML FORMATTING:
- <h2> for main section headings
- <h3> for subheadings within sections
- <p> for paragraphs
- <ul><li> for bullet lists
- <blockquote> for pull quotes
- <table> for comparison tables
- Inline citations as [1] [2]
- Health claims: "supports", "associated with", "may help", "evidence suggests"
- Minimum 1600 words, target 2000-2400 words
- CRITICAL JSON RULE: Never use backslashes anywhere in HTML. No escape sequences inside string values.

OUTPUT — return ONLY a valid JSON object:
{
  "title": "...",
  "photo_prompt": "Cinematic close-up editorial photograph of [specific natural element]. Natural earth tones, warm amber and green palette, shallow depth of field, atmospheric natural lighting, no text, no people, no product bottles.",
  "meta_title": "... max 55 chars",
  "meta_description": "... max 150 chars",
  "opening_quote": { "text": "...", "source": "..." },
  "sections": [
    { "heading": "Introduction", "html": "<p>...</p>" },
    { "heading": "What is [X]?", "html": "<p>...</p>" },
    { "heading": "What is [X] Used For?", "html": "<p>...</p><ul><li>...</li></ul>" },
    { "heading": "Evidence and Mechanisms", "html": "<p>...</p><blockquote>...</blockquote>" },
    { "heading": "Clinical Considerations", "html": "<h3>...</h3><p>...</p><ul><li>...</li></ul>" },
    { "heading": "How to Choose [X]", "html": "<ul><li>...</li></ul>" },
    { "heading": "Conclusion", "html": "<p>...</p>" }
  ],
  "chart": {
    "type": "bar",
    "title": "...",
    "subtitle": "Source: Author et al., Journal, Year",
    "labels": ["...", "..."],
    "values": [0.0, 0.0],
    "value_suffix": "%",
    "color_highlight_index": 0
  },
  "youtube_query": "...",
  "references": ["[1] ...", "[2] ..."],
  "word_count": 0
}

Return ONLY valid JSON. No markdown fences. No preamble."""

# ── SUPABASE ─────────────────────────────────────────────────────────────────
def sb(method, path, **kwargs):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    r = getattr(requests, method)(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, **kwargs)
    try:    return r.json()
    except: return {}

def get_next_keyword():
    rows = sb("get", "keywords", params={
        "status": "eq.queued",
        "order":  "priority.asc,created_at.asc",
        "limit":  "5"
    })
    if not rows: return None
    return random.choice(rows[:min(3, len(rows))])

def mark_keyword(kid, status):
    sb("patch", f"keywords?id=eq.{kid}", json={"status": status})

def log_run(status, message, articles=0, errors=None, duration=None):
    sb("post", "agent_runs", json={
        "agent_name":        "Content Agent",
        "status":            status,
        "message":           message,
        "articles_processed": articles,
        "errors":            errors,
        "duration_seconds":  duration,
        "completed_at":      datetime.datetime.utcnow().isoformat()
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
    focase_context = f"\n\nFOCASE FORMULA REFERENCE:\n{FOCASE_2_FORMULA}" if product == "focase" else ""
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=5000,
        system=ARTICLE_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f'Write a Holistic Nutrition research brief on: "{keyword}"\n\n'
                f'Product context: conclude with criteria that align with {prod["name"]}.{focase_context}\n\n'
                f'Return ONLY valid JSON.'
            )
        }]
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    raw = raw.strip()

    def safe_parse(text):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        try:
            fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        try:
            start = text.index('{')
            end   = text.rindex('}') + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            pass
        try:
            import ast
            cleaned = text.replace('true', 'True').replace('false', 'False').replace('null', 'None')
            return ast.literal_eval(cleaned)
        except Exception:
            pass
        return None

    result = safe_parse(raw)
    if result:
        return result

    print("  [Claude] All parse strategies failed — requesting full JSON rewrite...")
    fix_msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=6000,
        system="You are a JSON repair specialist. Return ONLY valid JSON with no markdown, no explanation, no preamble.",
        messages=[{
            "role": "user",
            "content": (
                "Rewrite this as valid JSON. "
                "All HTML must be properly escaped inside string values. "
                "Replace any backslashes in HTML with forward slashes or remove them. "
                "Return ONLY the JSON object, nothing else.\n\n"
                + raw[:8000]
            )
        }]
    )
    fixed = fix_msg.content[0].text.strip()
    fixed = re.sub(r'^```[a-z]*\n?', '', fixed)
    fixed = re.sub(r'\n?```$', '', fixed)
    result = safe_parse(fixed.strip())
    if result:
        return result
    raise ValueError("Could not parse article JSON after all attempts")

# ── GENERATE IMAGE ────────────────────────────────────────────────────────────
def upload_image_to_cloudinary(image_bytes, ext="webp"):
    if not CLOUDINARY_CLOUD or not CLOUDINARY_API_KEY or not CLOUDINARY_SECRET:
        return None
    try:
        import hashlib, time as _time
        timestamp  = str(int(_time.time()))
        public_id  = f"hn-articles/article-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        params_str = f"public_id={public_id}&timestamp={timestamp}"
        signature  = hashlib.sha1(f"{params_str}{CLOUDINARY_SECRET}".encode()).hexdigest()
        upload_url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD}/image/upload"
        response   = requests.post(
            upload_url,
            data={
                "api_key":   CLOUDINARY_API_KEY,
                "timestamp": timestamp,
                "public_id": public_id,
                "signature": signature,
                "folder":    "hn-articles"
            },
            files={"file": (f"image.{ext}", image_bytes, f"image/{ext}")},
            timeout=60
        )
        result = response.json()
        url = result.get("secure_url")
        if url:
            print(f"  [Cloudinary] Uploaded: {url}")
            return url
        else:
            print(f"  [Cloudinary] Upload error: {result.get('error', result)}")
    except Exception as e:
        print(f"  [Cloudinary] Exception: {e}")
    return None

def generate_hero_image(photo_prompt, product):
    import time
    print(f"  [Image] Generating hero image...")
    prod  = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    color = prod["color"]

    if REPLICATE_API_KEY:
        try:
            enhanced_prompt = (
                f"{photo_prompt} "
                "Ultra-wide cinematic banner photograph, 3:1 aspect ratio. "
                "Natural earth tones, warm amber and cream color palette. "
                "Shallow depth of field, professional botanical or scientific editorial photography. "
                "Soft atmospheric natural lighting. No text, no people, no product bottles, no lab coats. "
                "High resolution, photorealistic, National Geographic quality."
            )
            headers = {
                "Authorization": f"Bearer {REPLICATE_API_KEY}",
                "Content-Type":  "application/json",
                "Prefer":        "wait"
            }
            payload = {
                "input": {
                    "prompt":             enhanced_prompt,
                    "width":              1500,
                    "height":             500,
                    "num_outputs":        1,
                    "output_format":      "webp",
                    "output_quality":     90,
                    "go_fast":            True,
                    "megapixels":         "1",
                    "num_inference_steps": 4
                }
            }
            print(f"  [FLUX] Sending request...")
            r = requests.post(
                "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
                headers=headers, json=payload, timeout=120
            )
            result = r.json()
            print(f"  [FLUX] Status: {result.get('status', 'unknown')}")

            if result.get("status") not in ["succeeded", "failed", "canceled"]:
                poll_url = result.get("urls", {}).get("get")
                if poll_url:
                    for _ in range(30):
                        time.sleep(3)
                        poll   = requests.get(poll_url, headers={"Authorization": f"Bearer {REPLICATE_API_KEY}"})
                        result = poll.json()
                        print(f"  [FLUX] Polling... {result.get('status')}")
                        if result.get("status") in ["succeeded", "failed", "canceled"]:
                            break

            if result.get("status") == "succeeded":
                output  = result.get("output")
                img_url = output[0] if isinstance(output, list) else output
                print(f"  [FLUX] Success: {img_url}")
                img_r = requests.get(img_url, timeout=30)
                if img_r.status_code == 200:
                    cdn_url = upload_image_to_cloudinary(img_r.content, "webp")
                    if cdn_url:
                        return cdn_url, cdn_url
                    return img_url, img_url
            print(f"  [FLUX] Failed: {result.get('error', 'unknown')}")
        except Exception as e:
            print(f"  [FLUX] Error: {e} — using SVG fallback")

    print(f"  [Image] Using SVG placeholder")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="500" viewBox="0 0 1500 500">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{HN_CREAM};stop-opacity:1"/>
      <stop offset="55%" style="stop-color:#ccc5bb;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:{HN_BROWN};stop-opacity:0.7"/>
    </linearGradient>
  </defs>
  <rect width="1500" height="500" fill="url(#bg)"/>
  <rect x="0" y="0" width="6" height="500" fill="{color}"/>
  <text x="28" y="38" font-family="Georgia, serif" font-size="11" fill="{HN_CHARCOAL}" opacity="0.5" letter-spacing="5">HOLISTIC NUTRITION RESEARCH BRIEF</text>
</svg>'''
    svg_b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{svg_b64}", svg

# ── GENERATE CHART ────────────────────────────────────────────────────────────
def generate_chart(chart_data, product):
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

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + max(values)*0.02,
                f"{val}{suffix}",
                ha='center', va='bottom',
                fontsize=11, fontweight='600',
                color=HN_CHARCOAL, fontfamily='DejaVu Sans')

    ax.set_title(chart_data.get("title", ""), fontsize=13, fontweight='500',
                 color=HN_CHARCOAL, pad=16, fontfamily='DejaVu Sans')
    ax.set_ylabel(f"Value ({suffix})" if suffix else "Value", fontsize=9, color="#7a7570")
    ax.tick_params(colors=HN_CHARCOAL, labelsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color("#d4cec6")
    ax.spines['bottom'].set_color("#d4cec6")
    ax.yaxis.grid(True, color="#e8e3dc", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)

    subtitle = chart_data.get("subtitle", "")
    if subtitle:
        fig.text(0.5, -0.02, subtitle, ha='center', fontsize=8, color="#9a9590", style='italic')

    fig.text(0.98, 0.02, "holisticnutrition.us", ha='right', fontsize=7, color="#b0a89f")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    return f"data:image/png;base64,{b64}"

# ── YOUTUBE SEARCH ────────────────────────────────────────────────────────────
def find_youtube_video(query):
    print(f"  [YouTube] Searching: '{query}'")
    if not YOUTUBE_API_KEY:
        encoded = requests.utils.quote(query)
        return {
            "search_url":  f"https://www.youtube.com/results?search_query={encoded}",
            "embed_html":  None,
            "note":        "Add YOUTUBE_API_KEY to enable auto-embedding"
        }
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part":          "snippet",
                "q":             query,
                "type":          "video",
                "maxResults":    3,
                "videoDuration": "medium",
                "key":           YOUTUBE_API_KEY
            },
            timeout=10
        )
        items = r.json().get("items", [])
        if not items:
            return None
        item    = items[0]
        vid_id  = item["id"]["videoId"]
        title   = item["snippet"]["title"]
        channel = item["snippet"]["channelTitle"]
        return {
            "video_id":   vid_id,
            "title":      title,
            "channel":    channel,
            "embed_html": (
                f'<div style="margin:2rem 0;">'
                f'<p style="font-size:12px;color:#7a7570;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.06em;">Related Research</p>'
                f'<div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:8px;">'
                f'<iframe style="position:absolute;top:0;left:0;width:100%;height:100%;" src="https://www.youtube.com/embed/{vid_id}" frameborder="0" allowfullscreen></iframe>'
                f'</div>'
                f'<p style="font-size:11px;color:#9a9590;margin-top:6px;">{title} — {channel}</p>'
                f'</div>'
            )
        }
    except Exception as e:
        print(f"    YouTube error: {e}")
        return None

# ── ASSEMBLE HTML ─────────────────────────────────────────────────────────────
def assemble_html(article, hero_img_uri, chart_b64, youtube, product):
    prod  = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    color = prod["color"]
    parts = []

    # Hero image
    parts.append(
        f'<div style="margin:0 0 36px 0;border-radius:10px;overflow:hidden;">'
        f'<img src="{hero_img_uri}" alt="{article["title"]}" '
        f'style="width:100%;aspect-ratio:3/1;object-fit:cover;display:block;"/>'
        f'</div>'
    )

    # Opening quote
    q = article.get("opening_quote", {})
    if q.get("text"):
        parts.append(
            f'<blockquote style="border-left:4px solid {color};padding:16px 24px;margin:0 0 32px;'
            f'background:#faf9f7;border-radius:0 8px 8px 0;">'
            f'<p style="font-size:18px;line-height:1.6;color:#2C2A27;font-style:italic;margin:0 0 8px;">'
            f'"{q["text"]}"</p>'
            f'<cite style="font-size:12px;color:#7a7570;font-style:normal;">{q.get("source","")}</cite>'
            f'</blockquote>'
        )

    # Global styles
    parts.append(f'''<style>
.hn-article blockquote {{
  border-left: 4px solid {color};
  background: #faf9f7;
  padding: 20px 24px;
  margin: 28px 0;
  border-radius: 0 8px 8px 0;
  font-size: 17px;
  line-height: 1.6;
  color: #2C2A27;
  font-style: italic;
}}
.hn-article table {{
  width: 100%;
  border-collapse: collapse;
  margin: 24px 0;
  font-size: 14px;
}}
.hn-article th {{
  background: {color};
  color: white;
  padding: 10px 14px;
  text-align: left;
  font-weight: 500;
}}
.hn-article td {{
  padding: 9px 14px;
  border-bottom: 1px solid #e8e3dc;
  color: #2C2A27;
}}
.hn-article tr:nth-child(even) td {{ background: #faf9f7; }}
.hn-article ul {{ padding-left: 20px; margin: 12px 0; }}
.hn-article li {{ margin-bottom: 6px; line-height: 1.65; color: #2C2A27; }}
.hn-article h3 {{ font-size: 18px; font-weight: 500; color: #2C2A27; margin: 28px 0 10px; }}
</style><div class="hn-article">''')

    # Sections
    sections        = article.get("sections", [])
    chart_inserted  = False
    for sec in sections:
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

    # CTA
    parts.append(
        f'<div style="margin:48px 0 32px;padding:28px 32px;background:#faf9f7;'
        f'border-radius:12px;border:1px solid #e8e3dc;border-left:4px solid {color};">'
        f'<p style="margin:0 0 12px;font-size:15px;color:#2C2A27;line-height:1.7;">{prod["cta"]}</p>'
        f'<a href="{prod["cta_url"]}" style="display:inline-block;background:{color};color:white;'
        f'padding:10px 22px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:500;">'
        f'View the product &#x2192;</a>'
        f'</div>'
    )

    # Research Library backlink
    parts.append(
        f'<div style="margin:24px 0;padding:16px 20px;background:#f5f3f0;'
        f'border-radius:8px;border:1px solid #e8e3dc;">'
        f'<p style="margin:0;font-size:12px;color:#7a7570;line-height:1.6;">'
        f'This article is part of the <a href="https://holisticnutrition.us/pages/research-library" '
        f'style="color:{color};text-decoration:none;font-weight:500;">Holistic Nutrition Research Library</a>. '
        f'Browse all research briefs and ingredient factsheets.</p>'
        f'</div>'
    )

    # References
    refs = article.get("references", [])
    if refs:
        ref_html = "".join(
            f'<p style="font-size:12px;color:#7a7570;margin:4px 0;line-height:1.6;">{r}</p>'
            for r in refs
        )
        parts.append(
            f'<div style="margin-top:48px;padding-top:24px;border-top:1px solid #e8e3dc;">'
            f'<h2 style="font-size:14px;font-weight:500;color:#7a7570;'
            f'text-transform:uppercase;letter-spacing:0.08em;margin:0 0 16px;">References</h2>'
            f'{ref_html}</div>'
        )

    return "\n".join(parts)

# ── NOTIFY LIBRARY WEBHOOK ────────────────────────────────────────────────────
def notify_library(title, article_url, category):
    """Send new article metadata to Zapier library updater webhook."""
    if not ZAPIER_LIBRARY_HOOK:
        print("  [Library] No webhook configured — skipping")
        return
    payload = {
        "article_title":    title,
        "article_url":      article_url,
        "category":         category,
        "published_date":   datetime.datetime.utcnow().strftime("%B %d, %Y")
    }
    try:
        r = requests.post(ZAPIER_LIBRARY_HOOK, json=payload, timeout=30)
        print(f"  [Library] Webhook status: {r.status_code}")
    except Exception as e:
        print(f"  [Library] Webhook error: {e}")

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
        print("\n  Step 1/5 — Generating article...")
        art = generate_article(keyword, product)
        print(f"    Title : {art['title']}")
        print(f"    Words : {art.get('word_count', '?')}")

        print("\n  Step 2/5 — Creating hero image...")
        hero_uri, _ = generate_hero_image(art.get("photo_prompt", ""), product)

        print("\n  Step 3/5 — Rendering chart...")
        chart_b64 = None
        if art.get("chart"):
            chart_b64 = generate_chart(art["chart"], product)

        print("\n  Step 4/5 — Finding YouTube video...")
        yt = None
        if art.get("youtube_query"):
            yt = find_youtube_video(art["youtube_query"])

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

        # Build article URL from title slug
        title_slug  = re.sub(r'[^a-z0-9]+', '-', art["title"].lower()).strip('-')
        shopify_url = (
            result.get("url") or result.get("shopify_url")
            if isinstance(result, dict) else None
        ) or f"https://holisticnutrition.us/blogs/research-studies/{title_slug}"

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

        # Notify library updater
        prod     = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
        category = prod["category"]
        notify_library(art["title"], shopify_url, category)

        duration = int((datetime.datetime.utcnow() - start).total_seconds())
        log_run("completed", f"Published: {art['title']}", 1, duration=duration)

        print(f"\n{'='*65}")
        print(f"  PUBLISHED: {art['title']}")
        print(f"  Duration  : {duration}s")
        print(f"  URL       : {shopify_url}")
        print(f"  Category  : {category}")
        print(f"{'='*65}\n")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        if aid: update_article(aid, {"status": "failed"})
        mark_keyword(kid, "queued")
        log_run("failed", str(e), 0, errors=str(e))
        raise

if __name__ == "__main__":
    run()
