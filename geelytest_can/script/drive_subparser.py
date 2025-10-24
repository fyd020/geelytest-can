import argparse
import os
import platform
import sys
from jidutest_can.package import pkg_name
from jidutest_can.package import __version__
from jidutest_can.script.__main__ import MainParser
from jidutest_can.script.tools import set_log, rgb_red


@MainParser.RegisterSubparser("install-drive", [
    {"arg_name": "--debug", "type": int, "help": "Enable or disable debug level", "default": 0, "choices": [0, 1]},
],
    "Show package version")
def install_drive(args: argparse.Namespace) -> None:
    set_log(args.debug)
    plat = platform.system().lower()
    if plat == "linux":
        mkdir_cmd = "mkdir peak-linux-driver"
        cd_cmd = "cd peak-linux-driver;"
        download_cmd = cd_cmd + "wget https://www.peak-system.com/quick/PCAN-Linux-Driver"
        tar_cmd = cd_cmd + "tar -xzf PCAN-Linux-Driver --strip-components 1"
        make_cmd = cd_cmd + "make clean;make;make install"
        active_cmd = "modprobe pcan;modinfo pcan"
        rmdir_cmd = "rm -rf peak-linux-driver"
        cmds = [mkdir_cmd, download_cmd, tar_cmd, make_cmd, active_cmd, rmdir_cmd]
        for cmd in cmds:
            os.system(cmd)
    else:
        sys.exit(rgb_red("Just support Linux by now"))
