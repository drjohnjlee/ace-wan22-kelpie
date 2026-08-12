#!/usr/bin/env bash
set -uo pipefail

echo "[boot] ACE Wan 2.2 Kelpie worker starting"
echo "[boot] Model download is job-tracked; Kelpie is launching immediately"

while true; do
  /usr/local/bin/kelpie "$@"
  rc=$?
  echo "[boot] Kelpie exited rc=${rc}"

  if [[ "${KELPIE_NO_RESTART:-0}" == "1" ]]; then
    exit "${rc}"
  fi

  echo "[boot] Restarting Kelpie in 5 seconds"
  sleep 5
done
