from app.services.qa.route_constraints import explicit_route_hours


def test_explicit_route_hours_only_accepts_unambiguous_whole_hour_budgets():
    assert explicit_route_hours("我只有两个小时，推荐亲子路线") == 2
    assert explicit_route_hours("3小时的路线") == 3
    assert explicit_route_hours("2小时或4小时路线") is None
    assert explicit_route_hours("1.5小时路线") is None
    assert explicit_route_hours("两三小时路线") is None
    assert explicit_route_hours("2到4小时路线") is None
    assert explicit_route_hours("半天路线") is None
    assert explicit_route_hours("至少三小时的路线") is None
    assert explicit_route_hours("三小时后到景区，推荐路线") is None
    assert explicit_route_hours("一小时30分钟路线") is None
    assert explicit_route_hours("3小时以上的路线") is None
