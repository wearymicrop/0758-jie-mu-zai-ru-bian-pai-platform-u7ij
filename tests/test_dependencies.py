from app.modules.dependencies.checks import inspect


def test_cycle_members(dirty):  # TRAP-20
    assert dirty['dependencies']['cycles'] == [['X01','X02'],['X08']]


def test_cycle_child_distinguished(dirty):
    assert 'X03' in dirty['dependencies']['order']
    assert 'X03' not in dirty['dependencies']['issues']


def test_missing_reference(dirty):
    assert dirty['dependencies']['missing'] == {'X07':['Z99']}


def test_clean_order_respects_every_edge(clean):
    graph = clean['dependencies']
    pos = {key:i for i,key in enumerate(graph['order'])}
    assert all(pos[p] < pos[key] for key, needs in graph['edges'].items() for p in needs)


def test_ready_tie_uses_stable_identifier(clean):  # TRAP-19
    assert clean['dependencies']['order'][:3] == ['A01','A02','A03']


def test_priority_independent_of_input_order(clean):
    assert inspect(list(reversed(clean['orders']['orders'])))['order'] == clean['dependencies']['order']


def test_empty_graph():
    assert inspect([]) == dict(cycles=[],missing={},issues={},edges={},order=[])
