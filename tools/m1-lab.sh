#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
export COMPOSE_PROJECT_NAME=owr-m1
export COMPOSE_ANSI=never
export COMPOSE_PROGRESS=plain
compose() { docker compose --env-file .local/runtime.env -f lab/m1/compose.yml "$@"; }
case "${1:-help}" in
  prepare)
    image_lock=${OWR_IMAGE_LOCK:-lab/m1/images.env}
    [[ -f "$image_lock" ]] || { echo 'Pin local image IDs in lab/m1/images.env first.' >&2; exit 1; }
    [[ -f .local/backup-plugin/vendor/autoload.php ]] || { echo 'Prepare pinned plugin dependency first.' >&2; exit 1; }
    mkdir -p .local
    if [[ ! -f .local/runtime.env ]]; then
      umask 077
      cat "$image_lock" > .local/runtime.env
      for name in SOURCE_DB_PASSWORD SOURCE_ROOT_PASSWORD RECOVERY_DB_PASSWORD RECOVERY_ROOT_PASSWORD ADMIN_PASSWORD; do
        printf 'OWR_%s=%s\n' "$name" "$(php -r 'echo bin2hex(random_bytes(24));')" >> .local/runtime.env
      done
    fi
    compose config --quiet
    ;;
  up)
    compose up -d --wait --wait-timeout 150 source-db source preview
    ;;
  seed)
    compose exec -T source php /fixture/seed.php
    ;;
  verify)
    mkdir -p evidence/m1/phase1
    output=$(mktemp)
    trap 'rm -f "$output"' EXIT
    result=0
    compose exec -T source php /fixture/verify.php > "$output" || result=$?
    cp "$output" "evidence/m1/phase1/source-baseline-$(date -u +%Y%m%dT%H%M%S)-$$.json"
    cp "$output" evidence/m1/phase1/source-baseline.json
    # shellcheck disable=SC2016
    php -r '$r=json_decode(file_get_contents($argv[1]),true,512,JSON_THROW_ON_ERROR); echo "Baseline checks: ",count($r["checks"]),"; passed=",($r["passed"]?"true":"false"),PHP_EOL;' "$output"
    exit "$result"
    ;;
  status) compose ps ;;
  stop) compose stop ;;
  *) echo 'Usage: bash tools/m1-lab.sh prepare|up|seed|verify|status|stop'; exit 1 ;;
esac
