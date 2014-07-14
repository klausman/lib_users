#!/bin/bash

function die() {
    echo -e  "$@" >&2
    exit -1
}

DISTDIR="dists/"
FVERS=$(./lib_users.py --version 2>&1|head -n1|awk '{print $2}'||die "version?")
PNAME="lib_users-$FVERS"

[ -d $DISTDIR ] || mkdir $DISTDIR || die "mkdir failed"

mkdir "$PNAME" || die "mkdir failed"
cp -r COPYING testdata lib_users.py README test_libusers.py TODO "lib_users-$FVERS/" || die "cp failed"
find "$PNAME" -name '.svn' -print0 |xargs -0 rm -r 2>/dev/null
tar czf "$PNAME".tar.gz "$PNAME" || die "tar failed"
rm -rf "$PNAME" || die "rm failed"
mv "$PNAME".tar.gz $DISTDIR
