UNKNOWN = 'unknown'

# everything is fine
OK = 'ok'

# We already submitted this flag and the submission system tells us thats
DUPLICATE = 'duplicate'

# something is wrong with our submitter
ERROR = 'error'

# the service did not check the flag, but told us to fuck off
RATELIMIT = 'ratelimit'

# something is wrong with the submission system
EXCEPTION = 'exception'

# we tried to submit our own flag and the submission system lets us know
OWNFLAG = 'ownflag'

# the flag is not longer active. This is used if a flags are restricted to a
# specific time frame
INAKTIV = 'inaktiv'

# flag fits the format and could be sent to the submission system, but the
# submission system told us it is invalid
INVALID = 'invalid'

# This status code is used in case the scoring system requires the services to
# be working. Flags that are rejected might be sent again!
SERVICEBROKEN = 'servicebroken'

ALL = [UNKNOWN, OK, DUPLICATE, ERROR, RATELIMIT, EXCEPTION, OWNFLAG, INAKTIV,
    INVALID, SERVICEBROKEN]
