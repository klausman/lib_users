#!/usr/bin/python -tt
"""
Libusers - a script that finds users of libs that have been deleted/replaced
"""

# Copyright 2010 Tobias Klausmann
# Released under the GPL-2

import sys
import glob
import fnmatch

from os.path import normpath
from collections import defaultdict

PROCFSPAT = "/proc/*/maps"
PROCFSBASE = "/proc/"
__version__ = "0.2"

# These are no true libs so don't make our process a deleted libs user
NOLIBS = ["/SYSV*", "/dev/zero", "/dev/shm/*", "/drm"]

def get_deleted_libs(map_file):
    """
    Get all deleted libs from a given map file and return them as a list
    """
    deletedlibs = []

    for line in map_file:
        line = line.strip()
        if line.endswith("(deleted)"):
            lib = line.split()[-2]
            is_lib = all(not fnmatch.fnmatch(lib, pattern) 
                         for pattern in NOLIBS)
            if is_lib and lib not in deletedlibs:
                deletedlibs.append(lib)

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
    argv = [ e.strip() for e in argv ]
    argv = " ".join(argv)
    return argv

def main(verbose_mode=False):
    """Main program"""
    all_map_files = glob.glob(PROCFSPAT)
    users = defaultdict(list)
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
            
        deletedlibs = get_deleted_libs(mapsfile)
        if len(deletedlibs) > 0:
            argv = get_progargs(pid)
            if not argv:
                # The proc file went away, so we need to skip it
                # entirely
                continue
            users[argv].append(pid)

    if len(users)>0:
        for user, pids in users.iteritems():
            if len(pids)<5 or verbose_mode:
                print("{%s} %s" % (",".join(pids), user))
            else:
                print("(%s processes) %s" % (len(pids), user))
        

def usage():
    """Output usage info"""
    print "Lib_users version %s" % (__version__)
    print
    print "Usage: %s -[vh] --[help|verbose]" % (sys.argv[0])
    print "   -h, --help    - This text"
    print "   -v, --verbose - Print all PIDs, even if more than five."

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        usage()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] in ["-v", "--verbose"]:
        main(True)
    else:
        main()
