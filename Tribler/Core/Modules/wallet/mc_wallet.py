from Tribler.Core.Modules.wallet.wallet import Wallet
from Tribler.community.multichain.community import MultiChainCommunity


class MultichainWallet(Wallet):
    """
    This class is responsible for handling your wallet of MultiChain credits.
    """

    def __init__(self, session):
        super(MultichainWallet, self).__init__()

        self.session = session
        self.multichain_community = self.get_multichain_community()

    def get_multichain_community(self):
        for community in self.session.get_dispersy_instance().get_communities():
            if isinstance(community, MultiChainCommunity):
                return community

    def get_identifier(self):
        return 'mc'

    def create_wallet(self):
        pass

    def get_balance(self):
        total = self.multichain_community.persistence.get_total(self.multichain_community._public_key)

        #TODO(Martijn): fake the balance for now
        return {'total_up': 101000, 'total_down': 1000, 'net': 100000}

        if total == (-1, -1):
            return 0
        else:
            return int(max(0, total[0] - total[1]) / 2)
