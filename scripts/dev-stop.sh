#!/usr/bin/env bash
# Reliably stop the local dev stack.
#
# `bench start` runs several processes under honcho: web (:8000), socketio (:9000),
# plus schedule / worker / watch which DON'T hold a port. On macOS these can survive
# Ctrl+C (they re-parent to launchd). A surviving `bench schedule` keeps the scheduler
# lock, which makes the NEXT `bench start` exit instantly and tear the whole stack down.
#
# So we clean up BOTH: port holders AND the bench worker/schedule/watch processes —
# but only ones belonging to THIS bench (matched by working directory), so other
# Frappe projects on the machine are left untouched.
set -uo pipefail

BENCH_DIR="${BENCH_DIR:-$HOME/frappe-bench}"
PORTS=(8000 9000 8080)   # backend web, socketio, vite

kill_pids() { [ -n "${1:-}" ] && kill -9 $1 2>/dev/null || true; }

# 1) Port holders (web / socketio / vite)
for p in "${PORTS[@]}"; do
  pids=$(lsof -ti:"$p" -sTCP:LISTEN 2>/dev/null || true)
  [ -n "$pids" ] && { echo "Killing :$p -> $pids"; kill_pids "$pids"; } || echo ":$p already free"
done

# 2) Non-port bench processes (schedule / worker / watch / serve / socketio / esbuild)
#    scoped to THIS bench via each process's current working directory.
cands=$(ps ax -o pid,command | grep -iE "bench_helper frappe (schedule|worker|watch|serve|socketio)|esbuild --watch" | grep -v grep | awk '{print $1}')
for pid in $cands; do
  cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)
  case "$cwd" in
    "$BENCH_DIR"*) echo "Killing bench proc $pid (cwd=$cwd)"; kill_pids "$pid" ;;
    *) : ;;  # different bench / project — leave alone
  esac
done

# 3) Second pass for anything a reloader respawned
sleep 1
for p in "${PORTS[@]}"; do
  pids=$(lsof -ti:"$p" -sTCP:LISTEN 2>/dev/null || true)
  [ -n "$pids" ] && { echo "Re-killing :$p -> $pids"; kill_pids "$pids"; }
done

echo "Dev stack stopped."
