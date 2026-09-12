class GeoNodeRestException(Exception):
    """
    GeoNodeRestException

    """

    pass


class InvalidPkError(ValueError):
    """A pk argument is not a single pk, a range (``5-10``) or a list (``1,2,3``).

    A ``ValueError`` subclass so callers that already catch ``ValueError`` keep
    working. Raised instead of exiting so ``geonoderest`` stays usable as a
    library (#69); ``cmd_*`` turns it into ``EXIT_USAGE``.
    """


class ApiConfError(Exception):
    """The GeoNode API configuration is incomplete - a required env var is unset.

    Raised instead of exiting so ``geonoderest`` stays usable as a library (#69);
    the command line turns it into ``EXIT_USAGE``.
    """
