"""Form participants are part of the recorded input, not all available editor controls."""
import importlib.util,urllib.parse,time
from pathlib import Path
p=Path(__file__).parents[1]/'tools/reconstruct-operations.py'
s=importlib.util.spec_from_file_location('operations',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Fields:
 def __init__(self,_):self.values={'_wpnonce':'fresh-core','_acf_nonce':'fresh-acf','wpmem_block_meta_nonce':'must-not-be-added','ozmd_source_nonce':'must-not-be-added'}
class Module:pass
module=Module();module.Fields=Fields
class Client:
 def __init__(self):self.sent=None
 def request(self,url,data=None):
  if data is None:return [b'ordinary editor']
  self.sent=urllib.parse.parse_qs(data.decode(),keep_blank_values=True);return [b'saved']
c=Client();start=time.monotonic()
q={'endpoint':'wordpress.edit','target':99,'arguments':{'body':{'post_ID':99,'acf':{'field_text':'42'}},'nonce_fields':['_wpnonce','_acf_nonce']}}
assert m.dispatch(q,{}, {'markdown':c},{'markdown':module},None)==99
assert c.sent=={'post_ID':['99'],'acf[field_text]':['42'],'_wpnonce':['fresh-core'],'_acf_nonce':['fresh-acf']},c.sent
assert q['arguments']['body']=={'post_ID':99,'acf':{'field_text':'42'}}
q['arguments']['nonce_fields'].append('unavailable_nonce')
try:m.dispatch(q,{}, {'markdown':c},{'markdown':module},None)
except RuntimeError:pass
else:raise AssertionError('Missing recorded participant was inferred')
print({'form_participants_exact':True,'checks':4,'seconds':round(time.monotonic()-start,5)})
