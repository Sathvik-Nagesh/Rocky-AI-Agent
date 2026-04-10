import networkx as nx
import json
import os
import logging
from typing import List, Tuple

class KnowledgeGraph:
    def __init__(self, storage_path="jarvis/memory/knowledge_graph.json"):
        self.path = storage_path
        self.graph = nx.MultiDiGraph()
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    data = json.load(f)
                    # Convert back from adjacency list format
                    for node, adj in data.items():
                        for target, edges in adj.items():
                            for key, attr in edges.items():
                                self.graph.add_edge(node, target, **attr)
                logging.info(f"Knowledge Graph loaded with {self.graph.number_of_nodes()} nodes.")
            except Exception as e:
                logging.error(f"Failed to load Knowledge Graph: {e}")

    def save(self):
        try:
            # MultiDiGraph doesn't have a direct 'to_dict' that works well with json
            # We convert to a serializable format
            data = nx.to_dict_of_dicts(self.graph)
            with open(self.path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save Knowledge Graph: {e}")

    def add_fact(self, subject: str, relation: str, object_val: str):
        """Add a triple to the graph."""
        subject = subject.lower().strip()
        relation = relation.lower().strip()
        object_val = object_val.lower().strip()
        
        self.graph.add_edge(subject, object_val, relation=relation)
        self.save()

    def get_related(self, node: str) -> List[Tuple[str, str]]:
        """Find all nodes related to this node."""
        node = node.lower().strip()
        if node not in self.graph:
            return []
        
        results = []
        # Outgoing edges
        for target in self.graph.neighbors(node):
            edge_data = self.graph.get_edge_data(node, target)
            for key, attr in edge_data.items():
                results.append((attr['relation'], target))
        return results

    def query_facts(self, query: str) -> str:
        """Search the graph for nodes matching query keywords."""
        keywords = query.lower().split()
        relevant_nodes = [n for n in self.graph.nodes if any(k in n for k in keywords)]
        
        if not relevant_nodes:
            return ""
        
        facts = []
        for node in relevant_nodes:
            related = self.get_related(node)
            for rel, target in related:
                facts.append(f"{node} {rel} {target}")
        
        return "\n".join(facts[:5])

cerebro = KnowledgeGraph()
