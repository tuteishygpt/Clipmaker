export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 0. Internal Supabase proxy for IPv6-only Compute Engine API backend (protected by secret prefix)
    if (env.SB_PROXY_PREFIX && url.pathname.startsWith('/' + env.SB_PROXY_PREFIX + '/')) {
      const upstreamPath = url.pathname.slice(env.SB_PROXY_PREFIX.length + 1);
      const sbUrl = new URL(upstreamPath + url.search, 'https://aqcdxlnzrfxqmftsemek.supabase.co');
      const sbHeaders = new Headers(request.headers);
      sbHeaders.set('host', 'aqcdxlnzrfxqmftsemek.supabase.co');

      const sbInit = {
        method: request.method,
        headers: sbHeaders,
        redirect: 'manual',
      };
      if (request.method !== 'GET' && request.method !== 'HEAD') {
        sbInit.body = request.body;
        sbInit.duplex = 'half';
      }
      return fetch(sbUrl.toString(), sbInit);
    }

    // 1. Handle API requests by proxying over Cloudflare Workers VPC Tunnel to clipmaker-prod-2026 backend
    if (url.pathname.startsWith('/api')) {
      // Handle CORS preflight options directly
      if (request.method === 'OPTIONS') {
        return new Response(null, {
          status: 204,
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Max-Age': '86400',
          },
        });
      }

      if (!env.BACKEND_PROXY) {
        return new Response(
          JSON.stringify({ detail: 'BACKEND_PROXY binding is not configured' }),
          {
            status: 503,
            headers: {
              'Content-Type': 'application/json',
              'Access-Control-Allow-Origin': '*',
            },
          },
        );
      }

      const response = await env.BACKEND_PROXY.fetch(request);

      // Pass through 301/302/307/308 redirects directly so browser connects to R2
      if (response.status >= 300 && response.status < 400) {
        return response;
      }

      // Return response with proper CORS headers
      const responseHeaders = new Headers(response.headers);
      responseHeaders.set('Access-Control-Allow-Origin', '*');
      responseHeaders.set('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
      responseHeaders.set('Access-Control-Allow-Headers', '*');

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    }

    // 2. Handle static assets from Pages
    let response = await env.ASSETS.fetch(request);

    // 3. SPA Fallback: if not found (404), serve index.html for client-side routing
    if (response.status === 404 && request.method === 'GET' && !url.pathname.includes('.')) {
      const indexRequest = new Request(new URL('/', request.url), request);
      response = await env.ASSETS.fetch(indexRequest);
    }

    return response;
  }
};
