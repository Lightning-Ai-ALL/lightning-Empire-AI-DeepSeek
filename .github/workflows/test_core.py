# test_core.py
from datetime import datetime
from main import profit, risk, Order, dynamic_ai_share

def test_profit():
    o = Order("測試", 100, 40, 10, 300, 4.5, datetime.now())
    assert profit(o) == round(100 - 100*0.28 - 40 - 10, 2)

def test_risk():
    o = Order("高風險", 100, 40, 3, 1000, 4.0, datetime.now())
    assert risk(o) == 40 + 35 + 20  # 95

def test_dynamic_share():
    assert dynamic_ai_share(0) == 0.2
    assert dynamic_ai_share(100) == 0.05
    assert 0.05 < dynamic_ai_share(50) < 0.2
