'use strict';
const {compileRoutes} = require('./routes/compile');
const {matchRoute} = require('./routes/match');
const {createResolver} = require('./config/resolve');
const {authorize} = require('./policy/authorize');

function createRouter({routes, defaults = {}, tenants}) {
  const compiled = compileRoutes(routes);
  const resolve = createResolver(defaults, tenants);
  return {
    dispatch(request) {
      if (!tenants[request.tenant]) return {status: 404};
      const match = matchRoute(compiled, request.method, request.path);
      if (!match) return {status: 404};
      if (match.error) return {status: 400};
      const config = resolve(request.tenant, match.route);
      if (!config.enabled) return {status: 404};
      const status = authorize(config, request.principal);
      if (status !== 200) return {status};
      return {status: 200, route: match.route.id, params: match.params, config};
    }
  };
}
module.exports = {createRouter};
