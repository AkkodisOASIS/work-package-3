import traci
import re

from .. import oasisPrototypeVars
from traci import constants as tc

class OasisNetworkVehicules:
    def __init__(self, _addThreadQueue):
        """
        Le point de départ(dépôt) est fix sur le cahier des charges
        """
        self.__vehiculesData = {}
        self.__listeCamions = {}
        self.__addThreadQueue = _addThreadQueue

        self.__stepLength = None

    def getVehiculesData(self) -> dict:
        """
        Retourne les données des véhicules présents dans la simulation à l'instant T

        Note:
            Renvoie un dictionnaire vide si aucun véhicule n'est présent ou si une erreur survient
            Les distances et positions sont formatées en chaîne avec deux décimales

        Returns:
            dict[str, dict]: Dictionnaire dont les clés sont les identifiants des véhicules::

                {
                    "0": {
                        "edgeID": "E16to09",
                        "laneID": "E16to09_0",
                        "lanePosition(m)": "173.51",
                        "distance(m)": "168.41",
                        "timeSimu(s)": 13.0,
                        "routes": ["E16to09", "E09to10", "E10to15", "E15to18",
                                "E18to29", "E19to20", "E20to02", "E02to03"]
                    }
                }
        
        Exemple d'utilisation:
            .. code-block:: python

                oasis.networkVehicules.getVehiculesData()
        """
        def _thread_fetch():
            vehiclesIDs = traci.vehicle.getIDList()
            for id in vehiclesIDs:
                edgeAndLaneID = traci.vehicle.getLaneID(vehID=id)
                self.__vehiculesData[id] = {
                    "edgeID": edgeAndLaneID[:edgeAndLaneID.find("_")],
                    "laneID": edgeAndLaneID,
                    "lanePosition(m)": f"{float(traci.vehicle.getLanePosition(vehID=id)):.2f}",
                    "distance(m)": f"{float(traci.vehicle.getDistance(vehID=id)):.2f}",
                    "timeSimu(s)": traci.simulation.getTime(),
                    "routes": list(traci.vehicle.getRoute(vehID=id))
                }
            return self.__vehiculesData
        return self.__addThreadQueue(_thread_fetch)

    def getStatusVehiculeByID(self, vehID:str) -> bool:
        """
        Indique si un véhicule est présent (actif) dans la simulation SUMO

        Note:
            Renvoie True si l'identifiant du véhicule figure dans la liste des véhicules
            actifs fournie par TraCI, False sinon

        Args:
            vehID (str): Identifiant du véhicule à vérifier

        Returns:
            bool: True si le véhicule est présent dans la simulation, False sinon

        Exemple d'utilisation:
            .. code-block:: python

                oasis.networkVehicules.getStatusVehiculeByID(vehID="truck_1")
        """
        def _thread_fetch():
            return vehID in traci.vehicle.getIDList()
        return self.__addThreadQueue(_thread_fetch)

    def getCamionDataByID(self, vehID:str) -> list:
        """
        Retourne les informations suivantes pour un camion dans la simulation :
            - fuel : consommation de carburant total (en mg/s)
            - parking : identifiant du parking assigné au camion
            - parkingStatus : True si le camion est actuellement garé
        
        Les valeurs reflètent l'état du véhicule à l'instant T de la simulation.
        
        Args:
            vehID (str): Identifiant du camion

        Note: 
            Retourne une liste vide si le camion n'existe pas

        Returns:
            list: données d'un camion::

                {"fuel": 32222.0670, "parking": "pa_3", "parkingStatus": True}
        
        Exemple d'utilisation:
            .. code-block:: python

                oasis.networkVehicules.getCamionDataByID(vehID="truck_1")
        """
        if self.__listeCamions == {}:
            return {}
        else:
            return self.__listeCamions[vehID]

    def addCamion(self, vehID:str, parkingID:str, typeID:str="truck", depart:str="now", trip:dict[str, float] | None = None):
        """
        Ajoute un camion à la simulation SUMO et configure sa route et ses arrêts

        Args:
            vehID (str): Identifiant du camion à créer

            parkingID (str): Identifiant de la zone de parking où le camion doit s'arrêter à la fin

            typeID (str, optional): Type de véhicule SUMO, par défaut "truck"

            depart (str, optional): Moment de départ, par défaut "now"

            trip (dict | None, optional): Structure des edges et arrêts
        Exemple d'utilisation:
            .. code-block:: python

                TRIP = {
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
                oasis.networkVehicules.addCamion(vehID="truck_1", 
                                                edgesAndStops=TRIP, 
                                                parkingID="pa_1")
        """
        def _thread_fetch():
            try:
                edgesIDs = [list(trip.keys())[0]]
                traci.vehicle.add(vehID=vehID, routeID="", typeID=typeID, depart=depart)
                traci.vehicle.setRoute(vehID=vehID, edgeList=edgesIDs)

                self.__listeCamions[vehID] = {"fuel": 0.0, "parking": parkingID, "parkingStatus": False}

                for edgeID, containerID in trip.items():
                    if edgeID not in edgesIDs:
                        edgesIDs.append(edgeID)
                    traci.vehicle.setRoute(vehID=vehID, edgeList=edgesIDs)
                    for container in containerID:
                        traci.vehicle.setStop(vehID=vehID, edgeID=edgeID, pos=container["pos"], duration=container["duration"])
                traci.vehicle.setParkingAreaStop(vehID=vehID, stopID=parkingID, until=1)

                traci.vehicle.subscribe(vehID, [tc.VAR_FUELCONSUMPTION])

                if self.__stepLength is None:
                    self.__stepLength = traci.simulation.getDeltaT()
            except Exception as e:
                raise e
        return self.__addThreadQueue(_thread_fetch)

    def getTempsDeTrajetCamion(self, vehID:str) -> str:
        """
        Retourne le temps de trajet total d'un camion depuis son démarrage

        Note:
            Valeur disponible uniquement lorsque le camion se gare au dépôt
            Renvoie "0" si le camion est encore en trajet ou s'il n'est pas présent dans la simulation

        Args:
            vehID (str): Identifiant du camion

        Returns:
            str: Temps de trajet sous forme de chaîne::

                "123.45"
                "0" si indisponible
        
        Exemple d'utilisation:
            .. code-block:: python

                oasis.networkVehicules.getTempsDeTrajet(vehID="truck_1")
        """
        def _thread_fetch():
            stopData = re.search(r"arrival\s*=\s*([^,)\]]+)", str(traci.vehicle.getStops(vehID=vehID)))
            if stopData is None:
                return "0"
            else:
                return stopData.group(1).strip().strip("'\"")
        return self.__addThreadQueue(_thread_fetch)
    
    def getDistanceParcourue(self, vehID:str):
        """
        Retourne la distance parcourue par un véhicule depuis son démarrage

        Note:
            Valeur renvoyée uniquement si le véhicule est présent dans la simulation
            Renvoie 0.0 si le véhicule est absent ou si la distance n'est pas disponible

        Args:
            vehID (str): Identifiant du véhicule

        Returns:
            float: Distance parcourue en mètres, 0.0 si indisponible
        
        Exemple d'utilisation:
            .. code-block:: python

                oasis.networkVehicules.getDistanceParcourue(vehID="truck_1")
        """
        def _thread_fetch():
            return traci.vehicle.getDistance(vehID=vehID)
        return self.__addThreadQueue(_thread_fetch)

    def updateCamionFuel(self):
        """
        Met à jour et vérifie si chaque camion de la simulation est toujours actif ou non (dans un parking ou non)
        """
        if self.__listeCamions != {}:
            self.__updateConsommationCarburantVehicule()
            self.__checkParking()
            for id in self.__listeCamions.keys():
                self.__getConsommationCarburantVehicule(vehID=id)

    def __updateConsommationCarburantVehicule(self):
        """
        Met à jour la consommation des camions présent dans la simulation
        """
        if self.__listeCamions != {}:
            for id, fuel in self.__listeCamions.items():
                if self.__listeCamions[id]["parkingStatus"] == False:
                    fuel = self.__getConsommationCarburantVehicule(vehID=id)
                    if fuel != 0.0 and fuel > 0.0:
                        self.__listeCamions[id]["fuel"] = self.__listeCamions[id]["fuel"] + fuel

    def __checkParking(self):
        """
        Vérifie chaque parking présent dans la simulation en cours si des camions sont présents

        Returns:
            float: Distance parcourue en mètres, 0.0 si indisponible
        """
        for parkingID in oasisPrototypeVars._listeParkings:
            listeVehiculesInParking = traci.parkingarea.getSubscriptionResults(parkingID).get(tc.VAR_STOP_STARTING_VEHICLES_IDS)
            for id in listeVehiculesInParking:
                if id in self.__listeCamions:
                    self.__listeCamions[id]["parkingStatus"] = True

    def __getConsommationCarburantVehicule(self, vehID:str):
        """
        Retourne la consommation de carburant en mg/s depuis le dernier step 

        Args:
            vehID (str): Identifiant du véhicule

        Returns:
            double: Consommation en mg/s de la dernière étape
        """
        return traci.vehicle.getSubscriptionResults(objectID=vehID).get(tc.VAR_FUELCONSUMPTION) * self.__stepLength