from . import grammar
from hypothesis import given, reject
from hypothesis.strategies import composite, floats, text, sampled_from
from math import isnan


@composite
def names(draw):
    alpha_chars = "bcdeghijklmnopqrsuvxyz"  # no [awtf] at start to avoid reserved words
    name_chars = alpha_chars + "awtf-_"
    return draw(text(alphabet=alpha_chars, min_size=1)) + draw(
        text(alphabet=name_chars)
    )


@composite
def names_or_floats(draw):
    return draw(
        sampled_from(
            [draw(floats(allow_infinity=False, allow_nan=False)), draw(names())]
        )
    )


def operators():
    return sampled_from(["+", " -", "*", "<", ">", " is ", " not "])


@composite
def exprs(draw):
    length=draw(sampled_from([1, 2, 3]))
    result = str(draw(names_or_floats()))
    for _ in range(0, length):
        result += ws_between(
            draw(whitespaces()), draw(operators()), draw(names_or_floats())
        )
    return result


def whitespaces(min_size=0):
    return text(alphabet=" ,\n", min_size=min_size)


def ws_between(ws, *enum):
    return ws.join(map(str, enum))


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
    grammar["multiplication"].parse(ws_between(ws, n, "*", m))


@given(
    names_or_floats(),
    sampled_from(["<", ">", " is ", " not "]),
    names_or_floats(),
    sampled_from(["<", ">", " is ", " not "]),
    names_or_floats(),
    whitespaces(),
)
def test_inequality(val_a, comp_a, val_b, comp_b, val_c, ws):
    grammar["inequality"].parse(ws_between(ws, val_a, comp_a, val_b, comp_b, val_c))


@given(exprs())
def test_expr(e):
    grammar["expr"].parse(e)
