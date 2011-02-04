"""
Test suite for lib_users

To be run through nose, not executed directly.
"""

import sys
import os
import locale

from nose.plugins.skip import SkipTest

import lib_users

from cStringIO import StringIO

# Some tests use sort() - make sure the sorting is the same regardless of
# the users environment
locale.setlocale(locale.LC_ALL, "POSIX")

# Shorthand
EMPTYSET = frozenset()

def test_nonlibs():
    F=[]
    F.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /SYSV00000000 (deleted)""")
    F.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /dev/zero (deleted)""")
    F.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /dev/shm/foo (deleted)""")
    F.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /drm (deleted)""")
    F=StringIO("\n".join(F))
    res = lib_users.get_deleted_libs(F)
    assert(res == EMPTYSET)

def test_libs_with_patterns():
    F=[]
    F.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /lib/SYSV00000000 (deleted)""")
    F.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /lib/dev/zero (deleted)""")
    F.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /lib/dev/shm/foo (deleted)""")
    F.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /lib/drm (deleted)""")
    F=StringIO("\n".join(F))
    res = list(lib_users.get_deleted_libs(F))
    res.sort()
    assert(res == ['/lib/SYSV00000000', '/lib/dev/shm/foo', '/lib/dev/zero', '/lib/drm'])

def test_findlibs():
    F=StringIO("""7f02a85f1000-7f02a85f2000 rw-p 0000c000 09:01 32642 /lib64/libfindme.so (deleted)""")
    assert(lib_users.get_deleted_libs(F) == set(["/lib64/libfindme.so"]))

def test_libplainnames():
    F=StringIO("""7f02a85fc000-7f02a87fb000 ---p 0000a000 09:01 32647 (deleted) /lib64/libdontfindme.so""")
    assert(lib_users.get_deleted_libs(F) == EMPTYSET)

def test_parennames():
    F=StringIO("""7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 /lib64/libdontfindmeeither_(deleted)i-2.11.2.so""")
    assert(lib_users.get_deleted_libs(F) == EMPTYSET)

def test_parenwcontent():
    F=StringIO("""7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 /lib64/libdontfindmeeither-2.11.2.so (notdeleted)""")
    assert(lib_users.get_deleted_libs(F) == EMPTYSET)

def test_parenwcontent2():
    F=StringIO("""7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 /lib64/libdontfindmeeither-2.11.2.so (delete)""")
    assert(lib_users.get_deleted_libs(F) == EMPTYSET)

def test_progargs_str():
    PID=str(os.getpid())
    assert(len(lib_users.get_progargs(PID)) > 0)

def test_progargs_int():
    PID=os.getpid()
    assert(len(lib_users.get_progargs(PID)) > 0)

def test_usage():
    assert(lib_users.usage() == None)

# Input for these is { argv: ({pid, pid, ...}, {lib, lib, ...}), argv: ... }
def test_fmt_human():
    inp={"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
    outp='1,2 "argv1"'
    print lib_users.fmt_human(inp)
    assert(lib_users.fmt_human(inp)==outp)
    inp={"argv1": (set(["1"]), set(["l1", "l2"]))}
    outp='1 "argv1"'
    print lib_users.fmt_human(inp)
    assert(lib_users.fmt_human(inp)==outp)
    # The space at the end of this argv should go away.
    inp={"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
    outp='1 "argv1 argv2"'
    print lib_users.fmt_human(inp)
    assert(lib_users.fmt_human(inp)==outp)
    inp={}
    outp=''
    print lib_users.fmt_human(inp)
    assert(lib_users.fmt_human(inp)==outp)

def test_fmt_machine():
    inp={"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
    outp='1,2;l1,l2;argv1'
    print lib_users.fmt_machine(inp)
    assert(lib_users.fmt_machine(inp)==outp)
    inp={"argv1": (set(["1"]), set(["l1", "l2"]))}
    outp='1;l1,l2;argv1'
    print lib_users.fmt_machine(inp)
    assert(lib_users.fmt_machine(inp)==outp)
    # The space at the end of this argv should go away.
    inp={"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
    outp='1;l1,l2;argv1 argv2'
    print lib_users.fmt_machine(inp)
    assert(lib_users.fmt_machine(inp)==outp)
    inp={"argv1 argv2 ": (set(["1"]), set())}
    outp='1;;argv1 argv2'
    print lib_users.fmt_machine(inp)
    assert(lib_users.fmt_machine(inp)==outp)
    inp={}
    outp=''
    print lib_users.fmt_machine(inp)
    assert(lib_users.fmt_machine(inp)==outp)

def test_IOError_perm():
    if os.geteuid() == 0:
        raise SkipTest
    lib_users.PROCFSPAT="/proc/1/mem"
    # main() doesn't return anything, we only test for exceptions
    assert(lib_users.main() == None)

def test_IOError_nonexist():
    lib_users.PROCFSPAT="/DOESNOTEXIST"
    # main() doesn't return anything, we only test for exceptions
    assert(lib_users.main() == None)

def test_givenlist():
    def mock_get_deleted_libs(mapsfile):
        return(["foo"])
    lib_users.get_deleted_libs=mock_get_deleted_libs
    lib_users.PROCFSPAT="*"
    assert(lib_users.main() == None)

