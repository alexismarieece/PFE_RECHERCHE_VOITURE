import csv
import networkx as nx
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import numpy as np
import os

header = ["map_name",
          "nodes_number", 
          "edges_number",
          "oneway_edges_number", 
          "twoway_edges_number", 
          "edges_without_speed_number", 
          "edges_with_speed_number", 
          "max_speed", 
          "min_speed", 
          "average_speed"]

csv_info = []


def export_to_csv(name, option = 'none'):
    Node_list = []
    for node in G.nodes():
        Node_list.append([node, G.nodes[node]['pos'][0], G.nodes[node]['pos'][1]])

    Edge_list = []
    for edge in G.edges():
        Edge_list.append([edge[0], edge[1], G[edge[0]][edge[1]]['speed'], G[edge[0]][edge[1]]['type'], G[edge[0]][edge[1]]['length']])

        # Ajouter les arêtes dans les deux sens si elles sont à double sens
        if option == 'oriented':
            if G[edge[0]][edge[1]]['type'] == 'twoway':
                Edge_list.append([edge[1], edge[0], G[edge[0]][edge[1]]['speed'], G[edge[0]][edge[1]]['type'], G[edge[0]][edge[1]]['length']])
    
    # Convertir la liste en dataframe
    import pandas as pd
    df = pd.DataFrame(Node_list)
    df.columns = ['node_id', 'lon', 'lat']
    df.to_csv('./Sources/map/' + name + '_node_list.csv', index=False)

    df = pd.DataFrame(Edge_list)
    df.columns = ['node_id1', 'node_id2', 'speed', 'type', 'length']
    df.to_csv('./Sources/map/' + name + '_edge_list.csv', index=False)
    
    print(name + ' exported\n')

# pour chaque fichier dans le dossier map :
for file in os.listdir("./Parsing_graph/map"):

    # Charger le fichier OSM
    tree = ET.parse("./Parsing_graph/map/" + file)
    root = tree.getroot()

    # Créer un graphe dirigé avec networkx
    G = nx.DiGraph()
    print(f"Name: {file}" + "  " + str(len(csv_info)+1) + " out of " + str(len(os.listdir("./Parsing_graph/map"))))
    print(f"Number of nodes before parsing: {len(root.findall('.//node'))}")

    # valeur par défaut de la vitesse
    DEFAULT_SPEED = "default"

    # Parcourir les nœuds du fichier OSM
    for node in root.findall(".//node"):
        node_id = node.get('id')
        lat = float(node.get('lat'))
        lon = float(node.get('lon'))
        G.add_node(node_id, pos=(lon, lat))

    # Parcourir les relations du fichier OSM
    for way in root.findall(".//way"):
        # Eliminer les ways qui ne sont pas des routes
        highway = way.find(".//tag[@k='highway']")
        if highway is None:
            continue
        
        # Eliminer les ways qui sont des footways
        if highway.get('v') == 'footway':
            continue
        
        # Vérifier si la relation (way) est à sens unique
        if way.find(".//tag[@k='oneway']") is not None:
            oneway = way.find(".//tag[@k='oneway']").get('v')
            if oneway == 'yes':
                edge_color = 'red'
                edge_type = 'oneway'
            else:
                edge_color = 'gray'
                edge_type = 'twoway'
        else:
            edge_color = 'gray'
            edge_type = 'twoway'
        
        # Ajouter la vitesse sur la voie
        speed_tag = way.find(".//tag[@k='maxspeed']")
        speed_value = speed_tag.get('v').split()[0] if speed_tag is not None and speed_tag.get('v').split()[0].isdigit() else DEFAULT_SPEED
        speed = int(speed_value) if speed_value.isdigit() else DEFAULT_SPEED
            
        way_id = way.get('id')
        nodes = [nd.get('ref') for nd in way.findall(".//nd")]
        G.add_edges_from(zip(nodes[:-1], nodes[1:]), id=way_id, color=edge_color, type=edge_type, speed=speed)

    # Retirer les noeuds isolés
    G.remove_nodes_from(list(nx.isolates(G)))

    # Calculer la longueur des routes
    for edge in G.edges():
        length = 0
        for i in range(len(edge)-1):
            lat1 = float(G.nodes[edge[i]]['pos'][1])
            lon1 = float(G.nodes[edge[i]]['pos'][0])
            lat2 = float(G.nodes[edge[i+1]]['pos'][1])
            lon2 = float(G.nodes[edge[i+1]]['pos'][0])
            # formule de haversine
            R = 6371e3
            phi1 = np.radians(lat1)
            phi2 = np.radians(lat2)
            delta_phi = np.radians(lat2-lat1)
            delta_lambda = np.radians(lon2-lon1)
            a = np.sin(delta_phi/2) * np.sin(delta_phi/2) + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda/2) * np.sin(delta_lambda/2)
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            length += R * c
        G[edge[0]][edge[1]]['length'] = length

    # Identifier les nœuds avec une route entrante et une route sortante
    nodes_to_remove = []
    for node in G.nodes():
        predecessors = list(G.predecessors(node))
        successors = list(G.successors(node))
        if len(predecessors) == 1 and len(successors) == 1:
            pred_edge_type = G[predecessors[0]][node]['type']
            succ_edge_type = G[node][successors[0]]['type']
            pred_edge_speed = G[predecessors[0]][node]['speed']
            succ_edge_speed = G[node][successors[0]]['speed']
            
            # Vérifier que la vitesse et le type de route sont les mêmes pour les deux arêtes
            if pred_edge_type == succ_edge_type and pred_edge_speed == succ_edge_speed:
                nodes_to_remove.append(node)

    # Supprimer les nœuds et ajouter les routes directes entre les voisins
    for node in nodes_to_remove:
        predecessors = list(G.predecessors(node))
        successors = list(G.successors(node))
        pred_edge_type = G[predecessors[0]][node]['type']
        pred_edge_color = G[predecessors[0]][node]['color']
        pred_edge_speed = G[predecessors[0]][node]['speed']
        pred_edge_length = G[predecessors[0]][node]['length']
        succ_edge_length = G[node][successors[0]]['length']
        G.remove_node(node)
        G.add_edge(predecessors[0], successors[0], type=pred_edge_type, color=pred_edge_color, speed=pred_edge_speed, length=pred_edge_length+succ_edge_length)

    # Supprimer les arrêtes qui bouclent sur elles-mêmes
    edges_to_remove = []
    for edge in G.edges():
        if edge[0] == edge[1]:
            edges_to_remove.append(edge)
    G.remove_edges_from(edges_to_remove)

    # Supprimer les noeuds qui n'ont pas de position
    nodes_without_position = [node for node in G.nodes() if 'pos' not in G.nodes[node]]
    G.remove_nodes_from(nodes_without_position)

    csv_info.append([file,
                    len(G.nodes()),
                    len(G.edges()),
                    len([edge for edge in G.edges() if G[edge[0]][edge[1]]['type'] == 'oneway']),
                    len([edge for edge in G.edges() if G[edge[0]][edge[1]]['type'] == 'twoway']),
                    len([edge for edge in G.edges() if not(str(G[edge[0]][edge[1]]['speed']).isdigit())]),
                    len([edge for edge in G.edges() if str(G[edge[0]][edge[1]]['speed']).isdigit()]),
                    max([G[edge[0]][edge[1]]['speed'] for edge in G.edges() if str(G[edge[0]][edge[1]]['speed']).isdigit()]),
                    min([G[edge[0]][edge[1]]['speed'] for edge in G.edges() if str(G[edge[0]][edge[1]]['speed']).isdigit()]),
                    sum([G[edge[0]][edge[1]]['speed'] for edge in G.edges() if str(G[edge[0]][edge[1]]['speed']).isdigit()]) / len([edge for edge in G.edges() if str(G[edge[0]][edge[1]]['speed']).isdigit()])])

    # Creer un fichier dans le dossier Sources ayant le nom du fichier OSM avec les deux csv Edge_list et Node_list
    export_to_csv(file, 'oriented')



# Ecrire les informations dans un fichier csv
with open('./Sources/graph_info.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(header)
    writer.writerows(csv_info)
