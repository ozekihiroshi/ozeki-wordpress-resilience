#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_repo=${1:-/mnt/d/workspace/secure-s3-storage-for-wordpress}
commit=627e47c2b31527ef1486e582b79fd5dba875843f
target="$root/.local/backup-plugin"
[[ ! -e "$target" ]] || { echo 'Pinned dependency already exists; do not overwrite it.' >&2; exit 1; }
[[ -f "$source_repo/vendor/autoload.php" ]] || { echo 'Local vendor dependencies are required.' >&2; exit 1; }
mkdir -p "$target" "$root/evidence/m1/phase1"
git -C "$source_repo" archive "$commit" src composer.json composer.lock ozeki-database-backup-for-s3.php readme.txt LICENSE | tar -x -C "$target"
cp -a "$source_repo/vendor" "$target/vendor"
# shellcheck disable=SC2016
php -r '
$root=$argv[1];
$lock=json_decode(file_get_contents($root."/composer.lock"),true,512,JSON_THROW_ON_ERROR);
$installed=json_decode(file_get_contents($root."/vendor/composer/installed.json"),true,512,JSON_THROW_ON_ERROR);
$map=[]; foreach($installed["packages"]??$installed as $p){$map[$p["name"]]=$p;}
foreach($lock["packages"] as $p){$i=$map[$p["name"]]??null; if(!$i || $i["version"]!==$p["version"] || ($i["source"]["reference"]??null)!==($p["source"]["reference"]??null)){throw new RuntimeException("Vendor package does not match pinned lock.");}}
echo "Vendor package versions match pinned composer.lock.\n";
' "$target"
python3 - "$target" "$commit" "$root/evidence/m1/phase1/plugin-provenance.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]); aggregate=hashlib.sha256(); count=0
for path in sorted(p for p in root.rglob('*') if p.is_file()):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    aggregate.update((path.relative_to(root).as_posix()+'\0'+digest+'\n').encode());count+=1
record={'commit':sys.argv[2],'plugin_version':'0.3.0','composer_lock_sha256':hashlib.sha256((root/'composer.lock').read_bytes()).hexdigest(),'files':count,'tree_sha256':aggregate.hexdigest(),'dependencies':'local vendor snapshot; package versions and source references checked against pinned lock','scope':'Phase 1 activation; internal Recovery API adoption remains pending'}
Path(sys.argv[3]).write_text(json.dumps(record,indent=2)+'\n')
PY
