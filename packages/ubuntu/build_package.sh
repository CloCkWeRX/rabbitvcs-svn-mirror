#!/usr/bin/env bash

# TODO:
# . make the script less stateful -- use () and/or absolute paths
# . give the script a proper usage() function
# . some of the double-quotes below may not be necessary

# SOURCEDIR is needed to copy the changelog back later
SOURCEDIR="`pwd`"
if [ ! -d ${SOURCEDIR}/packages ]; then
    echo "ERROR:"
    echo "   ./packages not found."
    echo "   $0 must be run from the top level of a nautilussvn "
    echo "   working copy."
    exit 1
fi

# Grab some variables from the VERSION file
package=`head -n 1 VERSION`
version=`head -n 2 VERSION | tail -n 1`

# Cleanup
rm -rf /tmp/nautilussvn_build
mkdir /tmp/nautilussvn_build

# Export
svn export $SOURCEDIR /tmp/nautilussvn_build/${package}-${version}

# Zip up the original source code
cd /tmp/nautilussvn_build
tar -zcvf ${package}_${version}.orig.tar.gz ${package}-${version}
cd ${package}-${version}/

# Update the changelog (be sure to commit this afterwards)
cd packages/ubuntu/
debchange -i
cp ./debian/changelog "${SOURCEDIR}/packages/ubuntu/debian"

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
