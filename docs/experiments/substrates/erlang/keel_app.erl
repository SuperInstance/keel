%%%=============================================================================
%%% @doc Keel TTL OTP Application — entry point for the Erlang/OTP system.
%%%=============================================================================
-module(keel_app).
-behaviour(application).

-export([start/2, stop/1]).

start(_StartType, _StartArgs) ->
    keel_sup_chief:start_link().

stop(_State) ->
    ok.
