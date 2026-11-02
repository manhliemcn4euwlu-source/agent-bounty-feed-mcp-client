#!/usr/bin/env python3
"""Minimal Agent Bounty Feed MCP client (stdlib only).

Talks to the public Streamable-HTTP MCP server, lists the tools it exposes, and
prints the no-friction bounties (no KYC, no stake, no bond).

    python mcp_client.py            # list no-friction bounties
    python mcp_client.py <id>       # show one bounty, e.g. frantic:142
"""
import json
import sys
import urllib.request

URL = "https://agent-bounty-feed.dailydollar.workers.dev/mcp"
UA = "agent-bounty-feed-demo/1.0"


def post(payload, session=None):
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream",
               "User-Agent": UA}
    if session:
        headers["Mcp-Session-Id"] = session
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        sid = r.headers.get("mcp-session-id")
        raw = r.read().decode("utf-8", "ignore")
    for line in raw.splitlines():
        if line.startswith("data: "):
            raw = line[6:]
            break
    return json.loads(raw), sid


def call(method, params=None, session=None, rid=1):
    body = {"jsonrpc": "2.0", "id": rid, "method": method}
    if params is not None:
        body["params"] = params
    return post(body, session)


def tool(session, name, args, rid):
    res, _ = call("tools/call", {"name": name, "arguments": args}, session, rid)
    if "error" in res:
        raise SystemExit("tool error: %s" % res["error"])
    return json.loads(res["result"]["content"][0]["text"])


def main(argv):
    init, sid = call("initialize", {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "llmrt", "version": "1.0"}})
    info = init["result"]["serverInfo"]
    print("server: %s %s" % (info["name"], info["version"]))

    if len(argv) > 1:
        one = tool(sid, "get_bounty", {"id": argv[1]}, 2)
        print(json.dumps(one, indent=1, ensure_ascii=False))
        return

    listing = tool(sid, "list_bounties",
                   {"limit": 20, "exclude_requires": "kyc,stake,bond"}, 2)
    items = listing.get("items") or []
    print("%d of %d no-friction bounties" % (len(items), listing.get("total_matching")))
    for b in items:
        print("  $%-5s %-9s %-55s %s" % (
            b.get("est_usd"), b.get("source"), (b.get("title") or "")[:55], b.get("id")))

    stats = tool(sid, "get_feed_stats", {}, 3)
    print("\nfeed: %s items, %s USD total" % (
        stats.get("item_count"), stats.get("total_usd")))


if __name__ == "__main__":
    main(sys.argv)
