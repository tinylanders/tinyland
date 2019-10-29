from . import grammar, TinyTalkVisitor, whitespace_chars
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

visitor = TinyTalkVisitor()


def visit(tree):
    return visitor.visit(tree)


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
def data(draw, max_n=1):
    result = {"data": [],
              "text": ""}
    n = draw(sampled_from(list(range(1, max_n + 1))))
    for _ in range(0, n):
        name = draw(names())
        ws = draw(whitespaces(1))
        val = draw(exprs())
        result["data"].append((name, val["data"]))
        result["text"] += f"{ws}{name}: {val['text']}"
    result["text"] = result["text"].strip(whitespace_chars)
    return result


def operators(allow_inequalities=True):
    ops = ["+", " -", "*"]
    if allow_inequalities:
        ops += ["<", ">", " is ", " not "]
    return sampled_from(ops)


@composite
def exprs(draw, max_n=1, allow_inequalities=True):
    result = {}
    init_val = draw(names_or_floats())
    vals = [init_val]
    ops = []
    result["text"] = f"{init_val}"
    n = draw(sampled_from(list(range(1, max_n + 1))))
    for _ in range(0, n):
        op = draw(operators(allow_inequalities))
        val = draw(names_or_floats())
        ops.append(op)
        vals.append(val)
        result["text"] += draw(whitespaces()).join(["", op, str(val)])
    last2_vals = vals[-2:]
    vals = vals[:-2]
    op = ops.pop(-1).strip()
    data = op, *last2_vals
    while vals:
        data = ops.pop(-1).strip(), vals.pop(-1), data
    result["data"] = data
    return result


def whitespaces(min_size=0):
    return text(alphabet=" ,\n", min_size=min_size)


def ws_between(ws, *enum):
    return ws.join(map(str, enum))


## Tests


@given(floats(allow_infinity=False, allow_nan=False))
def test_number(n):
    result = grammar["number"].parse(str(n))
    assert visit(result) == n


@given(text())
def test_string(t):
    if '"' in t:
        reject()
    result = grammar["string"].parse('"' + t + '"')
    assert visit(result) == f'"{t}"'


@given(names())
def test_name(n):
    if n in ["as", "where"]:
        reject()
    result = grammar["name"].parse(n)
    assert visit(result) == n


@given(names(), names())
def test_name_with_pronouns(n, pn):
    if len(set([n, pn]).intersection(set(["as", "where"]))) > 0:
        reject()
    result = grammar["name_with_pronouns"].parse(n)
    assert visit(result) == [n]

    result = grammar["name_with_pronouns"].parse(n + "/" + pn + "/" + pn)
    assert visit(result) == [n, pn, pn]


@given(whitespaces(1))
def test_whitespace(t):
    grammar["ws"].parse(t)


@given(
    floats(allow_infinity=False, allow_nan=False),
    floats(allow_infinity=False, allow_nan=False),
    whitespaces(),
)
def test_addition(n, m, ws):
    result = grammar["addition"].parse(f"{n}{ws}+{ws}{m}")
    assert visit(result) == ("+", n, m)


@given(
    floats(allow_infinity=False, allow_nan=False),
    floats(allow_infinity=False, allow_nan=False),
    whitespaces(),
)
def test_multiplication(n, m, ws):
    result = grammar["multiplication"].parse(ws_between(ws, n, "*", m))
    assert visit(result) == ("*", n, m)


@given(
    names_or_floats(),
    sampled_from(["<", ">", " is ", " not "]),
    names_or_floats(),
    sampled_from(["<", ">", " is ", " not "]),
    names_or_floats(),
    whitespaces(),
)
def test_inequality(val_a, comp_a, val_b, comp_b, val_c, ws):
    result = grammar["inequality"].parse(
        ws_between(ws, val_a, comp_a, val_b, comp_b, val_c)
    )
    assert visit(result) == (
        "and",
        (comp_a.strip(), val_b, val_a),
        (comp_b.strip(), val_b, val_c),
    )


@given(exprs(13, allow_inequalities=False))
def test_expr(e):
    result = grammar["expr"].parse(e["text"])
    assert visit(result) == e["data"]


@given(names(), whitespaces(1), names_or_floats(), sampled_from(["<", ">"]))
def test_condition(name, ws, val, comp):
    result = grammar["condition"].parse(ws_between(ws, name, "where", name, comp, val))
    assert visit(result) == (name, ("cond", (comp, name, val)))


@given(data())
def test_datum(d):
    result = grammar["datum"].parse(d["text"])
    assert visit(result) == d["data"][0]


@given(names())
def test_tag(name):
    result = grammar["tag"].parse(f"#{name}")
    assert visit(result) == name


@given(names(), data(3), whitespaces())
def test_update(name, data, ws):
    grammar["update"].parse(ws_between(ws, "update ", name, " [", data["text"], "]"))


@given(sampled_from(["", "friend"]), names(), data(3), whitespaces())
def test_create(relation, tag, data, ws):
    grammar["create"].parse(
        ws_between(ws, "create ", relation, " [", f"#{tag} #{tag} ", data["text"], "]")
    )


@given(
    sampled_from(["", "one", "only", "global"]),
    sampled_from(["", "friend"]),
    names(),
    data(3),
    names(),
    whitespaces(),
)
def test_match(adjective, relation, tag, data, alias, ws):
    grammar["match"].parse(
        ws_between(
            ws, adjective, " ", relation, " [", f"#{tag} #{tag} ", data["text"], "] as ", alias
        )
    )


## end test_grammar.py
