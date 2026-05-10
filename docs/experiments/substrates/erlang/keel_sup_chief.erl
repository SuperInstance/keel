%%%=============================================================================
%%% @doc Chief Supervisor — top of the Keel TTL supervision tree.
%%%
%%%      This supervisor manages multiple `keel_sup` instances, each with its
%%%      own restart strategy.  If a subsupervisor dies from restart intensity
%%%      exhaustion, the chief supervisor (`one_for_all`) restarts everything.
%%%
%%%      This implements hierarchical TTL:
%%%        - Tiles die → subsupervisor handles it (maybe restart)
%%%        - Subsupervisor dies → chief restarts everything (temperature reset)
%%%=============================================================================
-module(keel_sup_chief).
-behaviour(supervisor).

-export([start_link/0, init/1]).

-spec start_link() -> supervisor:startlink_ret().
start_link() ->
    supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    {ok, {
        {one_for_all, 10, 60},
        [
            #{
                id       => keel_sup_one_for_one,
                start    => {keel_sup, start_link, [one_for_one]},
                restart  => permanent,
                shutdown => 10000,
                type     => supervisor,
                modules  => [keel_sup]
            },
            #{
                id       => keel_sup_one_for_all,
                start    => {keel_sup, start_link, [one_for_all]},
                restart  => permanent,
                shutdown => 10000,
                type     => supervisor,
                modules  => [keel_sup]
            },
            #{
                id       => keel_sup_rest_for_one,
                start    => {keel_sup, start_link, [rest_for_one]},
                restart  => permanent,
                shutdown => 10000,
                type     => supervisor,
                modules  => [keel_sup]
            }
        ]
    }}.
