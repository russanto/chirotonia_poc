import sys

from chirotonia.linkable_ring_signature import LinkableRingSignature
from chirotonia.voter import Voter

# Imposta il numero di votanti del gruppo
n_voters = int(sys.argv[1])
# Crea il gruppo di votanti
voters_group = [Voter() for _ in range(0, n_voters)]

# Seleziona un votante
voter = voters_group[0]

# Il contenuto del voto è espresso su n byte con n <= 32
# Se il contenuto è < di 32 byte si raggiungono i 32 byte 
# inserendo dati casuali
vote = voter.pack_vote_in_random32(b"\x01")

# Ottengo l'array delle chiavi pubbliche del gruppo di votanti
pkeys = [v.public_key for v in voters_group]

# Calcolo e stampo la firma del voto
signature = voter.ring_sign(pkeys, vote)
print(signature)
