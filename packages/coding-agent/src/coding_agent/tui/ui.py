import asyncio

from rich.console import Console
from .utils import run_workflow, Configuration, print_welcome_message
from ..agent import AgentType
from .logo import print_logo


class AgentUI:
    def __init__(self, agent_type: AgentType, config: Configuration) -> None:
        self.agent_type: AgentType = agent_type
        self._console = Console()
        self.config: Configuration = config

    def run(self) -> None:
        print_logo(self._console)
        print_welcome_message(self._console, self.agent_type)
        asyncio.run(run_workflow(self._console, self.config, self.agent_type))
