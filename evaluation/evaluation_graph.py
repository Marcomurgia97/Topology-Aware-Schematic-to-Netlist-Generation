import networkx as nx
from networkx.algorithms import isomorphism
import re
from collections import Counter

# --- 1. Parser ---

PIN_MAP = {
    'M': ['d', 'g', 's', 'b'],
    'R': ['t', 't'],  # Standard resistor (2 terminals, symmetric)
    'POT': ['t', 't', 'w'],  # Potentiometer (3 terminals)
    'L': ['t', 't'],
    'C': ['t', 't'],
    'V': ['p', 'n'],
    'I': ['p', 'n'],
    'Q': ['c', 'b', 'e'],
    'D': ['a', 'c'],
    'K': ['p', 's'],
}


class NetlistParser:

    def __init__(self, netlist_string: str):
        self.netlist_string = netlist_string
        self.graph = nx.Graph()
        self.ignore_types = {'V', 'I', 'K'}
        self.mosfet_types = {'NMOS', 'PMOS', 'NMOSFET', 'PMOSFET', 'CMOS', 'N_CH', 'P_CH'}

    _VALUE_KEYWORDS = {
        'VALUE', 'DIODE', 'NPN', 'PNP', 'NMOS', 'PMOS',
        'NMOSFET', 'PMOSFET', 'CMOS', 'N_CH', 'P_CH',
        'DC', 'AC', 'PULSE', 'SIN', 'PWL',
    }

    def _is_likely_value(self, token: str) -> bool:
        if token.upper() in self._VALUE_KEYWORDS: return True
        if '=' in token: return True
        if re.match(r'^\d+$', token): return False  # Pure integers = net nodes (e.g. 0, 1, 2)
        if any(c in token for c in ('/', '*', '{', '}', '(', ')')): return True
        try:
            val_str = token.lower()
            for unit in ['meg', 'k', 'm', 'u', 'n', 'p', 'f', 'g', 't']:
                if val_str.endswith(unit):
                    val_str = val_str[:-len(unit)]
                    break
            float(val_str)
            return True
        except ValueError:
            return False

    def parse(self) -> nx.Graph:
        lines = self.netlist_string.strip().split('\n')
        raw_components = []
        known_nets = {'0', 'GND', 'gnd'}

        # ── Pass 1: collect components and build known_nets from unambiguous pins ──
        for line in lines:
            line = line.strip()
            if not line or line.startswith('*') or line.startswith('.'): continue
            if ';' in line: line = line.split(';')[0]
            if '$' in line: line = line.split('$')[0]

            parts = re.split(r'\s+', line.strip())
            if not parts: continue

            comp_name = parts[0]
            comp_type = comp_name[0].upper()

            if comp_type in self.ignore_types: continue
            if comp_type not in PIN_MAP and comp_type != 'R': continue

            # Strip tokens after '=' or MOSFET model keywords
            clean_tokens = []
            for t in parts[1:]:
                if '=' in t or t.upper() in self.mosfet_types: break
                clean_tokens.append(t)

            raw_components.append({'name': comp_name, 'type': comp_type, 'tokens': clean_tokens})

            # Add unambiguous net names to known_nets
            # For R: only the first 2 tokens are guaranteed net names
            # For M: up to 4 tokens; for others: exactly num_pins tokens
            if comp_type == 'R':
                for t in clean_tokens[:2]:
                    if not self._is_likely_value(t): known_nets.add(t)
            elif comp_type == 'M':
                for t in clean_tokens[:4]:
                    if not self._is_likely_value(t): known_nets.add(t)
            else:
                num_pins = len(PIN_MAP.get(comp_type, []))
                for t in clean_tokens[:num_pins]:
                    if not self._is_likely_value(t): known_nets.add(t)

        # ── Pass 2: build the graph ──
        for comp in raw_components:
            comp_name = comp['name']
            comp_type = comp['type']
            tokens = comp['tokens']

            if comp_type in self.ignore_types: continue

            # ── MOSFET ──
            if comp_type == 'M':
                potential_nets = [t for t in tokens if not self._is_likely_value(t)]
                if len(potential_nets) > 4: potential_nets = potential_nets[:4]

                if len(potential_nets) == 4:
                    final_nets = potential_nets
                elif len(potential_nets) == 3:
                    final_nets = potential_nets + [potential_nets[2]]  # Bulk = Source
                else:
                    continue

                self.graph.add_node(comp_name, bipartite=0, type='M', full_name=comp_name)
                for pin_name, net_name in zip(PIN_MAP['M'], final_nets):
                    if pin_name == 'b': continue  # Skip bulk for base topology
                    if not self.graph.has_node(net_name): self.graph.add_node(net_name, bipartite=1)
                    self.graph.add_edge(comp_name, net_name, pin=pin_name)

            # ── RESISTOR or POTENTIOMETER ──
            elif comp_type == 'R':
                if len(tokens) < 2: continue
                net1, net2 = tokens[0], tokens[1]
                net_names = [net1, net2]
                node_type = 'R'

                # A third token is a wiper net (POT) if ALL of:
                #   1. Not a numeric value / keyword / expression
                #   2. Not the component's own name (symbolic value label, e.g. "R1 n1 n2 R1")
                #   3. Either already a known net in the circuit, or shorted to one of its terminals
                if len(tokens) >= 3:
                    t3 = tokens[2]
                    if (not self._is_likely_value(t3)
                            and t3.upper() != comp_name.upper()
                            and (t3 in known_nets or t3 == net1 or t3 == net2)):
                        net_names.append(t3)
                        node_type = 'POT'

                self.graph.add_node(comp_name, bipartite=0, type=node_type, full_name=comp_name)
                for pin_name, net_name in zip(PIN_MAP[node_type], net_names):
                    if not self.graph.has_node(net_name): self.graph.add_node(net_name, bipartite=1)
                    self.graph.add_edge(comp_name, net_name, pin=pin_name)

            # ── All other components ──
            else:
                pins = PIN_MAP.get(comp_type, [])
                num_pins = len(pins)
                if len(tokens) < num_pins: continue
                net_names = tokens[:num_pins]

                self.graph.add_node(comp_name, bipartite=0, type=comp_type, full_name=comp_name)
                for pin_name, net_name in zip(pins, net_names):
                    if not self.graph.has_node(net_name): self.graph.add_node(net_name, bipartite=1)
                    self.graph.add_edge(comp_name, net_name, pin=pin_name)

        return self.graph


# --- 2. Netlist Comparator ---

class NetlistGEDComparator:

    def __init__(self, golden_graph: nx.Graph, gen_graph: nx.Graph):
        self.g_golden = golden_graph
        self.g_gen = gen_graph

        self.weights = {
            "COMP_INS_DEL": 10,
            "EDGE_INS_DEL": 10,
            "COMP_SUBST_TYPE": 10,
            "COMP_SUBST_NAME": 0,
            "NET_INS_DEL": 0.1,
        }

        self.ged = None
        self.similarity = None
        self.detailed_errors = []

    def _find_detailed_errors(self):
        self.detailed_errors = []

        golden_types = Counter(d['type'] for _, d in self.g_golden.nodes(data=True) if d['bipartite'] == 0)
        gen_types = Counter(d['type'] for _, d in self.g_gen.nodes(data=True) if d['bipartite'] == 0)

        component_mismatch = golden_types != gen_types
        if component_mismatch:
            for t, c in (golden_types - gen_types).items():
                self.detailed_errors.append(f"Missing component: {c} x '{t}'")
            for t, c in (gen_types - golden_types).items():
                self.detailed_errors.append(f"Extra component: {c} x '{t}'")

        if not component_mismatch:
            matcher = isomorphism.GraphMatcher(
                self.g_golden, self.g_gen,
                node_match=lambda a, b: a.get('type') == b.get('type'),
                edge_match=lambda a, b: a.get('pin') == b.get('pin'),
            )
            if not matcher.is_isomorphic():
                self.detailed_errors.append("Topology error (wrong connections).")

    def _node_subst_cost(self, a, b):
        if a.get('bipartite') != b.get('bipartite'): return float('inf')
        if a.get('bipartite') == 0:
            return self.weights["COMP_SUBST_TYPE"] if a.get('type') != b.get('type') else self.weights[
                "COMP_SUBST_NAME"]
        return 0

    def _node_ins_del_cost(self, a):
        return self.weights["COMP_INS_DEL"] if a.get('bipartite') == 0 else self.weights["NET_INS_DEL"]

    def _edge_subst_cost(self, a, b):
        return 0 if a.get('pin') == b.get('pin') else self.weights["EDGE_INS_DEL"]

    def _edge_ins_del_cost(self, a):
        return self.weights["EDGE_INS_DEL"]

    def _calculate_ged(self, timeout=10):
        try:
            self.ged = nx.graph_edit_distance(
                self.g_golden, self.g_gen,
                node_subst_cost=self._node_subst_cost,
                node_del_cost=self._node_ins_del_cost,
                node_ins_cost=self._node_ins_del_cost,
                edge_subst_cost=self._edge_subst_cost,
                edge_del_cost=self._edge_ins_del_cost,
                edge_ins_cost=self._edge_ins_del_cost,
                timeout=timeout,
            )
            cost1 = (sum(self._node_ins_del_cost(d) for _, d in self.g_golden.nodes(data=True))
                     + sum(self._edge_ins_del_cost(d) for _, _, d in self.g_golden.edges(data=True)))
            cost2 = (sum(self._node_ins_del_cost(d) for _, d in self.g_gen.nodes(data=True))
                     + sum(self._edge_ins_del_cost(d) for _, _, d in self.g_gen.edges(data=True)))
            max_cost = cost1 + cost2
            self.similarity = (max(0, 1.0 - self.ged / max_cost) if max_cost > 0
                               else (1.0 if self.ged == 0 else 0.0))
        except nx.NetworkXTimeoutError:
            self.ged, self.similarity = float('inf'), 0.0

    def compare(self, timeout=10):
        self._find_detailed_errors()
        if not self.detailed_errors:
            self.ged, self.similarity = 0.0, 1.0
            return
        self._calculate_ged(timeout)

    def get_report(self):
        if self.ged is None:
            return "The comparison has not been executed", None, None

        summary = f"Summary: GED = {self.ged:.1f}, Similarity = {self.similarity:.2%}\n" + "-" * 40
        lines = [summary, "-" * len(summary)]

        if self.detailed_errors:
            lines.append("Errors details:")
            for e in self.detailed_errors:
                lines.append(f"  - {e}")
        elif self.ged == 0:
            lines.append("Status: Perfect Match (Correct).")
        else:
            lines.append("Status: Minor uncategorized differences found.")

        return "\n".join(lines), self.ged, self.similarity



