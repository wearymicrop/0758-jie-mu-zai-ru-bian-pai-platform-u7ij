from app.modules.schedule.search import search


def jobs(result):
    return {x['id']:x for x in result['schedule']['jobs']}


def test_skips_over_both_holds(dirty):  # TRAP-19
    job=jobs(dirty)['A01']
    assert (job['start'],job['end'],job['related']) == (605,640,['H01','H04'])


def test_stage_reset_blocks_dependent_stage(dirty):
    job=jobs(dirty)['A02']
    assert (job['ready'],job['start'],job['tech']) == (640,650,'L2')


def test_known_venue_closed_at_night(dirty):
    assert jobs(dirty)['X05']['code'] == 'NO_WINDOW'
    assert jobs(dirty)['X05']['status'] == 'pending'


def test_pending_chain(dirty):
    assert jobs(dirty)['X03']['related'] == ['X02']
    assert jobs(dirty)['X06']['related'] == ['X05']


def test_second_technician_prevents_needless_delay(clean):
    assert (jobs(clean)['C02']['start'],jobs(clean)['C02']['tech']) == (680,'S2')


def test_different_stage_can_start_during_stage_reset(clean):
    slots=jobs(clean)
    assert slots['B02']['start'] < slots['A01']['stage_end']
    assert slots['B02']['stage'] != slots['A01']['stage']


def test_no_known_gap_fit(dirty):
    task=jobs(dirty)['A01']
    holds={'stage:主舞台':[{'start':540,'end':1140,'id':'维护'}]}
    slot,code,trace=search(task,dirty['calendars'],holds,540,set())
    assert (slot,code,trace)==(None,'RESOURCE_FULL',['维护'])


def test_unreliable_reservations_cannot_be_allocated(dirty):
    task=jobs(dirty)['A01']
    assert search(task,dirty['calendars'],{},540,{'stage:主舞台'}) == (None,'HOLD_UNCERTAIN',['stage:主舞台'])
