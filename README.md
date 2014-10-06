RabbitVCS
=========

RabbitVCS is a set of graphical tools written to provide simple and 
straightforward access to the version control systems you use.

RabbitVCS is now distributed in two parts.  The first part is the python module
that is not connected to any file manager or text editor.  This is what is now 
known as "rabbitvcs".  The second part is the series of front-ends or clients
that we distribute.  These consist of a Nautilus extension, a Thunar extension,
a Gedit plugin, and a command line utility.  All of these clients use the same
python module as a back-end.


System Requirements
-------------------
pygtk             >= 2.12
python-configobj  >= 4.4.0
python-gobject    >= 2.14
python-simplejson >= 2.1.1
python-gtkspell             (for spell checking of commit messages)
python-svn        >= 1.7.2  (for subversion)
subversion        >= 1.4.6  (for subversion)
dulwich           >= 0.9.7  (for git)
git                         (for git)

Recommends:
meld (graphical diff tool)


Installation
------------
(as root or using sudo)
$ python setup.py install

On Ubuntu or Debian-based distros, instead run:
$ sudo python setup.py install --install-layout=deb

Each clients' README file contains details on their dependencies and installation.

Manual Upgrade:
To upgrade an existing version manually, copy the contents of the repository to the rabbitvcs lib folder.
For example:
    /usr/lib/pymodules/python2.7/rabbitvcs
Note: in case of Debian-based distros this path is most likely
    /usr/lib/python2.7/dist-packages/rabbitvcs

References
----------
Homepage: http://www.rabbitvcs.org
