#!/usr/bin/env bash

# TODO:
# . give the script a proper usage() function

SOURCEDIR=`pwd`
if [ ! -d ${SOURCEDIR}/packages ]; then
    echo "ERROR:"
    echo "   ./packages not found."
    echo "   $0 must be run from the top level of a nautilussvn "
    echo "   working copy."
    exit 1
fi

# Get the version identifier from the nautilussvn package
PACKAGE_ID=`python -c "from nautilussvn import *;print package_identifier()"`
PACKAGE_FILE=`echo $PACKAGE_ID | tr - _`

# Cleanup
BUILDPATH=/tmp/nautilussvn_build
rm -rf $BUILDPATH
mkdir $BUILDPATH

# Export
BUILDSRC=$BUILDPATH/$PACKAGE_ID
svn export $SOURCEDIR $BUILDSRC

# Zip up the original source code
(cd $BUILDPATH && tar zcvf $PACKAGE_FILE.orig.tar.gz $PACKAGE_ID)

# Update the changelog (be sure to commit this afterwards)
(cd $BUILDSRC/packages/ubuntu/ && debchange -i)
cp -v {$BUILDSRC,$SOURCEDIR}/packages/ubuntu/debian/changelog

# Copy the Debian directory into place and build the directory
cp -R $BUILDSRC{/packages/ubuntu/debian/,/}
(cd $BUILDSRC && debuild)

# Let the user know he should commit
echo 
echo "================================================================="
echo " PLEASE COMMIT THE NEW CHANGELOG"
echo "================================================================="
echo 
