import re


def is_valid_dir_name(s):
    return bool(re.search(r'^\w+$', s))


def is_int_value(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def is_valid_data_frame(msg: str) -> bool:
    if is_valid_can_data_frame_format(msg):
        if is_valid_can_id(int(msg.split("=")[0], 16)):
            return True
    return False


def is_valid_remote_frame(msg: str) -> bool:
    if is_valid_can_remote_frame_format(msg):
        if is_valid_can_id(int(msg.split("R")[0], 16)):
            return True
    return False


def is_valid_can_data_frame_format(frame_str: str, is_fd: bool=True) -> bool:
    if is_fd:
        data_frame_pattern = '^0x[A-Fa-f0-9]{1,8}=([A-Fa-f0-9]{2}:){0,63}[A-Fa-f0-9]{2}$'
    else:
        data_frame_pattern = '^0x[A-Fa-f0-9]{1,8}=([A-Fa-f0-9]{2}:){0,7}[A-Fa-f0-9]{2}$'
    if re.search(data_frame_pattern, frame_str):
        return True
    return False


def is_valid_can_remote_frame_format(frame_str: str) -> bool:
    remote_frame_pattern = "0x[0-7][A-Fa-f0-9]{0,2}R$"
    if re.search(remote_frame_pattern, frame_str):
        return True
    return False


def is_valid_can_payload(payload: str, is_fd: bool=False) -> bool:
    if is_fd:
        pattern='^([A-Fa-f0-9]{2}:){0,63}[A-Fa-f0-9]{2}$'
    else:
        pattern='^([A-Fa-f0-9]{2}:){0,7}[A-Fa-f0-9]{2}$'
    if re.search(pattern, payload):
        return True
    return False


def is_valid_can_id(frame_id: int, is_extended: bool=True) -> bool:      
    if is_extended:
        limit = 0x1fffffff
    else:
        limit = 0x7ff
    if not isinstance(frame_id, int):
        return False
    if frame_id in range(0, limit+1):
        return True
    return False


def is_valid_can_sgn_name_value_format(sgn_str: str) -> bool:
    pattern = '^\w+=\w+$'
    if re.search(pattern, sgn_str):
        return True
    return False
