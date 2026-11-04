#!/usr/bin/env python3
"""Minimal Agent Bounty Feed MCP client (stdlib only).

Talks to the public Streamable-HTTP MCP server and prints the no-friction
bounties (no KYC, no stake, no bond).

    python3 mcp_client.py             # list no-friction bounties
    python3 mcp_client.py frantic:142 # show one bounty
    python3 mcp_client.py --raw       # print the raw JSON-RPC reply of one call

The server is stateless: it answers `initialize` with no Mcp-Session-Id header and
serves `tools/call` without one, so no session bookkeeping is needed. That is
measured against the live service, not assumed from the spec.
"""
import json
import sys
import urllib.request

URL = "https://agent-bounty-feed.dailydollar.workers.dev/mcp"
UA = "agent-bounty-feed-demo/1.1"


def post(payload):
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": UA,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", "ignore")
        sid = r.headers.get("mcp-session-id")
    # The service answers plain JSON. A server that streams SSE instead puts the
    # JSON-RPC reply on a `data:` line, so both shapes are read here.
    for line in raw.splitlines():
        if line.startswith("data: "):
            raw = line[6:]
            break
    return json.loads(raw), sid


def call(method, params=None, rid=1):
    body = {"jsonrpc": "2.0", "id": rid, "method": method}
    if params is not None:
        body["params"] = params
    return post(body)


def tool(name, args, rid):
    res, _ = call("tools/call", {"name": name, "arguments": args}, rid)
    if "error" in res:
        raise SystemExit("tool error: %s" % res["error"])
    # The payload is a JSON *string* inside content[0].text, not an object.
    return json.loads(res["result"]["content"][0]["text"])


def main(argv):
    init, sid = call("initialize", {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "llmrt", "version": "1.1"}})
    info = init["result"]["serverInfo"]
    print("server: %s %s" % (info["name"], info["version"]))
    print("session id: %s" % (sid or "none (stateless: later calls need no header)"))

    if len(argv) > 1 and argv[1] == "--raw":
        print(json.dumps(call("tools/call", {"name": "get_feed_stats", "arguments": {}}, 2), indent=1))
        return

    if len(argv) > 1:
        print(json.dumps(tool("get_bounty", {"id": argv[1]}, 2), indent=1, ensure_ascii=False))
        return

    listing = tool("list_bounties", {"limit": 20, "exclude_requires": "kyc,stake,bond"}, 2)
    items = listing.get("items") or []
    print("\n%d of %d no-friction bounties" % (len(items), listing.get("total_matching")))
    for b in items:
        print("  $%-5s %-11s %-52s %s" % (
            b.get("est_usd"), b.get("source"), (b.get("title") or "")[:52], b.get("id")))

    stats = tool("get_feed_stats", {}, 3)
    print("\nfeed generated_at %s, %s items, %s USD listed" % (
        stats.get("generated_at"), stats.get("stats", {}).get("items"),
        stats.get("stats", {}).get("total_usd")))


if __name__ == "__main__":
    main(sys.argv)
