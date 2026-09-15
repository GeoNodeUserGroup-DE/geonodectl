class GeoNodeRestException(Exception):
    """The GeoNode API could not be reached, or an async operation never finished.

    Raised instead of exiting so ``geonoderest`` stays usable as a library (#69);
    the command line turns it into ``EXIT_FAILED``.
    """

    pass


class ResourceNotFoundError(GeoNodeRestException):
    """No object exists with the given uuid.

    A failed lookup, like a 404 on a pk - ``EXIT_FAILED``, not ``EXIT_USAGE``.
    """


class GeonodeUsageError(ValueError):
    """The command cannot be carried out as asked - bad or missing arguments.

    The base of every "you asked for something impossible" error, so a caller can
    catch the whole family in one clause. ``cmd_*`` turns it into ``EXIT_USAGE``.

    A ``ValueError`` subclass so callers that already catch ``ValueError`` keep
    working - but catch *this* rather than ``ValueError`` when mapping to an exit
    code: ``requests.exceptions.JSONDecodeError`` is also a ``ValueError``, and a
    malformed API response is a failed operation, not a usage error.
    """


class InvalidPkError(GeonodeUsageError):
    """An identifier is not a pk, a range (``5-10``), a list (``1,2,3``) or a uuid."""


class UuidTypeMismatchError(GeonodeUsageError):
    """A uuid resolved, but to a different kind of object than the command is about.

    ``geonodectl dataset describe <uuid-of-a-map>`` - the uuid is real, the verb
    is wrong, so this is a usage error rather than a failed lookup (#160).
    """


class MissingArgumentError(GeonodeUsageError):
    """A required argument was not given - e.g. a username for user creation."""


class ApiConfError(GeonodeUsageError):
    """The GeoNode API configuration is incomplete - a required env var is unset."""


class UnknownCommandError(GeonodeUsageError):
    """No built-in command and no installed extension goes by the given name."""
