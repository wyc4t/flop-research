import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
e=json.loads((ROOT.parent/'TECH-EXP-002-v1.2/plan-v1.2.json').read_text())
assert hashlib.sha256(canonical(e['plan'])).hexdigest()==e['plan_sha256']
p=copy.deepcopy(e['plan'])
p.update(protocol_version='probe-protocol-v1.3',amends='probe-protocol-v1.2',status='FROZEN_AWAITING_NEW_APPROVAL',amendment_reason='Bounded read-only recovery with unchanged cursor, generation checks, synchronized write admission and ten-second pre-dispatch read guard. New IDs; interrupted v1.2 excluded from complete comparison.')
p['prior_plans'].append(dict(sha256=e['plan_sha256'],version='probe-protocol-v1.2',classification='interrupted after B/C; excluded from complete controlled comparison'))
p['block_start_gate']['exclude_prior_probe_ids']=sorted(set(p['block_start_gate']['exclude_prior_probe_ids']+[q['probe_id'] for q in p['probes']]))
p['execution'].update(abort_policy='Initial gate read is never retried. Later GET timeouts/connection errors: at most two retries with 2s/5s backoff, total freshness budget 30s. HTTP errors, malformed data, gaps, generation changes, uncertain POSTs or missed deadlines abort. No POST retries or resumption.',capture='Cursor polling limit=200 every 2s outside a 10s pre-dispatch guard. No new normal read during guard. Pending recovery or in-flight read at dispatch deadline aborts rather than moving schedule. Capture must be at most 15s old at dispatch.',recovery_backoff_seconds=[2,5],recovery_max_staleness_seconds=30,dispatch_capture_max_age_seconds=15,pre_dispatch_read_guard_seconds=10,generation_rule='Require integer generation and reject any change.',completion='Capture until every venue window plus 15s grace has ended, then require a successful read after that cutoff. Final recovery bounded by 30s. Venue/client skew >30s aborts.')
for q in p['probes']:
 old=q['probe_id'];q['probe_id']='t'+hashlib.sha256(('TECH-EXP-002-v1.3:'+q['condition']).encode()).hexdigest()[:10];q['text']=q['text'].replace(old,q['probe_id'])
env=dict(plan_sha256=hashlib.sha256(canonical(p)).hexdigest(),plan=p)
(ROOT/'plan-v1.3.json').write_text(json.dumps(env,indent=2)+'\n')
lines=['# TECH-EXP-002 v1.3 — approval required','','Venue: https://technocore.chat/r/credence','','SHA256: '+env['plan_sha256'],'','One gate: ≥5 ambient messages / ≥3 other DIDs in five minutes, excluding all v1/v1.1/v1.2 IDs. NO-GO exits. Same existing DID. B → C → A → D at 0/180/360/540 seconds; 120-second venue windows.','',p['execution']['abort_policy'],'',p['execution']['capture'],'']
for q in p['probes']:lines += [f"## {q['condition']} +{q['target_offset_seconds_from_block_start']}s",'',q['text'],'']
(ROOT/'APPROVAL.md').write_text('\n'.join(lines))
print(env['plan_sha256'])
