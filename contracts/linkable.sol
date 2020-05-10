pragma solidity ^0.5.0;

import "./lib/UAOSRing.sol";

contract Linkable {
    
    function verify(
        uint256[] memory pubkeys,
        uint256[] memory tag,
        uint256[] memory tees,
        uint256 seed,
        uint256 message
    ) public view returns (bool) {
        bytes32 hashAcc = keccak256(abi.encodePacked(pubkeys[0]));
        for (uint i=1; i<pubkeys.length/2; i++) {
            hashAcc = keccak256(abi.encodePacked(hashAcc, pubkeys[i*2]));
        }
        return UAOSRing.Verify(uint256(hashAcc), message, tag, tees, seed, pubkeys );
    }
}