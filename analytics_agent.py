#!/usr/bin/env python3
"""
HN Analytics Agent
Pulls GA4 traffic / engagement / conversion data per blog article and writes it to
the Supabase `performance` table. This is what closes the loop:
  - the dashboard shows real performance (Organic Traffic, top articles), and
  - the content agent can favor topics/products that actually drive engagement & sales
    (see get_product_performance() in agent.py).

Requires three GitHub Actions secrets:
  SUPABASE_KEY             - same service_role key the other agents use
  GA_PROPERTY_ID           - your GA4 *numeric* property id (Admin > Property Settings)
  GA_SERVICE_ACCOUNT_JSON  - the full JSON of a Google service-account key that has
                             "Viewer" on the GA4 property (see setup notes in the PR)
"""

import os, json, datetime, requests

SUPABASE_URL            = "https://ykzkivpcojjzmbbnuewj.supabase.co"
SUPABASE_KEY            = os.environ.get("SUPABASE_KEY", "")
GA_PROPERTY_ID          = os.environ.get("GA_PROPERTY_ID", "")
GA_SERVICE_ACCOUNT_JSON = os.environ.get("GA_SERVICE_ACCOUNT_JSON", "")
LOOKBACK_DAYS           = int(os.environ.get("GA_LOOKBACK_DAYS", "30"))

# Metric sets tried in order — GA4 renamed "conversions" -> "keyEvents", and some
# properties don't expose revenue. We degrade gracefully so the agent works on any
# GA4 setup instead of erroring on an unknown metric name.
METRIC_SETS = [
    ["screenPageViews", "sessions", "engagementRate", "keyEvents", "totalRevenue"],
    ["screenPageViews", "sessions", "engagementRate", "conversions", "totalRevenue"],
    ["screenPageViews", "sessions", "engagementRate"],
    ["screenPageViews", "sessions"],
]

# ── SUPABASE ──────────────────────────────────────────────────────────────────
def sb(method, path, prefer="return=representation", **kwargs):
    if not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_KEY is empty — set the GitHub Actions secret.")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }
    r = getattr(requests, method)(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"Supabase {method.upper()} /{path} failed [{r.status_code}]: {r.text[:300]}")
    if r.status_code == 204 or not r.text:
        return []
    try:    return r.json()
    except: return r.text

def upsert_performance(row):
    # Needs a UNIQUE (article_id, date) constraint on `performance` (see setup SQL).
    sb("post", "performance?on_conflict=article_id,date",
       prefer="resolution=merge-duplicates,return=minimal",
       json=row)

def log_run(status, message, processed=0, errors=None):
    try:
        sb("post", "agent_runs", prefer="return=minimal", json={
            "agent_name":         "Analytics Agent",
            "status":             status,
            "message":            message,
            "articles_processed": processed,
            "errors":             errors,
            "completed_at":       datetime.datetime.utcnow().isoformat(),
        })
    except Exception as e:
        print(f"  [warn] log_run failed: {e}")

# ── GA4 ───────────────────────────────────────────────────────────────────────
def ga_client():
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.oauth2 import service_account
    if not GA_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GA_SERVICE_ACCOUNT_JSON is empty — paste the service-account key JSON into the secret.")
    info  = json.loads(GA_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/analytics.readonly"])
    return BetaAnalyticsDataClient(credentials=creds)

def fetch_article_metrics(client):
    """pagePath -> metric dict for blog articles over the lookback window."""
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, RunReportRequest, Filter, FilterExpression)

    last_err = None
    for metric_names in METRIC_SETS:
        try:
            req = RunReportRequest(
                property=f"properties/{GA_PROPERTY_ID}",
                dimensions=[Dimension(name="pagePath")],
                metrics=[Metric(name=m) for m in metric_names],
                date_ranges=[DateRange(start_date=f"{LOOKBACK_DAYS}daysAgo", end_date="today")],
                dimension_filter=FilterExpression(filter=Filter(
                    field_name="pagePath",
                    string_filter=Filter.StringFilter(
                        match_type=Filter.StringFilter.MatchType.CONTAINS, value="/blogs/"))),
                limit=10000,
            )
            resp = client.run_report(req)
            print(f"  [GA4] Report ok with metrics: {metric_names}")
            return _parse_report(resp, metric_names)
        except Exception as e:
            last_err = e
            print(f"  [GA4] metric set {metric_names} failed ({str(e)[:80]}) — trying simpler set")
    raise RuntimeError(f"All GA4 metric sets failed: {last_err}")

def _parse_report(resp, metric_names):
    idx = {name: i for i, name in enumerate(metric_names)}
    def mv(vals, name):
        i = idx.get(name)
        if i is None: return 0.0
        try:    return float(vals[i] or 0)
        except: return 0.0
    out = {}
    for row in resp.rows:
        path = row.dimension_values[0].value
        vals = [m.value for m in row.metric_values]
        out[path] = {
            "organic_traffic": int(mv(vals, "screenPageViews")),
            "sessions":        int(mv(vals, "sessions")),
            "engagement_rate": round(mv(vals, "engagementRate"), 4),
            "conversions":     int(mv(vals, "keyEvents") or mv(vals, "conversions")),
            "revenue":         round(mv(vals, "totalRevenue"), 2),
        }
    return out

def slug_of(url):
    return (url or "").rstrip("/").split("/")[-1].lower()

# ── MAIN ──────────────────────────────────────────────────────────────────────
def run():
    start = datetime.datetime.utcnow()
    print(f"\n{'='*65}\n  HN ANALYTICS AGENT — {start:%Y-%m-%d %H:%M UTC}\n{'='*65}")

    if not GA_PROPERTY_ID:
        raise RuntimeError("GA_PROPERTY_ID is empty — set it to your GA4 numeric property id.")

    articles = sb("get", "articles", params={
        "select": "id,title,shopify_url,product", "status": "eq.published", "limit": "1000"})
    if not isinstance(articles, list):
        articles = []
    by_slug = {slug_of(a.get("shopify_url")): a for a in articles if a.get("shopify_url")}
    print(f"  {len(by_slug)} published articles to match against GA4")

    try:
        client  = ga_client()
        metrics = fetch_article_metrics(client)
        print(f"  GA4 returned {len(metrics)} blog page paths")

        today   = datetime.date.today().isoformat()
        matched = 0
        for path, m in metrics.items():
            art = by_slug.get(slug_of(path))
            if not art:
                continue
            upsert_performance({"article_id": art["id"], "date": today, **m})
            matched += 1

        msg = f"Synced GA4 metrics for {matched} articles"
        print(f"  {msg}")
        log_run("completed", msg, matched)
    except Exception as e:
        print(f"\n  ERROR: {e}")
        log_run("failed", str(e), 0, errors=str(e))
        raise

if __name__ == "__main__":
    run()
