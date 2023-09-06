import enum


class FlagStatus(str, enum.Enum):
    UNKNOWN = 'unknown'

    # everything is fine
    OK = 'ok'

    # Flag is currently being submitted
    QUEUED = 'queued'

    # Flag is currently being submitted
    PENDING = 'pending'

    # We didn't submit this flag, but it would have been OK
    DUPLICATE_OK = 'duplicate_ok'

    # We didn't submit this flag because it would have expired anyways
    DUPLICATE_EXPIRED = 'duplicate_expired'

    # We already submitted this flag and the submission system tells us that
    DUPLICATE = 'duplicate'

    # We didn't submit this flag because it was a duplicate, but the status is not yet known (i.e. dependent on another
    # currently queued flag submission
    DUPLICATE_QUEUED = "duplicate_queued"

    # something is wrong with our submitter or the flag service
    ERROR = 'error'

    # the flag belongs to the NOP team
    NOP = 'NOP'

    # we tried to submit our own flag and the submission system lets us know
    OWNFLAG = 'ownflag'

    # the flag is not longer active. This is used if a flags are restricted to a
    # specific time frame
    INACTIVE = 'inactive'

    # flag fits the format and could be sent to the submission system, but the
    # submission system told us it is invalid
    INVALID = 'invalid'
