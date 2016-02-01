#!/usr/bin/python -tt
"""
Libusers - a script that finds users of files that have been deleted/replaced
"""
# Released under the GPL-2

import argparse
import sys
import glob
import fnmatch
import subprocess
import os.path

from collections import defaultdict

PROCFSPAT = "/proc/*/fd"
PROCFSBASE = "/proc/"
PERMWARNING = """\
Warning: Some files could not be read. Note that fd_users has to be run as
root to get a full list of deleted in-use libraries.\n"""
DELSUFFIX = " (deleted)"
__version__ = "0.9"

def get_deleted_files(fddir, ign_patterns, ign_literals):
    """
    Get list of deleted files listed in fddir.

    Args:
        fddir: name of the the FD infor directory, typically something like
               /proc/12345/fd/
        ign_pattern: List of globs for files to ignore
        ign_literal: List of fixed strings to ignore
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


def get_progargs(pid):
    """
    Get argv for a given PID and return it as a string (spaces-sep'd).
    """
    try:
        argv = open("%s/%s/cmdline" % (PROCFSBASE, pid)).read()
    except IOError:
        return None
    return argv.replace('\x00', ' ')


def fmt_human(lib_users, options):
    """
    Format a list of library users into a human-readable table.

    Args:
     lib_users: Dict of library users, keys are argvs (as string), values are
     tuples of two sets, first listing the libraries used, second listing the
     PIDs: { argv: ({pid, pid, ...}, {lib, lib, ...}), argv: ... }
     options: an object that has a showfiles bool that determines whether the
     libraries in use should be shown. usually the return value of argparse's
     parse_args().
    Returns:
     A multiline string for human consumption
    """
    res = []
    for argv, pidsfiles in lib_users.items():
        pidlist = ",".join(sorted(list(pidsfiles[0])))
        if options.showfiles:
            files = ",".join(sorted(pidsfiles[1]))
            res.append('%s "%s" uses %s' % (pidlist, argv.strip(), files))
        else:
            res.append('%s "%s"' % (pidlist, argv.strip()))
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
    res = []
    for argv, pidsfiles in lib_users.items():
        pidlist = ",".join(sorted(pidsfiles[0]))
        files = ",".join(sorted(pidsfiles[1]))
        res.append("%s;%s;%s" % (pidlist, files, argv.strip()))
    return "\n".join(res)


def query_systemctl(pid, output=None):
    """
    Run systemctl status [pid], return the first token of the first line

    This is normally the service a given PID belongs to by virtue of being
    the corresponding cgroup. If output is not None, do not run systemctl,
    instead use output as if it was provided by it.
    """
    # Since there is no way to query systemd for the unit a given PID belongs to
    # in a way that yields machine-readable output ("status" knows about PIDs,
    # but has only human-readable output, "show" has machine-readable output,
    # but doesn't know about PIDs), we have to do ad hoc parsing. So far, the
    # following formats have been encountered in the wild:
    # sshd.service - OpenSSH Daemon
    # ● sshd.service - OpenSSH Daemon

    if not output:
        cmd = ["systemctl", "status", pid]
        pcomm = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, _ = pcomm.communicate()
    if "No unit for PID %s is loaded." % (pid) in output:
        return None
    header = output.split("\n")[0]
    fields = header.split("-")[0].split()
    if len(fields) == 1:
        # ['sshd.service', 'OpenSSH Daemon']
        svc = fields[0]
    else:
        # ['●', 'sshd.service', 'OpenSSH Daemon']
        svc = fields[1]
    return svc


def get_services(lib_users):
    """
    Run systemctl status for the PIDs in the lib_users list and return a
    list of PIDs to service names as a string for human consumption.
    """
    svc4pid = defaultdict(list)
    try:
        for _, pidsfiles in lib_users.items():
            pidlist = sorted(pidsfiles[0])
            for pid in pidlist:
                unit = query_systemctl(pid)
                if unit:
                    svc4pid[unit].append(pid)
    except OSError as this_exc:
        return "Could not run systemctl: %s" % this_exc
    output = []
    for key, value in svc4pid.items():
        output.append("%s belong to %s" % (",".join(value), key))

    return "\n".join(output)


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

    users = defaultdict(lambda: (set(), set()))
    read_failure = False

    for fddir in glob.glob(PROCFSPAT):
        if (fddir.startswith("/proc/self/fd") or
            fddir.startswith("/proc/thread-self/fd") or
            fddir.startswith("/proc/%s/fd" % (os.getpid()))):
            continue

        deletedfiles = set()
        try:
            pid = os.path.normpath(fddir).split("/")[2]
        except IndexError:
            # This happens if the filenames look different
            # than we expect (e.g. the user changed PROCFSPAT)
            pid = "unknown"

        try:
            deletedfiles = get_deleted_files(fddir, options.ignore_pattern,
                                             options.ignore_literal)
        except IOError as exc:
            read_failure = True
            continue

        if deletedfiles:
            argv = get_progargs(pid)
            if not argv:
                continue
            users[argv][0].add(pid)
            users[argv][1].update(deletedfiles)

    if read_failure:
        sys.stderr.write(PERMWARNING)

    if len(users) > 0:
        if options.machine_readable:
            print(fmt_machine(users))
        else:
            print(fmt_human(users, options))
        if options.services:
            print()
            print(get_services(users))

if __name__ == "__main__":
    main(sys.argv[1:])
