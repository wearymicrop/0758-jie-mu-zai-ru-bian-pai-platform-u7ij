from app.modules.dependencies.graph import cycles_for, ready_order


def inspect(orders):
    indexed = {order["id"]: order for order in orders}
    graph = {key: [p for p in order["needs"] if p in indexed] for key, order in indexed.items()}
    missing = {key: sorted(set(order["needs"]) - indexed.keys()) for key, order in indexed.items()
               if set(order["needs"]) - indexed.keys()}
    cycles = cycles_for(graph)
    issues = {key: {"code": "MISSING_DEPENDENCY", "related": gaps} for key, gaps in missing.items()}
    for component in cycles:
        for key in component:
            issues[key] = {"code": "DEPENDENCY_CYCLE", "related": component}
    return {"cycles": cycles, "missing": missing, "issues": issues, "edges": graph,
            "order": ready_order(graph, indexed, issues)}
