#!/usr/bin/env bash

# TODO: this probably needs some work

# This is needed to copy the changelog back later
original_dir="`pwd`"

# Grab some variables from the VERSION file
package=`head -n 1 VERSION`
version=`head -n 2 VERSION | tail -n 1`

# Cleanup
rm -rf /tmp/nautilussvn_build
mkdir /tmp/nautilussvn_build

# Export
svn export . /tmp/nautilussvn_build/${package}-${version}

# Zip up the original source code
cd /tmp/nautilussvn_build
tar -zcvf ${package}_${version}.orig.tar.gz ${package}-${version}
cd ${package}-${version}/

# Update the changelog (be sure to commit this afterwards)
cd packages/ubuntu/
debchange -i
cp ./debian/changelog "${original_dir}/packages/ubuntu/debian"

# Copy the Debian directory into place and build the directory
cd ../../
cp -R packages/ubuntu/debian/ .
debuild

# Let the user know he should commit
echo ""
echo "================================================================="
echo " PLEASE COMMIT THE NEW CHANGELOG"
echo "================================================================="
echo ""
