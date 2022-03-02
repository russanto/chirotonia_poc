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
        string[] voti;
        mapping(uint256 => bool) votiAccettati;
    }
    
    mapping(string => Votazione) public votazioni;
    mapping(uint256 => Votante) public votanti;
    
    address public manager;
    address public identityManager;
    
    address public privacyManager;

    string encryptionKey;
    
    modifier onlyManager {
        require(msg.sender == manager);
        _;
    }
    
    modifier onlyIdentityManager {
        require(msg.sender == identityManager);
        _;
    }
    
    modifier onlyPrivacyManager {
        require(msg.sender == privacyManager);
        _;
    }
    
    constructor(address _identityManager) public {
        manager = msg.sender;
        identityManager = _identityManager;
    }
    
    /**
        Crea una nuova votazione
     */
    function nuovaVotazione(string calldata _identificativo, string calldata _quesito) external onlyManager {
        Votazione storage votazione = votazioni[_identificativo];
        require(votazione.stato == StatoVotazione.Chiusa, "Votazione già esistente");
        votazione.stato = StatoVotazione.Registrazione;
        votazione.quesito = _quesito;
        emit VotazioneCreata(_identificativo);
    }

    /**
        Imposta le scelte del quesito di una data votazione
     */
    function impostaScelta(string calldata _identificativo, string calldata _scelta, byte _codice) external onlyManager {
        Votazione storage votazione = votazioni[_identificativo];
        require(votazione.stato == StatoVotazione.Registrazione, "Registrazione scelte chiusa");
        votazione.scelte[_codice] = _scelta;
    }
    
    /**
        Funzione di accreditamento del votante da parte dell'identity manager.
        Il votante può essere accreditato per più votazioni. I suoi dati vengono salvati solo una volta.
     */
    function accreditaVotante(
        string calldata informazioni,
        uint256 _chiave_x,
        uint256 _chiave_y,
        string calldata _identificativoVotazione
    ) external onlyIdentityManager {
        Votazione storage votazione = votazioni[_identificativoVotazione];
        // Verifica che la votazione sia in fase di registrazione
        require(votazione.stato == StatoVotazione.Registrazione, "Registrazione votanti chiusa");
        // Verifica che il votante non si sia già registrato per la votazione specificata
        require(!votazione.votanteAccreditato[_chiave_x], "Votante già accreditato");
        // Se il votante si accredita per la prima volta ne salva le informazioni
        if (votanti[_chiave_x].chiaveX != _chiave_x) {
            votanti[_chiave_x] = Votante(informazioni, _chiave_x, _chiave_y);
        }
        // Calcola l'hash cumulativo delle chiavi pubbliche
        if (votazione.votanti.length == 0) {
            votazione.pkHashAccumulator = keccak256(abi.encodePacked(_chiave_x));
        } else {
            votazione.pkHashAccumulator = keccak256(abi.encodePacked(votazione.pkHashAccumulator, _chiave_x));
        }
        // Aggiunge il votante alla votazione specificata
        votazione.votanti.push(_chiave_x);
        // Segna il votante come accreditato
        votazione.votanteAccreditato[_chiave_x] = true;
        emit VotanteAccreditato(_identificativoVotazione, _chiave_x);
    }
    
    /**
        Verifica che un votante sia stato correttamente accreditato per una votazione
     */
    function verificaVotante(
        uint256 _chiave_x,
        string calldata _identificativoVotazione
    ) external view returns (bool) {
        return votazioni[_identificativoVotazione].votanteAccreditato[_chiave_x];
    }
    
    /**
        Recupera la lista delle ascisse delle chiavi pubbliche dei votanti
     */
    function ottieniVotanti(string calldata _identificativoVotazione) external view returns (uint256[] memory) {
        return votazioni[_identificativoVotazione].votanti;
    }
    
    /**
        Avvia una votazione ponendola in stato di Voto
     */
    function avviaVotazione(string calldata _identificativoVotazione) external onlyManager {
        Votazione storage votazione = votazioni[_identificativoVotazione];
        // Verifica che lo stato di partenza sia quello di registrazione
        require(votazione.stato == StatoVotazione.Registrazione, "Votazione già avviata");
        // Verifica che la votazione abbia almento un votante
        require(votazione.votanti.length > 0, "Nessun votante accreditato per la votazione selezionata");
        // Effettua il cambio di stato
        votazione.stato = StatoVotazione.Voto;
        emit VotazioneAvviata(_identificativoVotazione);
    }
    
    /**
        Funzione di voto
     */
    function vota(
        uint256[2] calldata tag,
        uint256[] calldata tees,
        uint256 seed,
        uint256 voteHash,
        string calldata voto,
        string calldata _identificativoVotazione
    ) external {
        Votazione storage votazione = votazioni[_identificativoVotazione];
        // La votazione deve essere in stato di Voto
        require(votazione.stato == StatoVotazione.Voto, "Il voto non è aperto");
        // La firma ad anello, per essere valida, deve essere lunga quanto i votanti
        require(tees.length == votazione.votanti.length, "L'elenco dei firmatari non corrisponde");
        // Verifica che il voto non sia stato già espresso
        require(!votazione.votiAccettati[tag[0]], "Voto già espresso");
        // Verifica la correttezza della firma ad anello
        require(verifyRingSignature(voteHash, tag, tees, seed, _identificativoVotazione), "Firma non valida");
        // Aggiunge il voto a quelli accettati
        votazione.voti.push(voto);
        // Segna il votante come già votato
        votazione.votiAccettati[tag[0]] = true;
    }
    
    function verificaTag(
        string calldata _identificativoVotazione,
        uint256 _xTag
    ) external view returns (bool) {
        return votazioni[_identificativoVotazione].votiAccettati[_xTag];
    }

    /**
        Chiude la votazione ponendo lo stato in Scrutinio
     */
    function chiudiVotazione(string calldata _identificativoVotazione) external onlyManager {
        Votazione storage votazione = votazioni[_identificativoVotazione];
        require(votazione.stato == StatoVotazione.Voto, "Non è possibile chiudere una votazione non aperta");
        votazione.stato = StatoVotazione.Scrutinio;
    }
    
    /**
        Recupera l'i-esimo voto per una data votazione
     */
    function getVoto(string calldata _identificativoVotazione, uint256 index) external view returns (string memory) {
        return votazioni[_identificativoVotazione].voti[index];
    }

    /**
        Mostra il numero di voti salvati per una data votazione
     */
    function getNumeroVotiAcquisiti(string calldata _identificativoVotazione) external view returns (uint256) {
        return votazioni[_identificativoVotazione].voti.length;
    }
    
    /**
        Imposta l'indirizzo del Privacy Manager per la crittazione dei voti
     */
    function setPrivacyManager(address _privacyManager) external onlyManager {
        privacyManager = _privacyManager;
    }
    
    /**
        Imposta l'indirizzo del Privacy Manager per la crittazione dei voti
     */
    function setEncryptionKey(string calldata _encryptionKey) external onlyPrivacyManager {
        encryptionKey = _encryptionKey;
    }

    /**
        Funzione di verifica della firma ad anello collegabile
     */
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
    
    /**
        Funzione di supporto per la verifica della firma ad anello collegabile
     */
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