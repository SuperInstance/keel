%%%=============================================================================
%%% @doc Keel TTL Engine — five gen_server types, each with first-person
%%%      self-termination.  Every entity carries its own death from its own
%%%      frame.  No central scheduler.
%%%
%%% Types (selected by `start_link/{1,2}` variant):
%%%
%%%   tile_ttl     Self-terminates after a fixed TTL.  Timer is set on init.
%%%   task_ttl     Self-terminates when stale.  A `{heartbeat}` message
%%%                resets the staleness timer; silence is death.
%%%   agent_ttl    Output IS heartbeat.  The process tracks whether it has
%%%                produced output recently; prolonged silence kills it.
%%%   bearing_ttl  Collision detection.  Registers a heading with the bearing
%%%                registry; if a conflicting bearing is detected, terminates.
%%%   trust_ttl    Trust decays naturally over time.  No explicit revocation
%%%                mechanism — trust simply decays until the entity dies.
%%%=============================================================================
-module(keel_ttl).
-behaviour(gen_server).

%% Public API — five start_link variants
-export([
    start_link/1,             %% tile_ttl(TTL_seconds)
    start_link/2,             %% {type, Args} tagged tuple
    start_link/3              %% Full: Name, Type, Args
]).

%% gen_server callbacks
-export([init/1, handle_call/3, handle_cast/2, handle_info/2,
         terminate/2, code_change/3]).

%% For trust decay via erlang:send_after
-define(DEFAULT_CHECK_INTERVAL, 1000).         %% 1 second tick
-define(AGENT_OUTPUT_WINDOW,     5000).        %% 5 s silence → death
-define(TRUST_DECAY_TICK,        1000).        %% trust recalc every 1 s
-define(TRUST_FLOOR,              0.01).       %% die when trust ≤ this

-include_lib("kernel/include/logger.hrl").

%%------------------------------------------------------------------------------
%% Records
%%------------------------------------------------------------------------------

-record(tile_state, {
    name       :: term(),
    ttl_ref    :: reference() | undefined       %% timer ref for tile TTL
}).

-record(task_state, {
    name       :: term(),
    stale_ref  :: reference() | undefined,      %% staleness timer ref
    stale_after :: non_neg_integer()            %% max idle ms
}).

-record(agent_state, {
    name           :: term(),
    last_output_ts :: non_neg_integer(),        %% erlang:monotonic_time(millisecond)
    silence_threshold :: non_neg_integer()
}).

-record(bearing_state, {
    name    :: term(),
    heading :: term(),
    speed   :: number()
}).

-record(trust_state, {
    name       :: term(),
    trust      :: float(),                      %% current trust value 0.0..1.0
    decay_rate :: float(),                      %% subtracted per tick
    decay_ref  :: reference() | undefined
}).

%% Type-tagged state
-record(keel_state, {
    type   :: tile_ttl | task_ttl | agent_ttl | bearing_ttl | trust_ttl,
    inner  :: term()                             %% specific record above
}).

%%%=============================================================================
%%% Public API
%%%=============================================================================

%% @doc Start a tile_ttl with a fixed lifetime.
%%      `TTL_seconds` — seconds until self-termination.
-spec start_link(pos_integer()) -> gen_server:start_ret().
start_link(TTL_seconds) when is_integer(TTL_seconds), TTL_seconds > 0 ->
    gen_server:start_link(?MODULE, [tile_ttl, TTL_seconds], []).

%% @doc Start any type with one argument.
%%      Arg tuple: `{tile_ttl, TTL_seconds}` |
%%                 `{task_ttl, StaleAfter_seconds}` |
%%                 `{agent_ttl, _default}` |
%%                 `{bearing_ttl, {Heading, Speed}}` |
%%                 `{trust_ttl, {InitialTrust, DecayRate}}`
-spec start_link(atom(), term()) -> gen_server:start_ret().
start_link(Type, Arg) ->
    gen_server:start_link(?MODULE, [Type, Arg], []).

%% @doc Start with explicit name registration.
-spec start_link({local | global, term()}, atom(), term()) -> gen_server:start_ret().
start_link(Name, Type, Arg) ->
    gen_server:start_link(Name, ?MODULE, [Type, Arg], []).

%%%=============================================================================
%%% gen_server callbacks
%%%=============================================================================

init([Type, Arg]) ->
    case Type of
        tile_ttl ->
            TTL_ms = Arg * 1000,
            Ref = erlang:send_after(TTL_ms, self(), ttl_expired),
            {ok, #keel_state{type=tile_ttl,
                  inner=#tile_state{name=Arg, ttl_ref=Ref}},
             hibernate};

        task_ttl ->
            StaleAfter_ms = Arg * 1000,
            Ref = erlang:send_after(StaleAfter_ms, self(), stale),
            {ok, #keel_state{type=task_ttl,
                  inner=#task_state{name=Arg, stale_ref=Ref,
                                    stale_after=StaleAfter_ms}},
             hibernate};

        agent_ttl ->
            Now = erlang:monotonic_time(millisecond),
            %% Initially consider the process alive (set last_output to now)
            erlang:send_after(?AGENT_OUTPUT_WINDOW, self(), check_silence),
            {ok, #keel_state{type=agent_ttl,
                  inner=#agent_state{name=Arg,
                                     last_output_ts=Now,
                                     silence_threshold=?AGENT_OUTPUT_WINDOW}},
             hibernate};

        bearing_ttl ->
            {Heading, Speed} = Arg,
            %% Register with the bearing registry
            keel_bearings:register(self(), Heading, Speed),
            timer:send_interval(?DEFAULT_CHECK_INTERVAL, self(), check_heading),
            {ok, #keel_state{type=bearing_ttl,
                  inner=#bearing_state{name=undefined,
                                       heading=Heading,
                                       speed=Speed}},
             hibernate};

        trust_ttl ->
            {InitialTrust, DecayRate} = Arg,
            Ref = erlang:send_after(?TRUST_DECAY_TICK, self(), decay_trust),
            {ok, #keel_state{type=trust_ttl,
                  inner=#trust_state{name=Arg,
                                     trust=InitialTrust,
                                     decay_rate=DecayRate,
                                     decay_ref=Ref}},
             hibernate}
    end.

%%% --- handle_call --- %%%

handle_call({get_type}, _From, #keel_state{type=T}=S) ->
    {reply, T, S};
handle_call({get_trust}, _From, #keel_state{type=trust_ttl,
          inner=#trust_state{trust=T}}=S) ->
    {reply, T, S};
handle_call({get_bearing}, _From, #keel_state{type=bearing_ttl,
          inner=#bearing_state{heading=H, speed=Sp}}=S) ->
    {reply, {H, Sp}, S};
handle_call({ping}, _From, S) ->
    {reply, {pong, S#keel_state.type}, S};
handle_call(_Req, _From, S) ->
    {reply, {error, unknown_call}, S}.

%%% --- handle_cast --- %%%

%% task_ttl: heartbeat resets staleness timer
handle_cast({heartbeat}, #keel_state{type=task_ttl,
          inner=#task_state{stale_ref=OldRef, stale_after=SA}=Inner}=S) ->
    _ = erlang:cancel_timer(OldRef),
    NewRef = erlang:send_after(SA, self(), stale),
    {noreply, S#keel_state{inner=Inner#task_state{stale_ref=NewRef}}};

%% agent_ttl: record that output was produced
handle_cast({output, _Data}, #keel_state{type=agent_ttl,
          inner=#agent_state{}=Inner}=S) ->
    Now = erlang:monotonic_time(millisecond),
    {noreply, S#keel_state{
        inner=Inner#agent_state{last_output_ts=Now}}};

%% trust_ttl: increase trust (like positive reinforcement)
handle_cast({boost_trust, Amount}, #keel_state{type=trust_ttl,
          inner=#trust_state{trust=T}=Inner}=S) ->
    NewTrust = min(1.0, T + Amount),
    ?LOG_INFO(#{what=>trust_boosted, trust=>NewTrust}),
    {noreply, S#keel_state{inner=Inner#trust_state{trust=NewTrust}}};

handle_cast(_Msg, S) ->
    {noreply, S}.

%%% --- handle_info --- %%%

%% tile_ttl: timer expired → die
handle_info(ttl_expired, #keel_state{type=tile_ttl}=S) ->
    ?LOG_INFO(#{what=>tile_ttl_expired, pid=>self()}),
    {stop, normal, S};

%% task_ttl: staleness timer fired → die
handle_info(stale, #keel_state{type=task_ttl}=S) ->
    ?LOG_INFO(#{what=>task_stale, pid=>self()}),
    {stop, normal, S};

%% agent_ttl: periodic silence check
handle_info(check_silence, #keel_state{type=agent_ttl,
          inner=#agent_state{last_output_ts=Last, silence_threshold=Thresh}}=S) ->
    Now = erlang:monotonic_time(millisecond),
    case (Now - Last) > Thresh of
        true ->
            ?LOG_INFO(#{what=>agent_silent_death, pid=>self(),
                        silent_ms => Now - Last}),
            {stop, normal, S};
        false ->
            erlang:send_after(Thresh, self(), check_silence),
            {noreply, S}
    end;

%% bearing_ttl: periodic heading check
handle_info(check_heading, #keel_state{type=bearing_ttl,
          inner=#bearing_state{heading=H, speed=Sp}}=S) ->
    %% Query bearing registry for collisions
    case keel_bearings:detect_collision(self(), H, Sp) of
        {collision, OtherPid} ->
            ?LOG_INFO(#{what=>bearing_collision, pid=>self(),
                        with=>OtherPid, heading=>H}),
            %% Die — collision detected, first-person termination
            {stop, normal, S};
        _NoCollision ->
            {noreply, S}
    end;

%% trust_ttl: decay trust by one tick
handle_info(decay_trust, #keel_state{type=trust_ttl,
          inner=#trust_state{trust=T, decay_rate=D}=Inner}=S) ->
    NewT = max(0.0, T - D),
    case NewT =< ?TRUST_FLOOR of
        true ->
            ?LOG_INFO(#{what=>trust_depleted, pid=>self(),
                        final_trust=>NewT}),
            {stop, normal, S};
        false ->
            Ref = erlang:send_after(?TRUST_DECAY_TICK, self(), decay_trust),
            {noreply, S#keel_state{
                inner=Inner#trust_state{trust=NewT, decay_ref=Ref}}}
    end;

handle_info(_Info, S) ->
    {noreply, S}.

%%% --- terminate --- %%%

terminate(_Reason, #keel_state{type=Type, inner=_Inner}) ->
    case Type of
        bearing_ttl ->
            keel_bearings:unregister(self());
        _ ->
            ok
    end,
    ok.

%%% --- code_change --- %%%

code_change(_OldVsn, S, _Extra) ->
    {ok, S}.

%%%=============================================================================
%%% Unit tests
%%%=============================================================================
-ifdef(TEST).
-include_lib("eunit/include/eunit.hrl").

tile_ttl_self_terminates_test() ->
    %% A tile with 0.1s TTL should die quickly
    {ok, Pid} = start_link(tile_ttl, 1),
    timer:sleep(1100),
    ?assertNot(erlang:is_process_alive(Pid)).

task_ttl_dies_without_heartbeat_test_() ->
    {ok, Pid} = start_link(task_ttl, 1),
    timer:sleep(1100),
    ?assertNot(erlang:is_process_alive(Pid)).

task_ttl_survives_with_heartbeat_test() ->
    {ok, Pid} = start_link(task_ttl, 2),
    %% Send heartbeats to keep alive
    gen_server:cast(Pid, {heartbeat}),
    timer:sleep(1500),
    ?assert(erlang:is_process_alive(Pid)),
    gen_server:cast(Pid, {heartbeat}),
    timer:sleep(1500),
    ?assert(erlang:is_process_alive(Pid)),
    %% Stop cleanly
    gen_server:stop(Pid).

agent_ttl_output_is_heartbeat_test() ->
    {ok, Pid} = start_link(agent_ttl, ok),
    %% Produce output regularly
    gen_server:cast(Pid, {output, data}),
    timer:sleep(2000),
    ?assert(erlang:is_process_alive(Pid)),
    gen_server:cast(Pid, {output, data}),
    timer:sleep(2000),
    ?assert(erlang:is_process_alive(Pid)),
    gen_server:stop(Pid).

trust_ttl_decays_over_time_test_() ->
    %% Start with high trust, slow decay — should survive
    {ok, Pid} = start_link(trust_ttl, {0.9, 0.01}),
    timer:sleep(500),
    ?assert(erlang:is_process_alive(Pid)),
    gen_server:stop(Pid).

-endif.
