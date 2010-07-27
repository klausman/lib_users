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

PROCFS = "/proc"
DELUSERS = []
__version__ = "0.1"
__revision__ = "$Revision$".split()[1]

# These are no true libs so don't make our process a deleted libs user
NOLIBS = ["/SYSV*", "/dev/zero"]

def get_deleted_libs(map_file):
    """
    Get all deleted libs from a given map file and return them as a list
    """
    deletedlibs = []

    try:
        maps = map_file.readlines()
    except IOError:
        # File is gone or not readable, so we can only return []
        return(deletedlibs)

    for line in maps:
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
    argv = open("%s/%s/cmdline" % (PROCFS, pid)).read()
    argv = argv.split('\x00')
    argv = [ e.strip() for e in argv ]
    return argv

def format_pal(argv, pid, deletedlibs, verbose=False):
    """
    Format pid, argv and library list into a nice format, also shortening the
    lib list if verbose is False and return it as a string

    """
    pidargs = "(%s) \"%s\"" % (pid, " ".join(argv))

    if len(deletedlibs) > 1 and verbose == False:
        ellipsis = "(+%s more)" % (len(deletedlibs)-1)
        deletedlibs = deletedlibs[:1]
        deletedlibs.append(ellipsis)
    pal = pidargs + " uses: " + " ".join(deletedlibs)

    return pal

def main(verbose_mode=False):
    """Main program"""
    all_map_files = glob.glob(PROCFS+"/*/maps")
    for maps_filename in all_map_files:
        pid = normpath(maps_filename).split("/")[2]

        mapsfile = open(maps_filename)
        deletedlibs = get_deleted_libs(mapsfile)

        if len(deletedlibs) > 0:
            argv = get_progargs(pid)
            pal = format_pal(argv, pid, deletedlibs, verbose=verbose_mode)
            DELUSERS.append(pal)

    if len(DELUSERS)>0:
        print "\n".join(DELUSERS)

def usage():
    """Output usage info"""
    print "Lib_users version %s (Rev. %s)" % (__version__, __revision__)
    print
    print "Usage: %s -[vh] --[help|verbose]" % (sys.argv[0])
    print "   -h, --help    - This text"
    print "   -v, --verbose - Print all deleted libs."

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        usage()
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] in ["-v", "--verbose"]:
        main(True)
    else:
        main()
