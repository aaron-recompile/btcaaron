"""
btcaaron.errors - Custom Exceptions
"""


class BtcAaronError(Exception):
    """Base exception for btcaaron"""
    pass


class KeyError(BtcAaronError):
    """Key-related errors"""
    pass


class BuildError(BtcAaronError):
    """Transaction/Tree building errors"""
    pass


class BroadcastError(BtcAaronError):
    """Network broadcast errors"""
    pass


class ValidationError(BtcAaronError):
    """Validation errors"""
    pass
