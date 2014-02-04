#!/bin/sh

LOCALE=$1
POFILE=$2

if [ -z "$POFILE" -o -z "$LOCALE" ]
then
    echo "usage: ./install_translation.sh LOCALE POFILE"
    exit 1
fi

mkdir -p ../locale/$LOCALE/LC_MESSAGES
msgfmt --output-file=../locale/$LOCALE/LC_MESSAGES/RabbitVCS.mo $POFILE

echo "Translations installed to ../locale/$LOCALE/LC_MESSAGES/RabbitVCS.mo"
