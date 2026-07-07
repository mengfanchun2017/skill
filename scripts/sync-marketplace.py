#!/usr/bin/env python3
"""Sync marketplace.json descriptions from SKILL.md frontmatter.

Usage:
  python3 scripts/sync-marketplace.py          # check mode (report drift, exit 1 if stale)
  python3 scripts/sync-marketplace.py --write  # update marketplace.json in-place
"""

import json, os, sys, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS = os.path.join(REPO, "plugins")
MARKETPLACE = os.path.join(REPO, ".claude-plugin", "marketplace.json")


def parse_frontmatter(path):
    """Extract name + description from SKILL.md YAML frontmatter."""
    with open(path) as f:
        content = f.read()
    if not content.startswith("---"):
        return None, None
    end = content.find("---", 3)
    if end == -1:
        return None, None
    fm = content[3:end]
    name = None
    desc = None
    for line in fm.split("\n"):
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("description:"):
            val = line.split(":", 1)[1].strip()
            if val == "|":
                # multi-line description
                desc_lines = []
                for sub in fm.split("\n")[fm.split("\n").index(line) + 1 :]:
                    if sub and not sub.startswith(" ") and ":" in sub:
                        break
                    desc_lines.append(sub.strip())
                desc = " ".join(desc_lines).strip()
            else:
                desc = val.strip('"').strip("'")
    return name, desc


def main():
    write_mode = "--write" in sys.argv

    # Read marketplace
    with open(MARKETPLACE) as f:
        mp = json.load(f)

    # Build index: name -> entry for local plugins
    local_entries = {}
    external_entries = []
    for entry in mp["plugins"]:
        src = entry.get("source", "")
        if isinstance(src, str) and src.startswith("./plugins/"):
            local_entries[entry["name"]] = entry
        else:
            external_entries.append(entry)

    # Scan plugin dirs
    plugin_dirs = set()
    if os.path.isdir(PLUGINS):
        for d in os.listdir(PLUGINS):
            skill_md = os.path.join(PLUGINS, d, "SKILL.md")
            if os.path.isfile(skill_md):
                plugin_dirs.add(d)

    # Collect frontmatter
    fm_data = {}
    for d in plugin_dirs:
        skill_md = os.path.join(PLUGINS, d, "SKILL.md")
        name, desc = parse_frontmatter(skill_md)
        if name and desc:
            fm_data[name] = desc

    changes = 0
    ghosts = []
    orphans = []

    # Check ghosts: marketplace entries without plugin dirs
    for name in local_entries:
        if name not in fm_data:
            ghosts.append(name)

    # Check orphans: plugin dirs without marketplace entries
    for name in fm_data:
        if name not in local_entries:
            orphans.append(name)

    # Sync descriptions
    for name, entry in local_entries.items():
        if name not in fm_data:
            continue
        fm_desc = fm_data[name]
        mp_desc = entry.get("description", "")
        if fm_desc != mp_desc:
            changes += 1
            print(f"  DRIFT  {name}")
            print(f"    marketplace: {mp_desc[:80]}...")
            print(f"    SKILL.md:    {fm_desc[:80]}...")
            if write_mode:
                entry["description"] = fm_desc

    # Report ghosts and orphans
    if ghosts:
        print(f"\n  GHOST ({len(ghosts)}): marketplace entries without plugin dirs:")
        for g in ghosts:
            print(f"    - {g}")
    if orphans:
        print(f"\n  ORPHAN ({len(orphans)}): plugin dirs without marketplace entries:")
        for o in orphans:
            print(f"    - {o}")

    # Summary
    total_issues = changes + len(ghosts) + len(orphans)
    if total_issues == 0:
        print("  OK — marketplace.json in sync with SKILL.md frontmatter")
        return

    if write_mode and changes > 0:
        # Rebuild plugins array: local entries (updated) + external entries
        new_plugins = list(local_entries.values()) + external_entries
        mp["plugins"] = new_plugins
        with open(MARKETPLACE, "w") as f:
            json.dump(mp, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"\n  WROTE {changes} description(s) updated in marketplace.json")

    if not write_mode and total_issues > 0:
        print(f"\n  {total_issues} issue(s) — run with --write to fix description drift")
        print(f"  Ghosts/orphans must be fixed manually (add/remove marketplace entries)")
        sys.exit(1)


if __name__ == "__main__":
    main()
