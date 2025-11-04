class MalformedMCPSpecification(Exception):
    """Raise when the MCP configuration file is malformed/misconfigured"""


class UnsupportedMCPType(Exception):
    """Raise when the MCP type is not supported"""


class MissingAPIKey(Exception):
    """Raise when ANTHROPIC_API_KEY is missing from the environment"""
