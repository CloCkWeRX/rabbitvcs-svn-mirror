#
# exceptions.py
#

class NotRepositoryError(Exception):
    """Indicates that no Git repository was found."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class NotTreeError(Exception):
    """Indicates the given sha1 hash does not point to a valid Tree"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class NotCommitError(Exception):
    """Indicates the given sha1 hash does not point to a valid Commit"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class NotBlobError(Exception):
    """Indicates the given sha1 hash does not point to a valid Blob"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class NotTagError(Exception):
    """Indicates the given sha1 hash does not point to a valid Commit"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class GittyupCommandError(Exception):
    """Indicates a command returned an error"""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
