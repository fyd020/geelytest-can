import argparse
import sys
from jidutest_can.package import pkg_name
from jidutest_can.package import __version__
from jidutest_can.script.__main__ import MainParser
from jidutest_can.script.tools import set_log


@MainParser.RegisterSubparser("version", [
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
],
    "Show package version")
def show_version(args: argparse.Namespace) -> None:
    set_log(args.debug)
    if __version__:
        sys.stdout.write(f"version = {__version__}\n")
    else:
        sys.stdout.write(f"Package {pkg_name} is not installed")
