from crccheck.crc import Crc8GsmA as Crc
from typing import Union, List, Tuple


def e2e_crc_data(data_id: int, counter: int, sig_value_length: Union[Tuple[int, int], List[Tuple[int, int]]]) -> int:
    crc_data = bytearray(b'')
    crc_data += data_id.to_bytes(2, 'little')
    crc_data += counter.to_bytes(1, 'little')
    value_length_list = [sig_value_length] if isinstance(sig_value_length, tuple) else sig_value_length
    for value, length in value_length_list:
        crc_data += value.to_bytes(((length - 1) // 8) + 1, 'little')
    return Crc.calc(crc_data)


if __name__ == '__main__':
    data_id = 1084
    counter = 6
    sig_value_length = [(4, 3), (0, 3)]
    result = e2e_crc_data(data_id, counter, sig_value_length)
    print(result)
    print(hex(result))
