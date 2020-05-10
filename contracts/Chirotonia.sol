pragma solidity ^0.5.0;

import "./lib/Curve.sol";

contract Chirotonia {
    
    event VotazioneCreata(string identificativo);
    event VotazioneAvviata(string identificativo);
    event VotazioneScrutinata(string identificativo);
    event VotazioneArchiviata(string identificativo);
    event VotanteAccreditato(string identificativoVotazione, uint256 chiaveX);
    
    
    using Curve for Curve.G1Point;
    
    struct Votante {
        string informazioni;
        uint256 chiaveX;
        uint256 chiaveY;
    }
    
    enum StatoVotazione { Chiusa, Registrazione, Voto, Scrutinio, Archiviata }
    
    struct Votazione {
        string quesito;
        mapping(byte => string) scelte;
        bytes32 pkHashAccumulator;
        uint256[] votanti;
        mapping(uint256 => bool) votanteAccreditato;
        StatoVotazione stato;
        uint256[] voti;
        mapping(uint256 => bool) votiAccettati;
    }
    
    mapping(string => Votazione) public votazioni;
    mapping(uint256 => Votante) public votanti;
    
    address public manager;
    address public identityManager;
    
    address public privacyManager;
    
    modifier onlyManager {
        require(msg.sender == manager);
        _;
    }
    
    modifier onlyIdentityManager {
        require(msg.sender == identityManager);
        _;
    }
    
    constructor(address _identityManager) public {
        manager = msg.sender;
        identityManager = _identityManager;
    }
    
    function nuovaVotazione(string calldata _identificativo, string calldata _quesito) external onlyManager {
        Votazione storage votazione = votazioni[_identificativo];
        require(votazione.stato == StatoVotazione.Chiusa, "Votazione già esistente");
        votazione.stato = StatoVotazione.Registrazione;
        votazione.quesito = _quesito;
        emit VotazioneCreata(_identificativo);
    }

    function impostaScelta(string calldata _identificativo, string calldata _scelta, byte _codice) external onlyManager {
        Votazione storage votazione = votazioni[_identificativo];
        require(votazione.stato == StatoVotazione.Registrazione, "Registrazione scelte chiusa");
        votazione.scelte[_codice] = _scelta;
    }
    
    function accreditaVotante(
        string calldata informazioni,
        uint256 _chiave_x,
        uint256 _chiave_y,
        string calldata _identificativoVotazione
    ) external onlyIdentityManager {
        Votazione storage votazione = votazioni[_identificativoVotazione];
        require(votazione.stato == StatoVotazione.Registrazione, "Registrazione votanti chiusa");
        require(!votazione.votanteAccreditato[_chiave_x], "Votante già accreditato");
        if (votanti[_chiave_x].chiaveX != _chiave_x) {
            votanti[_chiave_x] = Votante(informazioni, _chiave_x, _chiave_y);
        }
        if (votazione.votanti.length == 0) {
            votazione.pkHashAccumulator = keccak256(abi.encodePacked(_chiave_x));
        } else {
            votazione.pkHashAccumulator = keccak256(abi.encodePacked(votazione.pkHashAccumulator, _chiave_x));
        }
        votazione.votanti.push(_chiave_x);
        votazione.votanteAccreditato[_chiave_x] = true;
        emit VotanteAccreditato(_identificativoVotazione, _chiave_x);
    }
    
    function verificaVotante(
        uint256 _chiave_x,
        string calldata _identificativoVotazione
    ) external view returns (bool) {
        return votazioni[_identificativoVotazione].votanteAccreditato[_chiave_x];
    }
    
    function ottieniVotanti(string calldata _identificativoVotazione) external view returns (uint256[] memory) {
        return votazioni[_identificativoVotazione].votanti;
    }
    
    function avviaVotazione(string calldata _identificativoVotazione) external onlyManager {
        Votazione storage votazione = votazioni[_identificativoVotazione];
        require(votazione.stato == StatoVotazione.Registrazione, "Votazione già avviata");
        require(votazione.votanti.length > 0, "Nessun votante accreditato per la votazione selezionata");
        votazione.stato = StatoVotazione.Voto;
        emit VotazioneAvviata(_identificativoVotazione);
    }
    
    function vota(
        uint256[2] calldata tag,
        uint256[] calldata tees,
        uint256 seed,
        uint256 voto,
        string calldata _identificativoVotazione
    ) external {
        Votazione storage votazione = votazioni[_identificativoVotazione];
        require(votazione.stato == StatoVotazione.Voto, "Il voto non è aperto");
        require(tees.length == votazione.votanti.length, "L'elenco dei firmatari non corrisponde");
        require(!votazione.votiAccettati[tag[0]], "Voto già espresso");
        require(verifyRingSignature(voto, tag, tees, seed, _identificativoVotazione), "Firma non valida");
        votazione.voti.push(voto);
        votazione.votiAccettati[tag[0]] = true;
    }

    function chiudiVotazione(string calldata _identificativoVotazione) external onlyManager {
        Votazione storage votazione = votazioni[_identificativoVotazione];
        require(votazione.stato == StatoVotazione.Voto, "Non è possibile chiudere una votazione non aperta");
        votazione.stato = StatoVotazione.Scrutinio;
    }
    
    function getVoti(string calldata _identificativoVotazione) external view returns (uint256[] memory) {
        return votazioni[_identificativoVotazione].voti;
    }
    
    function setPrivacyManager(address _privacyManager) external onlyManager {
        privacyManager = _privacyManager;
    }

	function verifyRingSignature(
	    uint256 voteData,
	    uint256[2] memory tag,
	    uint256[] memory tees,
	    uint256 seed,
	    string memory _identificativoVotazione
	) public view returns (bool) {
	    Votazione storage votazione = votazioni[_identificativoVotazione];
		Curve.G1Point memory L = Curve.HashToPoint(uint256(votazione.pkHashAccumulator));
		Curve.G1Point memory M = Curve.HashToPoint(voteData);
		Curve.G1Point memory T = Curve.G1Point(tag[0], tag[1]);
		uint256 h = uint256(keccak256(abi.encodePacked(M.X, M.Y, T.X, T.Y)));

		uint256 c = seed;
		for( uint256 i = 0; i < votazione.votanti.length; i++ )
		{
			c = uint256(keccak256(abi.encodePacked(
					h,
					RingLink(
						Curve.G1Point(votazione.votanti[i], votanti[votazione.votanti[i]].chiaveY),
						L,
						T,
						tees[i],
						c
					))));
		}
		return c == seed;
	}
    
    function RingLink(
	    Curve.G1Point memory Y,
	    Curve.G1Point memory M,
	    Curve.G1Point memory tagpoint,
	    uint256 s,
	    uint256 c
	) internal view returns (uint256) {
		Curve.G1Point memory a = Curve.g1add(Curve.g1mul(Curve.P1(), s), Curve.g1mul(Y, c));
		Curve.G1Point memory b = Curve.g1add(Curve.g1mul(M, s), Curve.g1mul(tagpoint, c));

		return uint256(keccak256(abi.encodePacked(
			tagpoint.X, tagpoint.Y,
			a.X, a.Y,
			b.X, b.Y
		)));
	}
}