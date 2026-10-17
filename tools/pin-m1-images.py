#!/usr/bin/env python3
"""Pin existing local images without pulling or changing other projects."""
import argparse
import json
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser()
parser.add_argument('--output',default=str(root/'lab/m1/images.env'))
lock=Path(parser.parse_args().output)
lock.parent.mkdir(parents=True,exist_ok=True)
if lock.exists():
    raise SystemExit('Image lock exists; review an intentional version change instead of overwriting.')
records=[]
for variable,tag in [('OWR_WP_IMAGE','wordpress:php8.3-apache'),('OWR_DB_IMAGE','mariadb:11.8'),('OWR_PROXY_IMAGE','nginx:alpine')]:
    image=json.loads(subprocess.check_output(['docker','image','inspect',tag],timeout=25))[0]
    records.append({'variable':variable,'discovery_tag':tag,'image_id':image['Id'],'repo_digests':image.get('RepoDigests',[]),'os':image['Os'],'architecture':image['Architecture']})
lock.write_text(''.join(r['variable']+'='+r['image_id']+'\n' for r in records))
lock.with_suffix('.lock.json').write_text(json.dumps(records,indent=2)+'\n')
print('Pinned three local images by content ID.')
