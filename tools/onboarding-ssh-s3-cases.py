"""Actual SSH probe of the generated capture source and real experimental S3."""
import importlib.util,json,secrets,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT_SCOPE='Generated WP/MariaDB real pinned SSH inventory -> admitted capture -> experimental S3 fixed versions/retention -> separate test signature -> isolated restore and registration; no production or 72h state'
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Integration:
    def __init__(self,db,web,sql,run,results):
        self.db,self.web,self.sql,self.run,self.results=db,web,sql,run,results
        self.created=[];self.temp=tempfile.TemporaryDirectory(prefix='owr-onboarding-ssh-');self.root=Path(self.temp.name)
        self.transport=load('onboarding_real_s3','queue-s3-adapter.py');self.ready=False
    def ex(self,name,*args,**kw):return self.run('docker','exec',*(['-i'] if kw.get('input') is not None else []),name,*args,**kw)
    def put(self,name,path,value,mode='644'):
        p=self.root/'upload';p.write_text(value if isinstance(value,str) else json.dumps(value));self.run('docker','cp',str(p),name+':'+path);self.ex(name,'chown','root:root',path);self.ex(name,'chmod',mode,path)
    def setup(self,c,digest):
        self.host='owr-onboarding-ssh-'+secrets.token_hex(5);self.client=self.host+'-client';secret=secrets.token_hex(24)
        self.sql("CREATE USER 'owr_inspector'@'%' IDENTIFIED BY '"+secret+"'; GRANT SELECT ON lab.* TO 'owr_inspector'@'%';")
        for name,extra in [(self.host,['--volumes-from',self.web+':ro']),(self.client,['-v',str(ROOT)+':/repo:ro'])]:
            self.created.append(name)
            self.run('docker','run','-d','--name',name,'--label','owr.onboarding-ssh=generated','--network','container:'+self.db,*extra,'--entrypoint','sleep','owr-external-lab:local','infinity')
        for key in ('key','hostkey','wrong'):self.run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(self.root/key))
        self.ex(self.host,'mkdir','-p','/opt/owr','/etc/owr','/run/sshd')
        for file in ('host-inventory-ssh.py','notification-transfer.py','host-inventory.php'):self.run('docker','cp',str(ROOT/'tools'/file),self.host+':/opt/owr/'+file)
        self.ex(self.host,'chown','-R','root:root','/opt/owr');self.ex(self.host,'chmod','-R','go-w','/opt/owr')
        self.ex(self.host,'useradd','-m','-s','/bin/sh','inspector');self.ex(self.host,'usermod','-p','*','inspector')
        self.put(self.host,'/etc/owr/hostkey',(self.root/'hostkey').read_text(),'600')
        self.put(self.host,'/etc/owr/keys','restrict,command="/usr/bin/python3 -B /opt/owr/host-inventory-ssh.py endpoint --config /etc/owr/endpoint.json" '+(self.root/'key.pub').read_text())
        endpoint=dict(site_id=c['site_id'],config_sha256=digest,php='/usr/local/bin/php',probe=dict(DB_HOST='127.0.0.1',DB_NAME='lab',DB_PREFIX='wp_',DB_USER='owr_inspector',DB_PASSWORD=secret,ROOT='/var/www/html'))
        self.put(self.host,'/etc/owr/endpoint.json',endpoint,'640');self.ex(self.host,'chgrp','inspector','/etc/owr/endpoint.json')
        self.put(self.host,'/etc/owr/sshd','\n'.join(['Port 2222','HostKey /etc/owr/hostkey','PidFile /run/sshd/inventory.pid','AuthorizedKeysFile /etc/owr/keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','PermitRootLogin no','AllowUsers inspector','AllowTcpForwarding no','AllowAgentForwarding no','PermitTTY no','PermitUserEnvironment no','DisableForwarding yes'])+'\n')
        self.ex(self.host,'/usr/sbin/sshd','-f','/etc/owr/sshd')
        self.put(self.client,'/key',(self.root/'key').read_text(),'600')
        self.pin='owr-inventory-'+c['site_id']+' '
        self.put(self.client,'/known',self.pin+(self.root/'hostkey.pub').read_text())
        self.conn=dict(site_id=c['site_id'],host='127.0.0.1',user='inspector',port=2222,identity_file='/key',known_hosts='/known')
        self.ready=True
    def evidence(self,c,inv,workspace,report,health):
        pre=load('real_preflight','deployment-preflight.py');ssh=load('real_inventory_ssh','host-inventory-ssh.py')
        if not self.ready:self.setup(c,pre.capture.digest(c))
        inv['observed_at']=datetime.now(timezone.utc).isoformat()
        def transport(conn,packet):
            q=self.ex(self.client,*ssh.command(conn),input=json.dumps(packet).encode(),must=False,timeout=30)
            if q.returncode:raise RuntimeError('dedicated SSH inventory failed')
            return json.loads(q.stdout)
        # Real host-key failure must not become cached successful evidence.
        if not self.results or not any(x.get('name')=='real_ssh_pinned_source_inventory' for x in self.results):
            self.put(self.client,'/known',self.pin+(self.root/'wrong.pub').read_text())
            bad=ssh.inspect(self.conn,c,inv,workspace,transport=transport)
            assert bad['host_observation']['state']=='unavailable'
            self.put(self.client,'/known',self.pin+(self.root/'hostkey.pub').read_text())
        assessment=ssh.inspect(self.conn,c,inv,workspace,transport=transport)
        assert assessment['host_observation']['state']=='validated_report',assessment.get('issues')
        assert [x['code'] for x in assessment['issues']]==['host_unverified_scope_remaining'],assessment['issues']
        at=datetime.now(timezone.utc).isoformat()
        if not any(x.get('name')=='real_ssh_pinned_source_inventory' for x in self.results):
            self.results.append(dict(name='real_ssh_pinned_source_inventory',passed=True,readonly_site=True,select_only=True,wrong_host_key_rejected=True))
        return dict(report,result=assessment,attempted_at=at),dict(health,attempted_at=at,report_at=at,state='ok')
    def preflight(self):
        result=self.transport.preflight()
        assert result['passed']
    def adapter(self,operations):
        base=self.transport.S3Adapter
        class Recorded(base):
            def put(self,*args):
                result=super().put(*args);operations.append(dict(self.operations[-1]));return result
            def get(self,*args):
                result=super().get(*args);operations.append(dict(self.operations[-1]));return result
        return Recorded
    def close(self):
        for name in reversed(self.created):self.run('docker','rm','-f','-v',name)
        self.temp.cleanup()

def exercise(db,web,php,sql,hold,ready,release,run,check,results,output):
    integration=Integration(db,web,sql,run,results)
    try:load('admission_cases','first-site-daily-admission-cases.py').exercise(db,web,php,sql,hold,ready,release,run,check,results,output,roundtrip=True,integration=integration)
    finally:integration.close()
