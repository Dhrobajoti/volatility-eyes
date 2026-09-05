# -*- coding: utf-8 -*-
"""Curated volatility2 plugin list. Unlike volatility3, vol2 was never built
with a requirements-introspection API, so there's no way to auto-derive this
the way vol_service.discovery does for vol3 - hand-picked to the plugins
that actually matter for XP/2003-era triage, not vol2's full ~80-plugin
catalog. Extend this list as specific investigations need more.
"""

PLUGIN_CATALOG = [
    {"name": "pslist", "description": "Lists active processes by walking the EPROCESS list."},
    {"name": "pstree", "description": "Lists processes as a parent/child tree."},
    {"name": "psscan", "description": "Pool-scans for EPROCESS structures - finds hidden/terminated processes pslist misses."},
    {"name": "dlllist", "description": "Lists loaded DLLs for each process."},
    {"name": "cmdline", "description": "Displays process command-line arguments."},
    {"name": "connections", "description": "Lists open network connections (XP/2003 only)."},
    {"name": "connscan", "description": "Pool-scans for connection objects (XP/2003 only) - finds closed/hidden connections too."},
    {"name": "sockets", "description": "Lists open sockets (XP/2003 only)."},
    {"name": "sockscan", "description": "Pool-scans for socket objects."},
    {"name": "hivelist", "description": "Lists registry hives present in memory."},
    {"name": "printkey", "description": "Prints a registry key and its subkeys/values. Needs -K \"key path\" in extra args."},
    {"name": "hashdump", "description": "Dumps LM/NTLM password hashes from the SAM hive."},
    {"name": "svcscan", "description": "Lists Windows services, including hidden ones."},
    {"name": "malfind", "description": "Finds hidden/injected code in process memory."},
    {"name": "filescan", "description": "Pool-scans for file objects present in memory."},
    {"name": "handles", "description": "Lists open handles (files, registry keys, mutexes, etc.) per process."},
    {"name": "ssdt", "description": "Lists the System Service Descriptor Table - detects rootkit hooking."},
]

PLUGIN_NAMES = {p["name"] for p in PLUGIN_CATALOG}
