#!/usr/bin/env python3
"""Bounded four-probe runner. Default is fully offline; never reads secrets."""
import argparse, hashlib, importlib.util, json, os, re, threading, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from recovery import CaptureState, Abort

ROOT = Path(__file__).resolve().parent
PIN = 'dad6cd5c222a91eff9639edbea9c20ef8b3f73a4f499546220847faa4496ab8c'
def canonical(x): return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
def utc(): return datetime.now(timezone.utc).isoformat()
def ts(s):
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if d.tzinfo is None: raise ValueError('naive venue timestamp')
    return d.timestamp()
def load_plan():
    e = json.loads((ROOT/'plan-v1.3.json').read_text())
    if hashlib.sha256(canonical(e['plan'])).hexdigest() != PIN or e['plan_sha256'] != PIN: raise ValueError('plan hash mismatch')
    return e['plan']
def client():
    spec = importlib.util.spec_from_file_location('starter', '/Users/steph/technocore-did-starter/technocore_agent.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

def signed_bundle(private_key):
    """For an already-unlocked trusted local signer. No key loading or prompting."""
    p = load_plan(); m = client()
    if m.did_from_private_key(private_key) != p['self_did']: raise ValueError('wrong existing DID')
    nonce = time.time_ns()
    return {'plan_sha256': PIN, 'messages': [dict(did=p['self_did'], text=q['text'], nonce=str(nonce+i), sig=m.sign_bytes(private_key, m.message_payload(p['room'], str(nonce+i), q['text'])[1])) for i,q in enumerate(p['probes'])]}

def validate_bundle(b, p, m):
    if b.get('plan_sha256') != PIN or len(b.get('messages', [])) != 4: raise ValueError('wrong bundle')
    last = -1
    for q, x in zip(p['probes'], b['messages']):
        if set(x) != {'did','text','nonce','sig'} or x['did'] != p['self_did'] or x['text'] != q['text']: raise ValueError('bundle differs from frozen plan')
        normalized, payload = m.message_payload(p['room'], x['nonce'], x['text'])
        if normalized != q['text'] or int(x['nonce']) <= last: raise ValueError('noncanonical text or nonce order')
        m.verify_bytes(x['did'], x['sig'], payload); last = int(x['nonce'])

class Log:
    def __init__(self, path):
        path.mkdir(parents=True, exist_ok=False); self.path=path; self.lock=threading.Lock()
    def put(self, name, obj):
        with self.lock, (self.path/name).open('a') as f:
            f.write(json.dumps(obj, ensure_ascii=True)+'\n'); f.flush(); os.fsync(f.fileno())

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *a, **k): raise RuntimeError('redirect refused')
class Transport:
    def __init__(self, log): self.log=log; self.opener=build_opener(NoRedirect())
    def request(self, url, body=None):
        method='GET' if body is None else 'POST'
        self.log.put('http.jsonl', dict(event='request', utc=utc(), monotonic=time.monotonic(), method=method, url=url, body=body))
        req=Request(url, data=None if body is None else canonical(body), method=method, headers={'Content-Type':'application/json','User-Agent':'TECH-EXP-002-v1.3'})
        try:
            with self.opener.open(req, timeout=10) as r:
                raw=r.read(5*1024*1024+1); status=r.status
            self.log.put('http.jsonl', dict(event='response', utc=utc(), monotonic=time.monotonic(), method=method, status=status, raw=raw.decode('utf8', errors='replace')))
            if len(raw)>5*1024*1024 or status!=200: raise ValueError('invalid HTTP response')
            return json.loads(raw)
        except HTTPError as e:
            self.log.put('http.jsonl', dict(event='http_error', utc=utc(), status=e.code, raw=e.read(16384).decode('utf8', errors='replace'))); raise
        except Exception as e:
            self.log.put('http.jsonl', dict(event='transport_failure', utc=utc(), error_type=type(e).__name__)); raise

def records(data):
    if data.get('room')!='credence' or not isinstance(data.get('messages'),list): raise ValueError('invalid room response')
    out=sorted(data['messages'], key=lambda r:r['seq'])
    for r in out:
        if type(r['seq']) is not int or r['seq']<1 or not isinstance(r['from'],str) or not isinstance(r['text'],str): raise ValueError('malformed record')
        ts(r['ts'])
    if len({r['seq'] for r in out})!=len(out): raise ValueError('duplicate seq')
    return out

def gate(rows, now, p):
    g=p['block_start_gate']; excluded=g['exclude_prior_probe_ids']
    recent=[r for r in rows if now-300 <= ts(r['ts']) <= now+10]
    ambient=[r for r in recent if not any(x in r['text'] for x in excluded)]
    dids={r['from'] for r in ambient if r['from']!=p['self_did'] and r['from'].startswith('did:key:')}
    return dict(decision='GO' if len(ambient)>=5 and len(dids)>=3 else 'NO-GO', read_utc=datetime.fromtimestamp(now,timezone.utc).isoformat(), ambient_seqs=[r['seq'] for r in ambient], other_dids=sorted(dids), excluded_seqs=[r['seq'] for r in recent if r not in ambient])

class Capture:
    def __init__(self, transport, log, p):
        self.t=transport; self.log=log; self.p=p; self.state=None
        self.error=None; self.stop=threading.Event(); self.lock=threading.RLock()
        self.pending=False; self.next_deadline=None
    @property
    def rows(self): return self.state.rows if self.state else {}
    def read(self, initial=False):
        cursor=self.state.cursor if self.state else None
        url=self.p['base_url']+'/r/credence?format=json&limit=200&n='+str(time.time_ns())
        if not initial: url+='&since='+str(cursor)
        data=self.t.request(url); rows=records(data)
        if type(data.get('generation')) is not int: raise ValueError('missing generation')
        if initial:
            cursor=rows[0]['seq']-1 if rows else data.get('last_seq')
            if type(cursor) is not int or cursor<0: raise ValueError('invalid initial cursor')
            self.state=CaptureState(cursor,data['generation'],time.monotonic())
        with self.lock:
            self.state.accept(time.monotonic(),dict(data,messages=rows))
            for r in rows: self.log.put('messages.jsonl',r)
            self.log.put('events.jsonl',dict(event='capture_ok',utc=utc(),cursor=self.state.cursor,generation=self.state.generation))
        return rows
    def loop(self):
        while not self.stop.is_set():
            with self.lock:
                now=time.monotonic(); retry=self.state.retry_at
                if retry is not None and now<retry: delay=retry-now
                elif self.next_deadline is not None and now+10>=self.next_deadline and not self.state.failures: delay=.25
                else: delay=0; self.pending=True
            if delay:
                self.stop.wait(delay); continue
            try: self.read()
            except Exception as e:
                with self.lock:
                    try:
                        if isinstance(e,Abort): raise e
                        kind='timeout' if isinstance(e,TimeoutError) else 'connection_error' if isinstance(e,ConnectionError) or (isinstance(e,URLError) and isinstance(e.reason,(ConnectionError,TimeoutError))) else 'fatal_read'
                        if isinstance(e,HTTPError): kind='http_'+str(e.code)
                        self.state.read_failure(time.monotonic(),kind)
                        self.log.put('events.jsonl',dict(event='read_recovery',utc=utc(),error_type=type(e).__name__,cursor=self.state.cursor,retry_at_monotonic=self.state.retry_at))
                    except Abort as fatal:
                        self.error=str(fatal); self.stop.set()
            finally:
                with self.lock: self.pending=False
            with self.lock: retry=self.state.retry_at
            self.stop.wait(2 if retry is None else max(0,retry-time.monotonic()))

def attribution(rows, posts, p, m=None):
    out=[]
    for r in rows:
        verification='not_reverified'
        if m and r.get('sig'):
            try: m.verify_bytes(r['from'],r['sig'],m.message_payload(p['room'],r['nonce'],r['text'])[1]); verification='valid'
            except Exception: verification='invalid'
        for q, post in posts:
            if r['seq']<=post['seq']: continue
            delta=ts(r['ts'])-ts(post['ts']); token=bool(re.search(r'(?<![A-Za-z0-9_])'+re.escape(q['probe_id'])+r'(?![A-Za-z0-9_])',r['text']))
            inside=0<=delta<=120; other=r['from']!=p['self_did']
            if token or inside:
                out.append(dict(probe_id=q['probe_id'], seq=r['seq'], venue_ts=r['ts'], claimed_did=r['from'], signature=verification, latency_seconds=delta, within_120_seconds=inside, attributable_by_id=token, counted=token and inside and other, manual_review=inside and other and not token, exact_ack=r['text']=='ACK '+q['probe_id'], self_excluded=not other))
    return out

def execute(p, bundle, transport, log, approval, m):
    if approval!=PIN or hashlib.sha256(canonical(p)).hexdigest()!=PIN: raise ValueError('explicit matching frozen plan required')
    validate_bundle(bundle,p,m)
    # Written durably before any network call; never cleared automatically.
    with (ROOT/('live-'+PIN+'.lock')).open('x') as f:
        f.write(utc()); f.flush(); os.fsync(f.fileno())
    capture=Capture(transport,log,p); posts=[]; thread=None; attempts=0; status='ABORTED'
    try:
        rows=capture.read(initial=True)
        if any(q['probe_id'] in r['text'] for q in p['probes'] for r in rows): raise ValueError('current probe ID already observed')
        result=gate(rows,time.time(),p); log.put('events.jsonl',dict(event='gate',**result))
        if result['decision']!='GO': status='NO-GO'; return
        # A public signed nonce is checked against observed same-DID records before writes.
        previous=[int(r['nonce']) for r in rows if r['from']==p['self_did'] and str(r.get('nonce','')).isdigit()]
        if previous and int(bundle['messages'][0]['nonce'])<=max(previous): raise ValueError('signed nonce is stale')
        anchor=time.monotonic(); capture.next_deadline=anchor
        thread=threading.Thread(target=capture.loop); thread.start()
        for i,(q,body) in enumerate(zip(p['probes'],bundle['messages'])):
            deadline=anchor+q['target_offset_seconds_from_block_start']
            capture.stop.wait(max(0,deadline-time.monotonic()))
            with capture.lock:
                if capture.error or capture.pending: raise RuntimeError(capture.error or 'read in flight at dispatch deadline')
                capture.state.dispatch_due(time.monotonic(),deadline)
                attempts+=1
                log.put('events.jsonl',dict(event='dispatch',probe_id=q['probe_id'],attempt=attempts,utc=utc(),monotonic=time.monotonic(),target_monotonic=deadline,lateness_seconds=time.monotonic()-deadline))
                # Log I/O is part of the deadline budget; never send after a slow fsync.
                if time.monotonic()-deadline>1: raise RuntimeError('dispatch logging exceeded timing tolerance')
                data=transport.request(p['base_url']+'/r/credence?format=json',body)
                post=data.get('posted',{}); records(dict(room='credence',messages=[post]))
                if post['from']!=body['did'] or post['text']!=body['text'] or str(post.get('nonce'))!=str(body['nonce']): raise ValueError('POST receipt mismatch; outcome uncertain')
                if abs(ts(post['ts'])-time.time())>30: raise ValueError('venue/client clock discrepancy exceeds 30 seconds')
                posts.append((q,post)); log.put('posts.jsonl',dict(probe=q,posted=post,window_end_utc=datetime.fromtimestamp(ts(post['ts'])+120,timezone.utc).isoformat()))
                capture.next_deadline=anchor+p['probes'][i+1]['target_offset_seconds_from_block_start'] if i<3 else None
        # Require a post-cutoff successful read, even if recovering at the end.
        finish=time.monotonic()+max(135,max(ts(x['ts'])+135 for _,x in posts)-time.time())
        capture.stop.wait(max(0,finish-time.monotonic()))
        while True:
            with capture.lock:
                if capture.error: raise RuntimeError(capture.error)
                if capture.state.last_ok>=finish and not capture.state.failures: break
            if time.monotonic()>finish+30: raise RuntimeError('final capture recovery deadline exceeded')
            capture.stop.wait(.25)
        status='COMPLETE'
    except BaseException as e:
        log.put('events.jsonl',dict(event='abort',utc=utc(),error_type=type(e).__name__,reason=str(e)))
        raise
    finally:
        capture.stop.set()
        if thread: thread.join()
        try:
            for a in attribution(list(capture.rows.values()),posts,p,m): log.put('attribution.jsonl',a)
        finally:
            log.put('summary.jsonl',dict(status=status,plan_sha256=PIN,post_attempts=attempts,confirmed_posts=len(posts),captured_messages=len(capture.rows),capture_error=capture.error,utc=utc()))


def main():
    a=argparse.ArgumentParser(); a.add_argument('--dry-run',action='store_true'); a.add_argument('--live',action='store_true'); a.add_argument('--approved-plan-sha256'); a.add_argument('--signed-bundle',type=Path); a.add_argument('--output',type=Path); args=a.parse_args()
    p=load_plan()
    if not args.live:
        # No transport, imports of signing dependencies, or secret files in this path.
        print((ROOT/'APPROVAL.md').read_text())
        print('DRY RUN: 0 network reads; 0 network writes; 0 secret access.')
        return
    if args.dry_run or args.approved_plan_sha256!=PIN or not args.signed_bundle or not args.output: a.error('live requires matching approval hash, signed bundle and fresh output directory')
    b=json.loads(args.signed_bundle.read_text()); m=client(); validate_bundle(b,p,m)
    log=Log(args.output); (args.output/'plan.json').write_bytes((ROOT/'plan-v1.3.json').read_bytes())
    execute(p,b,Transport(log),log,args.approved_plan_sha256,m)
if __name__=='__main__':
    try: main()
    except Exception as e: raise SystemExit('Stopped safely: '+type(e).__name__+' (see local logs; no automatic retry).')
