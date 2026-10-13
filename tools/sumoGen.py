import argparse
import xml.etree.ElementTree as xmlET
import os
import subprocess

from xml.dom import minidom
from pathlib import Path

class sumoGen:
    def __init__(self, nameSumoFolder:str, pathTools:str, path:str):
        self.__nameFolderSumo = nameSumoFolder
        self.__path = path

        self.__pathTools = pathTools
        self.__netgenerateBin = "netgenerate"
        self.__sumoHome = os.getenv("SUMO_HOME")

        self.__destinationContainersID = None

    def createSumo(self):
        self.__createFolder()
        self.__createSumoCfg()
        self.__createNet()
        self.__createRoute()

        # Additional
        self.__createVtype()
        self.__createParkings()
        self.__createContainers()

    def __createSumoCfg(self):
        """
        Création du fichier de configuration SUMO (.sumocfg)
        """
        print("----- Création du fichier sumocfg.xml -----")
        rootCfg = xmlET.Element(
                "sumoConfiguration",
                {
                    "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation":
                    "http://sumo.dlr.de/xsd/sumoConfiguration.xsd"
                }
            )
        input = xmlET.SubElement(rootCfg, 'input')
        xmlET.SubElement(input, 'net-file', {'value': "network/network.net.xml"})
        xmlET.SubElement(input, 'route-files', {'value': "network/routes.rou.xml"})
        xmlET.SubElement(input, 'additional-files', {'value': "additional/vType.add.xml,additional/containers.add.xml,additional/parkings.add.xml"})
        
        time = xmlET.SubElement(rootCfg, 'time')
        xmlET.SubElement(time, 'begin', {'value': "0"})
        xmlET.SubElement(time, 'end', {'value': "750"})

        self.__writeXmlFile(root=rootCfg, output=f"{self.__path}/{self.__nameFolderSumo}/sumo.sumocfg")

    def __createNet(self):
        """
        Création du fichier du réseau modélisé SUMO (.net.xml)
        """
        print("----- Création du fichier network.net.xml -----")
        netgenerate = subprocess.Popen([self.__netgenerateBin,
                                        "--rand",
                                        "--output",
                                        f"{self.__path}/{self.__nameFolderSumo}/network/network.net.xml"], 
                                        stdout=subprocess.PIPE, text=True)
        
        for stdoutLine in netgenerate.stdout:
            print(stdoutLine, end="")
        netgenerate.wait()

    def __createRoute(self):
        """
        Création du fichier de traffic routier aléatoire SUMO (.rou.xml)
        """
        print("----- Création du fichier routes.rou.xml -----")   
        route = subprocess.Popen([f"{self.__sumoHome}/tools/randomTrips.py",
                                  "-n", f"{self.__path}/{self.__nameFolderSumo}/network/network.net.xml",
                                  "-r", f"{self.__path}/{self.__nameFolderSumo}/network/routes.rou.xml",
                                  "-e", "600",
                                  "-p", "4",
                                  "--min-distance", "100"],
                                  stdout=subprocess.PIPE, text=True)
        
        for stdoutLine in route.stdout:
            print(stdoutLine, end="")
        route.wait()

        try:
            os.remove("./trips.trips.xml")
        except FileNotFoundError:
            pass

    def __createContainers(self):
        """
        Création du fichier contenant les containers SUMO (containers.add.xml)
        """
        print("----- Création du fichier containers.add.xml -----")   
        containers = subprocess.Popen([f"python3", 
                                       f"{self.__pathTools}/containersGen.py",
                                       f"{self.__path}/{self.__nameFolderSumo}/network/network.net.xml",
                                       "-d", str(self.__destinationContainersID),
                                       "-o", f"{self.__path}/{self.__nameFolderSumo}/additional/"],
                                      stdout=subprocess.PIPE, text=True)

        for stdoutLine in containers.stdout:
            print(stdoutLine, end="")
        containers.wait()

    def __createParkings(self):
        """
        Création du fichier comportant les parkings SUMO (parkings.add.xml)
        """
        print("----- Création du fichier parkings.add.xml -----")   
        parkings = subprocess.Popen([f"{self.__sumoHome}/tools/generateParkingAreas.py",
                                     "-n", f"{self.__path}/{self.__nameFolderSumo}/network/network.net.xml",
                                     "-o", f"{self.__path}/{self.__nameFolderSumo}/additional/parkings.add.xml",
                                     "--min", "3",
                                     "--max", "3",],
                                     stdout=subprocess.PIPE, text=True)
        
        for stdoutLine in parkings.stdout:
            print(stdoutLine, end="")
        parkings.wait()

        self.__setXmlParkings()

    def __createVtype(self):
        """
        Création d'un type de class par défaut pour les camions SUMO (vtype.xml)
        """
        print("----- Création du fichier vtype.xml -----")
        rootVtype = xmlET.Element(
                "additional",
                {
                    "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation":
                    "http://sumo.dlr.de/xsd/additional_file.xsd"
                }
            )
        xmlET.SubElement(rootVtype, 'vType', {"id": "truck", "length": "8.00", "maxSpeed": "13.90", "guiShape": "truck", "color": "green", "containerCapacity": "5", "loadingDuration": "1.00"})
        self.__writeXmlFile(root=rootVtype, output=f"{self.__path}/{self.__nameFolderSumo}/additional/vType.add.xml")

    def __createFolder(self):
        """
        Création du dossier pour la simulation SUMO
        """
        print("----- Création du dossier SUMO -----")
        network = Path(f"{self.__path}/{self.__nameFolderSumo}/network")
        additional = Path(f"{self.__path}/{self.__nameFolderSumo}/additional")
        
        network.mkdir(parents=True, exist_ok=True)
        additional.mkdir(parents=False, exist_ok=True)

    def __setXmlParkings(self) -> str:
        """
        Conserver un seul élément <parkingArea> dans le fichier additional (supprime les autres)
        """
        rootParkings = xmlET.parse(f"{self.__path}/{self.__nameFolderSumo}/additional/parkings.add.xml").getroot()
        keepParkingID = rootParkings.findall("parkingArea")[0].get("id")
        keepParkingLaneID = rootParkings.findall("parkingArea")[0].get("lane")

        for parking in rootParkings.findall("parkingArea"):
            if parking.get("id") != keepParkingID:
                rootParkings.remove(parking)

        self.__writeXmlFile(root=rootParkings, output=f"{self.__path}/{self.__nameFolderSumo}/additional/parkings.add.xml")
        
        self.__destinationContainersID = keepParkingLaneID.split("_", 1)[0]
    
    def __writeXmlFile(self, root:xmlET.Element, output:str):
        """
        Génère un fichier xml
        """
        raw = xmlET.tostring(root, encoding='utf-8')
        dom = minidom.parseString(raw).toprettyxml(indent="    ")
        with open(f"{output}", "w", encoding="utf-8") as f:
            f.write(dom)

def main():
    parser = argparse.ArgumentParser(description="Génère une modélisation SUMO complète", 
        epilog=(
            "Exemples d'utilisation :\n"
            "  python3 sumoGen.py --name sumo --pathTools '.' -o .\n"
            "  python3 sumoGen.py --name sumo --pathTools '/home/<dossier_git>/<dossier_tools>' -o /tmp/\n"
    ),formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-n", "--name", required=True, type=str, help="nom de la modélisation (nom du dossier)")
    parser.add_argument("-pt", "--pathTools", required=True, type=str, help="Chemin vers le dossier contenant les scripts python, ex : containersGen.py")
    parser.add_argument("-o", "--output", required=True, type=str, help="Chemin de sortie pour le dossier contenant la modélisation SUMO")
    args = parser.parse_args()

    sumo = sumoGen(nameSumoFolder=args.name, path=str(Path(args.output).expanduser()), pathTools=str(Path(args.pathTools).expanduser()))
    sumo.createSumo()

if __name__ == "__main__":
    main()