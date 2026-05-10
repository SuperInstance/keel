%%%=============================================================================
%%% @doc Bearing Registry — field-based communication channel for the Keel TTL
%%%      Engine.  Processes register their heading (position + velocity).  Other
%%%      processes read headings without sending messages.  The field IS the
%%%      communication channel.
%%%
%%% Architecture: a named ETS table acting as a shared bearing field.
%%%   - Processes write their own bearing with `register/3`.
%%%   - Any process reads any bearing with `get_heading/1`.
%%%   - Collision detection is a read-side query, not a message exchange.
%%%
%%% "The field is the message" — inspired by tuple spaces (Linda) and
%%%  Erlang's shared-nothing ethos.  ETS is the compromise: shared state
%%%  that's read-heavy and write-light, exactly matching the bearing use-case.
%%%=============================================================================
-module(keel_bearings).
-export([start/0, register/3, register_pid/3, unregister/1, update/3,
         get_heading/1, list_all/0, detect_collision/3]).
-export([init/0]).

%% Table ID — created once, used globally
-define(TABLE, keel_bearings_table).

%% Record stored in ETS
-record(bearing, {
    pid     :: pid(),
    heading :: term(),
    speed   :: number(),           %% relative units; higher = faster
    ts      :: non_neg_integer()   %% erlang:monotonic_time() timestamp
}).

%%%=============================================================================
%%% API
%%%=============================================================================

%% @doc Create the bearing table.  Called once at application start.
start() ->
    case ets:info(?TABLE, name) of
        undefined ->
            ets:new(?TABLE, [named_table, public,
                             {keypos, #bearing.pid},
                             {write_concurrency, true},
                             {read_concurrency, true}]);
        _ ->
            {error, already_started}
    end.

%% @doc Compatibility alias — also exported as `register/3` via macro below.
register_pid(Pid, Heading, Speed) ->
    Ts = erlang:monotonic_time(),
    true = ets:insert(?TABLE, #bearing{pid=Pid, heading=Heading,
                                        speed=Speed, ts=Ts}),
    ok.

%% @doc Public alias: `register` clashes with the BIF but we export
%%      `register_pid` as the canonical name.
-spec register(pid(), term(), number()) -> ok.
register(Pid, Heading, Speed) ->
    register_pid(Pid, Heading, Speed).

%% @doc Remove a process from the bearing registry.
-spec unregister(pid()) -> ok.
unregister(Pid) ->
    ets:delete(?TABLE, Pid),
    ok.

%% @doc Update a process's bearing.  Replaces the entry.
-spec update(pid(), term(), number()) -> ok.
update(Pid, Heading, Speed) ->
    register_pid(Pid, Heading, Speed).

%% @doc Read a process's heading.  Returns `{ok, {Heading, Speed}}` or `error`.
-spec get_heading(pid()) -> {ok, {term(), number()}} | error.
get_heading(Pid) ->
    case ets:lookup(?TABLE, Pid) of
        [#bearing{heading=H, speed=Sp}] -> {ok, {H, Sp}};
        [] -> error
    end.

%% @doc List all registered bearings as `[{Pid, Heading, Speed}]`.
-spec list_all() -> [{pid(), term(), number()}].
list_all() ->
    [{Pid, H, Sp} || #bearing{pid=Pid, heading=H, speed=Sp}
                     <- ets:tab2list(?TABLE)].

%% @doc Detect collision: check if any process at the same heading
%%      is on a conflicting trajectory within a proximity threshold.
%%      Returns `{collision, OtherPid}` or `safe`.
%%
%%      Collision logic:
%%        - Same heading (compared via `=:=`)
%%        - Speeds are within a factor of 2 (similar velocity → collision risk)
-spec detect_collision(pid(), term(), number()) ->
    {collision, pid()} | safe.
detect_collision(MyPid, MyHeading, MySpeed) ->
    %% Compute speed bounds in Erlang to avoid match spec arithmetic.
    %% Collision: same heading, speed within factor of 2 of each other.
    MinSpeed = MySpeed / 2,
    MaxSpeed = MySpeed * 2,
    case ets:select(?TABLE, [{#bearing{pid='$1', heading=MyHeading,
                                       speed='$2', ts='_'},
                              [{'=/=', '$1', {const, MyPid}},
                               {'>=', '$2', MinSpeed},
                               {'=<', '$2', MaxSpeed}],
                              ['$1']}]) of
        [OtherPid | _] -> {collision, OtherPid};
        []             -> safe
    end.

%% @doc Compatibility init/0 for OTP application.
init() ->
    start().

%%%=============================================================================
%%% Unit tests
%%%=============================================================================
-ifdef(TEST).
-include_lib("eunit/include/eunit.hrl").

bearings_register_and_read_test() ->
    start(),
    Pid = spawn(fun() -> timer:sleep(infinity) end),
    register(Pid, north, 10),
    {ok, {north, 10}} = get_heading(Pid),
    unregister(Pid),
    error = get_heading(Pid).

bearings_collision_detection_test() ->
    start(),
    PidA = spawn(fun() -> timer:sleep(infinity) end),
    PidB = spawn(fun() -> timer:sleep(infinity) end),
    register(PidA, east, 5),
    register(PidB, east, 5),
    {collision, _} = detect_collision(PidA, east, 5),
    unregister(PidA),
    unregister(PidB).

bearings_no_collision_different_heading_test() ->
    start(),
    PidA = spawn(fun() -> timer:sleep(infinity) end),
    PidB = spawn(fun() -> timer:sleep(infinity) end),
    register(PidA, north, 5),
    register(PidB, south, 5),
    safe = detect_collision(PidA, north, 5),
    unregister(PidA),
    unregister(PidB).

-endif.
