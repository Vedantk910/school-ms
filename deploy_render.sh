#!/usr/bin/env bash
# One-command Render deploy for the school-ms public demo API.
#
# Creates the `school-ms-api` service from a filled-in blueprint using the
# repo's Render API key (.render_key). The Neon DB URL is read from .env.local
# (gitignored) and converted to the +psycopg scheme the app expects.
#
# Run from this folder:  bash deploy_render.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f .env.local ]; then echo ".env.local not found — abort"; exit 1; fi
KEY=$(tr -d '[:space:]' < .render_key)

# pooler URL from .env.local, with the +psycopg scheme SQLAlchemy needs
POOLER=$(grep -oE 'postgresql://[^@ ]*@ep-[^ /]*-pooler[^ "]*' .env.local | head -1)
if [ -z "$POOLER" ]; then echo "could not find a pooler DB URL in .env.local — abort"; exit 1; fi
DB="${POOLER/postgresql:/postgresql+psycopg:}"

BODY=$(python - "$DB" <<'PY'
import json, sys
db = sys.argv[1]
contents = f'''# Render Blueprint — School-MS API
services:
  - type: web
    name: school-ms-api
    runtime: python
    plan: free
    buildCommand: cd backend && pip install --no-cache-dir -r requirements.txt
    startCommand: cd backend && mkdir -p artifacts && uvicorn app.main:app --host 0.0.0.0 --port ${{PORT}}
    healthCheckPath: /healthz
    envVars:
      - key: SCHOOLMS_DATABASE_URL
        value: "{db}"
      - key: SCHOOLMS_JWT_SECRET
        generateValue: true
      - key: SCHOOLMS_CORS_ORIGINS
        value: "http://localhost:5173,http://localhost:3000,https://vedantk910.github.io,https://frontend-eta-two-66.vercel.app,https://school-ms.vedantk910s-projects.vercel.app"
      - key: SCHOOLMS_LLM_BACKEND
        value: "demo"
      - key: SCHOOLMS_COMMS_BACKEND
        value: "log"
      - key: PYTHONUNBUFFERED
        value: "1"
'''
print(json.dumps({
  "ownerID": "tea-dbgsfbnb9u1s7395js2g",
  "name": "school-ms",
  "repo": "https://github.com/Vedantk910/school-ms",
  "repoConfig": {"branch": "main"},
  "environment": "prod",
  "filePath": "render.yaml",
  "contents": contents,
  "forceNewServices": False,
}))
PY
)

echo "DB URL in use: ${DB%%@*}@... (password redacted)"
echo "Creating Render service from blueprint..."
RESP=$(curl -s -w "\nHTTP:%{http_code}" -X POST "https://api.render.com/v1/blueprints" \
  -H "Authorization: $KEY" -H "Content-Type: application/json" -d "$BODY")
echo "$RESP"
echo
echo "When the service is running (Render assigns a .onrender.com URL), point"
echo "the public UI at it:  GitHub repo -> Actions -> 'Deploy website' -> Run"
echo "workflow -> VITE_API_BASE = <your .onrender.com URL>"
