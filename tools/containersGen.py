import argparse
import random
import xml.etree.ElementTree as xmlET

from xml.dom import minidom

xmlET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')

def containersGen(sumoNetFile:str, destination:str) -> xmlET.Element:
        """
        Génère aléatoirement des containers pour un model SUMO à partir d'un réseau
        """
        rootContainer = xmlET.Element(
            "additional",
            {
                "{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation":
                "http://sumo.dlr.de/xsd/additional_file.xsd"
            }
        )

        rootNetwork = xmlET.parse(sumoNetFile).getroot()
        idContainer = 0

        for edge in rootNetwork.findall("edge"):
            if ":" not in edge.get("id"):
                lanes = list(edge) 
                for info in lanes:
                    id = edge.get("id")
                    pos = random.uniform(10, float(info.get("length")))
                    container = xmlET.SubElement(
                        rootContainer, 
                        "container",
                        attrib= {
                            "id": str(f"c_{idContainer}"), 
                            "depart":"0.00", 
                            "departPos":str(f"{pos:.2f}"), 
                            "color":"red"
                        }
                    )
                    xmlET.SubElement(
                        container,
                        "transport",
                        attrib={
                            "from": id,
                            "to": destination,
                            # "lines": "truck_1" # par défaut ANY
                        }
                    )
                    # xmlET.SubElement(
                    #     container, 
                    #     "stop",
                    #     attrib={
                    #         "edge":id, 
                    #         "endPos":str(f"{pos:.2f}"), 
                    #         "duration":"1000000000"
                    #     }
                    # )
                    idContainer += 1

        return rootContainer

def writeContainersFile(rootContainer:xmlET.Element, output:str):
    """
    Génère le fichier xml des containers
    """
    raw = xmlET.tostring(rootContainer, encoding='utf-8')
    dom = minidom.parseString(raw).toprettyxml(indent="    ")
    with open(f"{output + "/containers.add.xml"}", "w", encoding="utf-8") as f:
        f.write(dom)
            
def main():
    parser = argparse.ArgumentParser(description="Génère aléatoirement dans un fichier xml des containers pour un model SUMO à partir d'un réseau")
    parser.add_argument("input", help="Fichier xml (net.xml) du réseau SUMO contenant les edges et lanes")
    parser.add_argument("-d", "--destination", required=True, help="Destination de déchargement des containers")
    parser.add_argument("-o", "--output", required=True, help="Path de sortie du fichier xml générer contenant les containers 'containers.add.xml'")
    args = parser.parse_args()

    rootContainer = containersGen(args.input, args.destination)
    writeContainersFile(rootContainer=rootContainer, output=args.output)

if __name__ == "__main__":
    main()