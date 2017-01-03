# -*- coding: utf8 -*-
"""
Test suite for common

To be run through nose, not executed directly.
"""
import os
import sys
import locale
from lib_users_util import common
import unittest

if sys.version_info.major == 2:
    from backports import unittest_mock
    unittest_mock.install()
else:
    import unittest.mock


# Create a shorthand to prevent lines from becoming very long
MagicMock = unittest.mock.MagicMock

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
        self.showitems = False
        self.services = False
        self.ignore_pattern = {}
        self.ignore_literal = {}


class TestGetProgargs(unittest.TestCase):

    def test_progargs(self):
        """Test length of argv using string pid"""
        m = unittest.mock.mock_open(read_data="x\x00b")
        with unittest.mock.patch('__main__.open', m, create=True):
            pid = str(os.getpid())
            # Once with int, once with str
            self.assertGreater(len(common.get_progargs("%s" % pid)), 0)
            self.assertGreater(len(common.get_progargs(pid)), 0)

    def test_inaccesible_proc(self):
        """An inaccessible /proc should not break but yield an empty result"""
        self.assertEquals(common.get_progargs("this is not a pid"), None)


class TestFormatting(unittest.TestCase):
    # Input for these is { argv: ({pid, pid, ...}, {file, file, ...}), argv:
    # ... }

    def test_fmt_human(self):
        """Test function for human-readable output"""
        options = _options()
        inp = {"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
        outp = '1,2 "argv1"'
        print(common.fmt_human(inp, options))
        self.assertEquals(common.fmt_human(inp, options), outp)

        inp = {"argv1": (set(["1"]), set(["l1", "l2"]))}
        outp = '1 "argv1"'
        print(common.fmt_human(inp, options))
        self.assertEquals(common.fmt_human(inp, options), outp)

        # The space at the end of this argv should go away.
        inp = {"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
        outp = '1 "argv1 argv2"'
        print(common.fmt_human(inp, options))
        self.assertEquals(common.fmt_human(inp, options), outp)

        inp = {}
        outp = ''
        print(common.fmt_human(inp, options))
        self.assertEquals(common.fmt_human(inp, options), outp)

    def test_fmt_human_with_libs(self):
        """Test function for human-readable output"""
        inp = {"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
        outp = '1,2 "argv1" uses l1,l2'
        options = _options()
        options.showitems = True
        print(common.fmt_human(inp, options))
        self.assertEquals(common.fmt_human(inp, options), outp)

        inp = {"argv1": (set(["1"]), set(["l1"]))}
        outp = '1 "argv1" uses l1'
        print(common.fmt_human(inp, options))
        self.assertEquals(common.fmt_human(inp, options), outp)

        # The space at the end of this argv should go away.
        inp = {"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
        outp = '1 "argv1 argv2" uses l1,l2'
        print(common.fmt_human(inp, options))
        self.assertEquals(common.fmt_human(inp, options), outp)

        inp = {}
        outp = ''
        print(common.fmt_human(inp, options))
        self.assertEquals(common.fmt_human(inp, options), outp)

    def test_fmt_machine(self):
        """Test function for machine-readable output"""
        inp = {"argv1": (set(["1", "2"]), set(["l1", "l2"]))}
        outp = '1,2;l1,l2;argv1'
        print(common.fmt_machine(inp))
        self.assertEquals(common.fmt_machine(inp), outp)

        inp = {"argv1": (set(["1"]), set(["l1", "l2"]))}
        outp = '1;l1,l2;argv1'
        print(common.fmt_machine(inp))
        self.assertEquals(common.fmt_machine(inp), outp)

        # The space at the end of this argv should go away.
        inp = {"argv1 argv2 ": (set(["1"]), set(["l1", "l2"]))}
        outp = '1;l1,l2;argv1 argv2'
        print(common.fmt_machine(inp))
        self.assertEquals(common.fmt_machine(inp), outp)

        inp = {"argv1 argv2 ": (set(["1"]), set())}
        outp = '1;;argv1 argv2'
        print(common.fmt_machine(inp))
        self.assertEquals(common.fmt_machine(inp), outp)

        inp = {}
        outp = ''
        print(common.fmt_machine(inp))
        self.assertEquals(common.fmt_machine(inp), outp)


class Testsystemdintegration(unittest.TestCase):

    """Test code that integrates with/depends on systemd"""

    def setUp(self):
        """Set up golden data and save original function refs"""
        self.comm = common
        self.query = {"/usr/bin/foo": (("1", "2", "3"), ("libbar", "libbaz"))}
        self.golden = "1,2,3 belong to service.shmervice"
        self._orig_query_systemctl = self.comm.query_systemctl
        self._orig_Popen = self.comm.subprocess.Popen
        self._orig_stderr = self.comm.sys.stderr

    def tearDown(self):
        """Restore mocked out functions"""
        self.comm.query_systemctl = self._orig_query_systemctl
        self.comm.subprocess.Popen = self._orig_Popen
        self.comm.sys.stderr = self._orig_stderr

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
                return(self._encode_stdin("● sshd.service - OpenSSH Daemon"),
                       self._encode_stdin("stderr sez dat"))

            def _encode_stdin(self, value):
                if sys.version_info >= (3, 0):
                    return value.encode(sys.stdin.encoding)
                else:
                    return value

        return mock_proc()

    def _mock_Popen_broken(self, *_, **_unused):
        """Mock out subprocess.Popen, always raising OSError"""
        raise OSError("Another Dummy Reason")

    def test_get_services(self):
        """Test get_services"""
        self.comm.query_systemctl = self._mock_query_systemctl
        self.assertEquals(common.get_services(self.query), self.golden)

    def test_get_services_with_broken_systemctl(self):
        """Test get_services with broken systctl"""
        self.comm.query_systemctl = self._mock_query_systemctl_broken
        self.assertIn("Dummy Reason", common.get_services(self.query))

    def test_query_systemctl(self):
        """Test test_query_systemctl with mocked Popen"""
        self.comm.subprocess.Popen = self._mock_Popen
        ret = self.comm.query_systemctl("1")
        self.assertEquals(ret, "sshd.service")

    def test_query_systemctl_broken(self):
        """Test test_query_systemctl with mocked broken Popen"""
        self.comm.subprocess.Popen = self._mock_Popen_broken
        with self.assertRaises(OSError):
            self.comm.query_systemctl("1")

    def test_format1(self):
        """Test "classic" output format of systemctl status"""
        retval = self.comm.query_systemctl("1",
                                           "sshd.service - OpenSSH Daemon")
        self.assertEquals(retval, "sshd.service")

    def test_format2(self):
        """Test first iteration output format of systemctl status"""
        retval = self.comm.query_systemctl(
            "1", "● sshd.service - OpenSSH Daemon")
        self.assertEquals(retval, "sshd.service")

    def test_no_match(self):
        retval = self.comm.query_systemctl(
            "1", "No unit for PID 1 is loaded.\nBlah")
        self.assertEquals(retval, None)
