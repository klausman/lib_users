#!/usr/bin/python -tt
"""
Libusers - a script that finds users of libs that have been deleted/replaced
"""

# Copyright 2010 Tobias Klausmann
# Released under the GPL-2

import argparse
import sys
import glob
import fnmatch
import subprocess

from os.path import normpath
from collections import defaultdict

PROCFSPAT = "/proc/*/maps"
PROCFSBASE = "/proc/"
PERMWARNING = """\
Warning: Some files could not be read. Note that lib_users has to be run as
root to get a full list of deleted in-use libraries.\n"""
__version__ = "0.7"

# These are no true libs so don't make our process a deleted libs user
# The first set is patterns, i.e. they are compared using fnmatch()
# These are NOT regular expressions!
NOLIBSPT = set(["/SYSV*", "/dev/shm/*", "/tmp/orcexec.*"])
# This set is compared literally, i.e. no special characters
NOLIBSNP = set(["/dev/zero", "/drm", "object", "/[aio]"])


def get_deleted_libs(map_file):
    """
    Get all deleted libs from a given map file and return them as a set
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


def get_progargs(pid):
    """
    Get argv for a given PID and return it as a list
    """
    try:
        argv = open("%s/%s/cmdline" % (PROCFSBASE, pid)).read()
    except IOError:
        return None
    argv = argv.split('\x00')
    argv = [e.strip() for e in argv]
    argv = " ".join(argv)
    return argv


def fmt_human(lib_users, options):
    """
    Format a list of library users into a human-readable table

    Args:
     lib_users: Dict of library users, keys are argvs (as string), values are
     tuples of two sets, first listing the libraries used, second listing the
     PIDs: { argv: ({pid, pid, ...}, {lib, lib, ...}), argv: ... }
    Returns:
     A multiline string for human consumption
    """
    # Usually, users don't care about what libs exactly are used
    res = []
    for argv, pidslibs in lib_users.items():
        pidlist = ",".join(sorted(list(pidslibs[0])))
        if options.show_libs:
            libslist = ",".join(sorted(pidslibs[1]))
            res.append("%s \"%s\" uses %s" % (pidlist, argv.strip(), libslist))
        else:
            res.append("%s \"%s\"" % (pidlist, argv.strip()))
    return "\n".join(res)


def fmt_machine(lib_users):
    """
    Format a list of library users into a machine-readable table

    Args:
     lib_users: Dict of library users, keys are argvs (as string), values are
     tuples of two sets, first listing the libraries used, second listing the
     PIDs: { argv: ({lib, lib, ...}, {pid, pid, ...}), argv: ... }
    Returns:
     A multiline string for machine consumption
    """
    # Usually, users don't care about what libs exactly are used
    res = []
    for argv, pidslibs in lib_users.items():
        pidlist = ",".join(sorted(pidslibs[0]))
        libslist = ",".join(sorted(pidslibs[1]))
        res.append("%s;%s;%s" % (pidlist, libslist, argv.strip()))
    return "\n".join(res)


def query_systemctl(pid):
    """
    Run systemctl status [pid], return the first token of the first line

    This is noromally the service a given PID belongs to by virtue of being
    the corresponding cgroup.
    """
    # TODO: tests
    cmd = ["systemctl", "status", pid]
    pcomm = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, _ = pcomm.communicate()
    header = output.split("\n")[0]
    svc = header.split()[0]
    return svc


def get_services(lib_users):
    """
    Run systemctl status for the PIDs in the lib_users list and return a
    list of PIDs to service names as a string for human consumption.
    """
    # TODO: tests
    svc4pid = defaultdict(list)
    try:
        for argv, pidslibs in lib_users.items():
            pidlist = sorted(pidslibs[0])
            for pid in pidlist:
                svc4pid[query_systemctl(pid)].append(pid)
    except OSError as e:
        return("Could not run systemctl: %s" % e)
    output = []
    for k, v in svc4pid.items():
        output.append("%s belong to %s" % (",".join(v), k))

    return "\n".join(output)


def main(options):
    """Main program"""
    all_map_files = glob.glob(PROCFSPAT)
    users = {}
    users = defaultdict(lambda: (set(), set()))
    read_failure = False
    for map_filename in all_map_files:
        try:
            pid = normpath(map_filename).split("/")[2]
        except IndexError:
            # This happens if the filenames look different
            # than we expect (e.g. the user changed PROCFSPAT)
            pid = "unknown"

        try:
            mapsfile = open(map_filename)
        except IOError:
            # The file is unreadable for us, so skip it silently
            continue

        try:
            deletedlibs = get_deleted_libs(mapsfile)
        except IOError:
            read_failure = True
            continue

        if len(deletedlibs) > 0:
            argv = get_progargs(pid)
            if not argv:
                continue
            users[argv][0].add(pid)
            users[argv][1].update(deletedlibs)

    if read_failure:
        sys.stderr.write(PERMWARNING)

    if len(users) > 0:
        if options.machine_mode:
            print(fmt_machine(users))
        else:
            print(fmt_human(users, options))
        if options.services:
            print("")
            print(get_services(users))


def get_ignore_list(args):
    """Derive list of to-be-ignored strings and patterns from command line"""
    # TODO: tests
    argvset = set(sys.argv)
    if set(args).intersection(argvset):
        index = None
        for i in range(len(args)):
            try:
                index = sys.argv.index(args[i])
            except ValueError:
                continue
            break
        try:
            return sys.argv[index + 1]
        except IndexError:
            return ''

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--machine-readable", action="store_true",
                        help="Output machine readable info")
    parser.add_argument("-s", "--showlibs", action="store_true",
                        help="In human readable mode, show deleted libs in "
                             "use")
    parser.add_argument("-S", "--services", action="store_true",
                        help="Try to find systemd services for lib users")
    parser.add_argument("-i", "--ignore-pattern", default=[],
                        metavar="REGEXP", action='append',
                        help="Ignore deleted files matching %(metavar)s. "
                        "Can be specified multiple times.")
    parser.add_argument("-I", "--ignore-literal", default=[],
                        metavar="LITERAL", action='append',
                        help="Ignore deleted files named %(metavar)s. "
                        "Can be specified multiple times.")

    options = parser.parse_args()

    NOLIBSPT.update(options.ignore_pattern)
    NOLIBSNP.update(options.ignore_literal)

    main(options)
