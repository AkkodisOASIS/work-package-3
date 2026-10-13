# Exemple minimaliste d'instance et de lancement d'une simulation

from oasisPrototype import OasisPrototype

oasis = OasisPrototype(sumoCfg="./sumo/prototype/prototype.sumocfg",
                        sumoNet="./sumo/prototype/network/network.net.xml",
                        sumoContainers="./sumo/prototype/additional/containers.add.xml",
                        sumoParkings="./sumo/prototype/additional/parkings.add.xml")

oasis.runOasis() # Pour lancer la simulation dans un thread

# Les méthodes suivantes fonctionnent sans que la simulation ait besoin d’être lancée :
oasis.network.getAllNetwork()
oasis.network.getEdges()
oasis.network.getJonctions()
oasis.network.getLanes()
oasis.network.getContainers()
oasis.network.getParkings()