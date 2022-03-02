import argparse
import json
import logging

from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware # only for PoA and dev networks

from chirotonia.ethereum.contract import Contract
from chirotonia.voter import Voter

logger = logging.getLogger('ETH_4_VOTE')
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description='Simulate registration phase for a Chirotonia session')
parser.add_argument("session", type=str, help="Session name to use")
parser.add_argument("-e", "--endpoint", type=str, help="Custom rpc endpoint at port 8545", default='localhost')
parser.add_argument("--no_sign", action="store_true")
vote_flag_group = parser.add_mutually_exclusive_group(required=True)
vote_flag_group.add_argument("-v", "--vote", type=str, help="Name of vote to start")
vote_flag_group.add_argument("-a", "--all", const=True, help="Start all votes specified in configuration", nargs='?')
args = parser.parse_args()

session_name = args.session

w3 = Web3(HTTPProvider('http://' + args.endpoint))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# if not w3.isConnected():
#     raise 'Connection to ethereum node failed'

with open("./runs/%s.json" % session_name) as session_file:
    session_conf = json.load(session_file)

if 'mainContract' not in session_conf:
    logger.error('mainContract address must be set in configuration')
    exit(1)

if 'votersAddress' not in session_conf:
    logger.error("Voters address is required to be set in configuration. (field: votersAddress)")
    exit(1)

if "votersAddressPassword" not in session_conf:
    logger.error("Voters account password is required in configuration (field: votersAddressPassword)")
    exit(1)

w3.eth.defaultAccount = session_conf['votersAddress']
if not args.no_sign:
    w3.geth.personal.unlockAccount(w3.eth.defaultAccount, session_conf['votersAddressPassword'])
    logger.info('Voters account successfully unlocked')

chirotonia = Contract(w3, session_conf['mainContract'])

voters = []
for voter in session_conf['voters']:
    voters.append(Voter(private_key=voter['private_key'], description=voter['description']))

for vote in session_conf['votes']:
    if args.vote and vote['name'] != args.vote:
        continue
    if vote['status'] != 'started':
        logger.warning('Skipping vote %s because not in status started (found %s)', vote['name'], vote['status'])
        continue
    txs = []
    pkeys = [v.public_key for v in voters[:vote['voters']]]
    logger.info('Inserting ballots for vote %s', vote['name'])
    for i, ballot in enumerate(vote['ballots']):
        voted_ballot = voters[i].ring_sign(pkeys, Voter.pack_vote_in_random32(bytes([ballot])))
        txs.append(chirotonia.vote(vote['name'], voted_ballot))
    gasSpent = 0
    for tx in txs:
        tx_rcpt = chirotonia.wait(tx)
        gasSpent += tx_rcpt.gasUsed
    logger.info("Gas spent %d", gasSpent)
    logger.info('Ballots for vote %s successfully inserted', vote['name'])
    vote['status'] = 'voted'


with open("./runs/%s.json" % session_name, "w") as session_file:
    json.dump(session_conf, session_file, indent=4)

logger.info("Configuration updated at ./runs/%s.json", session_name)
