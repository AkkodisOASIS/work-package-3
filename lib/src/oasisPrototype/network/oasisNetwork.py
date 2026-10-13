import traci
import xml.etree.ElementTree as xmlET

from .. import oasisPrototypeVars
from traci import constants as tc

class OasisNetwork:
    def __init__(self, _addThreadQueue, sumoNet:str, sumoContainers: str, sumoParkings: str):
        """
        Args:
            sumoContainers: Fichier .xml contenant un ou plusieurs containers
            sumoNet: Fichier .xml contenant la modélisation du réseau SUMO
        """
        self.__network = {"edges": {}}
        self.__containers = {}
        self.__containersPos = {}
        self.__junctions = []
        self.__lanes = []
        self.__parkings = []

        self.__sumoNetFile = sumoNet
        self.__sumoContainersFile = sumoContainers
        self.__sumoParkingsFile = sumoParkings

        self.__addThreadQueue = _addThreadQueue

    def getAllNetwork(self, offline:bool=True) -> dict:
        """
        Retourne un dictionnaire représentant le réseau complet de la simulation

        Args:
            offline (bool): run de la méthode hors simulation SUMO

        Note:
            Contient les junctions, edges, lanes et conteneurs connus au moment de l'appel
            Si un fichier de conteneurs est configuré mais non parsé, il est parsé automatiquement

        Returns:
            dict[str, dict]: Structure du réseau::
            
                {
                    "edges": {
                        "E21to18": {
                            "lane": "E21to18_0",
                            "junctions": {"from": "J21", "to": "J18"},
                            "containers": {...}
                        },
                        ...
                    }
                }

        Exemple d'utilisation:
            .. code-block:: python

                oasis.network.getAllNetwork()
        """
        def _thread_fetch():
            if self.__containers == {}:
                self.__parseXmlFileContainers()

            networkEdges = self.getEdges()
            for edge in networkEdges:
                self.__network["edges"][edge] = {
                                                "lane": (f"{edge}_0"), 
                                                "junctions" : {
                                                    "from": traci.edge.getFromJunction(edgeID=edge),
                                                    "to" : traci.edge.getToJunction(edgeID=edge)
                                                    },
                                                "containers" : self.__containers.get(edge, [])
                                                }
            return self.__network
        
        if offline:
            self.__checkFiles()
            return self.__network
        else:
            return self.__addThreadQueue(_thread_fetch)

    def getEdges(self, offline:bool=True) -> tuple:
        """
        Retourne les identifiants de tous les edges du réseau

        Args:
            offline (bool): run de la méthode hors simulation SUMO
        
        Note:
            Filtre la liste fournie par TraCI pour ne conserver que les edges
            respectant la convention de nommage utilisée (préfixe "E")

        Returns:
            tuple[str, ...]: Tuple d'identifiants d'edges::

                ("E21to18", "E10to5", ...)

            Tuple vide si aucune edge ne correspond ou en cas d'erreur

        Exemple d'utilisation:
            .. code-block:: python

                oasis.network.getEdges()
        """
        def _thread_fetch():
            idsNetworkEdges = traci.edge.getIDList()
            return tuple(idObject for idObject in idsNetworkEdges if idObject.startswith("E"))
        
        if offline:
            self.__checkFiles()
            return tuple(self.__network.get("edges").keys())
        else:
            return self.__addThreadQueue(_thread_fetch)
    
    def getJonctions(self, offline:bool=True) -> tuple:
        """
        Retourne les identifiants de toutes les junctions du réseau

        Args:
            offline (bool): run de la méthode hors simulation SUMO

        Note:
            Filtre la liste fournie par TraCI pour ne conserver que les junctions
            respectant la convention de nommage utilisée (préfixe "J")

        Returns:
            tuple[str, ...]: Tuple d'identifiants de junctions::

                ("J01", "J21", ...)

            Tuple vide si aucune junction ne correspond ou en cas d'erreur

        Exemple d'utilisation:
            .. code-block:: python

                oasis.network.getJonctions()
        """
        def _thread_fetch():
            idsNetworkJunctions = traci.junction.getIDList()
            return tuple(idObject for idObject in idsNetworkJunctions if idObject.startswith("J")) 
        
        if offline:
            self.__checkFiles()
            return tuple(self.__junctions)
        else:
            return self.__addThreadQueue(_thread_fetch)

    def getLanes(self, offline:bool=True) -> tuple:
        """
        Retourne les identifiants de toutes les lanes du réseau

        Args:
            offline (bool): run de la méthode hors simulation SUMO

        Note:
            Filtre la liste fournie par TraCI pour ne conserver que les lanes
            respectant la convention de nommage utilisée (préfixe "E")

            Convention de nommage des lanes : E21to18_0
            (le suffixe "_0" est généré automatiquement par SUMO)

        Returns:
            tuple[str, ...]: Tuple d'identifiants des lanes::

                ("E21to18_0", "E10to5_0", ...)

            Tuple vide si aucune lane ne correspond ou en cas d'erreur

        Exemple d'utilisation:
            .. code-block:: python

                oasis.network.getLanes()
        """
        def _thread_fetch():
            idsNetworkLanes = traci.lane.getIDList()
            return tuple(idObject for idObject in idsNetworkLanes if idObject.startswith("E"))

        if offline:
            self.__checkFiles()
            return tuple(self.__lanes)
        else:        
            return self.__addThreadQueue(_thread_fetch)

    def getContainers(self) -> dict:
        """
        Retourne les conteneurs de la simulation si le fichier XML a été fourni et parsé

        Note:
            Si l'attribut interne containers est vide et qu'un chemin de fichier XML
            est défini, le fichier est parsé puis les conteneurs sont renvoyés

            Si containers contient déjà des données, ces données sont renvoyées
            directement.

            Sinon, un dictionnaire d'information est renvoyé pour indiquer l'absence
            de conteneurs ou l'absence de fichier XML

        Returns:
            dict[str, dict] | dict: Dictionnaire des conteneurs indexé par identifiant::

                {
                    "c_1": {"id_edge": "E03to02"},
                    "c_10": {"id_edge": "E06to05"},
                    ...
                }

            Si aucun conteneur n'est disponible::

                {"info": "Aucun container existant ou fichier xml non transmis"}

        Exemple d'utilisation:
            .. code-block:: python

                oasis.network.getContainers()
        """
        self.__checkFiles()
        if self.__containers == {}:
            return {"info" : "Aucun containers existant ou fichier xml non transmis"}
        return self.__containers

    def getContainersByEdge(self) -> dict:
        """
        Retourne le(s) conteneur(s) présent dans chaque edge

        Returns:
            dict[str, dict]::

            {
                "E03to02": ["c_1"], 
                "E06to05": ["c_10", "c_11", "c_12", "c_13"],
                "E09to07": ["c_14", "c_15", "c_16"]
                ...
            }
        
        Exemple d'utilisation:
            .. code-block:: python

                oasis.network.getContainersByEdge()
        """
        self.__checkFiles()
        if self.__containers == {}:
            return {"info" : "Aucun containers existant ou fichier xml non transmis"}
        else:    
            containersByEdge = {}
            for containerId, edgeId in self.__containers.items():
                if edgeId["id_edge"] not in containersByEdge.keys():
                    containersByEdge[edgeId["id_edge"]] = [containerId]
                if edgeId["id_edge"] in containersByEdge:
                    if containerId not in containersByEdge[edgeId["id_edge"]]:
                        containersByEdge[edgeId["id_edge"]].append(containerId)
            return containersByEdge
        
    def getContainerById(self, containerID:str) -> dict:
        """
        Retourne les informations d'un container par son ID

        Args:
            containerID (str): id du container

        Returns:
            dict[str, str]::

            {"pos": "221.29", "edgeID" : "E06to05"}
        
        Exemple d'utilisation:
            .. code-block:: python

                oasis.network.getContainerById(containerID="c_12")
        """
        self.__checkFiles()
        if self.__containers == {}:
            return {"info" : "Aucun containers existant ou fichier xml non transmis"}
        else:    
            return {
                "pos" : self.__containersPos.get(containerID)["pos"],
                "edgeID" : self.__containers.get(containerID)["id_edge"]
            }

    def getParkings(self, offline:bool=True) -> tuple:
        """
        Retourne les IDs des parkings du réseau

        Args:
            offline (bool): run de la méthode hors simulation SUMO

        Returns:
            tuple[str, ...]: Tuple d'identifiants des parkings::

                ("pa_1", "pa_2", ...)
        """
        def _thread_fetch():
            return traci.parkingarea.getIDList()
        if offline:
            self.__checkFiles()
            if self.__parkings == []:
                return {"info" : "Aucun parkings existant ou fichier xml non transmis"}
            return tuple(self.__parkings)
        else:
            return self.__addThreadQueue(_thread_fetch)

    def createRide(self, edgesAndContainer: dict) -> dict:
        """
        Créer et retourne un json de trajet pour l'ajout d'un camion dans une simualtion SUMO

        Args:
            edgesAndContainer (dict): Structure des edges et id de containers

        Returns:
            tuple[str, dict]: json contenant les id des edges et position par container::    

                 {
                    "E07to06": [],
                    "E06to05": [
                        {
                            "pos": 403.97,
                            "duration": 3.00,
                        }
                    ],
                    "E05to21": [],
                    "E21to17": [],
                    "E17to06": [],
                    "E06to07": [],
                    "E07to08": []
                }
        
        Exemple d'utilisation:
            .. code-block:: python

                RIDE = {
                            "E07to06": [],
                            "E06to05": [
                                "c_11"
                            ],
                            "E05to21": [],
                            "E21to17": [],
                            "E17to06": [],
                            "E06to07": [],
                            "E07to08": []
                        }

                trip = oasis.network.createRide(edgesAndContainer=RIDE)
        """
        if self.__containers == {}:
            self.__parseXmlFileContainers()

        trajet = {}
        for edgeID, containerID in edgesAndContainer.items():
            if edgeID not in trajet:
                trajet[edgeID] = []
            for c_id in containerID:
                trajet[edgeID].append({"pos" : self.__containersPos.get(c_id)["pos"], "duration": "3.00"})

        return trajet

    def closeEdge(self, edgeID:str, classesDisallowed=list[str]):
        """
        Ferme un edge dans la simulation SUMO en interdisant une ou plusieurs classes de véhicules

        Args:
            edgeID (str): Identifiant de l'edge à fermer
            classesDisallowed (list[str]): Liste des classes de véhicules à interdire

        Exemple d'utilisation:
            .. code-block:: python

                oasis.network.closeEdge(edgeID="E06to05", classesDisallowed=["truck"])
        """
        def _thread_fetch():
            traci.edge.setDisallowed(edgeID=edgeID, disallowedClasses=classesDisallowed)
        return self.__addThreadQueue(_thread_fetch)


    def __checkFiles(self) -> None:
        """
        Vérifie si les fichiers XML ont été traités
        """
        if self.__parkings == []:
            self.__parseXmlFileParkings()
        if self.__containers == {}:
            self.__parseXmlFileContainers()
        if self.__network["edges"] == {}:
            self.__parseXmlFileNetwork()

    def __parseXmlFileNetwork(self) -> None:
        """
        Parse un fichier xml qui contient la modélisation du réseau SUMO et stock les informations
        """
        root = xmlET.parse(self.__sumoNetFile).getroot()

        for edge in root.findall("edge"):
            if ":" not in edge.get("id"):
                child = list(edge) 
                for lane in child:
                    self.__network["edges"][edge.get("id")] = {
                        "lane": lane.get("id"), 
                        "junctions" : {
                            "from": edge.get("from"),
                            "to" : edge.get("to")
                        },
                        "containers" : self.__containers.get(edge.get("id"), [])                       
                    }
                    self.__lanes.append(lane.get("id"))

        for junction in root.findall("junction"):
            if ":" not in junction.get("id"):
                self.__junctions.append(junction.get("id"))

    def __parseXmlFileContainers(self) -> None:
        """
        Parse un fichier xml qui contient des containers et stock les informations
        """
        root = xmlET.parse(self.__sumoContainersFile).getroot()

        for container in root.findall("container"):
            child = list(container) 
            for info in child:
                edgeId = info.get("from")
                containerId = container.get("id")
                if edgeId not in self.__containers:
                    self.__containers[containerId] = {"id_edge" : edgeId}
                    self.__containersPos[containerId] = {"pos" : container.get("departPos")}
                else:
                    self.__containers[containerId].append({"id_edge" : edgeId})
    
    def __parseXmlFileParkings(self) -> None:
        """
        Parse un fichier xml qui contient des parkings et stock les informations
        """
        root = xmlET.parse(self.__sumoParkingsFile).getroot()

        for parking in root.findall("parkingArea"):
            self.__parkings.append(parking.get("id"))