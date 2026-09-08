"""Real HTTP, threads and scheduler; all traffic bound to 127.0.0.1."""
import json, socket, threading, time, unittest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit


ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'

def record(seq,text='ambient',sender='test-other-0',nonce=None):
    r=dict(seq=seq,ts=datetime.now(timezone.utc).isoformat(),text=text,**{'from':sender})
    if nonce is not None:r['nonce']=nonce
    return r

class FakeVenue:
    def __init__(self,scenario,scale):
        self.started=time.monotonic(); self.scenario=scenario; self.scale=scale; self.lock=threading.Lock(); self.posts=[]; self.gets=0; self.failures=0
        self.rows=[] if scenario=='no_go' else [record(i,sender='did:key:test-other-'+str(i%3)) for i in range(1,6)]
        venue=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a): pass
            def reply(self,data,code=200):
                body=json.dumps(data).encode()
                try:
                    self.send_response(code); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
                except (BrokenPipeError,ConnectionResetError): pass
            def do_GET(self):
                since=int(parse_qs(urlsplit(self.path).query).get('since',['0'])[0])
                with venue.lock:
                    venue.gets+=1; follow=venue.gets>1
                    timeout=follow and ((venue.scenario=='recover' and venue.failures<1) or (venue.scenario=='deadline_timeout' and venue.failures<2 and (time.monotonic()-venue.started)/venue.scale>167))
                    if timeout:
                        venue.failures+=1
                        # New ambient message arrives while the client has no reply.
                        venue.rows.append(record(len(venue.rows)+1,'arrived-during-timeout'))
                    rows=[dict(r) for r in venue.rows if r['seq']>since]
                    last=len(venue.rows)
                if timeout:
                    time.sleep(14*venue.scale); self.reply(dict(room='credence',generation=0,messages=rows,last_seq=last)); return
                if follow and venue.scenario=='http_503': self.reply({'error':'injected'},503); return
                if follow and venue.scenario=='gap' and len(rows): rows=rows[1:]
                data=dict(room='credence',generation=1 if follow and venue.scenario=='reset' else 0,messages=rows,last_seq=last)
                self.reply(data)
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                with venue.lock:
                    venue.posts.append(body); r=record(len(venue.rows)+1,body['text'],body['did'],body['nonce']); venue.rows.append(r)
                if venue.scenario=='lost_post_receipt':
                    time.sleep(14*venue.scale)
                if venue.scenario=='wrong_receipt':r=dict(r,text='wrong receipt')
                self.reply({'posted':r})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01})
    def __enter__(self):self.thread.start();return self
    def __exit__(self,*a):self.server.shutdown();self.server.server_close();self.thread.join()

