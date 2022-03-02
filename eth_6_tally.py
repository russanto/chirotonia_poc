import argparse
import json
import logging

from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware # only for PoA and dev networks

from chirotonia.ethereum.contract import Contract
from chirotonia.utils import int_to_big_endian

logger = logging.getLogger('ETH_6_TALLY')
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description='Count ballot submitted to vote using choices specified in configuration')
parser.add_argument("session", type=str, help="Session name to use")
parser.add_argument("-e", "--endpoint", type=str, help="Custom rpc endpoint at port 8545", default='localhost')
parser.add_argument("--no_sign", action="store_true")
vote_flag_group = parser.add_mutually_exclusive_group(required=True)
vote_flag_group.add_argument("-v", "--vote", type=str, help="Select single vote")
vote_flag_group.add_argument("-a", "--all", const=True, help="Count ballots for all votes", nargs='?')
args = parser.parse_args()

session_name = args.session

w3 = Web3(HTTPProvider('http://' + args.endpoint))
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

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
if not args.no_sign:
    w3.geth.personal.unlockAccount(w3.eth.defaultAccount, session_conf['managerPassword'])
    logger.info('Manager account successfully unlocked')

chirotonia = Contract(w3, session_conf['mainContract'])

def tally(vote):
    ballots = chirotonia.get_ballots(vote['name'])
    results = {}
    for b in ballots:
        choice = int_to_big_endian(b)[-1]
        if choice >= len(vote['choices']):
            logger.warning('Vote %d skipped because it is not a valid choice', choice)
            continue
        if vote['choices'][choice] in results:
            results[vote['choices'][choice]] += 1
        else:
            results[vote['choices'][choice]] = 1
    print(results)

if args.all:
    for vote in session_conf['votes']:
        tally(vote)
elif args.vote:
    found = False
    for vote in session_conf['votes']:
        if args.vote == vote['name']:
            tally(vote)
            found = True
    if not found:
        logger.error("Specified vote not found in configuration")
        exit(1)
else:
    logger.error("No vote has been specified")
    exit(1)

# with open("./runs/%s.json" % session_name, "w") as session_file:
#     json.dump(session_conf, session_file, indent=4)

# logger.info("Configuration updated at ./runs/%s.json", session_name)
