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

class TestGetProgargs(unittest.TestCase):

    def test_progargs(self):
        """Test length of argv using string pid"""
        m = unittest.mock.mock_open(read_data="x\x00b")
        with unittest.mock.patch('__main__.open', m):
            pid = str(os.getpid())
            # Once with int, once with str
            self.assertGreater(len(fd_users.get_progargs("%s" % pid)), 0)
            self.assertGreater(len(fd_users.get_progargs(pid)), 0)

    def test_inaccesible_proc(self):
        """Test that an inaccessible /proc does not break and yields an empty result"""
        self.assertEquals(fd_users.get_progargs("this is not a pid"), None)


  

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







class TestFormatting(unittest.TestCase):
# Input for these is { argv: ({pid, pid, ...}, {file, file, ...}), argv: ... }
    def test_fmt_human(self):
        """Test function for human-readable output"""
        options = _options()
        inp = {"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
        outp = '1,2 "argv1"'
        print(fd_users.fmt_human(inp, options))
        self.assertEquals(fd_users.fmt_human(inp, options), outp)

        inp = {"argv1": (set(["1"]), set(["l1", "l2"]))}
        outp = '1 "argv1"'
        print(fd_users.fmt_human(inp, options))
        self.assertEquals(fd_users.fmt_human(inp, options), outp)

        # The space at the end of this argv should go away.
        inp = {"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
        outp = '1 "argv1 argv2"'
        print(fd_users.fmt_human(inp, options))
        self.assertEquals(fd_users.fmt_human(inp, options), outp)

        inp = {}
        outp = ''
        print(fd_users.fmt_human(inp, options))
        self.assertEquals(fd_users.fmt_human(inp, options), outp)

    def test_fmt_human_with_libs(self):
        """Test function for human-readable output"""
        inp = {"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
        outp = '1,2 "argv1" uses l1,l2'
        options = _options()
        options.showfiles = True
        print(fd_users.fmt_human(inp, options))
        self.assertEquals(fd_users.fmt_human(inp, options), outp)

        inp = {"argv1": (set(["1"]), set(["l1"]))}
        outp = '1 "argv1" uses l1'
        print(fd_users.fmt_human(inp, options))
        self.assertEquals(fd_users.fmt_human(inp, options), outp)

        # The space at the end of this argv should go away.
        inp = {"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
        outp = '1 "argv1 argv2" uses l1,l2'
        print(fd_users.fmt_human(inp, options))
        self.assertEquals(fd_users.fmt_human(inp, options), outp)

        inp = {}
        outp = ''
        print(fd_users.fmt_human(inp, options))
        self.assertEquals(fd_users.fmt_human(inp, options), outp)

    def test_fmt_machine(self):
        """Test function for machine-readable output"""
        inp = {"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
        outp = '1,2;l1,l2;argv1'
        print(fd_users.fmt_machine(inp))
        self.assertEquals(fd_users.fmt_machine(inp), outp)

        inp = {"argv1": (set(["1"]), set(["l1", "l2"]))}
        outp = '1;l1,l2;argv1'
        print(fd_users.fmt_machine(inp))
        self.assertEquals(fd_users.fmt_machine(inp), outp)

        # The space at the end of this argv should go away.
        inp = {"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
        outp = '1;l1,l2;argv1 argv2'
        print(fd_users.fmt_machine(inp))
        self.assertEquals(fd_users.fmt_machine(inp), outp)

        inp = {"argv1 argv2 ": (set(["1"]), set())}
        outp = '1;;argv1 argv2'
        print(fd_users.fmt_machine(inp))
        self.assertEquals(fd_users.fmt_machine(inp), outp)

        inp = {}
        outp = ''
        print(fd_users.fmt_machine(inp))
        self.assertEquals(fd_users.fmt_machine(inp), outp)

    def test_ioerror_perm(self):
        """Test detection of -EPERM in /proc - works only as nonroot"""
        if os.geteuid() == 0:
            raise SkipTest
        fd_users.PROCFSPAT = "/proc/1/mem"
        # main() doesn't return anything, we only test for exceptions
        self.assertEquals(fd_users.main([]), None)

    def test_ioerror_nonexist(self):
        """Test handling of IOError for nonexistant /proc files"""
        fd_users.PROCFSPAT = "/DOESNOTEXIST"
        # main() doesn't return anything, we only test for exceptions
        self.assertEquals(fd_users.main([]), None)

class Testlibuserswithmocks(unittest.TestCase):

    """Run tests that need mocks"""

    def setUp(self):
        """Set up mocked-out functions and save original function refs"""

        self.options = _options()

        self.f_u = fd_users

        self._orig_get_deleted_files = self.f_u.get_deleted_files
        self._orig_get_progargs = self.f_u.get_progargs
        self._orig_stderr_write = self.f_u.sys.stderr.write

        self.f_u.get_deleted_files = self._mock_get_deleted_files
        self.f_u.get_progargs = self._mock_get_progargs
        self.f_u.sys.stderr.write = self._mock_sys_stderr_write

    def tearDown(self):
        """Restore mocked out functions"""
        self.f_u.get_deleted_files = self._orig_get_deleted_files
        self.f_u.get_progargs = self._orig_get_progargs
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


class Testsystemdintegration(unittest.TestCase):

    """Test code that integrates with/depends on systemd"""

    def setUp(self):
        """Set up golden data and save original function refs"""
        self.f_u = fd_users
        self.query = {"/usr/bin/foo": (("1", "2", "3"), ("libbar", "libbaz"))}
        self.golden = "1,2,3 belong to service.shmervice"
        self._orig_query_systemctl = self.f_u.query_systemctl
        self._orig_Popen = self.f_u.subprocess.Popen
        self._orig_stderr_write = self.f_u.sys.stderr.write

    def tearDown(self):
        """Restore mocked out functions"""
        self.f_u.query_systemctl = self._orig_query_systemctl
        self.f_u.subprocess.Popen = self._orig_Popen
        self.f_u.sys.stderr.write = self._orig_stderr_write

    def _mock_query_systemctl(self, _):
        """Mock out query_systemctl, always return "service.shmervice" """
        return "service.shmervice"

    def _mock_query_systemctl_broken(self, _):
        """Mock out query_systemctl, always raise OSError"""
        print("Raising OSError")
        raise OSError("Dummy Reason")

    def _mock_Popen(self, *_, **_unused):
        """Mock out subprocess.Popen"""
        class mock_proc(object):
            """A mock in a mock of a sock."""

            def __init__(self):
                pass

            def communicate(self):
                """...with a lock"""
                return("● sshd.service - OpenSSH Daemon", "stderr sez dat")

        return mock_proc()

    def _mock_Popen_broken(self, *_, **_unused):
        """Mock out subprocess.Popen, always raising OSError"""
        raise OSError("Another Dummy Reason")

    def _mock_sys_stderr_write(*_, **_unused):
        """Mock write() that swallows all args"""

    def test_get_services(self):
        """Test get_services"""
        self.f_u.query_systemctl = self._mock_query_systemctl
        self.assertEquals(fd_users.get_services(self.query), self.golden)

    def test_get_services_with_broken_systemctl(self):
        """Test get_services with broken systctl"""
        self.f_u.query_systemctl = self._mock_query_systemctl_broken
        self.assertIn("Dummy Reason", fd_users.get_services(self.query))

    def test_query_systemctl(self):
        """Test test_query_systemctl with mocked Popen"""
        self.f_u.subprocess.Popen = self._mock_Popen
        ret = self.f_u.query_systemctl("1")
        self.assertEquals(ret, "sshd.service")

    def test_query_systemctl_broken(self):
        """Test test_query_systemctl with mocked broken Popen"""
        self.f_u.subprocess.Popen = self._mock_Popen_broken
        with self.assertRaises(OSError):
            self.f_u.query_systemctl("1")

    def test_format1(self):
        """Test "classic" output format of systemctl status"""
        retval = self.f_u.query_systemctl("1", "sshd.service - OpenSSH Daemon")
        self.assertEquals(retval, "sshd.service")

    def test_format2(self):
        """Test first iteration output format of systemctl status"""
        retval = self.f_u.query_systemctl(
            "1", "● sshd.service - OpenSSH Daemon")
        self.assertEquals(retval, "sshd.service")

    def test_no_match(self):
        retval = self.f_u.query_systemctl(
            "1", "No unit for PID 1 is loaded.\nBlah")
        self.assertEquals(retval, None)
