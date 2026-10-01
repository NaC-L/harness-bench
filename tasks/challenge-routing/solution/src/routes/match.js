'use strict';
function matchRoute(routes, method, path) {
  const pathname = path.split('?')[0];
  const normalized = method.toUpperCase();
  const methods = normalized === 'HEAD' ? ['HEAD', 'GET'] : [normalized];
  for (const candidateMethod of methods) {
    for (const route of routes) {
      if (route.method !== candidateMethod) continue;
      const captures = route.expression.exec(pathname);
      if (!captures) continue;
      try {
        const params = Object.fromEntries(route.names.map((name, i) => [name, decodeURIComponent(captures[i + 1])]));
        return {route, params};
      } catch { return {error: true}; }
    }
  }
  return null;
}
module.exports = {matchRoute};
