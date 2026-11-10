#!/usr/bin/env python3
"""
seminarkanon_graphml.py – erzeugt aus seminarkanon.json einen bipartiten Graphen
(Stimmzettel ↔ Werke) im GraphML-Format.

Aufruf:
    python3 seminarkanon_graphml.py seminarkanon.json seminarkanon.graphml

Regeln:
  * Knoten Typ "voter": ein Knoten pro Stimmzettel (ID "v<Nr.>",
    Label "Nr. 1 (Pseudonym)" bzw. "Nr. 24 (anonym)").
  * Knoten Typ "work": ein Knoten pro Wikidata-ID des Werks. Die fünf Werkkomplexe
    werden zusammengefasst: Einzelbände und Gesamtreihe ergeben einen Knoten mit
    der Wikidata-ID des Komplexes. Label "Autor*in: Titel", z. B. "Anna Burns: Milkman".
  * Kanten: eine ungerichtete Kante pro Nennung auf Platz 1–10, Gewicht 1.
    Punkte und Ränge spielen keine Rolle; Titel jenseits von Platz 10 und leere
    Plätze werden ignoriert.
"""

import json
import sys
from collections import Counter, defaultdict

import networkx as nx

WD = "http://www.wikidata.org/entity/"


def most_common(values):
    return Counter(values).most_common(1)[0][0]


def build(data):
    G = nx.Graph()  # ohne Graph-Attribute: Gephi ignoriert sie ohnehin und warnt beim Import
    works = defaultdict(lambda: {"titles": [], "authors": [], "complex": None})

    for b in data["ballots"]:
        vid = f"v{b['id']}"
        G.add_node(vid, type="voter", bipartite=0, ballot=b["id"],
                   label=f"Nr. {b['id']} ({'anonym' if b['voter_anonymous'] else b['voter']})")
        for w in b["works"]:            # nur Platz 1–10, overflow wird ignoriert
            if w["empty"]:
                continue
            cx = w["work_complex"]
            qid = cx["wikidata"] if cx else w["wikidata"]
            works[qid]["titles"].append(w["title"])
            works[qid]["authors"].append(", ".join(a["name"] for a in w["authors"]))
            if cx:
                works[qid]["complex"] = cx["label"]
            if G.has_edge(vid, qid):    # Sicherheitsnetz: zwei Teile desselben Komplexes
                print(f"Hinweis: Stimmzettel {b['id']} nennt {qid} mehrfach – eine Kante",
                      file=sys.stderr)
            G.add_edge(vid, qid, weight=1)

    for qid, info in works.items():
        author = most_common(info["authors"])
        title = info["complex"] or most_common(info["titles"])
        G.add_node(qid, type="work", bipartite=1,
                   label=f"{author}: {title}" if author else title,
                   title=title,
                   author=author,
                   wikidata=WD + qid,
                   work_complex=bool(info["complex"]))
    return G


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        G = build(json.load(f))
    # GraphML-Booleans klein schreiben ("true"/"false"), wie es das Schema vorsieht
    xml = "\n".join(nx.generate_graphml(G, encoding="utf-8", prettyprint=True))
    xml = xml.replace(">True</data>", ">true</data>").replace(">False</data>", ">false</data>")
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write("<?xml version='1.0' encoding='utf-8'?>\n" + xml + "\n")
    voters = sum(1 for _, d in G.nodes(data=True) if d["type"] == "voter")
    print(f"{voters} Stimmzettel, {G.number_of_nodes() - voters} Werke, "
          f"{G.number_of_edges()} Kanten → {sys.argv[2]}", file=sys.stderr)


if __name__ == "__main__":
    main()
