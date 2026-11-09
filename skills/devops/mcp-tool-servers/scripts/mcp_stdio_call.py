#!/usr/bin/env python3
"""Generic stdio MCP probe: list tools, or call one tool and print the REAL payload.

Vendor CLIs (imagine, <vendor> serve) ke jhoothe error messages bypass karta hai: server ka
asli text + structured content dono deta hai.

Usage:
  python3 mcp_stdio_call.py <vendor-bin> [tool] [json-args] [--args serve] [--timeout 60]

Examples:
  # tools count + names
  python3 mcp_stdio_call.py imagine

  # ek real call (args JSON file se bhi de sakte ho: @args.json)
  python3 mcp_stdio_call.py imagine generate_image '{"prompt":"a red bicycle on a beach at dawn","aspect_ratio":"1:1","model":null,"duration":null,"org_id":"<org>"}'

Notes:
  - Required properties PRESENT hone chahiye (null chalega, omit nahi) — warna validation error.
  - struct: nested dict me aksar asli error hota hai (e.g. structured_content["assets"][0]["errorMessage"]).
  - structured_content vs structuredContent SDK version pe depend karta hai -> getattr fallback.
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def flat(res) -> str:
    return "".join(getattr(c, "text", "") for c in getattr(res, "content", []) or [])


def struct(res):
    return getattr(res, "structured_content", None) or getattr(res, "structuredContent", None)


async def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    bin_name = sys.argv[1]
    rest = sys.argv[2:]
    server_args = ["serve"]
    if "--args" in rest:
        i = rest.index("--args")
        server_args = rest[i + 1].split()
        rest = rest[:i] + rest[i + 1 + 1:]
    timeout = 60.0
    if "--timeout" in rest:
        i = rest.index("--timeout")
        timeout = float(rest[i + 1])
        rest = rest[:i] + rest[i + 2:]

    tool = rest[0] if rest else None
    args = {}
    if len(rest) > 1:
        raw = rest[1]
        if raw.startswith("@"):
            raw = Path(raw[1:]).read_text()
        args = json.loads(raw)

    params = StdioServerParameters(command=bin_name, args=server_args)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            si = getattr(init, "server_info", None) or getattr(init, "serverInfo", None)
            print(f"server: {getattr(si, 'name', '?')} {getattr(si, 'version', '?')}")

            tools = (await session.list_tools()).tools
            print(f"tools: {len(tools)}")
            names = [t.name for t in tools]
            print("names:", ", ".join(names[:40]), "..." if len(names) > 40 else "")

            if not tool:
                return 0

            res = await asyncio.wait_for(session.call_tool(tool, args), timeout=timeout)
            print("is_error:", getattr(res, "is_error", None))
            print("text:", flat(res)[:2000])
            sc = struct(res)
            if sc is not None:
                print("structured:", json.dumps(sc, default=str)[:2000])
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
