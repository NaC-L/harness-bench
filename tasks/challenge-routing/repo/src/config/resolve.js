'use strict';
const STANDARD = {enabled: true, authRequired: false, roles: [], timeoutMs: 1000, headers: {}};
function createResolver(defaults, tenants) {
  const cache = new Map();
  return (tenantName, route) => {
    if (cache.has(route.id)) return cache.get(route.id);
    const tenant = tenants[tenantName];
    const layers = [defaults, tenant.config || {}, route.config || {}, (tenant.routes || {})[route.id] || {}];
    const config = {...STANDARD, headers: {}};
    for (const layer of layers) {
      for (const key of ['enabled', 'authRequired', 'roles', 'timeoutMs']) {
        config[key] = layer[key] || config[key];
      }
      Object.assign(config.headers, layer.headers || {});
    }
    cache.set(route.id, config);
    return config;
  };
}
module.exports = {createResolver};
