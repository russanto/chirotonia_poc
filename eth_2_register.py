import argparse
import json
import logging

from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware # only for PoA and dev networks

from chirotonia.ethereum.contract import Contract
from chirotonia.voter import Voter

logger = logging.getLogger('ETH_2_REGISTER')
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description='Simulate registration phase for a Chirotonia session')
parser.add_argument("session", type=str, help="Session name to use")
parser.add_argument("-e", "--endpoint", type=str, help="Custom rpc endpoint at port 8545", default='localhost')
args = parser.parse_args()

session_name = args.session

w3 = Web3(HTTPProvider('http://' + args.endpoint + ':8545'))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

if not w3.isConnected():
    raise 'Connection to ethereum node failed'

with open("./runs/%s.json" % session_name) as session_file:
    session_conf = json.load(session_file)

if 'mainContract' not in session_conf:
    logger.error('Main contract address must be set in configuration (field: mainContract)')
    exit(1)

if 'votes' not in session_conf:
    logger.error("No votes have been found.")
    exit(1)

if 'identityManager' not in session_conf:
    logger.error("Identity manager address is required to be set in configuration (field: identityManager)")
    exit(1)

if 'identityManagerPassword' not in session_conf:
    logger.error("Identity manager password is required to be set in configuration (field: identityManagerPassword)")
    exit(1)

w3.eth.defaultAccount = session_conf['identityManager']
w3.geth.personal.unlockAccount(w3.eth.defaultAccount, session_conf['identityManagerPassword'])
logger.info('Successfully unlocked identity manager account.')

chirotonia = Contract(w3, session_conf['mainContract'])

voters = []
for i, vote in enumerate(session_conf['votes']):
    if not isinstance(vote['voters'], int):
        logger.warning('Skipping registration for vote ' + vote['name'])
        continue
    if len(voters) < vote['voters']:
        for i in range(vote['voters'] - len(voters)):
            voters.append(Voter(description='Votante%d' % len(voters)))
    registration_txs = []
    logger.info("Registering voters for vote %s", vote['name'])
    for i in range(vote['voters']):
        logger.debug("Registering voter %s for vote %s", voters[i].description, vote['name'])
        tx_hash = chirotonia.register_voter(voters[i].description, voters[i].public_key[0].n, voters[i].public_key[1].n, vote['name'], sync=False)
        registration_txs.append(tx_hash)
    logger.info("Waiting registration txs for vote %s", vote['name'])
    for tx in registration_txs:
        chirotonia.wait(tx)
    logger.info("Registrations for vote %s completed", vote['name'])
    

session_conf['voters'] = []
for voter in voters:
    voter.public_key = {
        "x": voter.public_key[0].n,
        "y": voter.public_key[1].n
    }
    session_conf['voters'].append(voter.__dict__)


with open("./runs/%s.json" % session_name, "w") as session_file:
    json.dump(session_conf, session_file, indent=4)

logger.info("Configuration updated at ./runs/%s.json", session_name)