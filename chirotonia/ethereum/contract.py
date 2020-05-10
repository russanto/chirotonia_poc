from web3 import Web3

from .contract_data import abi, bytecode
from ..linkable_ring_signature import LinkableRingSignature
from ..utils import bytes_to_int

class Contract:
    def __init__(self, web3: Web3, address=''):
        self.__web3 = web3
        if address:
            self.__contract = web3.eth.contract(address=address, abi=abi)
        else:
            self.__contract = web3.eth.contract(abi=abi, bytecode=bytecode)

    def deploy(self, identity_manager):
        tx_hash = self.__contract.constructor(identity_manager).transact()
        receipt = self.__web3.eth.waitForTransactionReceipt(tx_hash)
        self.__contract = self.__web3.eth.contract(address=receipt.contractAddress, abi=abi)
        self.identity_manager = identity_manager
        self.owner_address = self.__web3.eth.defaultAccount
        return receipt

    def create_vote(self, identifier: str, subject: str, **kwargs):
        tx_hash = self.__contract.functions.nuovaVotazione(identifier, subject).transact()
        if "sync" in kwargs and kwargs["sync"]:
            return self.__web3.eth.waitForTransactionReceipt(tx_hash)
        else:
            return tx_hash
    
    def set_choice(self, identifier: str, code: int, description: str, **kwargs):
        tx_hash = self.__contract.functions.impostaScelta(identifier, description, code.to_bytes(1, 'big')).transact()
        if "sync" in kwargs and kwargs["sync"]:
            return self.__web3.eth.waitForTransactionReceipt(tx_hash)
        else:
            return tx_hash

    def register_voter(self, description, pub_x, pub_y, vote_id, **kwargs):
        tx_hash = self.__contract.functions.accreditaVotante(description, pub_x, pub_y, vote_id).transact()
        if "sync" in kwargs and kwargs["sync"]:
            return self.__web3.eth.waitForTransactionReceipt(tx_hash)
        else:
            return tx_hash

    def start_vote(self, identifier: str, **kwargs):
        tx_hash = self.__contract.functions.avviaVotazione(identifier).transact()
        if "sync" in kwargs and kwargs["sync"]:
            return self.__web3.eth.waitForTransactionReceipt(tx_hash)
        else:
            return tx_hash

    def vote(self, identifier: str, signature: LinkableRingSignature, **kwargs):
        tag_array = [signature.tag[0].n, signature.tag[1].n]
        vote = bytes_to_int(signature.message)
        tx_hash = self.__contract.functions.vota(tag_array, signature.ring, signature.seed, vote, identifier).transact()
        if "sync" in kwargs and kwargs["sync"]:
            return self.__web3.eth.waitForTransactionReceipt(tx_hash)
        else:
            return tx_hash

    def stop_vote(self, identifier: str, **kwargs):
        tx_hash = self.__contract.functions.chiudiVotazione(identifier).transact()
        if "sync" in kwargs and kwargs["sync"]:
            return self.__web3.eth.waitForTransactionReceipt(tx_hash)
        else:
            return tx_hash

    def get_ballots(self, identifier: str):
        return self.__contract.functions.getVoti(identifier).call()
    
    def wait(self, tx_hash):
        return self.__web3.eth.waitForTransactionReceipt(tx_hash)