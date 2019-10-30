from . import grammar, TinyTalkVisitor, whitespace_chars, Command
from hypothesis import given, reject
from hypothesis.strategies import composite, floats, text, sampled_from

import random

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
def conditions(draw, max_n=1):
    result = {"data": [],
              "text": ""}
    n = draw(sampled_from(list(range(1, max_n + 1))))
    for _ in range(n):
        name = draw(names())
        ws = draw(whitespaces(0))
        val = draw(names_or_floats())
        op = draw(sampled_from([">", "<", " is "]))
        result["data"].append((name, (Command.COND.name, (op.strip(), name, val))))
        result["text"] = ws_between(draw(whitespaces(1)), result["text"], f"{name}{ws} where {ws}{name}{ws}{op}{ws}{val}")
    return result

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
        Command.AND.name,
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
    assert visit(result) == (name, (Command.COND.name, (comp, name, val)))


@given(data())
def test_datum(d):
    result = grammar["datum"].parse(d["text"])
    assert visit(result) == d["data"][0]


@given(data(10))
def test_data(d):
    result = grammar["data"].parse(d["text"])
    assert visit(result) == dict(d["data"])


@given(names())
def test_tag(name):
    result = grammar["tag"].parse(f"#{name}")
    assert visit(result) == name


@given(whitespaces(), whitespaces(1), names(), names())
def test_tags(lead_ws, ws, tag1, tag2):
    tags = [f"#{tag}" for tag in [tag1, tag2]]
    result = grammar["tags"].parse(ws_between(ws, lead_ws, *tags))
    assert visit(result) == [tag1, tag2]


@given(names(), data(3), whitespaces())
def test_update(name, data, ws):
    result = grammar["update"].parse(ws_between(ws, "update ", name, " [", data["text"], "]"))
    assert visit(result) == (Command.UPDATE.name, name, dict(data["data"]))


@given(sampled_from(["", "friend"]), names(), data(3), whitespaces())
def test_create(relation, tag, data, ws):
    parse_string = ws_between(ws, "create ", relation, " [", f"#{tag} #{tag} ", data["text"], "]")
    result = grammar["create"].parse(parse_string)
    assert visit(result) == (Command.CREATE.name, [tag, tag], relation or None, dict(data["data"]) if data else None)


@given(
    sampled_from(["", "one", "only", "global"]),
    sampled_from(["", "friend"]),
    names(),
    conditions(3),
    names(),
    whitespaces(),
)
def test_match(adjective, relation, tag, conditions, alias, ws):
    result = grammar["match"].parse(
        ws_between(
            ws, adjective, relation, " [", f"#{tag} #{tag} ", conditions["text"], "] as ", alias))
    assert visit(result) == (Command.MATCH.name,
                             adjective or None,
                             relation or None,
                             [tag, tag],
                             dict(conditions["data"]),
                             alias)


@given(
    sampled_from(list(range(1, 3))),
    sampled_from(list(range(0, 3))),
    sampled_from(list(range(0, 3))),
    whitespaces(1)
)
def test_app(num_matches, num_creates, num_updates, ws):
    if num_creates + num_updates == 0:
        reject()
    match_texts = ["global friend [ #a x where 0 < x < 50 ] as f", "[ #x ]"]
    match_data = [
        (Command.MATCH.name,
        "global",
        "friend",
        ["a"],
        {"x": (Command.COND.name, (Command.AND.name, ("<", "x", 0.0), ("<", "x", 50.0)))},
        "f"),
        (Command.MATCH.name, None, None, ["x"], None, None)]
    create_texts = ["create friend [ #a #b x: 50 ]"]
    create_data = [(Command.CREATE.name, ["a", "b"], "friend", {"x": 50.0})]
    update_texts = ["update paddle [ x: y ]"]
    update_data = [(Command.UPDATE.name, "paddle", {"x": "y"})]
    
    test_match_data = [match_data[i % len(match_data)] for i in range(num_matches)]
    test_create_update_texts = [create_texts[i % len(create_texts)] for i in range(num_creates)] + \
                               [update_texts[i % len(update_texts)] for i in range(num_updates)]
    test_create_update_data = [create_data[i % len(create_data)] for i in range(num_creates)] + \
                              [update_data[i % len(update_data)] for i in range(num_updates)]

    test_match_text = "; ".join([match_texts[i % len(match_texts)] for i in range(num_matches)])
    test_write_text = "; ".join(test_create_update_texts)

    app_text = ws_between(" ", "when", test_match_text, test_write_text)
    result = grammar["app"].parse(app_text)
    assert visit(result) == (test_match_data, test_create_update_data)


## end test_grammar.py
