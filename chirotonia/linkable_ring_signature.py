from __future__ import annotations

from .uaosring import uaosring_check
from .utils import bytes_to_int, quote, quotelist

class LinkableRingSignature:
    def __init__(self, pkeys, tag, ring, seed, message):
        self.pkeys = pkeys
        self.ring = ring
        self.seed = seed
        self.tag = tag
        self.message = message

    def isValid(self) -> bool:
        return uaosring_check(self.pkeys, self.tag, self.ring, self.seed, bytes_to_int(self.message))

    def isLinked(self, signature: LinkableRingSignature) -> bool:
        return signature.tag == self.tag

    def __str__(self):
        return "Check: %s\nPKs: %s\nTag: %s\nRing: %s\nSeed: %s\nMsg: %s\n" % (
            str(self.isValid()), quotelist([item.n for sublist in self.pkeys for item in sublist]),
            quotelist([self.tag[0].n, self.tag[1].n]),
            quotelist(self.ring),
            quote(self.seed), 
            quote(bytes_to_int(self.message)))