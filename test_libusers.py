"""
Test suite for lib_users

To be run through nose, not executed directly.
"""

import os
import sys
import locale
import lib_users
import unittest

from nose.plugins.skip import SkipTest

if sys.version.startswith("2"):
    from cStringIO import StringIO
else:
    from io import StringIO


# Some tests use sort() - make sure the sorting is the same regardless of
# the users environment
locale.setlocale(locale.LC_ALL, "POSIX")

# Shorthand
EMPTYSET = frozenset()

class Testlibusers(unittest.TestCase):
    """Run tests that don't need mocks"""

    def test_nonlibs(self):
        """Test detection of mappings that aren't libs"""
        pseudofile = []
        pseudofile.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /SYSV00000000 (deleted)""")
        pseudofile.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /dev/zero (deleted)""")
        pseudofile.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /dev/shm/foo (deleted)""")
        pseudofile.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /drm (deleted)""")
        pseudofile.append("""7fbb00535000-7fbb00556000 rw-s 00000000 00:0a 13493193 /[aio] (deleted)""")
        pseudofile = StringIO("\n".join(pseudofile))
        res = lib_users.get_deleted_libs(pseudofile)
        self.assertEquals(res, EMPTYSET)

    def test_libs_with_patterns(self):
        """Test detection of mappings that are libs but contain nonlib stuff"""
        pseudofile = []
        pseudofile.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /lib/SYSV00000000 (deleted)""")
        pseudofile.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /lib/dev/zero (deleted)""")
        pseudofile.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /lib/dev/shm/foo (deleted)""")
        pseudofile.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /lib/drm (deleted)""")
        pseudofile.append("""7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 /lib/[aio] (deleted)""")
        pseudofile = StringIO("\n".join(pseudofile))
        res = list(lib_users.get_deleted_libs(pseudofile))
        res.sort()
        self.assertEquals(res, ['/lib/SYSV00000000', '/lib/[aio]', '/lib/dev/shm/foo', '/lib/dev/zero', '/lib/drm'])

    def test_openvz_maps(self):
        testdata = open("testdata/openvz-maps").read()
        pseudofile = StringIO(testdata)
        res = lib_users.get_deleted_libs(pseudofile)
        expected = {'/var/tmp/portage/dev-libs/lzo-2.06/image/usr/lib64/liblzo2.so.2.0.0', 
                    '/var/tmp/portage/sys-libs/glibc-2.15-r3/image/lib64/libc-2.15.so', 
                    '/var/tmp/portage/net-misc/openvpn-2.3.1/image/usr/sbin/openvpn', 
                    '/var/tmp/portage/sys-libs/glibc-2.15-r3/image/lib64/libdl-2.15.so', 
                    '/var/tmp/portage/sys-libs/glibc-2.15-r3/image/lib64/ld-2.15.so'}
        self.assertEquals(res, expected)

    def test_drm_mm_maps(self):
        testdata = open("testdata/drm-mm-maps").read()
        pseudofile = StringIO(testdata)
        res = lib_users.get_deleted_libs(pseudofile)
        self.assertEquals(res, EMPTYSET)

    def test_findlibs(self):
        """Test detection of "classic" lib name"""
        pseudofile = StringIO("""7f02a85f1000-7f02a85f2000 rw-p 0000c000 09:01 32642 /lib64/libfindme.so (deleted)""")
        self.assertEquals(lib_users.get_deleted_libs(pseudofile), set(["/lib64/libfindme.so"]))

    def test_libplainnames(self):
        """Test detection of wrong order of fields"""
        pseudofile = StringIO("""7f02a85fc000-7f02a87fb000 ---p 0000a000 09:01 32647 (deleted) /lib64/libdontfindme.so""")
        self.assertEquals(lib_users.get_deleted_libs(pseudofile), EMPTYSET)

    def test_parennames(self):
        """Test detection of libraries with embedded special strings"""
        pseudofile = StringIO("""7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 /lib64/libdontfindmeeither_(deleted)i-2.11.2.so""")
        self.assertEquals(lib_users.get_deleted_libs(pseudofile), EMPTYSET)

    def test_parenwcontent(self):
        """Test detection of superstrings of special strings"""
        pseudofile = StringIO("""7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 /lib64/libdontfindmeeither-2.11.2.so (notdeleted)""")
        self.assertEquals(lib_users.get_deleted_libs(pseudofile), EMPTYSET)

    def test_parenwcontent2(self):
        """Test detection of substrings of special strings"""
        pseudofile = StringIO("""7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 /lib64/libdontfindmeeither-2.11.2.so (delete)""")
        self.assertEquals(lib_users.get_deleted_libs(pseudofile), EMPTYSET)

    def test_progargs_str(self):
        """Test length of argv using string pid"""
        pid = str(os.getpid())
        self.assertGreater(len(lib_users.get_progargs(pid)), 0)

    def test_progargs_int(self):
        """Test length of argv using integer pid"""
        pid = os.getpid()
        self.assertGreater(len(lib_users.get_progargs(pid)), 0)

    def test_usage(self):
        """Test usage() for Exceptions and retval"""
        self.assertEquals(lib_users.usage(), None)

# Input for these is { argv: ({pid, pid, ...}, {lib, lib, ...}), argv: ... }
    def test_fmt_human(self):
        """Test function for human-readable output"""
        inp = {"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
        outp = '1,2 "argv1"'
        print(lib_users.fmt_human(inp))
        self.assertEquals(lib_users.fmt_human(inp), outp)
        
        inp = {"argv1": (set(["1"]), set(["l1", "l2"]))}
        outp = '1 "argv1"'
        print(lib_users.fmt_human(inp))
        self.assertEquals(lib_users.fmt_human(inp), outp)

        # The space at the end of this argv should go away.
        inp = {"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
        outp = '1 "argv1 argv2"'
        print(lib_users.fmt_human(inp))
        self.assertEquals(lib_users.fmt_human(inp), outp)

        inp = {}
        outp = ''
        print(lib_users.fmt_human(inp))
        self.assertEquals(lib_users.fmt_human(inp), outp)

    def test_fmt_human_with_libs(self):
        """Test function for human-readable output"""
        inp = {"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
        outp = '1,2 "argv1" uses l1,l2'
        print(lib_users.fmt_human(inp))
        self.assertEquals(lib_users.fmt_human(inp, True), outp)
        
        inp = {"argv1": (set(["1"]), set(["l1"]))}
        outp = '1 "argv1" uses l1'
        print(lib_users.fmt_human(inp))
        self.assertEquals(lib_users.fmt_human(inp, True), outp)

        # The space at the end of this argv should go away.
        inp = {"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
        outp = '1 "argv1 argv2" uses l1,l2'
        print(lib_users.fmt_human(inp))
        self.assertEquals(lib_users.fmt_human(inp, True), outp)

        inp = {}
        outp = ''
        print(lib_users.fmt_human(inp))
        self.assertEquals(lib_users.fmt_human(inp), outp)

    def test_fmt_machine(self):
        """Test function for machine-readable output"""
        inp = {"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
        outp = '1,2;l1,l2;argv1'
        print(lib_users.fmt_machine(inp))
        self.assertEquals(lib_users.fmt_machine(inp), outp)

        inp = {"argv1": (set(["1"]), set(["l1", "l2"]))}
        outp = '1;l1,l2;argv1'
        print(lib_users.fmt_machine(inp))
        self.assertEquals(lib_users.fmt_machine(inp), outp)

        # The space at the end of this argv should go away.
        inp = {"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
        outp = '1;l1,l2;argv1 argv2'
        print(lib_users.fmt_machine(inp))
        self.assertEquals(lib_users.fmt_machine(inp), outp)

        inp = {"argv1 argv2 ": (set(["1"]), set())}
        outp = '1;;argv1 argv2'
        print(lib_users.fmt_machine(inp))
        self.assertEquals(lib_users.fmt_machine(inp), outp)

        inp = {}
        outp = ''
        print(lib_users.fmt_machine(inp))
        self.assertEquals(lib_users.fmt_machine(inp), outp)

    def test_ioerror_perm(self):
        """Test detection of i -EPERM in /proc - works only as nonroot"""
        if os.geteuid() == 0:
            raise SkipTest
        lib_users.PROCFSPAT = "/proc/1/mem"
        # main() doesn't return anything, we only test for exceptions
        self.assertEquals(lib_users.main(), None)

    def test_ioerror_nonexist(self):
        """Test handling of IOError for nonexistant /proc files"""
        lib_users.PROCFSPAT = "/DOESNOTEXIST"
        # main() doesn't return anything, we only test for exceptions
        self.assertEquals(lib_users.main(), None)

    def test_inaccesible_proc(self):
        self.assertEquals(lib_users.get_progargs("this is not a pid"), None)


class Testlibuserswithmocks(unittest.TestCase):
    """Run tests that don't need mocks"""

    def setUp(self):
        """Set up mocked-out functions and save original function refs"""
        self.l_u = lib_users

        self._orig_get_deleted_libs = self.l_u.get_deleted_libs
        self._orig_get_progargs = self.l_u.get_progargs

        self.l_u.get_deleted_libs = self._mock_get_deleted_libs
        self.l_u.get_progargs = self._mock_get_progargs

    def teardown(self):
        """Restore mocked out functions"""
        self.l_u.get_deleted_libs = self._orig_get_deleted_libs
        self.l_u.get_progargs = self._orig_get_progargs

    def _mock_get_deleted_libs(self, _):
        """Mock out get_deleted_files, always returns set(["foo"])"""
        return(set(["foo"]))

    def _mock_get_progargs(self, _):
        """
            Mock out progargs, always returns
            "/usr/bin/python4 spam.py --eggs --ham jam"
        """
        return("/usr/bin/python4 spam.py --eggs --ham jam")

    def test_actual(self):
        """Test main() in machine mode"""
        self.assertEquals(self.l_u.main(machine_mode=True), None)

    def test_actual2(self):
        """Test main() in human mode"""
        self.assertEquals(self.l_u.main(machine_mode=False), None)

    def test_givenlist(self):
        """Test main() in default mode"""
        self.assertEquals(self.l_u.main(), None)
    
    def test_givenlist(self):
        """Test main() in default mode"""
        self.assertEquals(self.l_u.main(), None)
    
