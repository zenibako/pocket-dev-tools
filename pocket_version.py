#!/usr/bin/env python3
"""Print the core.json version for a test build of a Pocket port's next release.

Shared by every port's `make package-test` so all of them number test builds
the same way. Test builds report <next>-rc.<N>, where N counts the commits since
the newest release tag (vX.Y.Z) merged into HEAD. That sorts above the last
release and below the next one, every machine gets the same N for the same
commit, and Pocket Sync stops offering the last release as an update.

<next> is NEXT_VERSION when set, else the --core-json version when a release
prep commit already bumped it past the last tag, else the last release with its
patch number bumped.

    python3 pocket_version.py --repo PORT_CHECKOUT [--core-json PATH]

Ports keep checking CORE_VERSION themselves before writing a package, since
the value can also be passed by hand.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

STABLE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
# core.json metadata.version allows at most 31 characters.
MAX_LENGTH = 31


class VersionError(Exception):
    pass


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def parse(version, what):
    match = STABLE.fullmatch(version)
    if not match:
        raise VersionError(f"{what} is not MAJOR.MINOR.PATCH: {version!r}")
    return tuple(int(part) for part in match.groups())


def committed_version(core_json):
    data = json.loads(Path(core_json).read_text())
    return data["core"]["metadata"]["version"]


def test_version(repo, core_json=None, next_version=None):
    """Return <next>-rc.<N> for the checkout at repo (no leading v)."""
    tags = [tag for tag in git(repo, "tag", "--merged", "HEAD", "--list", "v*").split()
            if STABLE.fullmatch(tag)]
    if not tags:
        raise VersionError("no vX.Y.Z release tag reachable from HEAD; run `git fetch --tags` "
                           "(`git fetch --unshallow --tags` in a shallow clone)")
    tag = max(tags, key=lambda name: parse(name, "tag"))
    last = parse(tag, "tag")
    if next_version:
        upcoming = parse(next_version, "NEXT_VERSION")
        if upcoming <= last:
            raise VersionError(f"NEXT_VERSION must be newer than {tag}")
    else:
        upcoming = (last[0], last[1], last[2] + 1)
        if core_json is not None:
            committed = parse(committed_version(core_json), f"{core_json} version")
            if committed > last:
                upcoming = committed
    count = int(git(repo, "rev-list", "--count", f"{tag}..HEAD"))
    version = "%d.%d.%d-rc.%d" % (*upcoming, count)
    if len(version) > MAX_LENGTH:
        raise VersionError(f"version is longer than the {MAX_LENGTH} characters core.json allows: {version}")
    return version


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default=".", help="port checkout (default: current directory)")
    parser.add_argument("--core-json", help="committed core.json whose version a release prep commit may have bumped")
    args = parser.parse_args(argv)
    try:
        print(test_version(Path(args.repo), args.core_json, os.environ.get("NEXT_VERSION") or None))
    except (VersionError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", None) or error
        print(f"pocket_version: {str(detail).strip()}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
