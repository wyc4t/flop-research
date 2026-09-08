"""Offline candidate policy. No HTTP client, signing, identity or publishing code."""
from dataclasses import dataclass, field

class Abort(RuntimeError):
    pass

@dataclass
class CaptureState:
    cursor: int
    generation: int
    last_ok: float
    rows: dict = field(default_factory=dict)
    failures: int = 0
    retry_at: float | None = None
    failed: bool = False
    trace: list = field(default_factory=list)

    def abort(self, now, reason):
        self.failed = True
        self.trace.append(dict(event='abort', at=now, reason=reason, cursor=self.cursor))
        raise Abort(reason)

    def read_failure(self, now, kind):
        if self.failed:
            raise Abort('already aborted')
        # Classifications supplied by a future transport adapter, never server text.
        if kind not in {'timeout', 'connection_error'}:
            self.abort(now, 'nonrecoverable read failure: '+kind)
        self.failures += 1
        if self.failures > 2 or now-self.last_ok >= 30:
            self.abort(now, 'read recovery budget exhausted')
        delay = (2, 5)[self.failures-1]
        self.retry_at = now+delay
        if self.retry_at-self.last_ok >= 30:
            self.abort(now, 'retry would exceed freshness budget')
        self.trace.append(dict(event='read_retry_scheduled', at=now, retry_at=self.retry_at, cursor=self.cursor, failure=kind))

    def accept(self, now, response):
        if self.failed:
            raise Abort('already aborted')
        if now-self.last_ok > 30:
            self.abort(now, 'response arrived after freshness budget')
        if self.retry_at is not None and now < self.retry_at:
            self.abort(now, 'retry completed before backoff')
        rows = response.get('messages')
        if response.get('room') != 'credence' or response.get('generation') != self.generation or not isinstance(rows, list):
            self.abort(now, 'room/generation/schema mismatch')
        # Validate the entire batch before recording anything or advancing cursor.
        candidate = self.cursor
        for record in rows:
            if not isinstance(record, dict) or type(record.get('seq')) is not int or record['seq'] != candidate+1:
                self.abort(now, 'gap, replay or invalid sequence')
            if not all(isinstance(record.get(k), str) for k in ('ts','from','text')):
                self.abort(now, 'malformed record')
            candidate = record['seq']
        if type(response.get('last_seq')) is not int or response['last_seq'] != candidate:
            self.abort(now, 'truncated/reset cursor')
        for record in rows:
            self.rows[record['seq']] = dict(record)
        self.cursor = candidate
        self.last_ok = now
        self.failures = 0
        self.retry_at = None
        self.trace.append(dict(event='read_success', at=now, cursor=self.cursor, received=len(rows)))

    def dispatch_due(self, now, deadline):
        """Decision only: never sends anything and never moves a deadline."""
        if self.failed:
            raise Abort('already aborted')
        if now < deadline:
            raise ValueError('not due')
        if now-deadline > 1 or self.failures or now-self.last_ok > 15:
            self.abort(now, 'scheduled dispatch lacks healthy capture or is late')
        self.trace.append(dict(event='simulated_dispatch_allowed', at=now, deadline=deadline))

    def write_failure(self, now):
        self.abort(now, 'uncertain POST: never retry')
