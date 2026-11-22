import graphlib
import heapq


def cycles_for(graph):
    index = {}
    low = {}
    stack = []
    active = set()
    cycles = []

    def visit(node):
        index[node] = low[node] = len(index)
        stack.append(node)
        active.add(node)
        for parent in graph[node]:
            if parent not in index:
                visit(parent)
                low[node] = min(low[node], low[parent])
            elif parent in active:
                low[node] = min(low[node], index[parent])
        if low[node] != index[node]:
            return
        component = []
        while stack:
            member = stack.pop()
            active.remove(member)
            component.append(member)
            if member == node:
                break
        if len(component) > 1 or node in graph[node]:
            cycles.append(sorted(component))

    for node in sorted(graph):
        if node not in index:
            visit(node)
    return sorted(cycles)


def ready_order(graph, orders, rejected):
    sorter = graphlib.TopologicalSorter({key: [p for p in deps if p not in rejected]
                                         for key, deps in graph.items() if key not in rejected})
    sorter.prepare()
    queue = []
    ordered = []
    while sorter.is_active():
        for key in sorter.get_ready():
            order = orders[key]
            heapq.heappush(queue, (order["priority"], order["deadline"], key))
        _, _, key = heapq.heappop(queue)
        ordered.append(key)
        sorter.done(key)
    return ordered
