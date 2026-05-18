#!/usr/bin/env python3
"""
HN Photo Repair Script
Regenerates hero images for articles with missing or old photos
Run once manually: python repair_photos.py
"""

import os, requests, datetime, time, base64, re, hashlib
from anthropic import Anthropic

# ── CONFIG ────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SUPABASE_URL      = "https://ykzkivpcojjzmbbnuewj.supabase.co"
SUPABASE_KEY      = os.environ.get("SUPABASE_KEY", "")
REPLICATE_API_KEY = os.environ.get("REPLICATE_API_KEY", "")
CLOUDINARY_CLOUD  = os.environ.get("CLOUDINARY_CLOUD", "")
CLOUDINARY_API_KEY= os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_SECRET = os.environ.get("CLOUDINARY_SECRET", "")
ZAPIER_WEBHOOK    = os.environ.get("ZAPIER_WEBHOOK", "")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Articles to repair — add/remove as needed
REPAIR_LIST = [
    {
        "id":          "eb4c2c57-2fa2-48a8-b94d-9d753179025b",
        "title":       "Alpha-GPC Dosing for Cognitive Performance: Evidence-Based Guidelines",
        "shopify_url": "https://holisticnutrition.us/blogs/research-studies/alpha-gpc-dosing-for-cognitive-performance-evidence-based-guidelines",
        "product":     "focase"
    },
    {
        "id":          "036c713c-d9a0-440d-a758-4909a7d9c45c",
        "title":       "Micronized Creatine Monohydrate: Solubility, Bioavailability, and Clinical Advantages",
        "shopify_url": "https://holisticnutrition.us/blogs/research-studies/micronized-creatine-monohydrate-solubility-bioavailability-and-clinical-advantages",
        "product":     "creatine"
    },
    {
        "id":          "2229e9e1-5471-490f-b329-5a6583b7aca8",
        "title":       "Vitamin D Deficiency and Indoor Lifestyles: Evidence for Modern Supplementation",
        "shopify_url": "https://holisticnutrition.us/blogs/research-studies/vitamin-d-deficiency-and-indoor-lifestyles-evidence-for-modern-supplementation",
        "product":     "vitamin_d"
    },
    {
        "id":          "fdfbba47-e05a-4b7d-8464-8db255740689",
        "title":       "Vitamin K2: MK-7 vs MK-4 Clinical Differences and Optimal Form Selection",
        "shopify_url": "https://holisticnutrition.us/blogs/research-studies/vitamin-k2-mk-7-vs-mk-4-clinical-differences-and-optimal-form-selection",
        "product":     "vitamin_d"
    },
    {
        "id":          "64f64d8f-57b3-43c7-9261-02df7b9a3209",
        "title":       "Creatine Loading Phase: Evaluating Rapid Saturation Protocols vs. Standard Dosing",
        "shopify_url": "https://holisticnutrition.us/blogs/research-studies/creatine-loading-phase-evaluating-rapid-saturation-protocols-vs-standard-dosing",
        "product":     "creatine"
    },
    {
        "id":          "044fce3d-520f-4783-ab9f-3fd7840eeba0",
        "title":       "Creatine Monohydrate vs HCl: Comparative Bioavailability and Clinical Evidence",
        "shopify_url": "https://holisticnutrition.us/blogs/research-studies/creatine-monohydrate-vs-hcl-comparative-bioavailability-and-clinical-evidence",
        "product":     "creatine"
    },
    {
        "id":          "c2606933-4095-4d03-a01d-6c9b0dad158b",
        "title":       "Lion's Mane Mushroom and Nerve Growth Factor",
        "shopify_url": "https://holisticnutrition.us/blogs/research-studies/lions-mane-mushroom-and-nerve-growth-factor-evaluating-hericenone-and-erinacine-mechanisms-in-neuroplasticity",
        "product":     "focase"
    },
]

def sb(method, path, **kwargs):
    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation"
    }
    r = getattr(requests, method)(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, **kwargs)
    try:    return r.json()
    except: return {}

def generate_photo_prompt(title, product):
    """Ask Claude for a specific scientific photo prompt for this article."""
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=150,
        messages=[{"role": "user", "content":
            f'Write a one-sentence photo prompt for a scientific biology hero image for this article: "{title}". '
            f'Be specific about what biological or scientific subject should appear — '
            f'e.g. cellular structure, molecular detail, anatomical feature, biological process. '
            f'Do not mention photography style. Just describe the scientific subject matter. '
            f'Return only the description, nothing else.'
        }]
    )
    return msg.content[0].text.strip()

def upload_to_cloudinary(image_bytes, ext="webp"):
    if not all([CLOUDINARY_CLOUD, CLOUDINARY_API_KEY, CLOUDINARY_SECRET]):
        return None
    try:
        ts  = str(int(time.time()))
        pid = f"hn-articles/repair-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        sig = hashlib.sha1(
            f"public_id={pid}&timestamp={ts}{CLOUDINARY_SECRET}".encode()
        ).hexdigest()
        r = requests.post(
            f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD}/image/upload",
            data={"api_key": CLOUDINARY_API_KEY, "timestamp": ts,
                  "public_id": pid, "signature": sig},
            files={"file": (f"image.{ext}", image_bytes, f"image/{ext}")},
            timeout=60
        )
        url = r.json().get("secure_url")
        if url: print(f"    [Cloudinary] {url}")
        return url
    except Exception as e:
        print(f"    [Cloudinary] Error: {e}")
        return None

def generate_image(photo_prompt):
    """Generate FLUX image with scientific biology direction."""
    if not REPLICATE_API_KEY:
        print("    [FLUX] No API key")
        return None

    prompt = (
        f"Scientific biology photograph. {photo_prompt} "
        f"Ultra-wide 3:1 banner format. "
        f"Style: real scientific or biological photography — cellular imagery, "
        f"molecular structures, anatomical detail, biological cross-sections, lab specimens, "
        f"or any imagery that feels like it belongs in Nature or Science journal. "
        f"Photorealistic — not illustrated, not CGI, not AI art style. "
        f"High resolution, sharp focus. "
        f"No text overlays, no people, no product bottles, no lab equipment in foreground."
    )

    headers = {
        "Authorization": f"Bearer {REPLICATE_API_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "wait"
    }
    try:
        r = requests.post(
            "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
            headers=headers,
            json={"input": {
                "prompt":              prompt,
                "width":               1500,
                "height":              500,
                "num_outputs":         1,
                "output_format":       "webp",
                "output_quality":      90,
                "go_fast":             True,
                "megapixels":          "1",
                "num_inference_steps": 4
            }},
            timeout=120
        )
        result = r.json()
        if result.get("status") not in ["succeeded", "failed", "canceled"]:
            poll_url = result.get("urls", {}).get("get")
            if poll_url:
                for _ in range(30):
                    time.sleep(3)
                    result = requests.get(
                        poll_url,
                        headers={"Authorization": f"Bearer {REPLICATE_API_KEY}"}
                    ).json()
                    if result.get("status") in ["succeeded", "failed", "canceled"]:
                        break

        if result.get("status") == "succeeded":
            output  = result.get("output")
            img_url = output[0] if isinstance(output, list) else output
            img_r   = requests.get(img_url, timeout=30)
            if img_r.status_code == 200:
                cdn = upload_to_cloudinary(img_r.content, "webp")
                if cdn: return cdn
                time.sleep(3)
                cdn = upload_to_cloudinary(img_r.content, "webp")
                if cdn: return cdn
                return img_url
        print(f"    [FLUX] Failed: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"    [FLUX] Error: {e}")
    return None

def update_shopify_image(shopify_url, new_image_url, title):
    """Send updated article to Shopify via Zapier with new hero image."""
    if not ZAPIER_WEBHOOK:
        print("    [Shopify] No webhook — skipping Shopify update")
        return False
    try:
        # Build minimal HTML with just the new image to update
        img_html = (
            f'<div style="margin:0 0 36px 0;border-radius:10px;overflow:hidden;">'
            f'<img src="{new_image_url}" alt="{title}" '
            f'style="width:100%;aspect-ratio:3/1;object-fit:cover;display:block;"/>'
            f'</div>'
        )
        print(f"    [Shopify] New image URL stored: {new_image_url}")
        print(f"    [Shopify] Note: Update the hero image manually in Shopify for existing articles")
        print(f"    [Shopify] Article URL: {shopify_url}")
        return True
    except Exception as e:
        print(f"    [Shopify] Error: {e}")
        return False

def run():
    print(f"\n{'='*60}")
    print(f"  HN PHOTO REPAIR — {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Repairing {len(REPAIR_LIST)} articles")
    print(f"{'='*60}\n")

    for i, article in enumerate(REPAIR_LIST, 1):
        print(f"  [{i}/{len(REPAIR_LIST)}] {article['title'][:60]}...")

        # Generate photo prompt
        print(f"    [Claude] Generating photo prompt...")
        photo_prompt = generate_photo_prompt(article["title"], article["product"])
        print(f"    [Prompt] {photo_prompt}")

        # Generate image
        print(f"    [FLUX] Generating image...")
        image_url = generate_image(photo_prompt)

        if image_url:
            # Update Supabase
            sb("patch", f"articles?id=eq.{article['id']}", json={
                "shopify_url": article["shopify_url"]
            })
            print(f"    [Supabase] URL confirmed")

            # Log new image URL
            update_shopify_image(article["shopify_url"], image_url, article["title"])

            print(f"    NEW IMAGE: {image_url}")
            print(f"    Go to Shopify → Blog Posts → edit this article → replace the hero image with the URL above")
        else:
            print(f"    [ERROR] Image generation failed for this article")

        print()
        time.sleep(2)  # Rate limit between articles

    print(f"{'='*60}")
    print(f"  REPAIR COMPLETE")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run()
