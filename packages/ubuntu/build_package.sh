#!/usr/bin/env bash

# FIXME: this is obviously just an example of the procedure, still need to actually
# write it properly (get the version number from somewhere).

rm -rf /tmp/nautilussvn_build
mkdir /tmp/nautilussvn_build
svn export . /tmp/nautilussvn_build/nautilussvn-0.12
cd /tmp/nautilussvn_build
tar -zcvf nautilussvn_0.12.orig.tar.gz nautilussvn-0.12
cd nautilussvn-0.12/
cd packages/ubuntu/
debchange -i
cd ../../
cp -R packages/ubuntu/debian/ .
debuild
