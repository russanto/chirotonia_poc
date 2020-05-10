from __future__ import print_function

from .curve import *
from .utils import *

"""
This implements a linkable variant of the AOS 1-out-of-n ring signature
which requires only `n+1` scalars to validate in addition to the `n` public keys.

For more information, see:

 - https://eprint.iacr.org/2004/027.pdf

"""

def uaosring_randkeys(n):
	skeys = [randsn() for _ in range(0, n)]
	pkeys = [sbmul(sk) for sk in skeys]
	return pkeys, skeys

# Versione ottimizzata per l'uso con smart contract
# - L'hash delle chiavi pubbliche viene calcolato accodando ogni nuova chiave pubblica all'hash delle precedenti
def uaosring_sign(pkeys, mypair, message, tees=None):
	assert len(pkeys) > 0
	mypk, mysk = mypair
	myidx = pkeys.index(mypk)

	tees = tees or [randsn() for _ in range(0, len(pkeys))]
	cees = [0 for _ in range(0, len(pkeys))]
	alpha = randsn()

	M = hashtopoint(message)
	L = hashtopoint(pkeys_hash_calculator(pkeys))
	T = multiply(L, mysk)
	h = hashp(M, T)

	for n, i in [(n, (myidx+n) % len(pkeys)) for n in range(0, len(pkeys))]:
		Y = pkeys[i]
		t = tees[i]
		c = alpha if n == 0 else cees[i-1]

		a = add(sbmul(t), multiply(Y, c))
		b = add(multiply(L, t), multiply(T, c))
		cees[i] = hashs(h, hashp(T, a, b))

	alpha_gap = submodn(alpha, cees[myidx-1])
	tees[myidx] = addmodn(tees[myidx], mulmodn(mysk, alpha_gap))

	return pkeys, T, tees, cees[-1]

def uaosring_check(pkeys, tag, tees, seed, message):
	assert len(pkeys) > 0
	assert len(tees) == len(pkeys)
	L = hashtopoint(pkeys_hash_calculator(pkeys))
	M = hashtopoint(message)
	h = hashp(M, tag)
	c = seed
	for i, y in enumerate(pkeys):
		t = tees[i]
		a = add(sbmul(t), multiply(y, c))
		b = add(multiply(L, t), multiply(tag, c))
		c = hashs(h, hashp(tag, a, b))
	return c == seed

def pkeys_hash_calculator(pkeys):
	assert len(pkeys) > 0
	hash_acc = hashs(pkeys[0][0].n)
	for pk in pkeys[1:len(pkeys)]:
		hash_acc = hashs(hash_acc, pk[0].n)
	return hash_acc


if __name__ == "__main__":
	msg = randsn()
	keys = uaosring_randkeys(4)

	print(uaosring_check(*uaosring_sign(*keys, message=msg), message=msg))

	proof = uaosring_sign(*keys, message=msg)

	tag = quotelist([proof[1][0].n, proof[1][1].n])
	print(quotelist([item.n for sublist in proof[0] for item in sublist]) + ',' + tag + ',' + quotelist(proof[2]) + ',' + quote(proof[3]) + ',' + quote(msg))
