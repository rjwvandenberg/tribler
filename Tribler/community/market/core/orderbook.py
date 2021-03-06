import logging
import time

from twisted.internet import reactor
from twisted.internet.defer import fail
from twisted.internet.task import deferLater
from twisted.python.failure import Failure

from Tribler.community.market.core.message_repository import MessageRepository
from Tribler.community.market.core.order import OrderId
from Tribler.community.market.core.price import Price
from Tribler.community.market.core.quantity import Quantity
from Tribler.community.market.core.side import Side
from Tribler.community.market.core.tick import Tick, Ask, Bid
from Tribler.community.market.database import MarketDB
from Tribler.dispersy.taskmanager import TaskManager


class OrderBook(TaskManager):
    """
    OrderBook is used for searching through all the orders and giving an indication to the user of what other offers
    are out there.
    """

    def __init__(self, message_repository):
        super(OrderBook, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)

        assert isinstance(message_repository, MessageRepository), type(message_repository)

        self.message_repository = message_repository
        self._bids = Side()
        self._asks = Side()

    def timeout_ask(self, order_id):
        ask = self.get_ask(order_id).tick
        self.remove_tick(order_id)
        return ask

    def timeout_bid(self, order_id):
        bid = self.get_bid(order_id).tick
        self.remove_tick(order_id)
        return bid

    def on_timeout_error(self, _):
        pass

    def on_invalid_tick_insert(self, _):
        self._logger.warning("Invalid tick inserted in order book.")

    def insert_ask(self, ask):
        """
        :type ask: Ask
        """
        assert isinstance(ask, Ask), type(ask)

        if not self._asks.tick_exists(ask.order_id) and ask.is_valid():
            self._asks.insert_tick(ask)
            timeout_delay = float(ask.timestamp) + float(ask.timeout) - time.time()
            task = deferLater(reactor, timeout_delay, self.timeout_ask, ask.order_id)
            self.register_task("ask_%s_timeout" % ask.order_id, task)
            return task.addErrback(self.on_timeout_error)
        return fail(Failure(RuntimeError("ask invalid"))).addErrback(self.on_invalid_tick_insert)

    def remove_ask(self, order_id):
        """
        :type order_id: OrderId
        """
        assert isinstance(order_id, OrderId), type(order_id)

        if self._asks.tick_exists(order_id):
            self.cancel_pending_task("ask_%s_timeout" % order_id)
            self._asks.remove_tick(order_id)

    def insert_bid(self, bid):
        """
        :type bid: Bid
        """
        assert isinstance(bid, Bid), type(bid)

        if not self._bids.tick_exists(bid.order_id) and bid.is_valid():
            self._bids.insert_tick(bid)
            timeout_delay = float(bid.timestamp) + float(bid.timeout) - time.time()
            task = deferLater(reactor, timeout_delay, self.timeout_bid, bid.order_id)
            self.register_task("bid_%s_timeout" % bid.order_id, task)
            return task.addErrback(self.on_timeout_error)
        return fail(Failure(RuntimeError("bid invalid"))).addErrback(self.on_invalid_tick_insert)

    def remove_bid(self, order_id):
        """
        :type order_id: OrderId
        """
        assert isinstance(order_id, OrderId), type(order_id)

        if self._bids.tick_exists(order_id):
            self.cancel_pending_task("bid_%s_timeout" % order_id)
            self._bids.remove_tick(order_id)

    def trade_tick(self, order_id, recipient_order_id, quantity, end_transaction_timestamp):
        """
        :type order_id: OrderId
        :type recipient_order_id: OrderId
        :type quantity: Quantity
        :type end_transaction_timestamp: Timestamp
        """
        assert isinstance(order_id, OrderId), type(order_id)
        assert isinstance(recipient_order_id, OrderId), type(recipient_order_id)
        assert isinstance(quantity, Quantity), type(quantity)
        self._logger.debug("Trading tick in order book for own order %s vs order %s (quantity: %s)",
                           str(order_id), str(recipient_order_id), str(quantity))

        if self.tick_exists(order_id):
            tick = self.get_tick(order_id)
            tick.quantity -= quantity
        if self.tick_exists(recipient_order_id):
            tick = self.get_tick(recipient_order_id)
            if tick.tick.timestamp < end_transaction_timestamp:
                tick.quantity -= quantity

    def tick_exists(self, order_id):
        """
        :param order_id: The order id to search for
        :type order_id: OrderId
        :return: True if the tick exists, False otherwise
        :rtype: bool
        """
        assert isinstance(order_id, OrderId), type(order_id)

        is_ask = self._asks.tick_exists(order_id)
        is_bid = self._bids.tick_exists(order_id)

        return is_ask or is_bid

    def get_ask(self, order_id):
        """
        :param order_id: The order id to search for
        :type order_id: OrderId
        :rtype: TickEntry
        """
        assert isinstance(order_id, OrderId), type(order_id)

        return self._asks.get_tick(order_id)

    def get_bid(self, order_id):
        """
        :param order_id: The order id to search for
        :type order_id: OrderId
        :rtype: TickEntry
        """
        assert isinstance(order_id, OrderId), type(order_id)

        return self._bids.get_tick(order_id)

    def get_tick(self, order_id):
        """
        Return a tick with the specified order id.
        :param order_id: The order id to search for
        :type order_id: OrderId
        :rtype: TickEntry
        """
        assert isinstance(order_id, OrderId), type(order_id)

        return self._bids.get_tick(order_id) or self._asks.get_tick(order_id)

    def ask_exists(self, order_id):
        """
        :param order_id: The order id to search for
        :type order_id: OrderId
        :return: True if the ask exists, False otherwise
        :rtype: bool
        """
        assert isinstance(order_id, OrderId), type(order_id)

        return self._asks.tick_exists(order_id)

    def bid_exists(self, order_id):
        """
        :param order_id: The order id to search for
        :type order_id: OrderId
        :return: True if the bid exists, False otherwise
        :rtype: bool
        """
        assert isinstance(order_id, OrderId), type(order_id)

        return self._bids.tick_exists(order_id)

    def remove_tick(self, order_id):
        """
        :type order_id: OrderId
        """
        assert isinstance(order_id, OrderId), type(order_id)

        self.remove_ask(order_id)
        self.remove_bid(order_id)

    @property
    def asks(self):
        """
        Return the asks side
        :rtype: Side
        """
        return self._asks

    @property
    def bids(self):
        """
        Return the bids side
        :rtype: Side
        """
        return self._bids

    def get_bid_price(self, price_wallet_id, quantity_wallet_id):
        """
        Return the price an ask needs to have to make a trade
        :rtype: Price
        """
        return self._bids.get_max_price(price_wallet_id, quantity_wallet_id)

    def get_ask_price(self, price_wallet_id, quantity_wallet_id):
        """
        Return the price a bid needs to have to make a trade
        :rtype: Price
        """
        return self._asks.get_min_price(price_wallet_id, quantity_wallet_id)

    def get_bid_ask_spread(self, price_wallet_id, quantity_wallet_id):
        """
        Return the spread between the bid and the ask price
        :rtype: Price
        """
        return self.get_ask_price(price_wallet_id, quantity_wallet_id) - \
               self.get_bid_price(price_wallet_id, quantity_wallet_id)

    def get_mid_price(self, price_wallet_id, quantity_wallet_id):
        """
        Return the price in between the bid and the ask price
        :rtype: Price
        """
        ask_price = int(self.get_ask_price(price_wallet_id, quantity_wallet_id))
        bid_price = int(self.get_bid_price(price_wallet_id, quantity_wallet_id))
        return Price((ask_price + bid_price) / 2, price_wallet_id)

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
        return self._asks.get_price_level(price).depth

    def get_bid_side_depth_profile(self, price_wallet_id, quantity_wallet_id):
        """
        format: [(<price>, <depth>), (<price>, <depth>), ...]

        :return: The depth profile
        :rtype: list
        """
        profile = []
        for key, value in self._bids.get_price_level_list(price_wallet_id, quantity_wallet_id).items():
            profile.append((key, value.depth))
        return profile

    def get_ask_side_depth_profile(self, price_wallet_id, quantity_wallet_id):
        """
        format: [(<price>, <depth>), (<price>, <depth>), ...]

        :return: The depth profile
        :rtype: list
        """
        profile = []
        for key, value in self._asks.get_price_level_list(price_wallet_id, quantity_wallet_id).items():
            profile.append((key, value.depth))
        return profile

    def bid_relative_price(self, price):
        """
        :param price: The price to be relative to
        :type price: Price
        :return: The relative price
        :rtype: Price
        """
        assert isinstance(price, Price), type(price)
        return self.get_bid_price('BTC', 'MC') - price

    def ask_relative_price(self, price):
        """
        :param price: The price to be relative to
        :type price: Price
        :return: The relative price
        :rtype: Price
        """
        assert isinstance(price, Price), type(price)
        return self.get_ask_price('BTC', 'MC') - price

    def relative_tick_price(self, tick):
        """
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

    def get_bid_price_level(self, price_wallet_id, quantity_wallet_id):
        """
        Return the price level that an ask has to match to make a trade
        :rtype: PriceLevel
        """
        return self._bids.get_max_price_list(price_wallet_id, quantity_wallet_id)

    def get_ask_price_level(self, price_wallet_id, quantity_wallet_id):
        """
        Return the price level that a bid has to match to make a trade
        :rtype: PriceLevel
        """
        return self._asks.get_min_price_list(price_wallet_id, quantity_wallet_id)

    def get_order_ids(self):
        """
        Return all IDs of the orders in the orderbook, both asks and bids. The returned list is sorted.

        :rtype: [OrderId]
        """
        ids = []

        for price_wallet_id, quantity_wallet_id in self.asks.get_price_level_list_wallets():
            for _, price_level in self.asks.get_price_level_list(price_wallet_id, quantity_wallet_id).items():
                for ask in price_level:
                    ids.append(ask.tick.order_id)

        for price_wallet_id, quantity_wallet_id in self.bids.get_price_level_list_wallets():
            for _, price_level in self.bids.get_price_level_list(price_wallet_id, quantity_wallet_id).items():
                for bid in price_level:
                    ids.append(bid.tick.order_id)

        return sorted(ids)

    def __str__(self):
        res_str = ''
        res_str += "------ Bids -------\n"
        for price_wallet_id, quantity_wallet_id in self.bids.get_price_level_list_wallets():
            for _, value in self._bids.get_price_level_list(price_wallet_id, quantity_wallet_id).items(reverse=True):
                res_str += '%s' % value
        res_str += "\n------ Asks -------\n"
        for price_wallet_id, quantity_wallet_id in self.asks.get_price_level_list_wallets():
            for _, value in self._asks.get_price_level_list(price_wallet_id, quantity_wallet_id).items():
                res_str += '%s' % value
        res_str += "\n"
        return res_str


class DatabaseOrderBook(OrderBook):
    """
    This class adds support for a persistency backend to store ticks.
    For now, it only provides methods to save all ticks to the database or to restore all ticks from the database.
    """
    def __init__(self, message_repository, database):
        super(DatabaseOrderBook, self).__init__(message_repository)

        assert isinstance(database, MarketDB)

        self.database = database

    def save_to_database(self):
        """
        Write all ticks to the database
        """
        self.database.delete_all_ticks()
        for order_id in self.get_order_ids():
            tick = self.get_tick(order_id)
            if tick.is_valid():
                self.database.add_tick(tick.tick)

    def restore_from_database(self):
        """
        Restore ticks from the database
        """
        for tick in self.database.get_ticks():
            if not self.tick_exists(tick.order_id) and tick.is_valid():
                self.insert_ask(tick) if tick.is_ask() else self.insert_bid(tick)
