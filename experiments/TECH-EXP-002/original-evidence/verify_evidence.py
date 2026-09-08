"""Offline evidence verifier. Requires cryptography; no networking or key loading."""
import base64,hashlib,json,re
from datetime import datetime,timedelta
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
ROOT=Path(__file__).resolve().parent
E=ROOT/'evidence'
PIN='dad6cd5c222a91eff9639edbea9c20ef8b3f73a4f499546220847faa4496ab8c'
def require(ok,message):
 if not ok:raise ValueError(message)
def read(name):return [json.loads(s) for s in (E/name).read_text().splitlines()]
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def public(did):
 require(did.startswith('did:key:z'),'unexpected DID')
 alphabet='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
 value=did[len('did:key:z'):];n=0
 for c in value:n=n*58+alphabet.index(c)
 raw=b'\0'*(len(value)-len(value.lstrip('1')))+n.to_bytes((n.bit_length()+7)//8,'big')
 require(len(raw)==34 and raw[:2]==b'\xed\x01','unexpected key encoding')
 return Ed25519PublicKey.from_public_bytes(raw[2:])
def main():
 for name,digest in json.loads((ROOT/'SHA256.json').read_text()).items():
  target=(ROOT/name).resolve();require(target.is_relative_to(ROOT),'unsafe manifest path')
  require(hashlib.sha256(target.read_bytes()).hexdigest()==digest,'hash mismatch: '+name)
 envelope=json.loads((E/'plan.json').read_text());p=envelope['plan']
 canonical=json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
 require(hashlib.sha256(canonical).hexdigest()==envelope['plan_sha256']==PIN,'plan mismatch')
 block=read('block-records.jsonl');allrows=read('messages.jsonl')
 require([r['seq'] for r in block]==list(range(6164,6179)),'block sequence mismatch')
 require([r['seq'] for r in allrows]==list(range(5964,6179)),'capture discontinuity')
 require(block==[r for r in allrows if r['seq']>=6164],'block/capture mismatch')
 for r in block:
  payload=f"credence|{r['nonce']}|{r['text']}".encode()
  public(r['from']).verify(base64.urlsafe_b64decode(r['sig']+'=='),payload)
 http=read('http.jsonl');events=read('events.jsonl');posts=read('posts.jsonl')
 requests=[x for x in http if x['event']=='request']
 writes=[x for x in requests if x['method']=='POST']
 require(len(writes)==len(posts)==4,'POST count mismatch')
 require([w['body']['text'] for w in writes]==[q['text'] for q in p['probes']],'POST text mismatch')
 require(all(w['url']=='https://technocore.chat/r/credence?format=json' for w in writes),'unexpected write endpoint')
 require(len([x for x in events if x['event']=='gate'])==1,'gate count mismatch')
 require(read('summary.jsonl')[0]['status']=='COMPLETE','incomplete block')
 results=[]
 for q,z in zip(p['probes'],posts):
  post=z['posted'];require(post in block and post['text']==q['text'],'receipt mismatch')
  count=sum(r['seq']>post['seq'] and r['from']!=p['self_did'] and dt(post['ts'])<=dt(r['ts'])<=dt(post['ts'])+timedelta(seconds=120) and bool(re.search(r'(?<![A-Za-z0-9_])'+re.escape(q['probe_id'])+r'(?![A-Za-z0-9_])',r['text'])) for r in block)
  results.append((q['condition'],count))
 require(results==[('B',2),('C',0),('A',3),('D',1)],'outcome mismatch')
 last=[x for x in http if x['event']=='response' and x['method']=='GET'][-1]
 require(dt(last['utc'])>max(dt(z['posted']['ts'])+timedelta(seconds=135) for z in posts),'capture ended early')
 print('PASS: package hashes, frozen plan, 15 signatures, contiguous capture, four exact POSTs, one gate, final capture cutoff.')
 print('In-window ID-attributable replies: '+', '.join(f'{c}={n}' for c,n in results))
 print('Signature verification does not authenticate venue timestamps or establish semantic compliance.')
if __name__=='__main__':main()
