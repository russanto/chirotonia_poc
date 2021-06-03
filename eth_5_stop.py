import argparse
import json
import logging

from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware # only for PoA and dev networks

from chirotonia.ethereum.contract import Contract

logger = logging.getLogger('ETH_5_STOP')
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description='Simulate stop action for a Chirotonia session')
parser.add_argument("session", type=str, help="Session name to use")
parser.add_argument("-e", "--endpoint", type=str, help="Custom rpc endpoint at port 8545", default='localhost')
vote_flag_group = parser.add_mutually_exclusive_group(required=True)
vote_flag_group.add_argument("-v", "--vote", type=str, help="Name of vote to start")
vote_flag_group.add_argument("-a", "--all", const=True, help="Start all votes specified in configuration", nargs='?')
args = parser.parse_args()

session_name = args.session

w3 = Web3(HTTPProvider('http://' + args.endpoint + ':8545'))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

if not w3.isConnected():
    raise 'Connection to ethereum node failed'

with open("./runs/%s.json" % session_name) as session_file:
    session_conf = json.load(session_file)

if 'mainContract' not in session_conf:
    logger.error('mainContract address must be set in configuration')
    exit(1)

if 'manager' not in session_conf:
    logger.error("Manager address is required to be set in configuration. Start aborted.")
    exit(1)

if "managerPassword" not in session_conf:
    logger.error("Manager account password is required in configuration (field: managerPassword)")
    exit(1)

w3.eth.defaultAccount = session_conf['manager']
w3.geth.personal.unlockAccount(w3.eth.defaultAccount, session_conf['managerPassword'])
logger.info('Manager account successfully unlocked')

chirotonia = Contract(w3, session_conf['mainContract'])

if args.all:
    txs = {}
    for vote in session_conf['votes']:
        logger.info("Stopping vote %s", vote['name'])
        try:
            txs[vote["name"]] = chirotonia.stop_vote(vote["name"])
        except:
            logger.error('Error stopping vote %s', vote['name'])
    for name, tx in txs.items():
        try:
            tx_rcpt = chirotonia.wait(tx)
            logger.info("Gas spent %d", tx_rcpt.gasUsed)
            logger.info("Vote %s successfully stopped", name)
            for vote in session_conf['votes']:
                if vote['name'] == name:
                    vote['status'] = 'stopped'
        except:
            logger.error('Error on transaction for vote %s', vote['name'])
elif args.vote:
    found = False
    for vote in session_conf['votes']:
        if args.vote == vote['name']:
            logger.info("Stopping vote %s", vote['name'])
            tx_rcpt = chirotonia.stop_vote(args.vote, sync=True)
            logger.info("Gas spent %d", tx_rcpt.gasUsed)
            logger.info("Vote %s successfully stopped", vote['name'])
            vote['status'] = 'stopped'
            found = True
    if not found:
        logger.error("Specified vote not found in configuration")
        exit(1)
else:
    logger.error("No vote has been specified")
    exit(1)

with open("./runs/%s.json" % session_name, "w") as session_file:
    json.dump(session_conf, session_file, indent=4)

logger.info("Configuration updated at ./runs/%s.json", session_name)
