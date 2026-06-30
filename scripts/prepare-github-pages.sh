#!/usr/bin/env bash
# Prepare published wwwroot for GitHub Pages (subpath hosting, Jekyll bypass, SPA 404).
set -euo pipefail

WWWROOT="${1:?usage: prepare-github-pages.sh <wwwroot-dir> <base-href>}"
BASE_HREF="${2:?usage: prepare-github-pages.sh <wwwroot-dir> <base-href>}"

# Ensure trailing slash for directory base paths (e.g. /MyRepo/)
if [[ "${BASE_HREF}" != "/" && "${BASE_HREF}" != */ ]]; then
  BASE_HREF="${BASE_HREF}/"
fi

INDEX="${WWWROOT}/index.html"

if grep -qE '<base[[:space:]]' "${INDEX}"; then
  sed -i "s|<base href=\"[^\"]*\"|<base href=\"${BASE_HREF}\"|" "${INDEX}"
else
  sed -i "s|<head>|<head>\n  <base href=\"${BASE_HREF}\">|" "${INDEX}"
fi

cp "${INDEX}" "${WWWROOT}/404.html"
touch "${WWWROOT}/.nojekyll"

echo "Prepared ${WWWROOT} with base href ${BASE_HREF}"
