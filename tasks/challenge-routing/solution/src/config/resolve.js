'use strict';
const STANDARD = {enabled: true, authRequired: false, roles: [], timeoutMs: 1000};
function createResolver(defaults, tenants) {
  return (tenantName, route) => {
    const tenant = tenants[tenantName];
    const overrides = tenant.routes || {};
    const layers = [defaults, tenant.config || {}, route.config || {}, Object.hasOwn(overrides, route.id) ? overrides[route.id] : {}];
    const config = {...STANDARD, headers: {}};
    for (const layer of layers) {
      for (const key of ['enabled', 'authRequired', 'roles', 'timeoutMs']) {
        if (Object.hasOwn(layer, key)) config[key] = layer[key];
      }
      Object.assign(config.headers, layer.headers || {});
    }
    config.roles = [...config.roles];
    return config;
  };
}
module.exports = {createResolver};
