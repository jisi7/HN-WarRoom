#!/usr/bin/env python3
"""
Holistic Nutrition Repurpose Agent
Triggers after content agent publishes → generates all social assets → 
saves to Google Drive → creates Publer dated drafts for FB, IG, Threads
TikTok and YouTube assets saved to Drive only (posted manually)
"""

import os, json, re, datetime, requests, time
from anthropic import Anthropic

# ── CONFIG ───────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL       = "https://ykzkivpcojjzmbbnuewj.supabase.co"
SUPABASE_KEY       = os.environ.get("SUPABASE_KEY", "")
_zrw = os.environ.get("ZAPIER_REPURPOSE_WEBHOOK", "")
ZAPIER_REPURPOSE_WEBHOOK = _zrw if _zrw else "https://hooks.zapier.com/hooks/catch/20680196/uvl38v5/"
DRIVE_FOLDER_NAME        = "HN Content A"  # folder inside 2026

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# HN Brand
HN_BROWN  = "#A3988B"
HN_CREAM  = "#E8E3DC"
HN_CHARCOAL = "#2C2A27"
HN_GREEN  = "#048142"
HN_RED    = "#D2042D"
HN_BLUE   = "#24418F"
HN_AMBER  = "#C8893A"

PRODUCT_MAP = {
    "creatine":  {"name": "Micronized Creatine Monohydrate", "url": "https://holisticnutrition.us/products/creatine-monohydrate", "color": HN_RED},
    "focase":    {"name": "Focase 2.0",                      "url": "https://holisticnutrition.us/products/focase",              "color": HN_BLUE},
    "vitamin_d": {"name": "Vitamin D3 + K2",                 "url": "https://holisticnutrition.us/products/vitamin-d3-k2",      "color": HN_AMBER},
    "general":   {"name": "Holistic Nutrition",               "url": "https://holisticnutrition.us",                             "color": HN_BROWN},
}



# ── SUPABASE ─────────────────────────────────────────────────────────────────
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
    # Fail loudly instead of swallowing — a bad key / RLS / schema error must surface.
    if r.status_code >= 400:
        raise RuntimeError(
            f"Supabase {method.upper()} /{path} failed [{r.status_code}]: {r.text[:300]}"
        )
    if r.status_code == 204 or not r.text:
        return []
    try: return r.json()
    except: return r.text

def get_latest_published_article():
    """Get the most recently published article that hasn't been repurposed yet."""
    rows = sb("get", "articles", params={
        "status": "eq.published",
        "order": "published_at.desc",
        "limit": "1"
    })
    if not rows or not isinstance(rows, list):
        return None
    article = rows[0]
    # Check if already repurposed
    drafts = sb("get", "social_drafts", params={
        "article_id": f"eq.{article['id']}",
        "limit": "1"
    })
    if drafts and isinstance(drafts, list) and len(drafts) > 0:
        print(f"  Article already repurposed: {article['title']}")
        return None
    return article

def log_social_draft(article_id, platform, content_type, content, status="pending", scheduled_at=None):
    # Best-effort: recording a draft for the dashboard must not crash a run that
    # already generated + sent the content to Zapier. Returns True on success.
    try:
        sb("post", "social_drafts", json={
            "article_id":   article_id,
            "platform":     platform,
            "content_type": content_type,
            "content":      content,
            "status":       status,
            "scheduled_at": scheduled_at
        })
        return True
    except Exception as e:
        print(f"  [warn] social_drafts write failed ({platform}): {e}")
        return False

def record_social_drafts(article, assets):
    """Write one social_drafts row per platform so the dashboard Social tab shows
    what was produced — and so the next run's 'already repurposed' check skips
    this article instead of re-sending duplicate content to Publer."""
    aid = article.get("id")
    if not aid:
        print("  [warn] article has no id — cannot record social drafts")
        return 0
    ig = assets.get("instagram_carousel", {})
    fb = assets.get("facebook_post", {})
    th = assets.get("threads_post", {})
    tk = assets.get("tiktok_scripts", []) or []
    yt = assets.get("youtube_script", {})
    tw = assets.get("x_thread", []) or []
    rows = [
        ("instagram", "carousel", ig.get("caption", "")),
        ("facebook",  "post",     fb.get("text", "")),
        ("threads",   "post",     th.get("text", "")),
        ("tiktok",    "script",   f"{len(tk)} TikTok scripts generated"),
        ("youtube",   "script",   yt.get("title", "")),
        ("x",         "thread",   f"{len(tw)}-tweet thread"),
    ]
    n = 0
    for platform, ctype, content in rows:
        if log_social_draft(aid, platform, ctype, (content or "")[:5000]):
            n += 1
    return n

def log_agent_run(status, message, articles=0, errors=None, duration=None):
    # Best-effort: a logging failure must never crash a run that already completed.
    try:
        sb("post", "agent_runs", json={
            "agent_name": "Repurpose Agent",
            "status": status,
            "message": message,
            "articles_processed": articles,
            "errors": errors,
            "duration_seconds": duration,
            "completed_at": datetime.datetime.utcnow().isoformat()
        })
    except Exception as e:
        print(f"  [warn] log_agent_run failed: {e}")

# ── CONTENT GENERATION ───────────────────────────────────────────────────────
REPURPOSE_SYSTEM = """You are the content repurposing specialist for Holistic Nutrition — a science-driven supplement company.

You take research brief articles and transform them into platform-optimized social content.

BRAND VOICE: Authoritative, educational, never hype-driven. Science leads, product follows naturally.
- Never use motivational filler or wellness clichés
- Every post should teach something specific and cite evidence
- CTAs are soft and informational, never pushy

OUTPUT: Return ONLY valid JSON with no markdown fences."""

def generate_all_assets(article):
    """Generate all social assets for an article in one Claude call."""
    title   = article.get("title", "")
    keyword = article.get("keyword", "")
    product = article.get("product", "general")
    prod    = PRODUCT_MAP.get(product, PRODUCT_MAP["general"])
    url     = article.get("shopify_url") or f"https://holisticnutrition.us/blogs/research-studies"

    print(f"  [Claude] Generating all social assets for: '{title}'")

    prompt = f"""Create all social media content for this Holistic Nutrition research brief.

Article title: {title}
Topic/keyword: {keyword}
Product: {prod['name']}
Article URL: {url}

Generate content optimized for each platform. Return this exact JSON structure:

{{
  "instagram_carousel": {{
    "slides": [
      {{"slide_num": 1, "type": "title", "headline": "...", "subtext": "..."}},
      {{"slide_num": 2, "type": "finding", "headline": "...", "body": "..."}},
      {{"slide_num": 3, "type": "finding", "headline": "...", "body": "..."}},
      {{"slide_num": 4, "type": "mechanism", "headline": "...", "body": "..."}},
      {{"slide_num": 5, "type": "practical", "headline": "...", "body": "..."}},
      {{"slide_num": 6, "type": "criteria", "headline": "What to look for", "bullets": ["...", "...", "..."]}},
      {{"slide_num": 7, "type": "cta", "headline": "Read the full brief", "subtext": "Link in bio", "url": "{url}"}}
    ],
    "caption": "...(150-200 words, educational, 1 question to drive comments, no excessive hashtags)...",
    "hashtags": ["#supplement", "#longevity", "#biohacking", "#holisticnutrition", "#research", "#science", "#health", "#wellness", "#nutrition", "#performancehealth"]
  }},
  "facebook_post": {{
    "text": "...(200-300 words, more detailed than Instagram, educational tone, link at end)...",
    "url": "{url}"
  }},
  "threads_post": {{
    "text": "...(one punchy research finding, under 500 chars, ends with article URL)..."
  }},
  "tiktok_scripts": [
    {{
      "angle": "Hook: surprising finding",
      "duration": "30s",
      "hook": "...(first 3 seconds — must stop the scroll)...",
      "script": "...(full script with on-screen text cues in [brackets])...",
      "onscreen_text": ["slide 1 text", "slide 2 text", "slide 3 text"],
      "cta": "..."
    }},
    {{
      "angle": "Myth vs Evidence",
      "duration": "30s", 
      "hook": "...",
      "script": "...",
      "onscreen_text": ["...", "...", "..."],
      "cta": "..."
    }},
    {{
      "angle": "Practical application",
      "duration": "30s",
      "hook": "...",
      "script": "...",
      "onscreen_text": ["...", "...", "..."],
      "cta": "..."
    }}
  ],
  "youtube_script": {{
    "title": "...(SEO-optimized YouTube title)...",
    "description": "...(YouTube description with timestamps and links)...",
    "hook": "...(first 30 seconds — pattern interrupt, preview value)...",
    "chapters": [
      {{"title": "Intro", "timestamp": "0:00", "script": "..."}},
      {{"title": "What is {keyword}", "timestamp": "0:45", "script": "..."}},
      {{"title": "The Research", "timestamp": "2:00", "script": "..."}},
      {{"title": "What This Means For You", "timestamp": "5:00", "script": "..."}},
      {{"title": "How to Choose", "timestamp": "7:00", "script": "..."}},
      {{"title": "Outro", "timestamp": "8:30", "script": "..."}}
    ],
    "total_duration": "9-10 minutes",
    "cta": "..."
  }},
  "x_thread": [
    "Tweet 1: Hook tweet with surprising stat or finding (under 280 chars)",
    "Tweet 2: ...",
    "Tweet 3: ...",
    "Tweet 4: ...",
    "Tweet 5: ...",
    "Tweet 6: ...",
    "Tweet 7: Full article link + CTA"
  ]
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=6000,
        system=REPURPOSE_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = msg.content[0].text.strip()
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)

    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        # Fix invalid escapes
        fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw)
        return json.loads(fixed.strip())

# ── SEND TO ZAPIER ───────────────────────────────────────────────────────────
def send_to_zapier(article, assets):
    """Send all repurposed content to Zapier in one payload."""
    if not ZAPIER_REPURPOSE_WEBHOOK:
        print("  [Zapier] No webhook configured")
        return False

    ig      = assets.get("instagram_carousel", {})
    fb      = assets.get("facebook_post", {})
    th      = assets.get("threads_post", {})
    tiktok  = assets.get("tiktok_scripts", [])
    yt      = assets.get("youtube_script", {})
    tweets  = assets.get("x_thread", [])
    title   = article.get("title", "")
    url     = article.get("shopify_url") or "https://holisticnutrition.us"
    date    = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    # Format carousel slides as readable text
    carousel_txt = ""
    for slide in ig.get("slides", []):
        carousel_txt += f"SLIDE {slide['slide_num']} — {slide.get('type','').upper()}\n"
        carousel_txt += f"Headline: {slide.get('headline', '')}\n"
        if slide.get('body'):    carousel_txt += f"Body: {slide['body']}\n"
        if slide.get('subtext'): carousel_txt += f"Subtext: {slide['subtext']}\n"
        if slide.get('bullets'): carousel_txt += f"Bullets:\n" + "\n".join(f"  • {b}" for b in slide['bullets']) + "\n"
        carousel_txt += "\n"

    # Format TikTok scripts
    tiktok_txt = ""
    for i, script in enumerate(tiktok, 1):
        tiktok_txt += f"SCRIPT {i}: {script.get('angle','')}\n"
        tiktok_txt += f"HOOK: {script.get('hook','')}\n"
        tiktok_txt += f"SCRIPT:\n{script.get('script','')}\n"
        tiktok_txt += f"ON-SCREEN: {' | '.join(script.get('onscreen_text',[]))}\n"
        tiktok_txt += f"CTA: {script.get('cta','')}\n\n"

    # Format YouTube script
    yt_txt = f"TITLE: {yt.get('title','')}\n\n"
    yt_txt += f"HOOK:\n{yt.get('hook','')}\n\n"
    for ch in yt.get("chapters", []):
        yt_txt += f"[{ch.get('timestamp','')}] {ch.get('title','')}\n{ch.get('script','')}\n\n"

    # Format X thread
    x_txt = "\n\n".join([f"Tweet {i}: {t}" for i, t in enumerate(tweets, 1)])

    payload = {
        # Article info
        "article_title":    title,
        "article_url":      url,
        "article_date":     date,
        "product":          article.get("product", "general"),
        "folder_name":      f"{date} — {title[:50]}",
        "drive_folder":     DRIVE_FOLDER_NAME,

        # Instagram
        "ig_carousel_copy": carousel_txt,
        "ig_caption":       ig.get("caption", ""),
        "ig_hashtags":      " ".join(ig.get("hashtags", [])),
        "ig_full":          f"{ig.get('caption','')}\n\n{' '.join(ig.get('hashtags',[]))}",

        # Facebook
        "fb_post":          f"{fb.get('text','')}\n\n{url}",

        # Threads
        "threads_post":     th.get("text", ""),

        # TikTok (manual posting)
        "tiktok_scripts":   tiktok_txt,

        # YouTube (manual posting)
        "youtube_script":   yt_txt,
        "youtube_title":    yt.get("title", ""),
        "youtube_description": yt.get("description", ""),

        # X thread (manual posting)
        "x_thread":         x_txt,
        "x_tweet_1":        tweets[0] if tweets else "",
        "x_tweet_2":        tweets[1] if len(tweets) > 1 else "",
        "x_tweet_3":        tweets[2] if len(tweets) > 2 else "",
        "x_tweet_4":        tweets[3] if len(tweets) > 3 else "",
        "x_tweet_5":        tweets[4] if len(tweets) > 4 else "",
        "x_tweet_6":        tweets[5] if len(tweets) > 5 else "",
        "x_tweet_7":        tweets[6] if len(tweets) > 6 else "",
    }

    r = requests.post(ZAPIER_REPURPOSE_WEBHOOK, json=payload, timeout=30)
    print(f"  [Zapier] Status: {r.status_code}")
    return r.status_code == 200

# ── MAIN ──────────────────────────────────────────────────────────────────────
# ── MAIN ──────────────────────────────────────────────────────────────────────
def run():
    start = datetime.datetime.utcnow()
    print(f"\n{'='*65}")
    print(f"  HN REPURPOSE AGENT — {start.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*65}")

    # Get latest unpurposed article
    article = get_latest_published_article()
    if not article:
        print("  No new articles to repurpose. Exiting.")
        log_agent_run("completed", "No new articles to repurpose")
        return

    title   = article.get("title", "")
    product = article.get("product", "general")
    print(f"\n  Article : {title}")
    print(f"  Product : {product}")
    print(f"  URL     : {article.get('shopify_url', '—')}")

    try:
        # 1. Generate all assets
        print("\n  Step 1/3 — Generating social assets...")
        assets = generate_all_assets(article)
        print(f"    ✓ Instagram carousel: {len(assets.get('instagram_carousel', {}).get('slides', []))} slides")
        print(f"    ✓ TikTok scripts: {len(assets.get('tiktok_scripts', []))}")
        print(f"    ✓ YouTube script: {assets.get('youtube_script', {}).get('total_duration', '?')}")
        print(f"    ✓ X thread: {len(assets.get('x_thread', []))} tweets")

        # 2. Send everything to Zapier
        print("\n  Step 2/3 — Sending to Zapier...")
        success = send_to_zapier(article, assets)

        # 3. Record drafts in Supabase (dashboard visibility + dedup for next run)
        print("\n  Step 3/3 — Recording social drafts...")
        drafts_written = record_social_drafts(article, assets)
        print(f"    ✓ Recorded {drafts_written} platform drafts")

        duration = int((datetime.datetime.utcnow() - start).total_seconds())
        log_agent_run("completed", f"Repurposed: {title} ({drafts_written} drafts)", 1, duration=duration)

        print(f"\n{'='*65}")
        print(f"  ✓ DONE — {title}")
        print(f"  Duration : {duration}s")
        print(f"  Zapier   : {'✓ sent' if success else '✗ failed'}")
        print(f"  Drafts   : {drafts_written} recorded")
        print(f"{'='*65}\n")

    except Exception as e:
        print(f"\n  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        log_agent_run("failed", str(e), 0, errors=str(e))
        raise

if __name__ == "__main__":
    run()
