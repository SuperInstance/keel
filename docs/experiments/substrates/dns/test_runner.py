#!/usr/bin/env python3
"""Test the Keel DNS server."""
import sys, os, threading, time, socket as sk

# Directly inject the path
sys.path.insert(0, '/tmp/keel-models/dns')

# Load the module directly, suppressing its startup print
exec(open('/tmp/keel-models/dns/keel-dns-server.py').read().replace(
    'if __name__ == "__main__":', 'if False:'))

from dnslib import DNSRecord, QTYPE

db = KeelZoneDB('fleet.example.')
db.add_record('agent-01.fleet.example.', 'A', 60, '10.0.0.1')
db.add_record('agent-01.fleet.example.', 'TXT', 15, 'heading|315|0.7|birth=1715000000')
db.add_record('agent-02.fleet.example.', 'A', 60, '10.0.0.2')
db.add_record('bearing.agent-01.agent-02.fleet.example.', 'TXT', 30, 'bearing|45|0.2|observed=1715000010')
db.add_record('trust.agent-01.fleet.example.', 'TXT', 3600, 'trust|0.95|0|proven=1715000000')

# Direct zone queries (no network)
r = db.query('agent-01.fleet.example.', QTYPE.A)
assert len(r) == 1, f'A rec count: {len(r)}'
assert str(r[0].rdata) == '10.0.0.1'
assert r[0].ttl == 60
print(f'A record: {r[0].rdata} TTL={r[0].ttl} ✓')

r = db.query('agent-01.fleet.example.', QTYPE.TXT)
assert len(r) == 1
assert 'heading|315' in str(r[0].rdata)
assert r[0].ttl == 15
print(f'TXT heading: {r[0].rdata} TTL={r[0].ttl} ✓')

r = db.query('bearing.agent-01.agent-02.fleet.example.', QTYPE.TXT)
assert len(r) == 1
assert 'bearing|45' in str(r[0].rdata)
assert r[0].ttl == 30
print(f'Bearing: {r[0].rdata} TTL={r[0].ttl} ✓')

r = db.query('trust.agent-01.fleet.example.', QTYPE.TXT)
assert len(r) == 1
assert 'trust|0.95' in str(r[0].rdata)
assert r[0].ttl == 3600
print(f'Trust: {r[0].rdata} TTL={r[0].ttl} ✓')

r = db.query('agent-99.fleet.example.', QTYPE.A)
assert len(r) == 0
print(f'NXDOMAIN: 0 records ✓')

print()

# Network test
srv = KeelDNSServer(db, port=5361, host='127.0.0.1')
t = threading.Thread(target=srv.start, daemon=True)
t.start()
time.sleep(0.3)

def query(name, qtype_str):
    q = DNSRecord.question(name, qtype=qtype_str)
    return DNSRecord.parse(q.send('127.0.0.1', port=5361))

r = query('agent-01.fleet.example.', 'A')
assert r.header.rcode == 0
assert str(r.rr[0].rdata) == '10.0.0.1'
assert r.rr[0].ttl == 60
print(f'Net A: {r.rr[0].rdata} TTL={r.rr[0].ttl} ✓')

r = query('agent-01.fleet.example.', 'TXT')
assert r.header.rcode == 0
assert 'heading|315' in str(r.rr[0].rdata)
assert r.rr[0].ttl == 15
print(f'Net TXT: {r.rr[0].rdata} TTL={r.rr[0].ttl} ✓')

r = query('bearing.agent-01.agent-02.fleet.example.', 'TXT')
assert r.header.rcode == 0
assert 'bearing|45' in str(r.rr[0].rdata)
assert r.rr[0].ttl == 30
print(f'Net Bearing: {r.rr[0].rdata} TTL={r.rr[0].ttl} ✓')

r = query('trust.agent-01.fleet.example.', 'TXT')
assert r.header.rcode == 0
assert 'trust|0.95' in str(r.rr[0].rdata)
assert r.rr[0].ttl == 3600
print(f'Net Trust: {r.rr[0].rdata} TTL={r.rr[0].ttl} ✓')

r = query('agent-99.fleet.example.', 'A')
assert r.header.rcode == 3
assert len(r.rr) == 0
print(f'Net NXDOMAIN: rcode=3 ✓')

r = query('agent-02.fleet.example.', 'A')
assert str(r.rr[0].rdata) == '10.0.0.2'
print(f'Net agent-02: {r.rr[0].rdata} ✓')

# Unblock and stop
s = sk.socket(sk.AF_INET, sk.SOCK_DGRAM)
s.sendto(b'\x00', ('127.0.0.1', 5361))
s.close()
time.sleep(0.3)
srv.running = False
time.sleep(0.2)

print(f'\nAll {len(srv.stats)} queries processed ✓')
print('ALL TESTS PASSED ✓')
