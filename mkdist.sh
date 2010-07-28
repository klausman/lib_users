#!/bin/bash

function die() {
    echo -e  "$@" >&2
    exit -1
}


FVERS=$(./lib_users.py --help|head -n1|sed -r -e 's/.*version ([^ ]*).*/\1/g') || die "Could not determine version"
PNAME="lib_users-$FVERS"

mkdir "$PNAME" || die "mkdir failed"
cp -r COPYING lib_users.py README test_libusers.py TODO "lib_users-$FVERS/" || die "cp failed"
find "$PNAME" -name '.svn' -print0 |xargs -0 rm -r 2>/dev/null
tar czf "$PNAME".tar.gz "$PNAME" || die "tar failed"
rm -rf "$PNAME" || die "rm failed"
mv "$PNAME".tar.gz dists/
