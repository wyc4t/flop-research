import hashlib,io,json,unittest
from pathlib import Path
from datetime import datetime,timezone
import test_integrated as tests
root=Path(__file__).resolve().parent
out=root/'test-results'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out.mkdir(parents=True)
tests.OUT=out
s=io.StringIO();result=unittest.TextTestRunner(stream=s,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
(out/'tests.txt').write_text(s.getvalue())
(out/'manifest.json').write_text(json.dumps(dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),traffic='loopback-only via test opener',signature_test='existing public v1.2 signature; new test bundles use explicit verifier stub',hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('*.py')}),indent=2))
print(s.getvalue());print(out);raise SystemExit(not result.wasSuccessful())
