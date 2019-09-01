RabbitVCS
=========

RabbitVCS is a set of graphical tools written to provide simple and 
straightforward access to the version control systems you use. We currently
support Subversion and Git on a variety of clients such as Nautilus, Thunar,
Nemo, Caja, and on the command line.


System Requirements
-------------------
* gtk               >= 3.0
* python-configobj  >= 4.4.0
* python-gobject    >= 2.14

For subversion:
* python-svn >= 1.7.2
* subversion >= 1.4.6

For git:
* dulwich >= 0.19.0
* git
* tkinter (for now)

For spell checking of commit messages (optional):
* python-gtkspell
* hunspell langpacks

For syntax highlighting (optional):
* python-pygments

Recommends:
* meld (graphical diff tool)


For Debian-based distros you can run: 
```
# apt-get install python-gtk3 python-configobj python-gobject python-gtkspell python-svn subversion python-dulwich python-pygments git meld tkinter
```

For Fedora-based distros you can run:
```
# dnf install python[23]-nautilus python[23]-pysvn python[23]-configobj python[23]-dbus python[23]-dulwich python[23]-tkinter python[23]-gtkspell3 python[23]-pygments subversion git meld
```

Manual Installation
-------------------
Note that you will require superuser rights in order to install RabbitVCS.
Execute the following as root or using sudo:
```
# python setup.py install
```

On Ubuntu or Debian-based distros, instead run:
```
# python setup.py install --install-layout=deb
```

Once this is run, make sure you install one or more client below.

Note
----

Please note that if there is a `PYTHON` environment variable it will be used
as a Runtime environtment for the rabbitvcs module. For example, if `PYTHON`
points to Python3, then the code in the rabbitvcs module will should be located
in the Python 3 module search path.


Clients
-------
RabbitVCS is the core library and set of dialogs, but you interact with them
through our clients. Each client needs to be purposefully installed and has
its own README. Here is a list of our currently working clients:

 * [Nautilus](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients/nautilus)
 * [Thunar](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients/thunar)
 * [Nemo](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients/nemo)
 * [Caja](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients/caja)
 * [Command Line](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients/cli)

We have some others as well that are either incomplete, experimental
or non-working.
[Check them out!](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients)


Upgrade
-------
To upgrade an existing version manually, copy the contents of the repository
to the rabbitvcs lib folder. Most likely it is located at
`/usr/lib/pymodules/python2.7/rabbitvcs`. In case of Debian-based distros this
is will be `/usr/lib/python2.7/dist-packages/rabbitvcs`.
For Fedora-based distros on 64-bit make sure to check `/usr/lib64`.


References
----------
Homepage: http://www.rabbitvcs.org
