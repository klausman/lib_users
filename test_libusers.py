#!/usr/bin/python -tt

"""
Test suite for lib_users
"""

import sys
import os

import lib_users

from cStringIO import StringIO

def test_nonlibs():
    F=StringIO("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /SYSV00000000 (deleted)""")
    assert(lib_users.get_deleted_libs(F) == [])

def test_findlibs():
    F=StringIO("""7f02a85f1000-7f02a85f2000 rw-p 0000c000 09:01 32642 /lib64/libfindme.so (deleted)""")
    assert(lib_users.get_deleted_libs(F) == ["/lib64/libfindme.so"])

def test_libplainnames():
    F=StringIO("""7f02a85fc000-7f02a87fb000 ---p 0000a000 09:01 32647 (deleted) /lib64/libdontfindme.so""")
    assert(lib_users.get_deleted_libs(F) == [])

def test_parennames():
    F=StringIO("""7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 /lib64/libdontfindmeeither_(deleted)i-2.11.2.so""")
    assert(lib_users.get_deleted_libs(F) == [])

def test_parenwcontent():
    F=StringIO("""7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 /lib64/libdontfindmeeither-2.11.2.so (notdeleted)""")
    assert(lib_users.get_deleted_libs(F) == [])

def test_parenwcontent2():
    F=StringIO("""7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 /lib64/libdontfindmeeither-2.11.2.so (delete)""")
    assert(lib_users.get_deleted_libs(F) == [])

def test_progargs_str():
    PID=str(os.getpid())
    assert(len(lib_users.get_progargs(PID)) > 0)

def test_progargs_int():
    PID=os.getpid()
    assert(len(lib_users.get_progargs(PID)) > 0)

def test_format_pal():
    ret=lib_users.format_pal(["ls", "foo"], 666, ["libdel", "librm"])
    assert(ret == "(666) \"ls foo\" uses: libdel (+1 more)")

def test_format_pal_explterse():
    ret=lib_users.format_pal(["ls", "foo"], 666, ["libdel", "librm"], verbose=False)
    assert(ret == "(666) \"ls foo\" uses: libdel (+1 more)")

def test_format_pal_verbose():
    ret=lib_users.format_pal(["ls", "foo"], 666, ["libdel", "librm"], verbose=True)
    assert(ret == "(666) \"ls foo\" uses: libdel librm")

def test_format_pal_strpid():
    ret=lib_users.format_pal(["ls", "foo"], "666", ["libdel", "librm"], verbose=True)
    assert(ret == "(666) \"ls foo\" uses: libdel librm")

def test_format_pal_emptyll():
    ret=lib_users.format_pal(["ls", "foo"], "666", [], verbose=True)
    assert(ret == "(666) \"ls foo\" uses: ")

def test_format_pal_noargs():
    ret=lib_users.format_pal(["ls"], 666, ["libdel", "librm"])
    assert(ret == "(666) \"ls\" uses: libdel (+1 more)")

def test_format_pal_emptyargv():
    ret=lib_users.format_pal([], 666, ["libdel", "librm"])
    assert(ret == "(666) \"\" uses: libdel (+1 more)")

def test_usage():
    assert(lib_users.usage() == None)

def test_IOError():
    class FileMock:
        def readlines(self):
            raise IOError
    F=FileMock()
    assert(lib_users.get_deleted_libs(F) == [])
