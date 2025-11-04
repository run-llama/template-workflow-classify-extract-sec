from rich_gradient import Gradient
from rich.panel import Panel
from rich.console import Console

LOGO = """
  ██████╗  ██████╗  ██████╗  ███████╗ ██████╗
 ██╔════╝ ██╔═══██╗ ██╔══██╗ ██╔════╝ ██╔══██╗
 ██║      ██║   ██║ ██║  ██║ █████╗   ██████╔╝
 ██║      ██║   ██║ ██║  ██║ ██╔══╝   ██╔══██╗
 ╚██████╗ ╚██████╔╝ ██████╔╝ ███████╗ ██║  ██║
  ╚═════╝  ╚═════╝  ╚═════╝  ╚══════╝ ╚═╝  ╚═╝
"""


def print_logo(console: Console):
    panel = Panel(LOGO, padding=(2, 2), border_style="bold")
    console.print(Gradient(panel, rainbow=True), justify="center")
    print()
    print()
