import json
import os

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../Chirotonia.bin')) as bytecode_file:
	bytecode = bytecode_file.read()

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../Chirotonia.abi')) as abi_file:
	abi = json.load(abi_file)