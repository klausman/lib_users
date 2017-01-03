# -*- coding: utf-8 -*-
"""Common utility functions for both lib_users and fd_users"""
import subprocess
import sys

from collections import defaultdict

FDPROCFSPAT = "/proc/*/fd"
LIBPROCFSPAT = "/proc/*/maps"
PROCFSBASE = "/proc/"


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
        if options.showitems:
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
    # Since there is no way to query systemd for the unit a given PID belongs
    # to in a way that yields machine-readable output ("status" knows about
    # PIDs, but has only human-readable output, "show" has machine-readable
    # output, but doesn't know about PIDs), we have to do ad hoc parsing. So
    # far, the following formats have been encountered in the wild:
    # sshd.service - OpenSSH Daemon
    # ● sshd.service - OpenSSH Daemon

    if not output:
        cmd = ["systemctl", "status", pid]
        pcomm = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, _ = pcomm.communicate()
        output = output.decode(sys.stdin.encoding or "utf-8")
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
