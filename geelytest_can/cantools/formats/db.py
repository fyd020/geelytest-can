from typing import List
from typing import Optional

from ..database import BusConfig
from ..database import Message
from ..database import Node
from ..formats.dbc_specifics import DbcSpecifics
from ..formats.arxml import AutosarDatabaseSpecifics


class InternalDatabase(object):
    """Internal CAN database.

    """

    def __init__(self,
                 messages: List[Message],
                 nodes: List[Node],
                 buses: List[BusConfig],
                 version : Optional[str],
                 dbc_specifics: Optional[DbcSpecifics] = None,
                 autosar_specifics: Optional[AutosarDatabaseSpecifics] = None):
        self.messages = messages
        self.nodes = nodes
        self.buses = buses
        self.version = version
        self.dbc = dbc_specifics
        self.autosar = autosar_specifics
