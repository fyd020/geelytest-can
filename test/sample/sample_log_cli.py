import argparse
from jidutest_can.script.log_subparser import read_log, log_parse


def test_read_log():
    arg = argparse.Namespace(
        log_file=r"D:\JiDU\jidutest\jidutest-sdk\jidutest-can\demo123.blf",
        debug=1,
    )
    read_log(arg)


def test_parse_log():
    arg = argparse.Namespace(
        log_file=r"D:\JiDU\jidutest\jidutest-sdk\jidutest-can\demo123.blf",
        db_path=r"D:\JiDU\jidutest\jidutest-sdk\jidutest-can\test\resource\v1.0\v1.0\SDB23R01_ADPrivateCANFD1_230116_Release.dbc",
        dest_file=None,
        debug=1,
    )
    log_parse(arg)


if __name__ == "__main__":
    test_read_log()
