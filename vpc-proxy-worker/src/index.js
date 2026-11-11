export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const targetUrl = new URL(url.pathname + url.search, 'http://clipmaker-api.internal');

    const headers = new Headers(request.headers);
    headers.set('host', '127.0.0.1:8000');

    const init = {
      method: request.method,
      headers: headers,
      redirect: 'manual',
    };

    if (request.method !== 'GET' && request.method !== 'HEAD') {
      init.body = request.body;
      init.duplex = 'half';
    }

    return env.BACKEND_VPC.fetch(targetUrl.toString(), init);
  },
};
