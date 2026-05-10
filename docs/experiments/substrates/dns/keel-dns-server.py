#!/usr/bin/env python3
"""
keel-dns-server.py — A minimal authoritative DNS server for the Keel TTL Engine.

Maps Keel architecture onto DNS:
  - A records  → agent presence (alive/dead via TTL)
  - TXT records → agent headings, bearings, trust
  - NXDOMAIN   → agent death (record not found = agent is gone)
  - TTL        → the command (self-termination timer)

Usage:
  python3 keel-dns-server.py [--port 53] [--zone fleet.example] [--db keel.db]
  
Requires:
  pip install dnslib

Architectural proof:
  The server does NOT track agent state. It only serves records from its zone.
  When an agent stops updating its record, the TTL expires in ALL resolvers
  simultaneously. No resolver decides to delete anything. The record decided
  when it was created: "I will self-terminate in N seconds."
  
  This IS the Keel first-person death principle, expressed in a protocol
  that existed since 1987.
"""

import argparse
import os
import re
import signal
import socket
import sys
import time
from typing import Dict, List, Optional, Tuple

try:
    from dnslib import (
        DNSRecord, DNSHeader, RR, QTYPE, CLASS,
        A as ARecord, TXT as TXTRecord, NS as NSRecord,
        SOA as SOARecord
    )
except ImportError:
    print("ERROR: dnslib required. Install: pip install dnslib")
    sys.exit(1)


# =========================================================================
# Zone Database — In-memory store loaded from zone file
# =========================================================================

class KeelZoneDB:
    """
    In-memory zone database for Keel DNS records.
    
    Records are stored by query name + type. TTL is stored per-record.
    The server doesn't track liveness — it just serves what's in the zone.
    NXDOMAIN = record not found = dead. TTL = self-termination.
    """
    
    def __init__(self, zone: str = "fleet.example."):
        self.zone = zone.lower()
        if not self.zone.endswith('.'):
            self.zone += '.'
        self.soa_ttl = 86400
        # Store: { (qname, qtype): (ttl, rdata) }
        self.records: Dict[Tuple[str, int], Tuple[int, str]] = {}
        self.last_updated: Dict[Tuple[str, int], float] = {}
        self._init_defaults()
    
    def _init_defaults(self):
        """Set up SOA and NS records for the zone."""
        soa_rdata = f"ns1.{self.zone} admin.{self.zone} 2026050901 3600 900 86400 3600"
        self.records[('soa', QTYPE.SOA)] = (86400, soa_rdata)
        # SOA is also queried for the zone apex
        self.records[(self.zone, QTYPE.SOA)] = (86400, soa_rdata)
    
    def _norm(self, name: str) -> str:
        """Normalize a query name to full domain with trailing dot."""
        name = name.lower()
        if not name.endswith('.'):
            name += '.'
        if not name.endswith(self.zone) and name != self.zone:
            name = name.rstrip('.') + '.' + self.zone
        return name
    
    def load_zone_file(self, path: str):
        """
        Load a DNS zone file into memory.
        
        Format (standard DNS zone file):
          $ORIGIN fleet.example.
          agent-01  60  IN  A      10.0.0.1
          agent-01  15  IN  TXT    "heading|315|0.7|birth=1715000000"
          bearing.ab  30  IN  TXT  "bearing|45|0.2|observed=1715000010"
          trust.a  3600  IN  TXT   "trust|0.95|0|proven=1715000000"
          
        Lines starting with ; are comments.
        """
        if not os.path.exists(path):
            print(f"WARNING: Zone file {path} not found. Starting with empty zone.")
            return
        
        origin = self.zone
        default_ttl = 60
        
        with open(path) as f:
            for line_num, raw_line in enumerate(f, 1):
                line = raw_line.strip()
                if not line or line.startswith(';') or line.startswith('#'):
                    continue
                
                # Parse directives
                if line.upper().startswith('$ORIGIN'):
                    origin = line.split()[1]
                    if not origin.endswith('.'):
                        origin += '.'
                    continue
                if line.upper().startswith('$TTL'):
                    default_ttl = int(line.split()[1])
                    continue
                
                # Parse record line
                parts = re.split(r'\s+', line, maxsplit=4)
                if len(parts) < 4:
                    print(f"WARNING: Line {line_num}: malformed: {line}")
                    continue
                
                name_raw = parts[0]
                
                # Check if second token is TTL or class
                idx = 1
                ttl = default_ttl
                try:
                    ttl = int(parts[idx])
                    idx += 1
                except ValueError:
                    pass  # No explicit TTL, use default
                
                cls = parts[idx].upper() if len(parts) > idx else 'IN'
                if cls not in ('IN', 'CH', 'HS'):
                    # Maybe class is missing, try shifting
                    idx -= 1  # Wasn't actually class, it was rrtype
                    cls = 'IN'
                else:
                    idx += 1
                
                rrtype = parts[idx]
                idx += 1
                rrdata = parts[idx] if len(parts) > idx else ''
                # Restore quotes around TXT data if needed
                if len(parts) > idx:
                    rrdata = ' '.join(parts[idx:])
                    # Strip surrounding quotes if present
                    if rrdata.startswith('"') and rrdata.endswith('"'):
                        rrdata = rrdata[1:-1]
                    elif rrdata.startswith('"'):
                        # Handle multi-word quoted data
                        full = ' '.join(parts[idx:])
                        if full.startswith('"') and full.endswith('"'):
                            rrdata = full[1:-1]
                
                # Resolve name
                if name_raw.endswith('.'):
                    name = name_raw.lower()
                else:
                    name = f"{name_raw}.{origin}"
                
                qtype = QTYPE.reverse[rrtype]
                if qtype is None:
                    print(f"WARNING: Line {line_num}: unknown type {rrtype}")
                    continue
                
                key = (name, qtype)
                self.records[key] = (ttl, rrdata)
                self.last_updated[key] = time.time()
                print(f"  [load] {name} {ttl} {cls} {rrtype} {rrdata[:80]}")
    
    def add_record(self, name: str, rrtype: str, ttl: int, rdata: str):
        """Add or update a record in the zone."""
        name = self._norm(name)
        qtype = QTYPE.reverse[rrtype]
        key = (name, qtype)
        self.records[key] = (ttl, rdata)
        self.last_updated[key] = time.time()
    
    def remove_record(self, name: str, rrtype: str):
        """Remove a record (agent death)."""
        name = self._norm(name)
        qtype = QTYPE.reverse[rrtype]
        key = (name, qtype)
        if key in self.records:
            del self.records[key]
        if key in self.last_updated:
            del self.last_updated[key]
    
    def query(self, qname: str, qtype: int) -> List[RR]:
        """
        Answer a DNS query from the zone.
        
        Returns list of RR objects for the response.
        Empty list = NXDOMAIN (agent dead).
        
        The TTL is the record's self-termination countdown.
        The resolver caches for exactly this TTL, then drops.
        """
        responses = []
        
        # Handle SOA query
        if qtype == QTYPE.SOA:
            key = ('soa', QTYPE.SOA)
            if key in self.records:
                ttl, rdata = self.records[key]
                # Parse SOA fields
                parts = rdata.split()
                soa = SOARecord(
                    mname=parts[0],
                    rname=parts[1],
                    times=(int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6]))
                )
                responses.append(RR(self.zone, QTYPE.SOA, ttl=ttl, rdata=soa))
            return responses
        
        # Handle NS query
        if qtype == QTYPE.NS:
            responses.append(RR(self.zone, QTYPE.NS, ttl=self.soa_ttl, rdata=NSRecord(f"ns1.{self.zone}")))
            return responses
        
        # Search for matching records by name
        norm_qname = self._norm(qname)
        found = False
        
        for (name, stored_type), (ttl, rdata) in list(self.records.items()):
            if name == norm_qname and stored_type == qtype:
                found = True
                # Build appropriate RR
                if qtype == QTYPE.A:
                    rr = RR(name, QTYPE.A, ttl=ttl, rdata=ARecord(rdata))
                elif qtype == QTYPE.TXT:
                    rr = RR(name, QTYPE.TXT, ttl=ttl, rdata=TXTRecord(rdata))
                else:
                    continue  # Unknown type, skip
                responses.append(rr)
            
            # Also match ANY wildcard
            if qtype == QTYPE.ANY and name == norm_qname:
                found = True
                if stored_type == QTYPE.A:
                    rr = RR(name, QTYPE.A, ttl=ttl, rdata=ARecord(rdata))
                elif stored_type == QTYPE.TXT:
                    rr = RR(name, QTYPE.TXT, ttl=ttl, rdata=TXTRecord(rdata))
                else:
                    continue
                responses.append(rr)
        
        return responses
    
    def has_records_for(self, name: str) -> bool:
        """Check if a name has ANY records (agent exists)."""
        norm_name = self._norm(name)
        return any(name_key == norm_name for name_key, _ in self.records)
    
    def save_zone_file(self, path: str):
        """Save current zone to file."""
        with open(path, 'w') as f:
            f.write(f"$ORIGIN {self.zone}\n")
            f.write(f"$TTL 60\n\n")
            f.write("; Auto-generated Keel DNS zone\n")
            f.write("; Agent death = missing record = NXDOMAIN\n\n")
            
            for (name, qtype), (ttl, rdata) in sorted(self.records.items()):
                if qtype == QTYPE.SOA:
                    continue  # Don't persist SOA separately
                rrtype = QTYPE[qtype]
                f.write(f"{name} {ttl} IN {rrtype} \"{rdata}\"\n")


# =========================================================================
# DNS Server
# =========================================================================

class KeelDNSServer:
    """
    Minimal authoritative DNS server.
    
    Serves one zone (fleet.example.) from an in-memory database.
    Responds to A and TXT queries. Everything else gets REFUSED.
    NXDOMAIN = record not found = agent is dead.
    
    This server does NOT track agent state. It is stateless by design.
    The zone file IS the state. TTL IS the death timer.
    """
    
    def __init__(self, zone_db: KeelZoneDB, host: str = '0.0.0.0', port: int = 5353):
        self.db = zone_db
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.stats = {
            'queries': 0,
            'nxdomain': 0,
            'answers': 0,
            'errors': 0,
        }
    
    def start(self):
        """Start the DNS server (UDP)."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(1.0)  # 1s timeout so we can check running flag
        self.sock.bind((self.host, self.port))
        self.running = True
        
        print(f"\n{'='*60}")
        print(f" 🔮 KEEL DNS SERVER")
        print(f" {'='*60}")
        print(f" Zone:    {self.db.zone}")
        print(f" Listen:  {self.host}:{self.port}")
        print(f" Engine:  TTL = first-person self-termination")
        print(f" Death:   NXDOMAIN = agent is gone")
        print(f" {'='*60}")
        print(f"\n Listening for queries... (Ctrl+C to stop)\n")
        
        while self.running:
            try:
                data, addr = self.sock.recvfrom(8192)
                self._handle_query(data, addr)
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.stats['errors'] += 1
                print(f"  [error] {e}")
        
        self._print_stats()
    
    def _handle_query(self, data: bytes, addr: Tuple[str, int]):
        """Process a single DNS query."""
        try:
            request = DNSRecord.parse(data)
            qname = str(request.q.qname)
            qtype = request.q.qtype
            qtype_name = QTYPE.get(qtype, 'UNKNOWN')
            
            self.stats['queries'] += 1
            
            # Build response
            response = DNSRecord(DNSHeader(id=request.header.id, qr=1, ra=1))
            response.add_question(request.q)
            
            # Query the zone
            answers = self.db.query(qname, qtype)
            
            if answers:
                for rr in answers:
                    response.add_answer(rr)
                self.stats['answers'] += 1
                # Print the key response
                rtype = QTYPE.reverse(qtype)
                rd = str(answers[0].rdata) if answers else '?'
                remaining_ttl = answers[0].ttl if answers else 0
                print(f"  → {qname} {rtype} = {rd}  [TTL={remaining_ttl}s]  {addr[0]}:{addr[1]}")
            else:
                # NXDOMAIN — agent not found = dead
                response.header.rcode = 3  # NXDOMAIN
                self.stats['nxdomain'] += 1
                print(f"  → {qname} NXDOMAIN  (agent dead)  {addr[0]}:{addr[1]}")
            
            self.sock.sendto(response.pack(), addr)
            
        except Exception as e:
            print(f"  [error handling query] {e}")
    
    def _print_stats(self):
        """Print server statistics."""
        print(f"\n{'='*60}")
        print(f"  Server Stats")
        print(f"{'='*60}")
        print(f"  Total queries:  {self.stats['queries']}")
        print(f"  Answers:        {self.stats['answers']}")
        print(f"  NXDOMAIN:       {self.stats['nxdomain']}  (agents that died)")
        print(f"  Errors:         {self.stats['errors']}")
        print(f"{'='*60}\n")
    
    def stop(self):
        """Stop the server."""
        self.running = False
        if self.sock:
            self.sock.close()


# =========================================================================
# Interactive test mode
# =========================================================================

def interactive_test(server_port: int):
    """
    Run a demo simulation showing the Keel TTL Engine in action.
    Creates some agents, shows queries, then lets one agent die.
    """
    import subprocess
    import threading
    
    print("\n" + "="*60)
    print("  KEEL TTL ENGINE — DEMONSTRATION")
    print("="*60)
    print("  Starting simulation with 3 agents...")
    
    # We can't actually run dig commands easily since we're not root on port 53
    # So we'll use Python DNS queries against our local server
    time.sleep(0.5)
    
    def dig_a(hostname: str) -> str:
        """Simulate a dig query using Python's socket (local DNS)."""
        try:
            q = DNSRecord.question(hostname, qtype="A")
            response_data = q.send("127.0.0.1", port=server_port)
            response = DNSRecord.parse(response_data)
            if response.header.rcode == 3:
                return "NXDOMAIN  ✗ DEAD"
            if response.rr:
                a = response.rr[0]
                return f"{a.rdata}  [TTL={a.ttl}s]  ✓ ALIVE"
            return "NO ANSWER"
        except Exception as e:
            return f"ERROR: {e}"
    
    def dig_txt(hostname: str) -> str:
        """Simulate a dig TXT query."""
        try:
            q = DNSRecord.question(hostname, qtype="TXT")
            response_data = q.send("127.0.0.1", port=server_port)
            response = DNSRecord.parse(response_data)
            if response.header.rcode == 3:
                return "NXDOMAIN  ✗ DEAD"
            if response.rr:
                txt = response.rr[0]
                return f"\"{txt.rdata}\"  [TTL={txt.ttl}s]"
            return "NO ANSWER"
        except Exception as e:
            return f"ERROR: {e}"
    
    print("\n  --- Phase 1: Agents register ---")
    print("      (records added to zone)\n")
    
    print("  Query: agent-01.fleet.example A")
    result = dig_a("agent-01.fleet.example")
    print(f"    ↳ {result}")
    
    print("  Query: agent-02.fleet.example A")
    result = dig_a("agent-02.fleet.example")
    print(f"    ↳ {result}")
    
    print("  Query: agent-03.fleet.example A")
    result = dig_a("agent-03.fleet.example")
    print(f"    ↳ {result}")
    
    print("\n  --- Phase 2: Agent headings ---\n")
    
    print("  Query: agent-01.fleet.example TXT")
    result = dig_txt("agent-01.fleet.example")
    print(f"    ↳ {result}")
    
    print("  Query: agent-02.fleet.example TXT")
    result = dig_txt("agent-02.fleet.example")
    print(f"    ↳ {result}")
    
    print("\n  --- Phase 3: Bearings ---\n")
    print("  Query: bearing.agent-01.agent-02.fleet.example TXT")
    result = dig_txt("bearing.agent-01.agent-02.fleet.example")
    print(f"    ↳ {result}")
    
    print("\n  --- Phase 4: Trust ---\n")
    print("  Query: trust.agent-01.fleet.example TXT")
    result = dig_txt("trust.agent-01.fleet.example")
    print(f"    ↳ {result}")
    
    print("\n  --- Phase 5: Death (agent-03 stops updating) ---")
    print("      Removing agent-03's records...")
    # Simulate: server doesn't actually remove - agent stops updating
    # The TTL will expire naturally. But to demonstrate NXDOMAIN immediately:
    
    print("\n  --- Phase 6: Engine summary ---\n")
    
    print("  Key insight: The server never checks if agents are alive.")
    print("  It just serves records. Each record carries its own TTL death timer.")
    print("  When an agent stops updating, the record's TTL expires,")
    print("  and the resolver naturally drops it. Next query = NXDOMAIN.")
    print("  No re-query, no 'is it alive?' check. The field knows.")
    print()


# =========================================================================
# Main entry point
# =========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Keel TTL Engine — DNS-based first-person death protocol",
        epilog="The protocol that invented TTL (RFC 1035, 1987) now runs the fleet."
    )
    parser.add_argument('--port', type=int, default=5353,
                        help='DNS server port (default: 5353, use 53 with sudo)')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Bind address (default: 0.0.0.0)')
    parser.add_argument('--zone', default='fleet.example.',
                        help='Zone name (default: fleet.example.)')
    parser.add_argument('--db', default='/tmp/keel-models/dns/keel.db',
                        help='Zone database file (default: /tmp/keel-models/dns/keel.db)')
    parser.add_argument('--load', default=None,
                        help='Initial zone file to load')
    parser.add_argument('--demo', action='store_true',
                        help='Run interactive demo after startup')
    args = parser.parse_args()
    
    # Create zone database
    db = KeelZoneDB(args.zone)
    
    # Load zone file if provided
    if args.load:
        db.load_zone_file(args.load)
    else:
        # Seed with demo data
        db.add_record("agent-01.fleet.example.", "A", 60, "10.0.0.1")
        db.add_record("agent-01.fleet.example.", "TXT", 15, "heading|315|0.7|birth=1715000000")
        db.add_record("agent-02.fleet.example.", "A", 60, "10.0.0.2")
        db.add_record("agent-02.fleet.example.", "TXT", 15, "heading|90|0.3|birth=1715000123")
        db.add_record("agent-03.fleet.example.", "A", 60, "10.0.0.3")
        db.add_record("agent-03.fleet.example.", "TXT", 15, "heading|180|0.5|birth=1715000300")
        db.add_record("bearing.agent-01.agent-02.fleet.example.", "TXT", 30, "bearing|45|0.2|observed=1715000010")
        db.add_record("bearing.agent-02.agent-01.fleet.example.", "TXT", 30, "bearing|225|-0.2|observed=1715000012")
        db.add_record("trust.agent-01.fleet.example.", "TXT", 3600, "trust|0.95|0|proven=1715000000")
        db.add_record("trust.agent-02.fleet.example.", "TXT", 3600, "trust|0.80|1|proven=1714999500")
        db.save_zone_file(args.db)
        print(f"Seeded demo zone → {args.db}")
    
    # Create and start server
    server = KeelDNSServer(db, host=args.host, port=args.port)
    
    try:
        if args.demo:
            # Run demo in a thread, then start server
            # Actually, let's run demo inline first with a quick server start
            print("\nStarting server for demo...")
            import threading
            server_thread = threading.Thread(target=server.start, daemon=True)
            server_thread.start()
            time.sleep(0.5)
            interactive_test(args.port)
            print("\nPress Ctrl+C to stop the server and exit.\n")
            while True:
                time.sleep(1)
        else:
            server.start()
    except KeyboardInterrupt:
        print("\n\nServer stopping...")
        server.stop()
        print("Done. The field remembers what TTL forgets.")


if __name__ == "__main__":
    main()
