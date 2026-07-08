#!/usr/bin/env bash
# Start the dashboard + a Cloudflare quick tunnel, then print the public URL.
#
# Usage:
#   DASHBOARD_PASSWORD=your-secret ./share.sh
#
# The public https://<random>.trycloudflare.com URL stays the same for as long
# as this script keeps running. Stop with Ctrl-C (both processes shut down).
#
# A stable custom URL (e.g. tasks.yourdomain.com) would require a domain on
# Cloudflare — not set up here by choice.
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"
export DASHBOARD_USER="${DASHBOARD_USER:-lakshay}"
# If no password is provided, the server generates and prints one at startup.
export DASHBOARD_PASSWORD="${DASHBOARD_PASSWORD:-}"

command -v cloudflared >/dev/null || { echo "cloudflared not found — run: brew install cloudflared"; exit 1; }

echo "Starting API server on :$PORT ..."
uv run --project backend python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" &
SERVER_PID=$!

# Shut both down together on exit.
cleanup() { kill "$SERVER_PID" "${TUNNEL_PID:-}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

sleep 3

echo "Starting Cloudflare tunnel ..."
TUNNEL_LOG="$(mktemp)"
cloudflared tunnel --url "http://localhost:$PORT" >"$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

# Wait for the public URL to appear in the tunnel log.
URL=""
for _ in $(seq 1 20); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1 || true)"
  [ -n "$URL" ] && break
  sleep 1
done

echo
echo "============================================================"
if [ -n "$URL" ]; then
  echo "  Dashboard is live at:"
  echo "    $URL"
  echo "  Log in with user '$DASHBOARD_USER' and your password."
else
  echo "  Tunnel started but no URL captured yet. Check:"
  echo "    $TUNNEL_LOG"
fi
echo "  Leave this running to keep the URL alive. Ctrl-C to stop."
echo "============================================================"

wait "$TUNNEL_PID"
