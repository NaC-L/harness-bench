'use strict';

/**
 * createRouter({routes, defaults, tenants}) -> {dispatch(request)}.
 * Constructor inputs are trusted: routes have unique string ids, uppercase
 * methods, and absolute paths made of literals and whole-segment :parameters.
 * Defaults and tenant entries are plain objects. Request fields are tenant,
 * method, path and optional principal {roles: string[]}; principal is trusted
 * authentication middleware output, never inferred from query parameters.
 *
 * Match the whole pathname (ignore the query). Normalize request method case.
 * Literal segments outrank parameters at the first differing segment; otherwise
 * declaration order breaks ties. HEAD uses an explicit HEAD match if present,
 * otherwise GET. Never fall back after selecting a disabled or forbidden route.
 * Decode captured parameters exactly once, AFTER splitting path segments;
 * encoded '/' remains inside a parameter. Malformed captures return 400.
 *
 * Only own tenant names are registered. Unknown tenant or no route returns 404.
 * Effective config precedence: defaults < tenant.config < route.config <
 * tenant.routes[route.id]. Only provided fields override; false, 0 and [] count.
 * headers merge by key in that order. Standard defaults: enabled=true,
 * authRequired=false, roles=[], timeoutMs=1000, headers={}.
 * A disabled selected route returns 404. authRequired OR nonempty roles requires
 * a principal (401); nonempty roles permit ANY listed role (otherwise 403).
 *
 * Success: {status:200, route:id, params, config}. Failure: {status} ONLY.
 * Dispatch never mutates constructor inputs. Returned params/config (including
 * roles and headers) are fresh snapshots; modifying them cannot affect later
 * requests or tenants. The router may be reused indefinitely.
 */
const {createRouter} = require('./gateway');
module.exports = {createRouter};
