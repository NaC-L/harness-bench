'use strict';
function matchRoute(routes, method, path) {
  let pathname;
  try { pathname = decodeURIComponent(path.split('?')[0]); }
  catch { return {error: true}; }
  const methods = method === 'HEAD' ? ['HEAD', 'GET'] : [method];
  for (const candidateMethod of methods) {
    for (const route of routes) {
      if (route.method !== candidateMethod) continue;
      const captures = route.expression.exec(pathname);
      if (!captures) continue;
      const params = Object.fromEntries(route.names.map((name, i) => [name, captures[i + 1]]));
      return {route, params};
    }
  }
  return null;
}
module.exports = {matchRoute};
