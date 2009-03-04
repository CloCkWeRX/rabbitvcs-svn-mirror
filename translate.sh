#!/bin/sh

# Set up a translation file
# 1. Extract strings from glade files into .h fileS
# 2. Extract gettext strings from py files
# 3. Delete the glade .h files

cd nautilussvn

for i in `find . | grep '\.glade' | grep -v '\.svn'`;
do
	intltool-extract --type=gettext/glade $i
done

xgettext -L Python --keyword=_ --keyword=N_ -o po/NautilusSvn.pot -f po/POTFILES.in

for i in `find . | grep '\.glade\.h' | grep -v '\.svn'`;
do
	rm -f $i
done

# Create binary a .mo file from a .po file
# msgfmt --output-file=locale/en_US/LC_MESSAGES/NautilusSvn.mo po/en_US.po

# Generate a new .po file for another language
# msginit --input=po/NautilusSvn.pot --locale=en_CA
