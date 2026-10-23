"""Reconstruct only into new private Docker resources; never targets an existing site."""
import argparse,importlib.util,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--wordpress-image',required=True);p.add_argument('--database-image',required=True);p.add_argument('--allow-dedicated-target',action='store_true');a=p.parse_args()
if not a.allow_dedicated_target or not all(re.fullmatch('sha256:[a-f0-9]{64}',x) for x in (a.wordpress_image,a.database_image)):p.error('Explicit dedicated target and pinned local images required')
s=importlib.util.spec_from_file_location('private_target',Path(__file__).with_name('run-site-materials-lab.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
result=m.trial_target(a.output,a.bundle,a.wordpress_image,a.database_image,validation_checks=False,keep_target=True)
print(json.dumps(result))
