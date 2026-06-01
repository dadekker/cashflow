from datetime import date
from types import SimpleNamespace as NS
from app.cashflow import calculated_balance, forecast, occurrences_for_item

def cf(**kwargs):
    defaults = dict(id=1, label='Item', amount=100, direction='expense', kind='recurring', frequency='monthly', start_date='2026-01-31', end_type='never', end_date=None, end_occurrences=None, active=True)
    defaults.update(kwargs)
    return NS(**defaults)

def anchor(id, day, amount):
    return NS(id=id, date=day, amount=amount, note=None)

def test_balance_uses_latest_anchor_and_strictly_after_anchor():
    anchors=[anchor(1,'2026-01-01',1000), anchor(2,'2026-01-15',500)]
    items=[cf(label='Pay', amount=200, direction='income', kind='one_off', frequency=None, start_date='2026-01-15'), cf(label='Rent', amount=100, direction='expense', kind='one_off', frequency=None, start_date='2026-01-16')]
    balance, used, occs = calculated_balance(anchors, items, date(2026,1,16))
    assert used.id == 2
    assert balance == 400
    assert [o.label for o in occs] == ['Rent']

def test_month_end_recurrence_clamps_to_short_months():
    item=cf(start_date='2026-01-31', end_type='occurrences', end_occurrences=4)
    assert [o.date.isoformat() for o in occurrences_for_item(item, date(2026,1,1), date(2026,5,1))] == ['2026-01-31','2026-02-28','2026-03-31','2026-04-30']

def test_forecast_surfaces_peak_and_trough():
    anchors=[anchor(1,'2026-01-01',100)]
    items=[cf(label='Income', amount=50, direction='income', kind='one_off', frequency=None, start_date='2026-01-02'), cf(label='Expense', amount=200, direction='expense', kind='one_off', frequency=None, start_date='2026-01-03')]
    out=forecast(anchors, items, date(2026,1,1), 3)
    assert out['peak']['date'] == '2026-01-02'
    assert out['trough']['balance'] == -50
