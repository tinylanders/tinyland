from . import grammar
from hypothesis import given, reject
from hypothesis.strategies import composite, floats, text, sampled_from

## Tests for TinyTalk's grammar
#
# To run the tests:
#
# $ pip install -r requirements.txt
# $ pytest
# ...
# ====== n passed in 1.97s ======


## Helper functions


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


@composite
def data(draw, n=1):
    result = []
    for i in range(0, n):
        name = draw(names())
        ws = draw(whitespaces(1))
        val = draw(exprs())
        result.append(f"{name}:{ws}{val}")
    return ws_between(ws, *result)


def operators():
    return sampled_from(["+", " -", "*", "<", ">", " is ", " not "])


@composite
def exprs(draw):
    length = draw(sampled_from([1, 2, 3]))
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


## Tests


@given(floats(allow_infinity=False, allow_nan=False))
def test_number(n):
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


@given(whitespaces(1))
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


@given(names(), whitespaces(1), names_or_floats(), sampled_from(["<", ">"]))
def test_condition(name, ws, val, comp):
    grammar["condition"].parse(ws_between(ws, name, "where", name, comp, val))


@given(data())
def test_datum(d):
    grammar["datum"].parse(d)


@given(names())
def test_tag(name):
    grammar["tag"].parse(f"#{name}")


@given(names(), data(2), whitespaces())
def test_update(name, data, ws):
    grammar["update"].parse(ws_between(ws, "update ", name, " [", data, "]"))


@given(sampled_from(["", "friend"]), names(), data(2), whitespaces())
def test_create(relation, tag, data, ws):
    grammar["create"].parse(
        ws_between(ws, "create ", relation, " [", f"#{tag} #{tag} ", data, "]")
    )


@given(
    sampled_from(["", "one", "only", "global"]),
    sampled_from(["", "friend"]),
    names(),
    data(2),
    names(),
    whitespaces(),
)
def test_match(adjective, relation, tag, data, alias, ws):
    grammar["match"].parse(
        ws_between(
            ws, adjective, " ", relation, " [", f"#{tag} #{tag} ", data, "] as ", alias
        )
    )


## end test_grammar.py
