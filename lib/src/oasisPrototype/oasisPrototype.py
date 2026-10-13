import traci
import threading, queue

from traci import constants as tc
from . import oasisPrototypeVars
from .network.oasisNetwork import *
from .network.oasisNetworkVehicules import *


class OasisPrototype:
    """
        Args:
            sumoBin: Chemin absolu vers le binaire SUMO ou alias exécutable (par exemple "sumo-gui" ou "sumo")

            sumoCfg: Chemin vers le fichier de configuration réseau "<nom>.sumocfg", utilisé comme point d’entrée de la simulation SUMO
            
            sumoContainers : Chemin vers le fichier contenant les containers de la simulation "<nom>.add.xml"

            sumoParkings : Chemin vers le fichier contenant les parkings de la simulation "<nom>.add.xml"

            sumoNet : Chemin vers le fichier de la modélisation du réseau SUMO "<nom>.net.xml"

            delay: Délai en millisecondes appliqué entre chaque step de simulation, permettant de ralentir ou synchroniser l’exécution
        
        Exemple d'utilisation:
            .. code-block:: python

                from oasisPrototype import OasisPrototype
                oasis = OasisPrototype(sumoCfg="./sumo/prototype.sumocfg",
                                        sumoContainers="./sumo/additional/containers.add.xml",
                                        sumoParkings="./sumo/additional/parkings.add.xml",
                                        sumoNet="./sumo/réseau_prototype.net.xml")
                oasis.runOasis() # pour lancer la simulation dans un thread
    """
    
    network:OasisNetwork
    networkVehicules:OasisNetworkVehicules

    def __init__(self, sumoBin:str="sumo-gui", sumoCfg:str="prototype.sumocfg", sumoContainers:str="containers.add.xml", 
                 sumoParkings:str="parkings.add.xml", sumoNet:str="network.net.xml", delay:str="50"):

        self.__dev_mode = False
        self.__simuStatus = False

        self.__thread = None
        self.__thread_local = threading.local()
        self.__queue = queue.Queue()

        self.network = OasisNetwork(_addThreadQueue=self._addThreadQueue, sumoNet=sumoNet, sumoContainers=sumoContainers, sumoParkings=sumoParkings)
        self.networkVehicules = OasisNetworkVehicules(_addThreadQueue=self._addThreadQueue)

        self.__sumoArgs = [
                    sumoBin, 
                    "-c", 
                    sumoCfg,
                    "--start",
                    "--quit-on-end",
                    "--delay", delay
                ]

    def runOasis(self):
        """
        Lance la simulation SUMO dans un thread séparé en utilisant TraCI

        Note:
            En mode développement (devMode=True), la simulation est lancée directement dans le thread courant (appel bloquant)
            En mode production, la simulation est lancée dans un thread dédié
        """
        if self.__dev_mode:
            self.__runSimulation()
        else:
            self.__simuStatus = True
            self.__thread = threading.Thread(
                target=self.__runSimulation,
                name="__runSimulation",
                daemon=False
            )
            self.__thread.start()

    def _addThreadQueue(self, fonction, *args, **kwargs):
        """
        Ajoute un appel de méthode à la file d'exécution du thread de simulation

        Note:
            En mode développement (devMode=True), exécution synchrone dans le thread courant
            En production, la tâche est placée dans la queue du worker de simulation et l'appelant attend le résultat (avec timeout)
            Si l'appel provient du thread worker lui-même, la fonction est exécutée directement pour éviter un deadlock

        Args:
            fonction (callable): Fonction à exécuter dans le contexte du worker
            *args: Arguments positionnels transmis à la fonction
            **kwargs: Arguments nommés transmis à la fonction

        Returns:
            object: Valeur renvoyée par la fonction exécutée

        Raises:
            RuntimeError: Si aucune simulation n'est en cours
            TimeoutError: Si l'attente du résultat dépasse le délai configuré
            Exception: Toute exception levée par la fonction est propagée
        """
        if self.__dev_mode:
            try:
                return fonction(*args, **kwargs)
            except Exception as e:
                raise e

        if not self.__simuStatus or not self.__thread.is_alive():
            raise RuntimeError("Aucune simulation en cours")

        if getattr(self.__thread_local, "in_worker", False):
            return fonction(*args, **kwargs)

        res_holder = {}
        res_event = threading.Event()

        self.__queue.put((fonction, args, kwargs, res_event, res_holder))
        res_event.wait(timeout=5)
        
        if 'error' in res_holder:
            raise res_holder['error']
        return res_holder.get('value')

    def __runMethodeQueue(self):
        """
        Exécute les appels de méthode placés dans la file du thread worker

        Note:
            Récupère les tâches depuis la queue et les exécute dans le contexte du thread worker

            Marque l'attribut thread-local in_worker à True pendant l'exécution pour
            éviter les deadlocks si une tâche appelle à son tour des méthodes qui utilisent la même queue

            Utilise task_done() pour indiquer que la tâche est traitée

            Le worker continue de tourner tant que la simulation est active ou que la
            queue contient des éléments et se termine proprement si la simulation est
            arrêtée et que la queue est vide
        """
        while not self.__queue.empty():
            fonction, args, kwargs, result_event, res = self.__queue.get()

            self.__thread_local.in_worker = True
            try:
                res['value'] = fonction(*args, **kwargs)
            except Exception as e:
                res['value'] = e
            finally:
                self.__thread_local.in_worker = False
                result_event.set()

    def __runSimulation(self):
        """
        Lance et pilote une simulation SUMO via TraCI dans le thread courant

        Note:
            Démarre SUMO avec les arguments fournis

            Initialise la simulation

            Exécute la boucle principale, traite la file de tâches internes puis avance
            d'un pas de simulation tant que la simulation est active et que la durée
            maximale n'est pas atteinte

            Assure la fermeture propre de la connexion TraCI et la mise à jour de l'état
            de la simulation même en cas d'erreur
        """
        traci.start(cmd=self.__sumoArgs, label="client_1")
        steps = 0
        try:
            self.__setupSimu()
            while self.__simuStatus:
                self.__runMethodeQueue()
                self.networkVehicules.updateCamionFuel()
                if steps >= 750:
                    break
                traci.simulationStep()
                steps+=1
        except Exception as e:
            print(e)
            traci.close()
        finally:
            traci.close()
            self.__simuStatus = False
            print("Fin de la simulation")

    def __setupSimu(self):
        """
        Configure l'environnement de la simulation SUMO via TraCI

        Note:
            Configure l'interface graphique (schéma de la vue) ainsi que les subscribes
        """
        try:
            traci.gui.setSchema("View #0", "real world")

            oasisPrototypeVars._listeParkings = list(self.network.getParkings())

            for parkingID in oasisPrototypeVars._listeParkings:
                traci.parkingarea.subscribe(parkingID, [tc.VAR_STOP_STARTING_VEHICLES_IDS])
        except Exception as e:
            print(e)