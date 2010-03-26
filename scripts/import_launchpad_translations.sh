#!/bin/sh

# This script should be run from the scripts directory

LOCALE_TGZ=$1

if [ -z "$LOCALE_TGZ" ];
then
    echo "usage: ./import_launchpad_translations.sh LOCALE_TGZ"
    exit 1
fi

rm -rf translations
mkdir translations
cd translations
tar xzf $LOCALE_TGZ
rm -rf templates

for mo in `ls`;
do
    if [ -f ../../locale/$mo/LC_MESSAGES/RabbitVCS.mo ];
    then
        mv $mo/LC_MESSAGES/* ../../locale/$mo/LC_MESSAGES/RabbitVCS.mo
    else
        mkdir -p ../../locale/$mo/LC_MESSAGES
        mv $mo/LC_MESSAGES/rabbit-vcs.mo ../../locale/$mo/LC_MESSAGES/RabbitVCS.mo
    fi
done

cd ..
rm -rf translations
