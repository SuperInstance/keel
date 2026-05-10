#include <stdint.h>
#include <stdio.h>

#ifdef PLATFORM_NATIVE
// Simulated TTL registers for native compilation/testing
static uint32_t ttl_sim[128];  // 32 registers × 4 fields
#define TTL ((ttl_reg_t *) ttl_sim)
static inline void ttl_tick(void) {
    int i;
    for (i = 0; i < 32; i++) {
        ttl_reg_t *r = (ttl_reg_t *)ttl_sim + i;
        if ((r->ctrl & (1UL << 31)) && r->current > 0) {
            r->current--;
            if (r->current == 0) r->status |= 1;
        }
    }
}
#else
// Real hardware — memory-mapped TTL registers
#define TTL_BASE  0x40000000UL
#define TTL       ((ttl_reg_t *) TTL_BASE)
static inline void ttl_tick(void) { /* Hardware handles this */ }
#endif

typedef volatile struct {
    uint32_t ctrl;       // [31] enable  [30] interrupt-enable
    uint32_t load;       // Initial TTL value
    uint32_t current;    // Current countdown
    uint32_t status;     // [0] expired flag
} ttl_reg_t;

// ─── TileTtl ────────────────────────────────────────────────────────────────────

typedef struct {
    uint32_t data[8];
    uint8_t  ttl_idx;
    uint8_t  alive;
} tile_ttl_t;

static inline void tile_init(tile_ttl_t *t, uint32_t *data, uint32_t ttl_val) {
    int i;
    for (i = 0; i < 8; i++) t->data[i] = data[i];
    t->ttl_idx = 0;
    TTL[t->ttl_idx].load = ttl_val;
    TTL[t->ttl_idx].current = ttl_val;
    TTL[t->ttl_idx].ctrl = (1UL << 31);
    TTL[t->ttl_idx].status = 0;
    t->alive = 1;
}

static inline int tile_is_alive(tile_ttl_t *t) {
    return (TTL[t->ttl_idx].status & 1) == 0;
}

// ─── AgentTtl ──────────────────────────────────────────────────────────────────

typedef struct {
    uint32_t ttl_ms;
    uint32_t last_output;
    uint8_t  ttl_idx;
    uint8_t  heartbeat_pin;
} agent_ttl_t;

static inline void agent_init(agent_ttl_t *a, uint32_t ttl_val) {
    a->ttl_ms = ttl_val;
    a->last_output = 0;
    a->ttl_idx = 1;
    TTL[a->ttl_idx].load = ttl_val / 4;
    TTL[a->ttl_idx].current = ttl_val / 4;
    TTL[a->ttl_idx].ctrl = (1UL << 31);
    TTL[a->ttl_idx].status = 0;
}

static inline void agent_heartbeat(agent_ttl_t *a) {
    a->last_output++;
    TTL[a->ttl_idx].current = a->ttl_ms / 4;  // reset output window
}

static inline int agent_is_present(agent_ttl_t *a) {
    return (TTL[a->ttl_idx].status & 1) == 0;
    // "Output IS the heartbeat. Silence IS death."
}

// ─── BearingTtl ────────────────────────────────────────────────────────────────

typedef struct {
    uint8_t  ttl_idx_a;
    uint8_t  ttl_idx_b;
    int32_t  angle;    // fixed-point
    int32_t  rate;     // fixed-point
} bearing_ttl_t;

static inline void bearing_init(bearing_ttl_t *b, uint8_t a, uint8_t b_idx) {
    b->ttl_idx_a = a;
    b->ttl_idx_b = b_idx;
    b->angle = 0;
    b->rate = 0;
}

static inline int bearing_collision_risk(bearing_ttl_t *b) {
    if ((TTL[b->ttl_idx_a].status & 1) || (TTL[b->ttl_idx_b].status & 1))
        return 2;  // CRITICAL
    if (b->rate == 0 && b->angle < 1000)
        return 1;  // WARNING
    return 0;  // STABLE
}

// ─── Demo ───────────────────────────────────────────────────────────────────────

int main(void) {
    uint32_t tile_data[8] = {1,2,3,4,5,6,7,8};
    tile_ttl_t tile;
    agent_ttl_t agent;
    bearing_ttl_t bearing;

    // Initialize
    tile_init(&tile, tile_data, 5);     // dies after 5 ticks
    agent_init(&agent, 20);              // output window = 5 ticks
    bearing_init(&bearing, 0, 1);        // watch tile vs agent

    printf("🔮 Keel on the Metal — Native Simulation\n\n");

    int tick;
    for (tick = 0; tick < 10; tick++) {
        printf("Tick %d:\n", tick);

        // Tile
        printf("  Tile: %s\n", tile_is_alive(&tile) ? "ALIVE" : "DEAD");

        // Agent (heartbeat every 3 ticks)
        if (tick % 3 == 0) {
            agent_heartbeat(&agent);
            printf("  Agent: HEARTBEAT\n");
        }
        printf("  Agent: %s\n", agent_is_present(&agent) ? "PRESENT" : "ABSENT");

        // Bearing
        int risk = bearing_collision_risk(&bearing);
        printf("  Bearing: %s\n",
            risk == 2 ? "CRITICAL (position unknown)" :
            risk == 1 ? "WARNING (constant bearing)" :
            "STABLE");

        // Tick the simulation
        ttl_tick();
        printf("\n");
    }

    printf("  Tile alive after loop: %s\n", tile_is_alive(&tile) ? "YES" : "NO");
    printf("  Agent present after loop: %s\n", agent_is_present(&agent) ? "YES" : "NO");
    printf("\n🔮 Done. Death is default.\n");

    return 0;
}
