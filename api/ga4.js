export const config = { runtime: 'edge' };

/**
 * Vercel Edge Function: /api/ga4
 * Proxies Google Analytics Data API v1beta for the war room dashboard.
 *
 * Required Vercel env vars:
 *   GOOGLE_SA_KEY    — base64-encoded service account JSON key
 *                      (create at console.cloud.google.com → IAM → Service Accounts)
 *   GA4_PROPERTY_ID  — numeric GA4 property ID
 *                      (GA4 Admin → Property Settings → Property ID)
 *
 * The service account needs "Viewer" role on the GA4 property:
 *   GA4 Admin → Property Access Management → Add users
 */

export default async function handler(req) {
  const RAW_KEY   = process.env.GOOGLE_SA_KEY;
  const PROP_ID   = process.env.GA4_PROPERTY_ID;

  if (!RAW_KEY || !PROP_ID) {
    return new Response(JSON.stringify({ error: true, code: 'env_missing' }), {
      status: 500, headers: { 'Content-Type': 'application/json' }
    });
  }

  async function getToken() {
    const SA_KEY = JSON.parse(atob(RAW_KEY));
    const now    = Math.floor(Date.now() / 1000);

    const header  = btoa(JSON.stringify({ alg: 'RS256', typ: 'JWT' })).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
    const payload = btoa(JSON.stringify({
      iss:   SA_KEY.client_email,
      scope: 'https://www.googleapis.com/auth/analytics.readonly',
      aud:   'https://oauth2.googleapis.com/token',
      exp:   now + 3600,
      iat:   now
    })).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');

    const pemBody = SA_KEY.private_key
      .replace(/-----BEGIN PRIVATE KEY-----/g, '')
      .replace(/-----END PRIVATE KEY-----/g, '')
      .replace(/\s/g, '');

    const keyData = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));
    const key     = await crypto.subtle.importKey(
      'pkcs8', keyData,
      { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
      false, ['sign']
    );

    const sigData = new TextEncoder().encode(header + '.' + payload);
    const sigBuf  = await crypto.subtle.sign({ name: 'RSASSA-PKCS1-v1_5' }, key, sigData);
    const sig     = btoa(String.fromCharCode(...new Uint8Array(sigBuf)))
      .replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');

    const jwt = header + '.' + payload + '.' + sig;
    const tr  = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${jwt}`
    });
    const td = await tr.json();
    if (!td.access_token) throw new Error('token_error: ' + JSON.stringify(td));
    return td.access_token;
  }

  try {
    const token = await getToken();
    const today = new Date().toISOString().slice(0, 10);
    const BASE  = `https://analyticsdata.googleapis.com/v1beta/properties/${PROP_ID}`;

    const [rtResp, dayResp] = await Promise.all([
      fetch(`${BASE}:runRealtimeReport`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          metrics: [{ name: 'activeUsers' }]
        })
      }),
      fetch(`${BASE}:runReport`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dateRanges: [{ startDate: today, endDate: today }],
          dimensions: [{ name: 'pagePath' }],
          metrics: [
            { name: 'screenPageViews' },
            { name: 'sessions' }
          ],
          orderBys: [{ metric: { metricName: 'screenPageViews' }, desc: true }],
          limit: 10
        })
      })
    ]);

    const rtData  = await rtResp.json();
    const dayData = await dayResp.json();

    const activeUsers     = parseInt(rtData?.rows?.[0]?.metricValues?.[0]?.value || '0');
    let pageViewsToday    = 0;
    let sessionsToday     = 0;
    const topPages        = [];

    for (const row of (dayData.rows || [])) {
      const path  = row.dimensionValues?.[0]?.value || '/';
      const views = parseInt(row.metricValues?.[0]?.value || '0');
      const sess  = parseInt(row.metricValues?.[1]?.value || '0');
      pageViewsToday += views;
      sessionsToday  += sess;
      topPages.push({ path, views });
    }

    return new Response(
      JSON.stringify({ activeUsers, pageViewsToday, sessionsToday, topPages }),
      { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store, max-age=0' } }
    );

  } catch(e) {
    return new Response(
      JSON.stringify({ error: true, code: e.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
