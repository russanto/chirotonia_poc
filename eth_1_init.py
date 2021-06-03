import argparse
import json
import logging
import os
import sys

from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware # only for PoA and dev networks

from chirotonia.ethereum.contract import Contract

logger = logging.getLogger('ETH_1_INIT')
logging.basicConfig(level=logging.INFO)

# TODO
# -v flag per aggiornare solo le votazioni

parser = argparse.ArgumentParser(description='Initialize a new Chirotonia session - Proof of concept for Chirotonia e-voting system')
parser.add_argument("session", type=str, help="Session name to use as identifier for this session")
parser.add_argument("-c", "--configuration", type=str, help="Custom demo configuration file. (default: eth_demo.json)", default='eth_demo.json')
parser.add_argument("-e", "--endpoint", type=str, help="Custom rpc endpoint at port 8545", default='localhost')
args = parser.parse_args()

session_name = args.session
logger.info("Initializing session %s", session_name)

try:
    demo_conf = open(args.configuration)
    chirotonia_conf = json.load(demo_conf)
except:
    logger.error("Error with configuration file")

w3 = Web3(HTTPProvider('http://' + args.endpoint + ':8545'))
w3.middleware_onion.inject(geth_poa_middleware, layer=0) # only for PoA and dev networks

if not w3.isConnected():
    raise 'Connection to ethereum node failed'

if not os.path.exists("./runs"):
    os.makedirs("./runs")
else:
    if os.path.isfile("./runs/%s.json" % session_name):
        logger.error("Session %s already initialized", session_name)
        exit(1)

chirotonia_conf["session"] = session_name

if "identityManager" not in chirotonia_conf:
    logger.error("Identity manager address is required in configuration (field: identityManager)")
    exit(1)

if "manager" not in chirotonia_conf:
    logger.error("Manager address is required in configuration (field: manager)")
    exit(1)

if "managerPassword" not in chirotonia_conf:
    logger.error("Manager account password is required in configuration (field: managerPassword)")
    exit(1)

w3.eth.defaultAccount = chirotonia_conf['manager']
w3.geth.personal.unlockAccount(w3.eth.defaultAccount, chirotonia_conf['managerPassword'])
logger.info('Manager account successfully unlocked')

chirotonia = Contract(w3)
logger.info("Deploying Chirotonia contract")
tx_receipt = chirotonia.deploy(chirotonia_conf["identityManager"])
chirotonia_conf["mainContract"] = tx_receipt.contractAddress
logger.info("Deployed contract at %s", tx_receipt.contractAddress)
logger.info("Gas spent %d", tx_receipt.gasUsed)

if "votes" not in chirotonia_conf:
    logger.warning("No votations have been found. Add manually one to register voters")
    exit(0)

logger.info("Creating votes")
for vote in chirotonia_conf["votes"]:
    try:
        if "name" not in vote:
            logger.warning("Vote skipped due to missing name")
            continue
        if "subject" not in vote:
            logger.warning("Vote %s skipped due to missing subject")
            continue
        tx_rcpt = chirotonia.create_vote(vote["name"], vote["subject"], sync=True)
        logger.info("Gas spent %d", tx_rcpt.gasUsed)
        logger.info("Created vote %s, adding choices...", vote["name"])
        txs = []
        for i, choice in enumerate(vote["choices"]):
            txs.append(chirotonia.set_choice(vote["name"], i+1, choice))
        for tx in txs:
            tx_rcpt = chirotonia.wait(tx)
            logger.info("Gas spent %d", tx_rcpt.gasUsed)
        logger.info("Choices added")
    except Exception as error:
        logger.error(error)

with open("./runs/%s.json" % session_name, "w") as session_file:
    json.dump(chirotonia_conf, session_file, indent=4)
    logger.info("Session configuration written at ./runs/%s.json", session_name)  