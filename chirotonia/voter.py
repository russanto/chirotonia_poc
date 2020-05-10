from os import urandom

from .curve import randsn, sbmul, hashs
from .uaosring import uaosring_sign
from .utils import bytes_to_int, Point

from .linkable_ring_signature import LinkableRingSignature

class Voter:
    def __init__(self, **kwargs):
        if 'private_key' in kwargs:
            self.private_key = kwargs['private_key']
            self.public_key = sbmul(self.private_key)
        if 'public_key' in kwargs:
            self.public_key = kwargs['public_key']
        if 'description' in kwargs:
            self.description = kwargs['description']
        if not hasattr(self, 'public_key'):
            self.private_key = randsn()
            self.public_key = sbmul(self.private_key)
    
    def ring_sign(self, pkeys: [Point], message: bytes, tees: [int] = None) -> LinkableRingSignature:
        if not self.private_key:
            raise "Voter can't sign without a private key"
        signature = uaosring_sign(pkeys, (self.public_key, self.private_key), bytes_to_int(message), tees)
        return LinkableRingSignature(pkeys, signature[1], signature[2], signature[3], message)

    @classmethod
    def pack_vote_in_random32(self, vote: bytes) -> bytes:
        assert(len(vote) <= 32)
        return urandom(32 - len(vote)) + vote

