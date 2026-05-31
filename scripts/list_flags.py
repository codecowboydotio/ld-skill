#!/usr/bin/env python3
"""
List all feature flags for a given LaunchDarkly project.

Usage:
    python list_flags.py --project <project-key> [--env <environment-key>] [--summary]

Environment variables:
    LD_API_KEY   Your LaunchDarkly API key (or pass via --api-key)
"""

import argparse
import os
import sys
import json
import urllib.request
import urllib.error

LD_API_BASE = "https://app.launchdarkly.com/api/v2"


def get_headers(api_key: str) -> dict:
    return {
        "Authorization": api_key,
        "Content-Type": "application/json",
        "LD-API-Version": "20240415",
    }


def fetch(url: str, api_key: str) -> dict:
    req = urllib.request.Request(url, headers=get_headers(api_key))
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            detail = json.loads(body).get("message", body)
        except Exception:
            detail = body
        print(f"HTTP {e.code} error: {detail}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def list_flags(api_key: str, project_key: str, env_key: str | None):
    params = "?limit=100"
    if env_key:
        params += f"&env={env_key}"

    url = f"{LD_API_BASE}/flags/{project_key}{params}"
    all_flags = []
    offset = 0

    while True:
        page_url = url + (f"&offset={offset}" if offset else "")
        data = fetch(page_url, api_key)
        items = data.get("items", [])
        all_flags.extend(items)

        total = data.get("totalCount", len(all_flags))
        offset += len(items)
        if offset >= total or not items:
            break

    return all_flags, data.get("totalCount", len(all_flags))


def main():
    parser = argparse.ArgumentParser(description="List LaunchDarkly feature flags for a project.")
    parser.add_argument("--project", "-p", required=True, help="LaunchDarkly project key")
    parser.add_argument("--env", "-e", default=None, help="Filter/show env details for this environment key")
    parser.add_argument("--api-key", "-k", default=None, help="LaunchDarkly API key (overrides LD_API_KEY env var)")
    parser.add_argument("--filter-tag", "-t", default=None, help="Only show flags with this tag")
    parser.add_argument("--filter-kind", default=None, choices=["boolean", "multivariate"], help="Filter by flag kind")
    parser.add_argument("--filter-key", action="append", default=None, metavar="KEY", help="Only show flags with this key (repeatable)")
    parser.add_argument("--archived", action="store_true", help="Include archived flags only")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("LD_API_KEY")
    if not api_key:
        print("Error: provide --api-key or set the LD_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    flags, total = list_flags(api_key, args.project, args.env)

    # Client-side filters
    if args.filter_tag:
        flags = [f for f in flags if args.filter_tag in f.get("tags", [])]
    if args.filter_kind:
        flags = [f for f in flags if f.get("kind") == args.filter_kind]
    if args.filter_key:
        flags = [f for f in flags if f.get("key") in args.filter_key]
    if args.archived:
        flags = [f for f in flags if f.get("archived")]

    # Distil to fields most useful for a Claude skill
    output = {
        "project": args.project,
        "environment": args.env,
        "total": total,
        "count": len(flags),
        "flags": [
            {
                "key": f.get("key"),
                "name": f.get("name"),
                "kind": f.get("kind"),
                "description": f.get("description") or "",
                "tags": f.get("tags", []),
                "archived": f.get("archived", False),
                "deprecated": f.get("deprecated", False),
                "temporary": f.get("temporary", False),
                "variations": [
                    {
                        "value": v.get("value"),
                        "name": v.get("name", ""),
                        "description": v.get("description", ""),
                    }
                    for v in f.get("variations", [])
                ],
                **(
                    {
                        "environment": {
                            "on": f.get("environments", {}).get(args.env, {}).get("on", False),
                            "offVariation": f.get("environments", {}).get(args.env, {}).get("offVariation"),
                        }
                    }
                    if args.env else {}
                ),
            }
            for f in flags
        ],
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()