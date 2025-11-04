class UnsupportAgentError(Exception):
    """Raise when an unsupported coding agent is requested by the user"""


class UnrecognizedMode(Exception):
    """Raise when the HumanDecision event has an unrecognized mode"""
