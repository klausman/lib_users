"""
Test suite for fd_users

To be run through nose, not executed directly.
"""
# -*- coding: utf8 -*-
import os
import sys
import locale
import fd_users
import unittest
import unittest.mock

MagicMock = unittest.mock.MagicMock

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


class _options(object):
    """Mock options object that mimicks the bare necessities"""

    def __init__(self):
        self.machine_readable = False
        self.showfiles = False
        self.services = False
        self.ignore_pattern = {}
        self.ignore_literal = {}


class TestGetDeletedFiles(unittest.TestCase):

    def setUp(self):
        """Set up mocked-out functions and save original function refs"""

        self.options = _options()

        self.f_u = fd_users
        self._orig_glob_glob = self.f_u.glob.glob
        self._orig_os_readlink = self.f_u.os.readlink

    def tearDown(self):
        """Restore mocked out functions"""
        self.f_u.glob.glob = self._orig_glob_glob
        self.f_u.os.readlink = self._orig_os_readlink

    def testSimpleCase(self):
        self.f_u.glob.glob = MagicMock(return_value=["/nonexistant/1/fd/1"])
        self.f_u.os.readlink = MagicMock(return_value="/some/other/file")
        res = self.f_u.get_deleted_files("/nonexistant/1/fd", [], [])

        self.assertEqual(res, [])
        self.f_u.glob.glob.assert_called_once_with("/nonexistant/1/fd/*")
        self.f_u.os.readlink.assert_called_once_with("/nonexistant/1/fd/1")

    def testOneDeletedFile(self):
        self.f_u.glob.glob = MagicMock(return_value=["/nonexistant/1/fd/1"])
        self.f_u.os.readlink = MagicMock(
            return_value="/some/other/file (deleted)")
        res = self.f_u.get_deleted_files("/nonexistant/1/fd", [], [])

        self.assertEqual(res, ["/some/other/file"])
        self.f_u.glob.glob.assert_called_once_with("/nonexistant/1/fd/*")
        self.f_u.os.readlink.assert_called_once_with("/nonexistant/1/fd/1")

    def testMixedFileStates(self):
        fdlist = ["/nonexistant/1/fd/1", "/nonexistant/1/fd/2"]
        filelist = ["/some/other/file (deleted)", "/some/other/file2"]
        self.f_u.glob.glob = MagicMock(return_value=fdlist)
        self.f_u.os.readlink = MagicMock(
            return_value="/some/other/file (deleted)")
        self.f_u.os.readlink.side_effect = ["/some/other/file (deleted)",
                                            "/some/other/file2"]

        res = self.f_u.get_deleted_files("/nonexistant/1/fd", [], [])
        self.assertEqual(res, ["/some/other/file"])
        self.f_u.glob.glob.assert_called_once_with("/nonexistant/1/fd/*")
        self.f_u.os.readlink.assert_has_calls(
            unittest.mock.call(x) for x in fdlist)

    def testMixedFileStatesWithLiteral(self):
        fdlist = ["/nonexistant/1/fd/1", "/nonexistant/1/fd/2"]
        filelist = ["/some/other/file (deleted)", "/some/other/file2"]
        self.f_u.glob.glob = MagicMock(return_value=fdlist)
        self.f_u.os.readlink = MagicMock(
            return_value="/some/other/file (deleted)")
        self.f_u.os.readlink.side_effect = ["/some/other/file (deleted)",
                                            "/some/other/file2"]

        res = self.f_u.get_deleted_files("/nonexistant/1/fd", [],
                                         ["/some/other/file"])
        self.assertEqual(res, [])
        self.f_u.glob.glob.assert_called_once_with("/nonexistant/1/fd/*")
        self.f_u.os.readlink.assert_has_calls(
            unittest.mock.call(x) for x in fdlist)

    def testMixedFileStatesWithLiteralNomatch(self):
        fdlist = ["/nonexistant/1/fd/1", "/nonexistant/1/fd/2"]
        filelist = ["/some/other/file (deleted)", "/some/other/file2"]
        self.f_u.glob.glob = MagicMock(return_value=fdlist)
        self.f_u.os.readlink = MagicMock(
            return_value="/some/other/file (deleted)")
        self.f_u.os.readlink.side_effect = ["/some/other/file (deleted)",
                                            "/some/other/file2"]

        res = self.f_u.get_deleted_files("/nonexistant/1/fd", [],
                                         ["/literal/doesnt/match"])
        self.assertEqual(res, ["/some/other/file"])
        self.f_u.glob.glob.assert_called_once_with("/nonexistant/1/fd/*")
        self.f_u.os.readlink.assert_has_calls(
            unittest.mock.call(x) for x in fdlist)

    def testMixedFileStatesWithPattern(self):
        fdlist = ["/nonexistant/1/fd/1", "/nonexistant/1/fd/2"]
        filelist = ["/some/other/file (deleted)", "/some/other/file2"]
        self.f_u.glob.glob = MagicMock(return_value=fdlist)
        self.f_u.os.readlink = MagicMock(
            return_value="/some/other/file (deleted)")
        self.f_u.os.readlink.side_effect = ["/some/other/file (deleted)",
                                            "/some/other/file2"]

        res = self.f_u.get_deleted_files("/nonexistant/1/fd",
                                         ["/some/other/fil*"], [])
        self.assertEqual(res, [])
        self.f_u.glob.glob.assert_called_once_with("/nonexistant/1/fd/*")
        self.f_u.os.readlink.assert_has_calls(
            unittest.mock.call(x) for x in fdlist)

    def testMixedFileStatesWithPatternNomatch(self):
        fdlist = ["/nonexistant/1/fd/1", "/nonexistant/1/fd/2"]
        filelist = ["/some/other/file (deleted)", "/some/other/file2"]
        self.f_u.glob.glob = MagicMock(return_value=fdlist)
        self.f_u.os.readlink = MagicMock(
            return_value="/some/other/file (deleted)")
        self.f_u.os.readlink.side_effect = ["/some/other/file (deleted)",
                                            "/some/other/file2"]

        res = self.f_u.get_deleted_files("/nonexistant/1/fd",
                                         ["/pattern/doesnt/match*"], [])
        self.assertEqual(res, ["/some/other/file"])
        self.f_u.glob.glob.assert_called_once_with("/nonexistant/1/fd/*")
        self.f_u.os.readlink.assert_has_calls(
            unittest.mock.call(x) for x in fdlist)


class Testlibuserswithmocks(unittest.TestCase):

    """Run tests that need mocks"""

    def setUp(self):
        """Set up mocked-out functions and save original function refs"""

        self.options = _options()

        self.f_u = fd_users

        self._orig_get_deleted_files = self.f_u.get_deleted_files
        self._orig_get_progargs = self.f_u.common.get_progargs
        self._orig_stderr_write = self.f_u.sys.stderr.write

        self.f_u.get_deleted_files = self._mock_get_deleted_files
        self.f_u.common.get_progargs = self._mock_get_progargs
        self.f_u.sys.stderr.write = self._mock_sys_stderr_write

    def tearDown(self):
        """Restore mocked out functions"""
        self.f_u.get_deleted_files = self._orig_get_deleted_files
        self.f_u.common.get_progargs = self._orig_get_progargs
        self.f_u.sys.stderr.write = self._orig_stderr_write

    def _mock_get_deleted_files(*unused_args):
        """Mock out get_deleted_files, always returns set(["foo"])"""
        return set(["foo"])

    def _mock_get_progargs(*unused_args):
        """
            Mock out progargs, always returns
            "/usr/bin/python4 spam.py --eggs --ham jam"
        """
        return "/usr/bin/python4 spam.py --eggs --ham jam"

    def _mock_sys_stderr_write(*_, **_unused):
        """Mock write() that swallows all args"""

    def test_actual(self):
        """Test main() in human mode"""
        self.assertEquals(self.f_u.main([]), None)

    def test_actual2(self):
        """Test main() in machine mode"""
        self.assertEquals(self.f_u.main(["-m"]), None)

    def test_givenlist(self):
        """Test main() in default mode"""
        self.assertEquals(self.f_u.main([]), None)
