'use strict';
function authorize(config, principal) {
  if ((config.authRequired || config.roles.length > 0) && !principal) return 401;
  if (config.roles.length > 0 && !config.roles.every((role) => principal.roles.includes(role))) return 403;
  return 200;
}
module.exports = {authorize};
