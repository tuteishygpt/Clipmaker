export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1. Handle API requests by proxying to Google Cloud Run backend
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

      const backendBase = 'https://clipmaker-api-536283296767.us-central1.run.app';
      const targetUrl = new URL(url.pathname + url.search, backendBase);

      const headers = new Headers(request.headers);
      headers.set('host', 'clipmaker-api-536283296767.us-central1.run.app');

      const init = {
        method: request.method,
        headers: headers,
        redirect: 'manual', // Pass 307 redirects straight to browser for R2 streaming
      };

      if (request.method !== 'GET' && request.method !== 'HEAD') {
        init.body = request.body;
        init.duplex = 'half';
      }

      const response = await fetch(targetUrl.toString(), init);

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
