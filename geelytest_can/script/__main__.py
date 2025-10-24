import sys
import types
import typing
import pathlib
import argparse
import importlib
from jidutest_can import pkg_name, bin_name
from jidutest_can.package import package_path


class MainParser:

    __instance = None

    def __new__(cls, *args, **kwargs) -> typing.Any:
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self) -> None:
        self.mainparser = self.RegisterSubparser.mainparser
        self.subparsers = self.RegisterSubparser.subparsers
        self.subparser_instances = self.RegisterSubparser.subparser_instances
        self.subparser_set = self.RegisterSubparser.subparser_set
        self.subparser_tasks = self.RegisterSubparser.subparser_tasks
        self.__load_subparsers()

    @staticmethod
    def __load_subparsers(
            subparsers_dir: str = "script",
            subparser_suffix: str = "*_subparser.py",
    ):

        for content in pathlib.Path(package_path, subparsers_dir).glob(subparser_suffix):
            module_name = content.name.replace(".py", "")
            module_fullname = f".{subparsers_dir}.{module_name}"
            importlib.import_module(module_fullname, package=pkg_name)

    def __call__(self):
        if not sys.argv[1:]:
            self.mainparser.print_help()
            self.mainparser.exit()
        main_args = self.mainparser.parse_args()

        for subparser_task in self.subparser_tasks:
            if getattr(main_args, "callback") != subparser_task.__name__:
                continue
            subparser_task(main_args)

    class RegisterSubparser:

        mainparser = argparse.ArgumentParser(
            prog=bin_name,
            add_help=True,
            usage=f"\n\t{bin_name}",
            formatter_class=lambda prog: argparse.HelpFormatter(
                prog, max_help_position=40, width=140
            ),
        )
        subparsers = mainparser.add_subparsers(help="")
        subparser_instances = set()
        subparser_set = set()
        subparser_tasks = set()

        def __new__(cls, *args, **kwargs) -> typing.Any:
            instance = super().__new__(cls)
            cls.subparser_instances.add(instance)
            return instance

        def __init__(
            self, subparser_name: str, subparser_args: list, subparser_help=""
        ) -> None:
            self.subparser = self.subparsers.add_parser(
                subparser_name, add_help=True, help=subparser_help
            )
            for subparser_arg in subparser_args:
                self.subparser.add_argument(
                    subparser_arg.get("arg_name"),
                    # dest=subparser_arg.get("dest"),
                    type=subparser_arg.get("type", None),
                    # required=subparser_arg.get("required", False),
                    choices=subparser_arg.get("choices", None),
                    default=subparser_arg.get("default", None),
                    metavar=subparser_arg.get("metavar", None),
                    help=subparser_arg.get("help", None),
                    nargs=subparser_arg.get("nargs", None),
                    action=subparser_arg.get("action", "store"),
                    const=subparser_arg.get("const", None),
                )

        def __call__(self, subparser_task: types.FunctionType) -> typing.Callable:
            self.subparser.set_defaults(callback=subparser_task.__name__)
            type(self).subparser_set.add(self.subparser)
            type(self).subparser_tasks.add(subparser_task)

            def do_subparser_task(*args, **kwargs):
                subparser_task(*args, **kwargs)

            return do_subparser_task
