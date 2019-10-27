from . import grammar
from hypothesis import given, reject
from hypothesis.strategies import composite, floats, text, sampled_from
from math import isnan
from random import choice


@composite
def names(draw):
    alpha_chars = "abcdefghijklmnopqrstuvwxyz"
    name_chars = alpha_chars + "-_"
    return draw(text(alphabet=alpha_chars, min_size=1)) + draw(
        text(alphabet=name_chars)
    )


@composite
def names_or_floats(draw):
    return choice([draw(floats(allow_infinity=False, allow_nan=False)), draw(names())])


def whitespaces(min_size=0):
    return text(alphabet=" ,\n", min_size=min_size)


@given(floats(allow_infinity=False, allow_nan=False))
def test_number_grammar(n):
    grammar["number"].parse(str(n))


@given(text())
def test_string(t):
    if '"' in t:
        reject()
    grammar["string"].parse('"' + t + '"')


@given(names())
def test_name(n):
    if n in ["as", "where"]:
        reject()
    grammar["name"].parse(n)


@given(names(), names())
def test_name_with_pronouns(n, pn):
    if len(set([n, pn]).intersection(set(["as", "where"]))) > 0:
        reject()
    grammar["name_with_pronouns"].parse(n + "/" + pn)


@given(text(alphabet=" \n,", min_size=1))
def test_whitespace(t):
    grammar["ws"].parse(t)


@given(
    floats(allow_infinity=False, allow_nan=False),
    floats(allow_infinity=False, allow_nan=False),
    whitespaces(),
)
def test_addition(n, m, ws):
    grammar["addition"].parse(f"{n}{ws}+{ws}{m}")


@given(
    floats(allow_infinity=False, allow_nan=False),
    floats(allow_infinity=False, allow_nan=False),
    whitespaces(),
)
def test_multiplication(n, m, ws):
    grammar["multiplication"].parse(f"{n}{ws}*{ws}{m}")


@given(
    names_or_floats(),
    sampled_from(["<", ">", " is ", " not "]),
    names_or_floats(),
    sampled_from(["<", ">", " is ", " not "]),
    names_or_floats(),
    whitespaces(),
)
def test_inequality(val_a, comp_a, val_b, comp_b, val_c, ws):
    grammar["inequality"].parse(
        f"{val_a}{ws}{comp_a}{ws}{val_b}{ws}{comp_b}{ws}{val_c}"
    )
