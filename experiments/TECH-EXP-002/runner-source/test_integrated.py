import contextlib,io,json,threading,time,types,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,build_opener,ProxyHandler
import runner as r
from fake_venue import FakeVenue

ROOT=Path(__file__).resolve().parent
P=r.load_plan()
OUT=ROOT/'test-results'
class FastTime:
    def __init__(self):self.start=time.monotonic()
    def monotonic(self):return (time.monotonic()-self.start)/.02
    time_ns=staticmethod(time.time_ns)
    time=staticmethod(time.time)
class FastEvent:
    def __init__(self):self.e=threading.Event()
    def wait(self,n):return self.e.wait(max(0,n)*.02)
    def set(self):self.e.set()
    def is_set(self):return self.e.is_set()
class LoopbackOpener:
    def __init__(self,port):self.port=port;self.opener=build_opener(ProxyHandler({}),r.NoRedirect())
    def open(self,req,timeout):
        assert req.full_url.startswith('https://technocore.chat/r/credence?')
        local=req.full_url.replace('https://technocore.chat','http://127.0.0.1:'+str(self.port),1)
        return self.opener.open(Request(local,data=req.data,method=req.method,headers=dict(req.headers)),timeout=timeout*.02)
class VerifierStub:
    """Only used for new unsigned test payloads. Real signatures tested separately."""
    def message_payload(self,room,nonce,text):return text,f'{room}|{nonce}|{text}'.encode()
    def verify_bytes(self,*a):pass
class Tests(unittest.TestCase):
    def run_case(self,scenario):
        d=OUT/scenario;d.mkdir(parents=True); log=r.Log(d/'run')
        bundle=dict(plan_sha256=r.PIN,messages=[dict(did=P['self_did'],text=q['text'],nonce=str(time.time_ns()+i),sig='TEST-ONLY') for i,q in enumerate(P['probes'])])
        fast=FastTime()
        with FakeVenue(scenario,.02) as venue,patch.object(r,'ROOT',d),patch.object(r,'time',fast),patch.object(r,'threading',types.SimpleNamespace(RLock=threading.RLock,Lock=threading.Lock,Thread=threading.Thread,Event=FastEvent)):
            t=r.Transport(log);t.opener=LoopbackOpener(venue.server.server_port)
            try:r.execute(P,bundle,t,log,r.PIN,VerifierStub())
            except Exception:pass
            s=json.loads((log.path/'summary.jsonl').read_text())
            with self.assertRaises(FileExistsError):r.execute(P,bundle,t,log,r.PIN,VerifierStub())
            evidence=dict(posts=venue.posts,rows=venue.rows,gets=venue.gets)
            (d/'server.json').write_text(json.dumps(evidence,indent=2))
        return s,evidence,log
    def test_healthy(self):
        s,e,log=self.run_case('healthy');self.assertEqual(s['status'],'COMPLETE');self.assertEqual(len(e['posts']),4)
        events=[json.loads(x) for x in (log.path/'events.jsonl').read_text().splitlines()]
        self.assertEqual(len([x for x in events if x['event']=='gate']),1)
        ds=[x for x in events if x['event']=='dispatch'];anchor=ds[0]['target_monotonic']
        for x,n in zip(ds,[0,180,360,540]):self.assertAlmostEqual(x['target_monotonic']-anchor,n);self.assertLess(x['lateness_seconds'],1)
        self.assertEqual(s['captured_messages'],len(e['rows']))
    def test_recover(self):
        s,e,log=self.run_case('recover');self.assertEqual(s['status'],'COMPLETE');self.assertEqual(s['captured_messages'],len(e['rows']))
        events=[json.loads(x) for x in (log.path/'events.jsonl').read_text().splitlines()]
        self.assertEqual(len([x for x in events if x['event']=='read_recovery']),1)
    def test_deadline_timeout(self):
        s,e,_=self.run_case('deadline_timeout');self.assertEqual(s['status'],'ABORTED');self.assertEqual(len(e['posts']),1)
    def test_lost_receipt(self):
        s,e,_=self.run_case('lost_post_receipt');self.assertEqual(s['status'],'ABORTED');self.assertEqual(len(e['posts']),1);self.assertEqual(s['confirmed_posts'],0)
    def test_http503(self):
        s,e,_=self.run_case('http_503');self.assertEqual(s['status'],'ABORTED');self.assertEqual(e['gets'],2)
    def test_gap(self):
        s,e,_=self.run_case('gap');self.assertEqual(s['status'],'ABORTED');self.assertEqual(len(e['posts']),1)
    def test_reset(self):
        s,e,_=self.run_case('reset');self.assertEqual(s['status'],'ABORTED');self.assertEqual(len(e['posts']),1)
    def test_no_go(self):
        s,e,_=self.run_case('no_go');self.assertEqual(s['status'],'NO-GO');self.assertEqual(e['posts'],[])
    def test_dry_offline(self):
        with patch('sys.argv',['runner','--dry-run']),patch.object(r,'client',side_effect=AssertionError),patch.object(r,'Transport',side_effect=AssertionError),contextlib.redirect_stdout(io.StringIO()):r.main()
    def test_old_bundle_rejected(self):
        old=json.loads((ROOT.parent/'TECH-EXP-002-v1.2/signed-bundle.json').read_text())
        with self.assertRaises(ValueError):r.validate_bundle(old,P,r.client())
    def test_real_signature_and_tampering(self):
        old=json.loads((ROOT.parent/'TECH-EXP-002-v1.2/signed-bundle.json').read_text());m=r.client();x=old['messages'][0]
        payload=m.message_payload('credence',x['nonce'],x['text'])[1]
        m.verify_bytes(x['did'],x['sig'],payload)
        with self.assertRaises(Exception):m.verify_bytes(x['did'],x['sig'],payload+b'changed')
    def test_120_second_boundary(self):
        q=P['probes'][0];post=dict(seq=1,ts='2026-09-08T12:00:00Z')
        a=r.attribution([dict(seq=2,ts='2026-09-08T12:02:00Z',text=q['probe_id'],**{'from':'did:key:other'}),dict(seq=3,ts='2026-09-08T12:02:00.000001Z',text=q['probe_id'],**{'from':'did:key:other'})],[(q,post)],P)
        self.assertEqual([x['counted'] for x in a],[True,False])
    def test_prior_exclusions(self):
        old=json.loads((ROOT.parent/'TECH-EXP-002-v1.2/plan-v1.2.json').read_text())['plan']
        self.assertTrue(set(q['probe_id'] for q in old['probes'])<=set(P['block_start_gate']['exclude_prior_probe_ids']))
        rows=[dict(seq=i,ts=r.utc(),text=old['probes'][0]['probe_id'],**{'from':'did:key:other'+str(i)}) for i in range(5)]
        self.assertEqual(r.gate(rows,time.time(),P)['decision'],'NO-GO')
