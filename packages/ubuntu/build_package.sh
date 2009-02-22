#!/usr/bin/env bash

# FIXME: this is obviously just an example of the procedure, still need to actually
# write it properly (get the version number from somewhere).

package=`head -n 1 VERSION`
version=`head -n 2 VERSION | tail -n 1`
rm -rf /tmp/nautilussvn_build
mkdir /tmp/nautilussvn_build
svn export . /tmp/nautilussvn_build/${package}-${version}
cd /tmp/nautilussvn_build
tar -zcvf ${package}_${version}.orig.tar.gz ${package}-${version}
cd ${package}-${version}/
cd packages/ubuntu/
debchange -i
cd ../../
cp -R packages/ubuntu/debian/ .
debuild
