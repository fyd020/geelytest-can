import sys
import platform
import argparse
from jidutest_can.script.tools.tools import show_dev
from jidutest_can.script.__main__ import MainParser
from jidutest_can.script.tools import rgb_red, set_log


@MainParser.RegisterSubparser("show-dev", [
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
],
    "Show all attached CAN devices")
def can_show_dev(args: argparse.Namespace) -> None:
    set_log(args.debug, level="ERROR")
    plat = platform.system().lower()
    if plat in ("linux", "windows"):
        show_dev()
    else:
        sys.exit(rgb_red("Just support Linux or Windows by now"))
