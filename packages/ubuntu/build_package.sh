#!/usr/bin/env bash

# TODO: this is obviously just an example of the procedure, still need to actually
# write it properly.

svn export /home/bruce/Development/projects/nautilussvn/trunk nautilussvn-0.12
tar -zcvf nautilussvn_0.12.orig.tar.gz nautilussvn-0.12
cd nautilussvn-0.12/
cd packages/ubuntu/
debchange -i
cd ../../
cp -R packages/ubuntu/debian/ .
debuild
