import copy, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from test_site_materials import m, Store, site


def page_bytes(size, japanese=False):
    row=site()['entries'][0]
    row['nodes']=[{'type':'paragraph','text':''} for _ in range(400)]
    remaining=size-len(m.canon(row))
    for node in row['nodes']:
        n=min(remaining,18000)
        node['text']=('あ'*(n//3)+'a'*(n%3)) if japanese else 'a'*n
        remaining-=n
    assert remaining==0 and len(m.canon(row))==size
    return row


class Limits(unittest.TestCase):
    def test_asset_boundary_roundtrip_ascii_and_utf8(self):
        for japanese in (False,True):
            for delta in (-1,0,1):
                with self.subTest(japanese=japanese,delta=delta),tempfile.TemporaryDirectory() as d:
                    store=Store();repo=m.Repository(store,d,'bounds/');s=site()
                    s['entries']=[page_bytes(m.MAX_ASSET_BYTES+delta,japanese)]
                    if delta<=0:
                        ref=repo.save('boundary',None,s)
                        self.assertEqual(m.receive(store,ref)['site'],s)
                    else:
                        with self.assertRaisesRegex(ValueError,'Canonical asset size'):repo.save('boundary',None,s)
                        self.assertEqual(store.writes,0)
                        self.assertFalse((Path(d)/'head.json').exists())
                        self.assertFalse((Path(d)/'boundary.json').exists())

    def test_old_reproduction_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store();repo=m.Repository(store,d,'bounds/');s=site()
            s['entries'][0]['nodes']=[{'type':'paragraph','text':'a'*20000} for _ in range(320)]
            with self.assertRaisesRegex(ValueError,'Canonical asset size'):repo.save('oversize',None,s)
            self.assertEqual(store.writes,0)
            self.assertFalse((Path(d)/'head.json').exists())

    def test_large_later_asset_does_not_partially_store(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store();repo=m.Repository(store,d,'bounds/');s=site();old=repo.save('old',None,s)
            before={p.name:p.read_bytes() for p in Path(d).glob('*.json')};count=store.writes
            large=page_bytes(m.MAX_ASSET_BYTES+1);large['id']='z-large';large['slug']='z-large'
            s['entries'].append(large)
            with self.assertRaises(ValueError):repo.save('rejected',old,s)
            self.assertEqual(store.writes,count)
            self.assertEqual(before,{p.name:p.read_bytes() for p in Path(d).glob('*.json')})
            self.assertEqual(m.receive(store,old)['site'],site())

    def test_manifest_budget_boundary(self):
        # Independently account for the complete preflight envelope including Q,
        # parent, policy and worst-case fixed-version references.
        s=site();s['entries']=[page_bytes(4*1024*1024)]
        second=copy.deepcopy(s['entries'][0]);second.update(id='services',slug='services');s['entries'].append(second)
        def budget(s):
            objects=[{'id':r['id'],'ref':'x'*(m.MAX_REFERENCE_BYTES-2),'raw_sha256':m.sha(m.canon(r)),'raw_size':len(m.canon(r)),'encoding':'gzip'} for r in s['entries']]
            manifest={'schema':'owr-site-generation-v1','site_title':s['title'],'landing':s['landing'],'objects':objects,'expected':m.expected(s),'parent':None,'operation':'boundary','policy':'integrity','approval_ref':None,'protect_until':2000000000+35*86400,'rules':'portable-nodes-v1'}
            return len(m.canon(manifest))
        excess=budget(s)-m.MAX_STORED_BYTES
        # Keep the digit counts of raw_size fixed while trimming text.
        s['entries'][1]['nodes'][0]['text']=s['entries'][1]['nodes'][0]['text'][:-excess]
        self.assertEqual(budget(s),m.MAX_STORED_BYTES)
        for delta in (-1,0,1):
            candidate=copy.deepcopy(s);text=candidate['entries'][1]['nodes'][0]['text']
            candidate['entries'][1]['nodes'][0]['text']=text[:-1] if delta<0 else text+'a'*delta
            with self.subTest(delta=delta),tempfile.TemporaryDirectory() as d,patch.object(m.time,'time',return_value=2000000000):
                store=Store();repo=m.Repository(store,d,'bounds/')
                if delta<=0:
                    ref=repo.save('boundary',None,candidate)
                    self.assertEqual(m.receive(store,ref)['site'],candidate)
                else:
                    with self.assertRaisesRegex(ValueError,'Manifest size budget'):repo.save('boundary',None,candidate)
                    self.assertEqual(store.writes,0);self.assertFalse((Path(d)/'boundary.json').exists())

    def test_size_failure_then_corrected_request_can_start(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store();repo=m.Repository(store,d,'bounds/');s=site();s['entries']=[page_bytes(m.MAX_ASSET_BYTES+1)]
            with self.assertRaises(ValueError):repo.save('same',None,s)
            self.assertEqual(store.writes,0)
            ref=repo.save('same',None,site());self.assertEqual(m.receive(store,ref)['site'],site())

if __name__=='__main__':unittest.main()
