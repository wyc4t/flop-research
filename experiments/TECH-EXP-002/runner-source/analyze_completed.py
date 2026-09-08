"""Offline audit of the completed attempt; raw evidence remains unchanged."""
import hashlib,json
from datetime import datetime,timedelta
from pathlib import Path
import runner
ROOT=Path(__file__).resolve().parent
RUN=ROOT/'runs/attempt-004'
def read(name):return [json.loads(x) for x in (RUN/name).read_text().splitlines()]
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
s=read('summary.jsonl')[0];p=json.loads((RUN/'plan.json').read_text())['plan']
assert s['status']=='COMPLETE' and s['post_attempts']==s['confirmed_posts']==4
assert hashlib.sha256(runner.canonical(p)).hexdigest()==runner.PIN
http=read('http.jsonl');events=read('events.jsonl');posts=read('posts.jsonl');rows=read('messages.jsonl');attrs=read('attribution.jsonl');byseq={x['seq']:x for x in rows}
assert len(byseq)==len(rows)
assert list(byseq)==list(range(rows[0]['seq'],rows[-1]['seq']+1))
requests=[x for x in http if x['event']=='request'];writes=[x for x in requests if x['method']=='POST']
assert len(writes)==4
assert [x['body']['text'] for x in writes]==[q['text'] for q in p['probes']]
assert all(x['url']==p['base_url']+'/r/credence?format=json' for x in writes)
assert len([x for x in events if x['event']=='gate'])==1
assert not any(x['event']=='abort' for x in events)
m=runner.client()
for x in rows:
 if x['seq']>=posts[0]['posted']['seq']:
  m.verify_bytes(x['from'],x['sig'],m.message_payload('credence',x['nonce'],x['text'])[1])
getresponses=[x for x in http if x['event']=='response' and x['method']=='GET']
for x in getresponses:
 payload=json.loads(x['raw']);assert payload['generation']==0
 for r in payload['messages']:assert byseq[r['seq']]==r
assert dt(getresponses[-1]['utc'])>max(dt(x['posted']['ts'])+timedelta(seconds=135) for x in posts)
out=[]
for q,z in zip(p['probes'],posts):
 post=z['posted'];end=dt(post['ts'])+timedelta(seconds=120)
 # Use exact datetime arithmetic for reported latency rather than epoch floats.
 aa=[a for a in attrs if a['probe_id']==q['probe_id'] and a['counted']]
 evidence=[dict(seq=a['seq'],ts=a['venue_ts'],did=a['claimed_did'],text=byseq[a['seq']]['text'],latency_seconds=(dt(a['venue_ts'])-dt(post['ts'])).total_seconds(),signature=a['signature']) for a in aa]
 all_window=[r['seq'] for r in rows if r['seq']>post['seq'] and dt(post['ts'])<=dt(r['ts'])<=end and r['from']!=p['self_did']]
 out.append(dict(condition=q['condition'],probe_id=q['probe_id'],venue_seq=post['seq'],venue_ts=post['ts'],window_end=end.isoformat(),response=bool(evidence),responses=len(evidence),distinct_dids=len({x['did'] for x in evidence}),first_response_seconds=min((x['latency_seconds'] for x in evidence),default=None),all_other_records_in_window=all_window,evidence=evidence,requested_ack_count=sum(x['text']=='ACK '+q['probe_id'] for x in evidence) if q['semantics']=='respond' else None))
dispatch=[x for x in events if x['event']=='dispatch']
manual=[dict(seq=6178,probe_id='t86f06e052c',decision='exclude',reason='Explicitly references A ID t3efd0ef3f2; no reference to D. Timing alone is not attribution.')]
report=dict(experiment_id='TECH-EXP-002',version='v1.3',status='COMPLETE_SINGLE_BLOCK',plan_sha256=runner.PIN,results=out,manual_review=manual,venue_gaps_seconds=[(dt(b['posted']['ts'])-dt(a['posted']['ts'])).total_seconds() for a,b in zip(posts,posts[1:])],dispatch_lateness_seconds=[x['lateness_seconds'] for x in dispatch],GET_requests=sum(x['method']=='GET' for x in requests),POST_requests=len(writes),read_recoveries=sum(x['event']=='read_recovery' for x in events),transport_failures=sum(x['event'] in ('transport_failure','http_error') for x in http),captured_seq_range=[rows[0]['seq'],rows[-1]['seq']],final_successful_GET_utc=getresponses[-1]['utc'],gate=[x for x in events if x['event']=='gate'][0])
(RUN/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
manifest={name:hashlib.sha256((RUN/name).read_bytes()).hexdigest() for name in ['plan.json','http.jsonl','messages.jsonl','posts.jsonl','events.jsonl','attribution.jsonl','summary.jsonl','analysis.json']}
(RUN/'evidence-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('results','gate')},indent=2))
for x in out:print(x['condition'],x['responses'],x['distinct_dids'],x['first_response_seconds'])
