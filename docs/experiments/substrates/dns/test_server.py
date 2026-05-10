#!/usr/bin/env python3
"""Test script for keel-dns-server.py"""
import importlib.util
import sys
import threading
import time

spec = importlib.util.spec_from_file_location('kds', '/tmp/keel-models/dns/keel-dns-server.py')
kds = importlib.util.module_from_spec(spec)
sys.modules['kds'] = kds
spec.loader.exec_module(kds)

from dnslib import DNSRecord, QTYPE

db = kds.KeelZoneDB('fleet.example.')
db.add_record('agent-01.fleet.example.', 'A', 60, '10.0.0.1')
db.add_record('agent-01.fleet.example.', 'TXT', 15, 'heading|315|0.7|birth=1715000000')
db.add_record('agent-02.fleet.example.', 'A', 60, '10.0.0.2')
db.add_record('bearing.agent-01.agent-02.fleet.example.', 'TXT', 30, 'bearing|45|0.2|observed=1715000010')
db.add_record('trust.agent-01.fleet.example.', 'TXT', 3600, 'trust|0.95|0|proven=1715000000')

# Direct zone queries
print('=== Zone Query Tests ===')
r = db.query('agent-01.fleet.example.', QTYPE.A)
assert len(r) == 1, f"Expected 1 A record, got {len(r)}"
print(f'A record: {r[0].rdata} [TTL={r[0].ttl}s] ✓')

r = db.query('agent-01.fleet.example.', QTYPE.TXT)
assert len(r) == 1, f"Expected 1 TXT record, got {len(r)}"
print(f'TXT heading: {r[0].rdata} [TTL={r[0].ttl}s] ✓')

r = db.query('bearing.agent-01.agent-02.fleet.example.', QTYPE.TXT)
assert len(r) == 1, f"Expected 1 bearing, got {len(r)}"
print(f'Bearing: {r[0].rdata} [TTL={r[0].ttl}s] ✓')

r = db.query('trust.agent-01.fleet.example.', QTYPE.TXT)
assert len(r) == 1, f"Expected 1 trust, got {len(r)}"
print(f'Trust: {r[0].rdata} [TTL={r[0].ttl}s] ✓')

r = db.query('agent-99.fleet.example.', QTYPE.A)
assert len(r) == 0, f"Expected NXDOMAIN (0 records), got {len(r)}"
print(f'NXDOMAIN (dead agent): 0 records ✓')

# Network tests
print()
print('=== Network Tests ===')
srv = kds.KeelDNSServer(db, port=5358, host='127.0.0.1')
t = threading.Thread(target=srv.start, daemon=True)
t.start()
time.sleep(0.5)

tests = [
    ('agent-01.fleet.example.', 'A', 'A record', 
     lambda r: str(r.rr[0].rdata) == '10.0.0.1' and r.rr[0].ttl == 60),
    ('agent-01.fleet.example.', 'TXT', 'TXT heading',
     lambda r: 'heading|315' in str(r.rr[0].rdata) and r.rr[0].ttl == 15),
    ('bearing.agent-01.agent-02.fleet.example.', 'TXT', 'Bearing',
     lambda r: 'bearing|45' in str(r.rr[0].rdata) and r.rr[0].ttl == 30),
    ('trust.agent-01.fleet.example.', 'TXT', 'Trust',
     lambda r: 'trust|0.95' in str(r.rr[0].rdata) and r.rr[0].ttl == 3600),
    ('agent-99.fleet.example.', 'A', 'NXDOMAIN',
     lambda r: r.header.rcode == 3 and len(r.rr) == 0),
]

all_passed = True
for name, qtype_str, label, check_fn in tests:
    q = DNSRecord.question(name, qtype=qtype_str)
    resp = DNSRecord.parse(q.send('127.0.0.1', port=5358))
    ok = check_fn(resp)
    status = '✓' if ok else '✗'
    rcode = {0:'OK', 3:'NXDOMAIN'}.get(resp.header.rcode, str(resp.header.rcode))
    rd = str(resp.rr[0].rdata) if resp.rr else '-'
    ttl = resp.rr[0].ttl if resp.rr else '-'
    print(f'{label}: rcode={rcode} data={rd} ttl={ttl} {status}')
    if not ok:
        all_passed = False

print(f'Server stats: {srv.stats}')
srv.running = False

assert all_passed, 'Some tests failed!'
print()
print(f'✓ All {len(tests)} network tests passed!')
print(f'✓ All zone query tests passed!')
print()
print('The Keel DNS server works correctly.')
print('Agent death = NXDOMAIN. TTL = first-person self-termination.')
