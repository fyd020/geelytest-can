from bitstruct import CompiledFormatDict
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING
from typing import Union
from typing_extensions import Literal
from typing_extensions import TypedDict
from typing_extensions import OrderedDict
if TYPE_CHECKING:
    import os
    from ..database import Message
    from ..database import NamedSignalValue
    from ..database import Signal


class Formats(NamedTuple):
    big_endian: CompiledFormatDict
    little_endian: CompiledFormatDict
    padding_mask: int


StringPathLike = Union[str, "os.PathLike[str]"]
Comments = Dict[Optional[str], str]
Codec = TypedDict(
    "Codec",
    {
        "signals": List["Signal"],
        "formats": Formats,
        "multiplexers": Dict[str, Dict[int, Any]],  # "Any" should be "Codec" (cyclic definition is not possible though)
    },
)

ByteOrder = Literal["little_endian", "big_endian"]
Choices = OrderedDict[int, Union[str, "NamedSignalValue"]]

# Type aliases. Introduced to reduce type annotation complexity while
# allowing for more complex encode/decode schemes like the one used
# for AUTOSAR container messages.
SignalValueType = Union[float, str, "NamedSignalValue"]
SignalDictType = Dict[str, SignalValueType]
ContainerHeaderSpecType = Union["Message", str, int]
ContainerUnpackResultType = Sequence[Union[Tuple["Message", bytes], Tuple[int, bytes]]]
ContainerUnpackListType = List[Union[Tuple["Message", bytes], Tuple[int, bytes]]]
ContainerDecodeResultType = Sequence[
    Union[Tuple["Message", SignalDictType], Tuple[int, bytes]]
]
ContainerDecodeResultListType = List[
    Union[Tuple["Message", SignalDictType], Tuple[int, bytes]]
]
ContainerEncodeInputType = Sequence[
    Tuple[ContainerHeaderSpecType, Union[bytes, SignalDictType]]
]
DecodeResultType = Union[SignalDictType, ContainerDecodeResultType]
EncodeInputType = Union[SignalDictType, ContainerEncodeInputType]

SecOCAuthenticatorFn = Callable[["Message", bytearray, int], bytearray]
