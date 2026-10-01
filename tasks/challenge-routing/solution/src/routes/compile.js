'use strict';
function compileRoutes(routes) {
  return routes.map((route, order) => {
    const names = [];
    const segments = route.path.split('/');
    const rank = segments.map((segment) => segment.startsWith(':') ? 0 : 1);
    const pattern = segments.map((segment) => {
      if (segment.startsWith(':')) {
        names.push(segment.slice(1));
        return '([^/]+)';
      }
      return segment.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }).join('/');
    return {...route, names, rank, order, expression: new RegExp('^' + pattern + '$')};
  }).sort((a, b) => {
    for (let i = 0; i < Math.min(a.rank.length, b.rank.length); i++) {
      if (a.rank[i] !== b.rank[i]) return b.rank[i] - a.rank[i];
    }
    return a.order - b.order;
  });
}
module.exports = {compileRoutes};
