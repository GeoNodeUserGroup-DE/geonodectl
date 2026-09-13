class GeoNodeRestException(Exception):
    """The GeoNode API could not be reached, or an async operation never finished.

    Raised instead of exiting so ``geonoderest`` stays usable as a library (#69);
    the command line turns it into ``EXIT_FAILED``.
    """

    pass


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
    """A pk argument is not a single pk, a range (``5-10``) or a list (``1,2,3``)."""


class MissingArgumentError(GeonodeUsageError):
    """A required argument was not given - e.g. a username for user creation."""


class ApiConfError(GeonodeUsageError):
    """The GeoNode API configuration is incomplete - a required env var is unset."""
