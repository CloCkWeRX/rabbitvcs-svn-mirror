#!/bin/sh

# Converts all the po source files into mo binary files and installs them in 
# the correct location

for i in `ls ../po/*.po`;
do
    filename=`basename $i`
    locale=`echo ${filename%.*}`
    ./install_translation.sh $locale $i
done
