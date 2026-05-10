# Makefile — The Keel Scheduler
#
# The Makefile IS the scheduler. NOT a cron daemon. NOT a systemd timer.
# Make is declarative, dependency-driven, and stateless — like a proper scheduler.
#
# Philosophy:
#   make agent       → starts an agent (builds a target = spawns a process)
#   make kill-stale  → kills expired agents (cleans stale build artifacts)
#   make status      → fleet health report (make inspect)
#   make clean       → decommission the fleet (make clean = death)
#
# Make targets ARE processes. Dependencies ARE inter-agent awareness.
# The schedule is IN the Makefile. Not in a config file. Not in a database.
#
# Rules:
#   .PHONY targets = processes (not files on disk)
#   Agent PIDs are tracked in /var/run/keel/agents/
#   A `make` invocation is a launch command. Nothing more.

SHELL := /bin/bash
KEEL_RUNDIR := /tmp/.keel
KEEL_AGENTDIR := $(KEEL_RUNDIR)/agents
KEEL_FIFODIR := $(KEEL_RUNDIR)/fifos
KEELD := ./keeld.sh
KEEL_INIT := ./keel-init.sh
KEEL_AGENT := ./keel-agent.sh
KEEL_BEARINGS := ./keel-bearings.sh

# Default TTL for agents (seconds)
TTL_DEFAULT := 30

# export KEEL_RUNDIR so child processes inherit it
export KEEL_RUNDIR

# ------------------------------------------------------------------
# Fleet Management
# ------------------------------------------------------------------

.PHONY: all start stop status kill-stale agent scout relay logger \
        watch bearings plot clean fclean full-clean help

all: start

# --- start the keel daemon ---
start: $(KEELD)
	@echo "[make] Laying daemon keel..."
	@mkdir -p $(KEEL_AGENTDIR) $(KEEL_FIFODIR) 2>/dev/null || true
	@$(KEELD) start &
	@echo "[make] Daemon launched."

# --- stop the keel daemon ---
stop:
	@echo "[make] Decommissioning daemon..."
	-$(KEELD) stop 2>/dev/null || true
	@echo "[make] Daemon decommissioned."

# --- fleet status ---
status: $(KEELD)
	@$(KEELD) status

# --- kill stale agents ---
# A stale agent is one whose PID file exists but whose PID is gone.
# kill -0 IS is_present(). If kill -0 fails, the keel is a headstone.
kill-stale:
	@echo "[make] Checking for stale keels..."
	@stale=0; \
	for pidfile in $(KEEL_AGENTDIR)/*.pid; do \
		[ -f "$$pidfile" ] || continue; \
		agent=$$(basename "$$pidfile" .pid); \
		pid=$$(cat "$$pidfile" 2>/dev/null | head -1); \
		if [ -n "$$pid" ] && ! kill -0 "$$pid" 2>/dev/null; then \
			echo "  Removing stale keel: $$agent (PID $$pid)"; \
			rm -f "$$pidfile" "$(KEEL_FIFODIR)/$$agent" 2>/dev/null || true; \
			stale=$$((stale + 1)); \
		fi; \
	done; \
	if [ "$$stale" -eq 0 ]; then \
		echo "  No stale keels found."; \
	else \
		echo "  Removed $$stale stale keel(s)."; \
	fi

# ------------------------------------------------------------------
# Agent Launches
# ------------------------------------------------------------------

# --- launch an agent via keel-init + keel-agent ---
# The Makefile IS the scheduler. `make agent` is equivalent to `make <target>`.
# The agent runs in the background. Its death is its own.
agent:
	@echo "[make] Launching agent with TTL=$(TTL_DEFAULT)s..."
	@$(KEEL_INIT) "agent-$(shell date +%s)" \
		$(KEEL_AGENT) --name "agent-$(shell date +%s)" \
		--heading "000@5kt" --ttl $(TTL_DEFAULT) --interval 3 &
	@echo "[make] Agent launched. TTL set to $(TTL_DEFAULT)s."

# --- launch a named scout agent ---
# Scouts report position and heading. Their purpose is to be sensed.
# --interval 1 = high-frequency heading updates (tight bearing tracking)
scout:
	@echo "[make] Launching scout with TTL=$(TTL_DEFAULT)s..."
	@$(KEEL_INIT) "scout-$(shell date +%s)" \
		$(KEEL_AGENT) --name "scout-$(shell date +%s)" \
		--heading "scouting" --ttl $(TTL_DEFAULT) --interval 1 &
	@echo "[make] Scout launched."

# --- launch a relay agent ---
# Relays sit between agents, forwarding headings.
# --interval 5 = lower frequency (relays don't need real-time)
relay:
	@echo "[make] Launching relay with TTL=$(TTL_DEFAULT)s..."
	@$(KEEL_INIT) "relay-$(shell date +%s)" \
		$(KEEL_AGENT) --name "relay-$(shell date +%s)" \
		--heading "relaying" --ttl $(TTL_DEFAULT) --interval 5 &
	@echo "[make] Relay launched."

# --- launch a logger agent ---
# Loggers persist headings to disk. They have a longer TTL.
logger:
	@echo "[make] Launching logger with TTL=60s..."
	@$(KEEL_INIT) "logger-$(shell date +%s)" \
		$(KEEL_AGENT) --name "logger-$(shell date +%s)" \
		--heading "logging" --ttl 60 --interval 5 &
	@echo "[make] Logger launched."

# ------------------------------------------------------------------
# Sensing and Bearings
# ------------------------------------------------------------------

# --- watch fleet bearings (continuous) ---
watch:
	@$(KEEL_BEARINGS) --watch --interval 2

# --- show fleet bearing map (continuous) ---
bearings:
	@echo "[make] Single bearing snapshot:"
	@$(KEEL_BEARINGS)

# --- show fleet bearing map (continuous) ---
plot:
	@$(KEEL_BEARINGS) --plot --watch

# ------------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------------

# --- clean up this make session's agents ---
# kill all PIDs tracked in the agent directory
clean:
	@echo "[make] Decommissioning fleet..."
	@if [ -d $(KEEL_AGENTDIR) ]; then \
		for pidfile in $(KEEL_AGENTDIR)/*.pid; do \
			[ -f "$$pidfile" ] || continue; \
			pid=$$(cat "$$pidfile" 2>/dev/null | head -1); \
			if [ -n "$$pid" ]; then \
				kill "$$pid" 2>/dev/null && echo "  Killed PID $$pid" || true; \
			fi; \
		done; \
	fi; \
	if [ -f $(KEEL_RUNDIR)/keeld.pid ]; then \
		pid=$$(cat $(KEEL_RUNDIR)/keeld.pid 2>/dev/null); \
		[ -n "$$pid" ] && kill "$$pid" 2>/dev/null || true; \
	fi
	@echo "[make] Fleet decommissioned."

# --- clean everything (fleet + runtime directories) ---
fclean: clean
	@echo "[make] Removing runtime directories..."
	-rm -rf $(KEEL_RUNDIR) 2>/dev/null || true
	@echo "[make] Runtime directories removed."

# --- deep clean (fclean + this directory's artifacts) ---
full-clean: fclean
	@echo "[make] Full clean complete."

# --- show all targets ---
help:
	@echo "Keel TTL Engine — UNIX Processes & Pipes"
	@echo ""
	@echo "Targets:"
	@echo "  all          → start daemon (default)"
	@echo "  start        → start the keel daemon"
	@echo "  stop         → stop the keel daemon"
	@echo "  status       → show fleet status"
	@echo "  kill-stale   → remove dead agent records"
	@echo ""
	@echo "  agent        → launch an agent (TTL=$(TTL_DEFAULT)s)"
	@echo "  scout        → launch a scout (TTL=$(TTL_DEFAULT)s, fast)"
	@echo "  relay        → launch a relay (TTL=$(TTL_DEFAULT)s, slow)"
	@echo "  logger       → launch a logger (TTL=60s)"
	@echo ""
	@echo "  watch        → continuous bearing display"
	@echo "  plot         → continuous bearing map"
	@echo "  bearings     → single bearing snapshot"
	@echo ""
	@echo "  clean        → kill all agents"
	@echo "  fclean       → clean + remove runtime dirs"
	@echo "  full-clean   → deep clean"
	@echo ""
	@echo "Philosophy:"
	@echo "  The Makefile IS the scheduler."
	@echo "  exit 0 IS completed-successfully-then-died."
	@echo "  PID files ARE keel dates."
	@echo "  kill -0 IS is_present()."
	@echo "  mkfifo IS the field channel."
	@echo "  trap 'exit 0' SIGALRM IS first-person TTL."
	@echo "  Silence IS death."
