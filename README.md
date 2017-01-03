# Lib_users

Lib_users is a Python script that goes through `/proc/*/maps` and finds all
cases of libraries being mapped but marked as deleted. It then extracts the
programs name and arguments from `/proc/<pid>/cmdline`. This information is
presented to the user so that those processes can be restarted.

The reason to do this is that after an update, you might end up with processes
that run for a long time and still use old libraries. In some cases this might
be a security problem, as the library may be vulnerable. The script displays
all the distinct argument lists of processes that have deleted files mapped.
In essence, you get a list of processes and their PIDs. The reason why not
just the first element of the argument list is presented is that for scripts,
this will always be the interpreter name (i.e. `perl`, `python` etc.) which is
not useful by itself.

The script cleans up the list from `/proc/<pid>/maps` to not display false
positives - some programs have a pseudo file called `/SYSxxxx` mapped which
obviously is not a library that was updated.

As of v0.10, there is a companion to `lib_users`, called `fd_users`. It
basically does the same, but for open FDs (`/proc/PID/fd`) that are marked as
deleted. The intended use is to spot daemons that have had their log files
deleted (or rotated and compressed), but not told to reopen the file.

## Output formats

Lib_users supports two output formats/modes, human- and machine-readable:

human-readable:

```
16341 "supervising syslog-ng"
16342 "/usr/sbin/syslog-ng"
27550 "/usr/sbin/exim -bd -q15m"
12451,16244,16249,16252,16253,16254,26931,28912,29631,8810,894 "/usr/sbin/apache2 -D DEFAULT_VHOST -D INFO -D LANGUAGE -D DAV -D SVN -D MAILMAN -D PHP5 -D USERDIR -D SVN_AUTHZ -D SUEXEC -D SSL -D SSL_DEFAULT_VHOST -D AUTH_DIGEST -D PERL -d /usr/lib64/apache2 -f /etc/apache2/httpd.conf -k start"
```

Here, the first column is a comma-separated list of PIDs that share the same
command line. The second column is the command line in quotation marks. If the
-s command line option is used, there will also be information about the names
of the deleted files in use.

machine-readable:

```
16341;/lib64/libpcre.so.0.0.1;supervising syslog-ng
16342;/lib64/libpcre.so.0.0.1;/usr/sbin/syslog-ng
27550;/lib64/libpcre.so.0.0.1,/usr/sbin/exim;/usr/sbin/exim -bd -q15m
12451,16244,16249,16252,16253,16254,26931,28912,29631,8810,894;/lib64/libpcre.so.0.0.1;/usr/sbin/apache2 -D DEFAULT_VHOST -D INFO -D LANGUAGE -D DAV -D SVN -D MAILMAN -D PHP5 -D USERDIR -D SVN_AUTHZ -D SUEXEC -D SSL -D SSL_DEFAULT_VHOST -D AUTH_DIGEST -D PERL -d /usr/lib64/apache2 -f /etc/apache2/httpd.conf -k start
```

With the -m command line parameter changes to this form:
`<list of PIDs>;<list of deleted mapped files>;<command line>`

The lists are made up of comma-separated values. There are no provisions taken
for the case of one of the libraries contain a ",". The command line is also
not altered in any way. This may be fixed in a future version.

## Dependencies

The script requires Python 2.7 or higher and should work with Python 3. It only
uses modules from Pythons standard library, so apart from a Python
installation, there are no external dependencies.

If you want to run the test suite easily, install the Nose Python testing
framework. This is not needed for day-to-day operations. Running the tests with
Python 2.7 also requires the backported mock submodule of unittest
(https://github.com/jaraco/backports.unittest_mock)

## Limitations

The program quite probably only works on Linux (or, at least, only on systems
that have the same maps file structure as a Linux system).

If the script is not run as root, it can not display all processes on the
system that use deleted libs. In the spirit of graceful degradation, it will
then only display the information for processes it has access to. Usually this
is the list of processes owned by the user that runs lib_users. It will also
output a warning to stderr that it could not read all map files.

The `-S` command line switch relies on systemdctl and its output. Therefore, it
may break if the command is renamed or its output changes significantly. Note
that the output it produces is advisory and entirely reliant on systemd.

## False positives

Some programs open temporary files and immediately delete them. This is done
so they don't leave those files behind after a crash. As a consequence,
lib_users may report these programs. A notable example are programs that use
liborc, the Oil Runtime Compiler. Here's an example, the media player
quodlibet:

```
$ lib_users 
2753 "/usr/bin/python2.7 /usr/bin/quodlibet"
$ grep deleted /proc/2753/maps 
7f409dd0b000-7f409dd1b000 rw-s 00000000 08:01 1179661 /tmp/orcexec.sqa9cE (deleted)
```

The file `/tmp/orcexec.sqa9cE` is output from the aforementioned compiler. These
processes/files can be safely ignored. In fact, restarting quodlibet will just
result in a different liborc tempfile show up as deleted.

Using the -s command line option will show you which deleted files are in use,
so you decide whether the listed process is a false positive.

Starting with lib_users 0.8, the `-i` and `-I` command line options can be used to
supply additional to-be-ignored patterns and static strings.

## License

This program is released under the GPL-2, which is included in distributions
of this script as the file COPYING. If you want to use it for something that
is incompatible with the GPL-2, feel free to contact me; I'm sure we can work
something out.

## Contact & Contributions

If you want to contact me, my email address is `klausman-lu@schwarzvogel.de.`
Patches and bug reports (or feature requests, even) are of course welcome.
