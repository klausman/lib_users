"""
Test suite for lib_users

To be run through nose, not executed directly.
"""
# -*- coding: utf8 -*-
import sys
import locale
import lib_users
import unittest

if sys.version.startswith("2"):
    from cStringIO import StringIO
else:
    from io import StringIO


# Some tests use sort() - make sure the sorting is the same regardless of
# the users environment
locale.setlocale(locale.LC_ALL, "POSIX")

# Shorthand
EMPTYSET = frozenset()


class _mock_stdx(object):
    """A stand-in for sys.stdout/stderr"""

    def write(self, *_, **_unused):
        """Discard everything"""


class _options(object):
    """Mock options object that mimicks the bare necessities"""

    def __init__(self):
        self.machine_readable = False
        self.showlibs = False
        self.services = False
        self.ignore_pattern = {}
        self.ignore_literal = {}


class Testlibusers(unittest.TestCase):
    """Run tests that don't need mocks"""

    def setUp(self):
        self.l_u = lib_users
        self._orig_stderr = self.l_u.sys.stderr

        self.l_u.sys.stderr = _mock_stdx()

    def tearDown(self):
        self.l_u.sys.stderr = self._orig_stderr

    def test_nonlibs(self):
        """Test detection of mappings that aren't libs"""
        pseudofile = []
        pseudofile.append(
            "7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 "
            "/SYSV00000000 (deleted)")
        pseudofile.append(
            "7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 "
            "/dev/zero (deleted)")
        pseudofile.append(
            "7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 "
            "/dev/shm/foo (deleted)")
        pseudofile.append(
            "7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 "
            "/drm (deleted)")
        pseudofile.append(
            "7fbb00535000-7fbb00556000 rw-s 00000000 00:0a 13493193 "
            "/[aio] (deleted)")
        pseudofile.append(
            "7fbb00535000-7fbb00556000 rw-s 00000000 00:0a 13493193 "
            "/i915 (deleted)")
        pseudofile = StringIO("\n".join(pseudofile))
        res = lib_users.get_deleted_libs(pseudofile)
        self.assertEquals(res, EMPTYSET)

    def test_libs_with_patterns(self):
        """Test detection of mappings that are libs but contain nonlib stuff"""
        pseudofile = []
        pseudofile.append(
            "7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 "
            "/lib/SYSV00000000 (deleted)")
        pseudofile.append(
            "7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 "
            "/lib/dev/zero (deleted)")
        pseudofile.append(
            "7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 "
            "/lib/dev/shm/foo (deleted)")
        pseudofile.append(
            "7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 "
            "/lib/drm (deleted)")
        pseudofile.append(
            "7f02a4202000-7f02a6202000 rw-s 00000000 00:04 425984 "
            "/lib/[aio] (deleted)")
        pseudofile.append(
            "7fbb00535000-7fbb00556000 rw-s 00000000 00:0a 13493193 "
            "/usr/lib/i915 (deleted)")
        pseudofile = StringIO("\n".join(pseudofile))
        res = list(lib_users.get_deleted_libs(pseudofile))
        res.sort()
        self.assertEquals(
            res, ['/lib/SYSV00000000', '/lib/[aio]', '/lib/dev/shm/foo',
                  '/lib/dev/zero', '/lib/drm', '/usr/lib/i915'])

    def test_openvz_maps(self):
        """Test that OpenVZ maps are handled correctly"""
        testdata = open("testdata/openvz-maps").read()
        pseudofile = StringIO(testdata)
        res = lib_users.get_deleted_libs(pseudofile)
        expected = {
            '/v/t/p/dev-libs/lzo-2.06/image/usr/lib64/liblzo2.so.2.0.0',
            '/v/t/p/sys-libs/glibc-2.15-r3/image/lib64/libc-2.15.so',
            '/v/t/p/net-misc/openvpn-2.3.1/image/usr/sbin/openvpn',
            '/v/t/p/sys-libs/glibc-2.15-r3/image/lib64/libdl-2.15.so',
            '/v/t/p/sys-libs/glibc-2.15-r3/image/lib64/ld-2.15.so'
        }
        self.assertEquals(res, expected)

    def test_drm_mm_maps(self):
        """Test that deleted DRM maps yield no results"""
        testdata = open("testdata/drm-mm-maps").read()
        pseudofile = StringIO(testdata)
        res = lib_users.get_deleted_libs(pseudofile)
        self.assertEquals(res, EMPTYSET)

    def test_findlibs(self):
        """Test detection of "classic" lib name"""
        pseudofile = StringIO(
            "7f02a85f1000-7f02a85f2000 rw-p 0000c000 09:01 32642 "
            "/lib64/libfindme.so (deleted)")
        self.assertEquals(
            lib_users.get_deleted_libs(pseudofile),
            set(["/lib64/libfindme.so"]))

    def test_libplainnames(self):
        """Test detection of wrong order of fields"""
        pseudofile = StringIO(
            "7f02a85fc000-7f02a87fb000 ---p 0000a000 09:01 32647 (deleted) "
            "/lib64/libdontfindme.so")
        self.assertEquals(lib_users.get_deleted_libs(pseudofile), EMPTYSET)

    def test_parennames(self):
        """Test detection of libraries with embedded special strings"""
        pseudofile = StringIO(
            "7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 "
            "/lib64/libdontfindmeeither_(deleted)i-2.11.2.so")
        self.assertEquals(lib_users.get_deleted_libs(pseudofile), EMPTYSET)

    def test_parenwcontent(self):
        """Test detection of superstrings of special strings"""
        pseudofile = StringIO(
            "7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 "
            "/lib64/libdontfindmeeither-2.11.2.so (notdeleted)")
        self.assertEquals(lib_users.get_deleted_libs(pseudofile), EMPTYSET)

    def test_parenwcontent2(self):
        """Test detection of substrings of special strings"""
        pseudofile = StringIO(
            "7f02a87fc000-7f02a87fd000 rw-p 0000a000 09:01 32647 "
            "/lib64/libdontfindmeeither-2.11.2.so (delete)")
        self.assertEquals(lib_users.get_deleted_libs(pseudofile), EMPTYSET)


class Testlibuserswithmocks(unittest.TestCase):

    """Run tests that need mocks"""

    def setUp(self):
        """Set up mocked-out functions and save original function refs"""

        self.options = _options()

        self.l_u = lib_users

        self._orig_get_deleted_libs = self.l_u.get_deleted_libs
        self._orig_get_progargs = self.l_u.common.get_progargs
        self._orig_stderr = self.l_u.sys.stderr

        self.l_u.get_deleted_libs = self._mock_get_deleted_libs
        self.l_u.common.get_progargs = self._mock_get_progargs
        self.l_u.sys.stderr = _mock_stdx()

    def tearDown(self):
        """Restore mocked out functions"""
        self.l_u.get_deleted_libs = self._orig_get_deleted_libs
        self.l_u.get_progargs = self._orig_get_progargs
        self.l_u.sys.stderr = self._orig_stderr

    def _mock_get_deleted_libs(*unused_args):
        """Mock out get_deleted_files, always returns set(["foo"])"""
        return set(["foo"])

    def _mock_get_progargs(*unused_args):
        """
            Mock out progargs, always returns
            "/usr/bin/python4 spam.py --eggs --ham jam"
        """
        return "/usr/bin/python4 spam.py --eggs --ham jam"

    def test_actual(self):
        """Test main() in human mode"""
        self.assertEquals(self.l_u.main([]), None)

    def test_actual2(self):
        """Test main() in machine mode"""
        self.assertEquals(self.l_u.main(["-m"]), None)

    def test_givenlist(self):
        """Test main() in default mode"""
        self.assertEquals(self.l_u.main([]), None)
