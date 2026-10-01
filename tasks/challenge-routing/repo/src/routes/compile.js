'use strict';
function compileRoutes(routes) {
  return routes.map((route) => {
    const names = [];
    const pattern = route.path.split('/').map((segment) => {
      if (segment.startsWith(':')) {
        names.push(segment.slice(1));
        return '([^/]+)';
      }
      return segment.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }).join('/');
    return {...route, names, expression: new RegExp('^' + pattern)};
  });
}
module.exports = {compileRoutes};
