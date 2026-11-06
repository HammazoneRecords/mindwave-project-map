#!/usr/bin/env python3
"""Validate Project Map JSON documents with precise, dependency-free errors."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def load(path):
    try: return json.loads(path.read_text())
    except json.JSONDecodeError as e: raise ValueError(f"{path}: JSON line {e.lineno}, column {e.colno}: {e.msg}")

def require(obj, keys, path):
    if not isinstance(obj, dict): raise ValueError(f"{path}: expected object")
    for key in keys:
        if key not in obj: raise ValueError(f"{path}: missing required field '{key}'")

def validate_map(data, path):
    require(data,["schemaVersion","id","nodes","edges","roles","permissions"],path)
    ids={}
    for i,n in enumerate(data["nodes"]):
        p=f"{path}:nodes[{i}]"; require(n,["id","type"],p)
        if n["id"] in ids: raise ValueError(f"{p}: duplicate node id '{n['id']}'")
        ids[n["id"]]=p
    for i,e in enumerate(data["edges"]):
        p=f"{path}:edges[{i}]"; require(e,["from","to","type"],p)
        if e["from"] not in ids: raise ValueError(f"{p}: unknown from node '{e['from']}'")
        if e["to"] not in ids: raise ValueError(f"{p}: unknown to node '{e['to']}'")
    roles=set(data["roles"])
    for i,pmt in enumerate(data["permissions"]):
        p=f"{path}:permissions[{i}]"; require(pmt,["subject","relation","object"],p)
        role=pmt["subject"].removeprefix("role:"); node=pmt["object"].removeprefix("node:")
        if role not in roles: raise ValueError(f"{p}: unknown role '{role}'")
        if node not in ids: raise ValueError(f"{p}: unknown object node '{node}'")

def validate_journeys(data, map_data, path):
    if not isinstance(data,list): raise ValueError(f"{path}: expected array")
    node_ids={n["id"] for n in map_data["nodes"]}
    for i,j in enumerate(data):
        p=f"{path}[{i}]"; require(j,["schemaVersion","id","map","initial","steps"],p)
        if j["map"] != map_data["id"]: raise ValueError(f"{p}: map '{j['map']}' does not match '{map_data['id']}'")
        require(j["initial"],["role","node"],p+".initial")
        if j["initial"]["node"] not in node_ids: raise ValueError(f"{p}.initial: unknown node '{j['initial']['node']}'")
        if not isinstance(j["steps"],list): raise ValueError(f"{p}.steps: expected array")
        for k,s in enumerate(j["steps"]):
            sp=f"{p}.steps[{k}]"; require(s,["type"],sp)
            if s["type"] == "move" and s.get("to") not in node_ids: raise ValueError(f"{sp}: unknown target node '{s.get('to')}'")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--map",required=True); ap.add_argument("--journeys",required=True); args=ap.parse_args()
    try:
        mpath=Path(args.map); jpath=Path(args.journeys); m=load(mpath); validate_map(m,args.map); validate_journeys(load(jpath),m,args.journeys)
    except (OSError,ValueError) as e: print(f"INVALID: {e}"); return 1
    print(f"VALID: map={m['id']} journeys={args.journeys}"); return 0
if __name__ == "__main__": sys.exit(main())
