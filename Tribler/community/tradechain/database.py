"""
This file contains everything related to persistence for TradeChain.
"""
from os import path
from hashlib import sha256

from Tribler.community.tradechain.conversion import encode_block_requester_half, encode_block, EMPTY_HASH, \
    encode_block_crawl
from Tribler.dispersy.database import Database

DATABASE_DIRECTORY = path.join(u"sqlite")
# Path to the database location + dispersy._workingdirectory
DATABASE_PATH = path.join(DATABASE_DIRECTORY, u"tradechain.db")
# Version to keep track if the db schema needs to be updated.
LATEST_DB_VERSION = 1
# Schema for the TradeChain DB.
schema = u"""
CREATE TABLE IF NOT EXISTS trade_chain(
 public_key_requester		TEXT NOT NULL,
 public_key_responder		TEXT NOT NULL,
 asset1_type                INTEGER NOT NULL,
 asset1_amount              DOUBLE NOT NULL,
 asset2_type                INTEGER NOT NULL,
 asset2_amount              DOUBLE NOT NULL,

 total_btc_requester TEXT   DOUBLE NOT NULL,
 total_mc_requester TEXT    DOUBLE NOT NULL,
 sequence_number_requester  INTEGER NOT NULL,
 previous_hash_requester	TEXT NOT NULL,
 signature_requester		TEXT NOT NULL,
 hash_requester		        TEXT PRIMARY KEY,

 total_btc_responder TEXT   DOUBLE NOT NULL,
 total_mc_responder TEXT    DOUBLE NOT NULL,
 sequence_number_responder  INTEGER NOT NULL,
 previous_hash_responder	TEXT NOT NULL,
 signature_responder		TEXT NOT NULL,
 hash_responder		        TEXT NOT NULL,

 insert_time                TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
 );

CREATE TABLE option(key TEXT PRIMARY KEY, value BLOB);
INSERT INTO option(key, value) VALUES('database_version', '""" + str(LATEST_DB_VERSION) + u"""');
"""


class TradeChainDB(Database):
    """
    Persistence layer for the TradeChain Community.
    Connection layer to SQLiteDB.
    Ensures a proper DB schema on startup.
    """

    def __init__(self, dispersy, working_directory):
        """
        Sets up the persistence layer ready for use.
        :param dispersy: Dispersy stores the PK.
        :param working_directory: Path to the working directory
        that will contain the the db at working directory/DATABASE_PATH
        :return:
        """
        super(TradeChainDB, self).__init__(path.join(working_directory, DATABASE_PATH))
        self._dispersy = dispersy
        self.open()

    def add_block(self, block):
        """
        Persist a block
        :param block: The data that will be saved.
        """
        data = (buffer(block.public_key_requester), buffer(block.public_key_responder),
                block.asset1_type, block.asset1_amount, block.asset2_type, block.asset2_amount,
                block.total_btc_requester, block.total_mc_requester,
                block.sequence_number_requester, buffer(block.previous_hash_requester),
                buffer(block.signature_requester), buffer(block.hash_requester),
                block.total_btc_responder, block.total_mc_responder,
                block.sequence_number_responder, buffer(block.previous_hash_responder),
                buffer(block.signature_responder), buffer(block.hash_responder))

        self.execute(
            u"INSERT INTO trade_chain (public_key_requester, public_key_responder, asset1_type, asset1_amount,"
            u"asset2_type, asset2_amount, "
            u"total_btc_requester, total_mc_requester, sequence_number_requester, previous_hash_requester, "
            u"signature_requester, hash_requester, "
            u"total_btc_responder, total_mc_responder, sequence_number_responder, previous_hash_responder, "
            u"signature_responder, hash_responder) "
            u"VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            data)
        self.commit()

    def update_block_with_responder(self, block):
        """
        Update an existing block
        :param block: The data that will be saved.
        """
        data = (
            block.total_btc_responder, block.total_mc_responder,
            block.sequence_number_responder, buffer(block.previous_hash_responder),
            buffer(block.signature_responder), buffer(block.hash_responder), buffer(block.hash_requester))

        self.execute(
            u"UPDATE trade_chain "
            u"SET total_btc_responder = ?, total_mc_responder = ?, "
            u"sequence_number_responder = ?, previous_hash_responder = ?, "
            u"signature_responder = ?, hash_responder = ? "
            u"WHERE hash_requester = ?",
            data)
        self.commit()

    def get_latest_hash(self, public_key):
        """
        Get the relevant hash of the latest block in the chain for a specific public key.
        Relevant means the hash_requester if the last block was a request,
        hash_responder if the last block was a response.
        :param public_key: The public_key for which the latest hash has to be found.
        :return: the relevant hash
        """
        public_key = buffer(public_key)
        db_query = u"SELECT block_hash FROM (" \
                   u"SELECT hash_requester AS block_hash, sequence_number_requester AS sequence_number " \
                   u"FROM trade_chain WHERE public_key_requester = ? " \
                   u"UNION " \
                   u"SELECT hash_responder AS block_hash, sequence_number_responder AS sequence_number " \
                   u"FROM trade_chain WHERE public_key_responder = ?) ORDER BY sequence_number DESC LIMIT 1"
        db_result = self.execute(db_query, (public_key, public_key)).fetchone()
        return str(db_result[0]) if db_result else None

    def get_latest_block(self, public_key):
        return self.get_by_hash(self.get_latest_hash(public_key))

    def get_by_hash_requester(self, hash_requester):
        """
        Returns a block saved in the persistence
        :param hash_requester: The hash_requester of the block that needs to be retrieved.
        :return: The block that was requested or None
        """
        db_query = u"SELECT public_key_requester, public_key_responder, up, down, " \
                   u"total_up_requester, total_down_requester, sequence_number_requester, previous_hash_requester, " \
                   u"signature_requester, hash_requester, " \
                   u"total_up_responder, total_down_responder, sequence_number_responder, previous_hash_responder, " \
                   u"signature_responder, hash_responder, insert_time " \
                   u"FROM `trade_chain` WHERE hash_requester = ? LIMIT 1"
        db_result = self.execute(db_query, (buffer(hash_requester),)).fetchone()
        # Create a DB Block or return None
        return self._create_database_block(db_result)

    def get_by_hash(self, hash):
        """
        Returns a block saved in the persistence, based on a hash that can be either hash_requester or hash_responder
        :param hash: The hash of the block that needs to be retrieved.
        :return: The block that was requested or None
        """
        if hash is None:
            return None

        db_query = u"SELECT public_key_requester, public_key_responder, up, down, " \
                   u"total_up_requester, total_down_requester, sequence_number_requester, previous_hash_requester, " \
                   u"signature_requester, hash_requester, " \
                   u"total_up_responder, total_down_responder, sequence_number_responder, previous_hash_responder, " \
                   u"signature_responder, hash_responder, insert_time " \
                   u"FROM `trade_chain` WHERE hash_requester = ? OR hash_responder = ? LIMIT 1"
        db_result = self.execute(db_query, (buffer(hash), buffer(hash))).fetchone()
        # Create a DB Block or return None
        return self._create_database_block(db_result)

    def get_by_public_key_and_sequence_number(self, public_key, sequence_number):
        """
        Returns a block saved in the persistence.
        :param public_key: The public key corresponding to the block
        :param sequence_number: The sequence number corresponding to the block.
        :return: The block that was requested or None"""
        db_query = u"SELECT public_key_requester, public_key_responder, up, down, " \
                   u"total_up_requester, total_down_requester, sequence_number_requester, previous_hash_requester, " \
                   u"signature_requester, hash_requester, " \
                   u"total_up_responder, total_down_responder, sequence_number_responder, previous_hash_responder, " \
                   u"signature_responder, hash_responder, insert_time " \
                   u"FROM (" \
                   u"SELECT *, sequence_number_requester AS sequence_number, " \
                   u"public_key_requester AS pk FROM `trade_chain` " \
                   u"UNION " \
                   u"SELECT *, sequence_number_responder AS sequence_number," \
                   u"public_key_responder AS pk FROM `trade_chain`) " \
                   u"WHERE sequence_number = ? AND pk = ? LIMIT 1"
        db_result = self.execute(db_query, (sequence_number, buffer(public_key))).fetchone()
        # Create a DB Block or return None
        return self._create_database_block(db_result)

    def get_blocks_since(self, public_key, sequence_number):
        """
        Returns database blocks with sequence number higher than or equal to sequence_number, at most 100 results
        :param public_key: The public key corresponding to the member id
        :param sequence_number: The linear block number
        :return A list of DB Blocks that match the criteria
        """
        db_query = u"SELECT public_key_requester, public_key_responder, up, down, " \
                   u"total_up_requester, total_down_requester, sequence_number_requester, previous_hash_requester, " \
                   u"signature_requester, hash_requester, " \
                   u"total_up_responder, total_down_responder, sequence_number_responder, previous_hash_responder, " \
                   u"signature_responder, hash_responder, insert_time " \
                   u"FROM (" \
                   u"SELECT *, sequence_number_requester AS sequence_number," \
                   u" public_key_requester AS public_key FROM `trade_chain` " \
                   u"UNION " \
                   u"SELECT *, sequence_number_responder AS sequence_number," \
                   u" public_key_responder AS public_key FROM `trade_chain`) " \
                   u"WHERE sequence_number >= ? AND public_key = ? " \
                   u"ORDER BY sequence_number ASC " \
                   u"LIMIT 100"
        db_result = self.execute(db_query, (sequence_number, buffer(public_key))).fetchall()
        return [self._create_database_block(db_item) for db_item in db_result]

    def get_blocks(self, public_key, limit=100):
        """
        Returns database blocks identified by a specific public key (either of the requester or the responder).
        Optionally limit the amount of blocks returned.
        :param public_key: The public key corresponding to the member id
        :param limit: The maximum number of blocks to return
        :return A list of DB Blocks that match the criteria
        """
        db_query = u"SELECT public_key_requester, public_key_responder, up, down, " \
                   u"total_up_requester, total_down_requester, sequence_number_requester, previous_hash_requester, " \
                   u"signature_requester, hash_requester, " \
                   u"total_up_responder, total_down_responder, sequence_number_responder, previous_hash_responder, " \
                   u"signature_responder, hash_responder, insert_time " \
                   u"FROM (" \
                   u"SELECT *, sequence_number_requester AS sequence_number," \
                   u" public_key_requester AS public_key FROM `trade_chain` " \
                   u"UNION " \
                   u"SELECT *, sequence_number_responder AS sequence_number," \
                   u" public_key_responder AS public_key FROM `trade_chain`) " \
                   u"WHERE public_key = ? " \
                   u"ORDER BY sequence_number DESC " \
                   u"LIMIT ?"
        db_result = self.execute(db_query, (buffer(public_key), limit)).fetchall()
        return [self._create_database_block(db_item) for db_item in db_result]

    def get_num_unique_interactors(self, public_key):
        """
        Returns the number of people you interacted with (either helped or that have helped you)
        :param public_key: The public key of the member of which we want the information
        :return: A tuple of unique number of interactors that helped you and that you have helped respectively
        """
        peers_you_helped = set()
        peers_helped_you = set()
        for block in self.get_blocks(public_key, limit=-1):
            if block.public_key_requester == public_key:
                if int(block.up) > 0:
                    peers_you_helped.add(block.public_key_responder)
                if int(block.down) > 0:
                    peers_helped_you.add(block.public_key_responder)
            else:
                if int(block.up) > 0:
                    peers_helped_you.add(block.public_key_requester)
                if int(block.down) > 0:
                    peers_you_helped.add(block.public_key_requester)
        return len(peers_you_helped), len(peers_helped_you)

    def _create_database_block(self, db_result):
        """
        Create a Database block or return None.
        :param db_result: The DB_result with the DatabaseBlock or None
        :return: DatabaseBlock if db_result else None
        """
        if db_result:
            return DatabaseBlock(db_result)
        else:
            return None

    def get_all_hash_requester(self):
        """
        Get all the hash_requester saved in the persistence layer.
        :return: list of hash_requester.
        """
        db_result = self.execute(u"SELECT hash_requester FROM trade_chain").fetchall()
        # Unpack the db_result tuples and decode the results.
        return [str(x[0]) for x in db_result]

    def contains(self, hash_requester):
        """
        Check if a block is existent in the persistence layer.
        :param hash_requester: The hash_requester that is queried
        :return: True if the block exists, else false.
        """
        db_query = u"SELECT hash_requester FROM trade_chain WHERE hash_requester = ? LIMIT 1"
        db_result = self.execute(db_query, (buffer(hash_requester),)).fetchone()
        return db_result is not None

    def get_latest_sequence_number(self, public_key):
        """
        Return the latest sequence number known for this public_key.
        If no block for the pk is know returns -1.
        :param public_key: Corresponding public key
        :return: sequence number (integer) or -1 if no block is known
        """
        public_key = buffer(public_key)
        db_query = u"SELECT MAX(sequence_number) FROM (" \
                   u"SELECT sequence_number_requester AS sequence_number " \
                   u"FROM trade_chain WHERE public_key_requester = ? UNION " \
                   u"SELECT sequence_number_responder AS sequence_number " \
                   u"FROM trade_chain WHERE public_key_responder = ? )"
        db_result = self.execute(db_query, (public_key, public_key)).fetchone()[0]
        return db_result if db_result is not None else -1

    def get_total(self, public_key):
        """
        Return the latest (total_up, total_down) known for this node.
        if no block for the pk is know returns (0,0)
        :param public_key: public_key of the node
        :return: (total_up (int), total_down (int)) or (0, 0) if no block is known.
        """
        public_key = buffer(public_key)
        db_query = u"SELECT total_up, total_down FROM (" \
                   u"SELECT total_up_requester AS total_up, total_down_requester AS total_down, " \
                   u"sequence_number_requester AS sequence_number FROM trade_chain " \
                   u"WHERE public_key_requester = ? UNION " \
                   u"SELECT total_up_responder AS total_up, total_down_responder AS total_down, " \
                   u"sequence_number_responder AS sequence_number FROM trade_chain WHERE public_key_responder = ? ) " \
                   u"ORDER BY sequence_number DESC LIMIT 1"
        db_result = self.execute(db_query, (public_key, public_key)).fetchone()
        return (db_result[0], db_result[1]) if db_result is not None and db_result[0] is not None \
                                               and db_result[1] is not None else (0, 0)

    def open(self, initial_statements=True, prepare_visioning=True):
        return super(TradeChainDB, self).open(initial_statements, prepare_visioning)

    def close(self, commit=True):
        return super(TradeChainDB, self).close(commit)

    def check_database(self, database_version):
        """
        Ensure the proper schema is used by the database.
        :param database_version: Current version of the database.
        :return:
        """
        assert isinstance(database_version, unicode)
        assert database_version.isdigit()
        assert int(database_version) >= 0

        if int(database_version) < LATEST_DB_VERSION:
            # Remove all previous data, since we have only been testing so far, and previous blocks might not be
            # reliable. In the future, we should implement an actual upgrade procedure
            self.executescript(schema)
            self.commit()

        return LATEST_DB_VERSION


class DatabaseBlock:
    """ DataClass for a tradechain block. """

    def __init__(self, data):
        """ Create a block from data """
        # Common part
        self.public_key_requester = str(data[0])
        self.public_key_responder = str(data[1])
        self.asset1_type = data[2]
        self.asset1_amount = data[3]
        self.asset2_type = data[4]
        self.asset2_amount = data[5]
        # Requester part
        self.total_btc_requester = data[6]
        self.total_mc_requester = data[7]
        self.sequence_number_requester = data[8]
        self.previous_hash_requester = str(data[9])
        self.signature_requester = str(data[10])
        self.hash_requester = str(data[11])
        # Responder part
        self.total_btc_responder = data[12]
        self.total_mc_responder = data[13]
        self.sequence_number_responder = data[14]
        self.previous_hash_responder = str(data[15])
        self.signature_responder = str(data[16])
        self.hash_responder = str(data[17])

        self.insert_time = data[18]

    @classmethod
    def from_signature_response_message(cls, message):
        payload = message.payload
        requester = message.authentication.signed_members[0]
        responder = message.authentication.signed_members[1]
        return cls((requester[1].public_key, responder[1].public_key, payload.asset1_type, payload.asset1_amount,
                    payload.asset2_type, payload.asset2_amount,
                    payload.total_btc_requester, payload.total_mc_requester,
                    payload.sequence_number_requester, payload.previous_hash_requester,
                    requester[0], sha256(encode_block_requester_half(payload, requester[1].public_key,
                                                                     responder[1].public_key, requester[0])).digest(),
                    payload.total_btc_responder, payload.total_mc_responder,
                    payload.sequence_number_responder, payload.previous_hash_responder,
                    responder[0], sha256(encode_block(payload, requester, responder)).digest(),
                    None))

    @classmethod
    def from_signature_request_message(cls, message):
        payload = message.payload
        requester = message.authentication.signed_members[0]
        responder = message.authentication.signed_members[1]
        return cls((requester[1].public_key, responder[1].public_key, payload.asset1_type, payload.asset1_amount,
                    payload.asset2_type, payload.asset2_amount,
                    payload.total_btc_requester, payload.total_mc_requester,
                    payload.sequence_number_requester, payload.previous_hash_requester,
                    requester[0], sha256(encode_block_requester_half(payload, requester[1].public_key,
                                                                     responder[1].public_key, requester[0])).digest(),
                    0, 0,
                    -1, EMPTY_HASH,
                    "", EMPTY_HASH,
                    None))

    @classmethod
    def from_block_response_message(cls, message, requester, responder):
        payload = message.payload
        return cls((requester.public_key, responder.public_key, payload.asset1_type, payload.asset1_amount,
                    payload.asset2_type, payload.asset2_amount,
                    payload.total_btc_requester, payload.total_mc_requester,
                    payload.sequence_number_requester, payload.previous_hash_requester,
                    payload.signature_requester,
                    sha256(encode_block_requester_half(payload, payload.public_key_requester,
                                                       payload.public_key_responder,
                                                       payload.signature_requester)).digest(),
                    payload.total_btc_responder, payload.total_mc_responder,
                    payload.sequence_number_responder, payload.previous_hash_responder,
                    payload.signature_responder, sha256(encode_block_crawl(payload)).digest(),
                    None))

    def to_payload(self):
        """
        :return: (tuple) corresponding to the payload data in a Signature message.
        """
        return (self.asset1_type, self.asset1_amount,
                self.asset2_type, self.asset2_amount,
                self.total_btc_requester, self.total_mc_requester,
                self.sequence_number_requester, self.previous_hash_requester,
                self.total_btc_responder, self.total_mc_responder,
                self.sequence_number_responder, self.previous_hash_responder,
                self.public_key_requester, self.signature_requester,
                self.public_key_responder, self.signature_responder)

    # def to_dictionary(self):
    #     """
    #     :return: (dict) a dictionary that can be sent over the internet.
    #     """
    #     return {
    #         "up": self.up,
    #         "down": self.down,
    #         "total_up_requester": self.total_up_requester,
    #         "total_down_requester": self.total_down_requester,
    #         "sequence_number_requester": self.sequence_number_requester,
    #         "previous_hash_requester": base64.encodestring(self.previous_hash_requester).strip(),
    #         "total_up_responder": self.total_up_responder,
    #         "total_down_responder": self.total_down_responder,
    #         "sequence_number_responder": self.sequence_number_responder,
    #         "previous_hash_responder": base64.encodestring(self.previous_hash_responder).strip(),
    #         "public_key_requester": base64.encodestring(self.public_key_requester).strip(),
    #         "signature_requester": base64.encodestring(self.signature_requester).strip(),
    #         "public_key_responder": base64.encodestring(self.public_key_responder).strip(),
    #         "signature_responder": base64.encodestring(self.signature_responder).strip(),
    #         "insert_time": self.insert_time
    #     }
