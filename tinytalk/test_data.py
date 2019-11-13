from . import data, Command
from collections import namedtuple


def test_variable_exists():
    rowtup = namedtuple("row", ["x"])
    row = rowtup(x=100)
    var = "x"
    cond = "ANY"
    assert data.condition(var, cond, row)


def test_variable_does_not_exist():
    rowtup = namedtuple("row", ["x"])
    row = rowtup(x=100)
    var = "y"
    cond = "ANY"
    assert not data.condition(var, cond, row)


def test_single_condition_true():
    rowtup = namedtuple("row", ["x"])
    row = rowtup(x=50)
    var = "x"
    cond = ["is", "x", 50.0]
    assert data.condition(var, cond, row)


def test_single_condition_false():
    rowtup = namedtuple("row", ["x"])
    row = rowtup(x=50)
    var = "x"
    cond = ["not", "x", 50.0]
    assert not data.condition(var, cond, row)


def test_multiple_condition():
    rowtup = namedtuple("row", ["x"])
    row = rowtup(x=50)
    var = "x"
    cond = [Command.AND.name, ["<", 0.0, "x"], ["<", "x", 100.0]]
    assert data.condition(var, cond, row)

