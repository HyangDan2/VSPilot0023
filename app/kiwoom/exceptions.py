class KiwoomError(Exception):
    pass

class KiwoomRateLimitError(KiwoomError):
    pass

class KiwoomAuthError(KiwoomError):
    pass
