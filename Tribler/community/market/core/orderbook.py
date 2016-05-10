import logging
from collections import deque

from side import Side
from tick import MessageId, Ask, Bid, Timestamp, Message, Trade, Price, Tick


class OrderBook(object):
    """Class representation of an order book"""

    def __init__(self):
        """
        Initialise the order book
        """
        self._logger = logging.getLogger(self.__class__.__name__)

        self._trades = deque(maxlen=100)  # List of trades with a limit of 100
        self._bids = Side()
        self._asks = Side()
        self._last_message = None  # The last message processed by this order book
        self._last_timestamp = Timestamp(0.0)  # The time at which the last message was processed

    def _process_message(self, message):
        """
        Process a message that is passed to this order book

        :param message: The message that needs to be processed
        :type message: Message
        """
        assert isinstance(message, Message), type(message)

        if message.timestamp > self._last_timestamp:
            self._last_timestamp = message.timestamp
        self._last_message = message

    def insert_ask(self, ask):
        """
        Insert an ask into the order book

        :param ask: The ask to add
        :type ask: Ask
        """
        assert isinstance(ask, Ask), type(ask)

        self._process_message(ask)

        if not self._asks.tick_exists(ask.message_id):
            self._asks.insert_tick(ask)

    def remove_ask(self, message_id):
        """
        Remove an ask from the order book

        :param message_id: The id of the ask to remove
        :type message_id: MessageId
        """
        assert isinstance(message_id, MessageId), type(message_id)

        if self._asks.tick_exists(message_id):
            self._asks.remove_tick(message_id)

    def insert_bid(self, bid):
        """
        Insert a bid into the order book

        :param bid: The bid to add
        :type bid: Bid
        """
        assert isinstance(bid, Bid), type(bid)

        self._process_message(bid)

        if not self._bids.tick_exists(bid.message_id):
            self._bids.insert_tick(bid)

    def remove_bid(self, message_id):
        """
        Remove a bid from the order book

        :param message_id: The id of the bid to remove
        :type message_id: MessageId
        """
        assert isinstance(message_id, MessageId), type(message_id)

        if self._bids.tick_exists(message_id):
            self._bids.remove_tick(message_id)

    def insert_trade(self, trade):
        """
        Insert a trade into the order book

        :param trade: The trade to add
        :type trade: Trade
        """
        assert isinstance(trade, Trade), type(trade)

        self._process_message(trade)

        self._trades.appendleft(trade)

    def tick_exists(self, message_id):
        """
        Check if a tick exists with the given message id

        :param message_id: The message id to search for
        :type message_id: MessageId
        :return: True if the tick exists, False otherwise
        :rtype: bool
        """
        assert isinstance(message_id, MessageId), type(message_id)

        is_ask = self._asks.tick_exists(message_id)
        is_bid = self._bids.tick_exists(message_id)

        return is_ask or is_bid

    def remove_tick(self, message_id):
        """
        Remove a tick with the given message id from the order book

        :param message_id: The message id of the tick that needs to be removed
        :type message_id: MessageId
        """
        assert isinstance(message_id, MessageId), type(message_id)

        self.remove_ask(message_id)
        self.remove_bid(message_id)

    @property
    def bid_price(self):
        """
        Return the price of a bid

        :return: The price an ask needs to have to make a trade
        :rtype: Price
        """
        return self._bids.max_price

    @property
    def ask_price(self):
        """
        Return the price of an ask

        :return: The price a bid needs to have to make a trade
        :rtype: Price
        """
        return self._asks.min_price

    @property
    def bid_ask_spread(self):
        """
        Return the spread between the bid and the ask price

        :return: The spread
        :rtype: Price
        """
        return self.ask_price - self.bid_price

    @property
    def mid_price(self):
        """
        Return the price in between the bid and the ask price

        :return: The mid price
        :rtype: Price
        """
        return Price.from_mil((int(self.ask_price) + int(self.bid_price)) / 2)

    def bid_side_depth(self, price):
        """
        Return the depth of the price level with the given price on the bid side

        :param price: The price for the price level
        :type price: Price
        :return: The depth at that price level
        :rtype: Quantity
        """
        assert isinstance(price, Price), type(price)
        return self._bids.get_price_level(price).depth

    def ask_side_depth(self, price):
        """
        Return the depth of the price level with the given price on the ask side

        :param price: The price for the price level
        :type price: Price
        :return: The depth at that price level
        :rtype: Quantity
        """
        assert isinstance(price, Price), type(price)
        return self._bids.get_price_level(price).depth

    @property
    def bid_side_depth_profile(self):
        """
        Return the bid side depth profile

        format: [(<price>, <depth>), (<price>, <depth>), ...]

        :return: The depth profile
        :rtype: list
        """
        profile = []
        for key, value in self._bids._price_tree.items():
            profile.append((key, value.depth))
        return profile

    @property
    def ask_side_depth_profile(self):
        """
        Return the ask side depth profile

        format: [(<price>, <depth>), (<price>, <depth>), ...]

        :return: The depth profile
        :rtype: list
        """
        profile = []
        for key, value in self._asks._price_tree.items():
            profile.append((key, value.depth))
        return profile

    def bid_relative_price(self, price):
        """
        Return the relative bid price

        :param price: The price to be relative to
        :type price: Price
        :return: The relative price
        :rtype: Price
        """
        assert isinstance(price, Price), type(price)
        return self.bid_price - price

    def ask_relative_price(self, price):
        """
        Return the relative ask price

        :param price: The price to be relative to
        :type price: Price
        :return: The relative price
        :rtype: Price
        """
        assert isinstance(price, Price), type(price)
        return self.ask_price - price

    def relative_tick_price(self, tick):
        """
        Return the relative tick price

        :param tick: The tick with the price to be relative to
        :type tick: Tick
        :return: The relative price
        :rtype: Price
        """
        assert isinstance(tick, Tick), type(tick)

        if tick.is_ask():
            return self.ask_relative_price(tick.price)
        else:
            return self.bid_relative_price(tick.price)

    @property
    def bid_price_level(self):
        """
        Return the price level that an ask has to match to make a trade

        :return: The maximum bid price level
        :rtype: PriceLevel
        """
        return self._bids.max_price_list

    @property
    def ask_price_level(self):
        """
        Return the price level that a bid has to match to make a trade

        :return: The maximum ask price level
        :rtype: PriceLevel
        """
        return self._asks.min_price_list

    def __str__(self):
        """
        Return the string representation of the order book

        :return: The string representation of the order book
        :rtype: str
        """
        from cStringIO import StringIO

        tempfile = StringIO()
        tempfile.write("------ Bids -------\n")
        if self._bids is not None and len(self._bids) > 0:
            for key, value in self._bids._price_tree.items(reverse=True):
                tempfile.write('%s' % value)
        tempfile.write("\n------ Asks -------\n")
        if self._asks is not None and len(self._asks) > 0:
            for key, value in self._asks._price_tree.items():
                tempfile.write('%s' % value)
        tempfile.write("\n------ Trades ------\n")
        if self._trades is not None and len(self._trades) > 0:
            num = 0
            for entry in self._trades:
                if num < 5:
                    tempfile.write(
                        str(entry.quantity) + " @ " + str(entry.price) + " (" + str(entry.timestamp) + ")\n")
                    num += 1
                else:
                    break
        tempfile.write("\n")
        return tempfile.getvalue()