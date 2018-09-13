#!/usr/bin/python -tt
"""
Libusers - a script that finds users of files that have been deleted/replaced
"""
# Released under the GPL-2
# -*- coding: utf8 -*-
import argparse
import sys
import glob
import fnmatch
import os

from collections import defaultdict
from lib_users_util import common

DELSUFFIX = " (deleted)"
PERMWARNING = """Warning: Some files could not be read."""
PERMWARNINGUID0="""\
Warning: Some files could not be read. Note that fd_users has to be run as
root to get a full list of deleted in-use libraries.\n"""

__version__ = "0.12"


def get_deleted_files(fddir, ign_patterns, ign_literals):
    """
    Get list of deleted files listed in fddir.

    Args:
        fddir: name of the the FD infor directory, typically something like
               /proc/12345/fd/
        ign_patterns: List of globs for files to ignore
        ign_literals: List of fixed strings to ignore
    Returns:
        List of deleted files.
    """
    deletedfds = []
    literals = set(ign_literals)
    allfds = glob.glob(os.path.join(fddir, "*"))
    for onefd in allfds:
        # We can't use os.path.exists() since that simply does not work
        # correctly on /proc files (broken links look like working ones).
        target = os.readlink(onefd)
        if target.endswith(DELSUFFIX):
            actual_target = target[:-len(DELSUFFIX)]
            if actual_target in literals:
                continue
            if match_any(actual_target, ign_patterns):
                continue
            deletedfds.append(actual_target)
    return deletedfds


def match_any(name, patterns):
    """Return if name matches any of the patterns (globs)"""
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def main(argv):
    """Main program"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version',
                        version='%%(prog)s %s' % (__version__))
    parser.add_argument("-m", "--machine-readable", action="store_true",
                        help="Output machine readable info")
    parser.add_argument("-s", "--showfiles", action="store_true",
                        help="In human readable mode, show deleted files")
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
    options.showitems = options.showfiles

    users = defaultdict(lambda: (set(), set()))
    read_failure = False

    for fddir in glob.glob(common.FDPROCFSPAT):
        if (fddir.startswith("/proc/self/fd") or
                fddir.startswith("/proc/thread-self/fd") or
                fddir.startswith("/proc/%s/fd" % (os.getpid()))):
            continue

        try:
            pid = os.path.normpath(fddir).split("/")[2]
        except IndexError:
            # This happens if the filenames look different
            # than we expect (e.g. the user changed common.FDPROCFSPAT)
            pid = "unknown"

        try:
            deletedfiles = get_deleted_files(fddir, options.ignore_pattern,
                                             options.ignore_literal)
        except IOError:
            read_failure = True
            continue

        if deletedfiles:
            argv = common.get_progargs(pid)
            if not argv:
                continue
            users[argv][0].add(pid)
            users[argv][1].update(deletedfiles)

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
