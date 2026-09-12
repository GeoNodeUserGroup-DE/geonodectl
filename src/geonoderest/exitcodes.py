"""The exit code contract every ``cmd_*`` method and the dispatcher share.

``geonodectl`` is meant to be usable from a shell script or a CI job, so the
outcome of a command has to be readable from ``$?`` without scraping stderr
(see issue #151).

The boundary that makes this work:

* **library methods** (``get``, ``patch``, ``delete``, ``upload``, …) never exit
  the process. They return a value or raise - see issue #69, geonoderest is also
  used as a library and must not kill its host.
* **``cmd_*`` methods** are the only layer that turns an outcome into an exit
  code, by *returning* one of the constants below. Returning ``None`` still means
  success, so a command with nothing to report needs no explicit return.
* **``geonodectl()``** passes that value through to the console script wrapper,
  which calls ``sys.exit()`` on it.
"""

#: everything the command was asked to do succeeded
EXIT_OK: int = 0

#: the operation failed - object not found, the API rejected it, metadata was
#: invalid. In a pk range or list, one failure is enough to report this.
EXIT_FAILED: int = 1

#: the command could not be carried out as asked - an unparseable pk, missing
#: env vars, unreadable input json. ``argparse`` already exits 2 for its own
#: usage errors, so this stays consistent with it.
EXIT_USAGE: int = 2
