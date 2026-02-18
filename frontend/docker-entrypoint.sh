#!/bin/sh
# Inject runtime environment variables

# Set defaults
export PORT="${PORT:-80}"
API_URL="${API_URL:-/api}"

# Substitute PORT into nginx config
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

# Create env-config.js with runtime API URL
cat <<EOF > /usr/share/nginx/html/env-config.js
(function(window) {
  window.__env = {
    API_URL: "${API_URL}"
  };
})(window);
EOF

exec "$@"
