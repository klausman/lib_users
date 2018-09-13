#!/usr/bin/python -tt
"""
Libusers - a script that finds users of libs that have been deleted/replaced
"""

# Released under the GPL-2
# -*- coding: utf8 -*-

import argparse
import sys
import glob
import fnmatch
import os

from os.path import normpath
from collections import defaultdict
from lib_users_util import common

PERMWARNING = """Warning: Some files could not be read."""
PERMWARNINGUID0="""\
Warning: Some files could not be read. Note that lib_users has to be run as
root to get a full list of deleted in-use libraries.\n"""

__version__ = "0.12"

# These are no true libs so don't make our process a deleted libs user
# The first set is patterns, i.e. they are compared using fnmatch()
# These are NOT regular expressions!
NOLIBSPT = set(["/SYSV*", "/dev/shm/*", "/tmp/orcexec.*", "/var/run/nscd/db*",
                "/memfd:*", "/run/user/*/orcexec*"])
# This set is compared literally, i.e. no special characters
NOLIBSNP = set(["/dev/zero", "/drm", "object", "/[aio]", "/i915"])


def get_deleted_libs(map_file):
    """
    Get all deleted libs from a given map file and return them as a set.
    """
    deletedlibs = set()

    for line in map_file:
        line = line.strip()
        # Normal Linux maps file
        if line.endswith("(deleted)"):
            lib = line.split()[-2]
            is_lib = all(not fnmatch.fnmatch(lib, pattern)
                         for pattern in NOLIBSPT)
            if is_lib and lib not in NOLIBSNP:
                deletedlibs.add(lib)

        # OpenVZ maps file
        elif line.split()[-1].startswith("(deleted)"):
            lib = line.split()[-1][9:]
            is_lib = all(not fnmatch.fnmatch(lib, pattern)
                         for pattern in NOLIBSPT)
            if is_lib and lib not in NOLIBSNP:
                deletedlibs.add(lib)

    return deletedlibs


def main(argv):
    """Main program"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version',
                        version='%%(prog)s %s' % (__version__))
    parser.add_argument("-m", "--machine-readable", action="store_true",
                        help="Output machine readable info")
    parser.add_argument("-s", "--showlibs", action="store_true",
                        help="In human readable mode, show deleted libs")
    parser.add_argument("-S", "--services", action="store_true",
                        help="Try to find systemd services for lib users")
    parser.add_argument("-i", "--ignore-pattern", default=[],
                        metavar="GLOB", action='append',
                        help="Ignore deleted files matching %(metavar)s. "
                        "Can be specified multiple times.")
    parser.add_argument("-I", "--ignore-literal", default=[],
                        metavar="LITERAL", action='append',
                        help="Ignore deleted files named %(metavar)s. "
                        "Can be specified multiple times.")

    options = parser.parse_args(argv)
    options.showitems = options.showlibs

    NOLIBSPT.update(options.ignore_pattern)
    NOLIBSNP.update(options.ignore_literal)

    users = defaultdict(lambda: (set(), set()))
    read_failure = False

    for map_filename in glob.glob(common.LIBPROCFSPAT):
        deletedlibs = set()
        try:
            pid = normpath(map_filename).split("/")[2]
        except IndexError:
            # This happens if the filenames look different
            # than we expect (e.g. the user changed common.LIBPROCFSPAT)
            pid = "unknown"

        try:
            mapsfile = open(map_filename)
            deletedlibs = get_deleted_libs(mapsfile)
        except IOError as exc:
            read_failure = True
            continue

        if deletedlibs:
            argv = common.get_progargs(pid)
            if not argv:
                continue
            users[argv][0].add(pid)
            users[argv][1].update(deletedlibs)

    if read_failure:
        if os.geteuid() == 0:
            sys.stderr.write(PERMWARNING)
        else:
            sys.stderr.write(PERMWARNINGUID0)

    if len(users) > 0:
        if options.machine_readable:
            print(common.fmt_machine(users))
        else:
            print(common.fmt_human(users, options))
        if options.services:
            print()
            print(common.get_services(users))

if __name__ == "__main__":
    main(sys.argv[1:])
