#!/usr/bin/env python

from collections import namedtuple
from typing import (
    Dict,
    List,
    Optional,
)

from hummingbot.core.data_type.order_book_row import OrderBookRow
from hummingbot.core.data_type.order_book_message import (
    OrderBookMessage,
    OrderBookMessageType,
)

NdaxOrderBookEntry = namedtuple("NdaxOrderBookEntry", "mdUpdateId accountId actionDateTime actionType lastTradePrice orderId price productPairCode quantity side")
NdaxTradeEntry = namedtuple("NdaxTradeEntry", "tradeId productPairCode quantity price order1 order2 tradeTime direction takerSide blockTrade orderClientId")


class NdaxOrderBookMessage(OrderBookMessage):

    _DELETE_ACTION_TYPE = 2
    _BUY_SIDE = 0
    _SELL_SIDE = 1

    def __new__(
        cls,
        message_type: OrderBookMessageType,
        content: Dict[str, any],
        timestamp: Optional[float] = None,
        *args,
        **kwargs,
    ):
        if timestamp is None:
            if message_type is OrderBookMessageType.SNAPSHOT:
                raise ValueError("timestamp must not be None when initializing snapshot messages.")
            timestamp = content["timestamp"]

        return super(NdaxOrderBookMessage, cls).__new__(
            cls, message_type, content, timestamp=timestamp, *args, **kwargs
        )

    @property
    def update_id(self) -> int:
        if self.type in [OrderBookMessageType.DIFF, OrderBookMessageType.SNAPSHOT]:
            entry: NdaxOrderBookEntry = self.content["data"][0]
            return int(entry.actionDateTime)
        elif self.type == OrderBookMessageType.TRADE:
            entry: NdaxTradeEntry = self.content["data"][0]
            return int(entry.tradeTime)

    @property
    def trade_id(self) -> int:
        entry: NdaxTradeEntry = self.content["data"][0]
        return entry.tradeId

    @property
    def trading_pair(self) -> str:
        return self.content["trading_pair"]

    @property
    def asks(self) -> List[OrderBookRow]:
        entries: List[NdaxOrderBookEntry] = self.content["data"]
        return [self._order_book_row_for_entry(entry) for entry in entries if entry.side == self._SELL_SIDE]

    @property
    def bids(self) -> List[OrderBookRow]:
        entries: List[NdaxOrderBookEntry] = self.content["data"]
        return [self._order_book_row_for_entry(entry) for entry in entries if entry.side == self._BUY_SIDE]

    def _order_book_row_for_entry(self, entry: NdaxOrderBookEntry) -> OrderBookRow:
        price = float(entry.price)
        amount = float(entry.quantity) if entry.actionType != self._DELETE_ACTION_TYPE else 0.0
        update_id = entry.mdUpdateId
        return OrderBookRow(price, amount, update_id)

    def __eq__(self, other) -> bool:
        return type(self) == type(other) and self.type == other.type and self.timestamp == other.timestamp

    def __lt__(self, other) -> bool:
        # If timestamp is the same, the ordering is snapshot < diff < trade
        return (self.timestamp < other.timestamp or (self.timestamp == other.timestamp and self.type.value < other.type.value))

    def __hash__(self) -> int:
        return hash((self.type, self.timestamp))
