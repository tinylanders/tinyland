from enum import Enum
import pprint

from parsimonious.grammar import Grammar, NodeVisitor
from parsimonious.nodes import RegexNode

class Command(Enum):
    MATCH = 0
    CREATE = 1
    UPDATE = 2
    COND = 3
    AND = 4

whitespace_chars = " \n,"

grammar = Grammar(
    r"""
    app = read ws? write
    read = "when" ws match (";" ws? match)*
    write = (create / update) (";" ws? (create / update))*
    match = adjectives? relation? begin ws? tags ws? data_condition? end (ws alias)?
    create = "create" (ws relation)? begin ws? tags ws data? end
    update = "update" ws name begin data end
    adjectives = ws? adjective (ws adjective)*
    tags = ws? tag (ws tag)*
    data = ws? datum (ws datum)*
    data_condition = ws? (condition / datum) (ws (condition / datum))*
    alias = "as" ws name_with_pronouns
    ws = ~"([ \t\n,])+"
    adjective = "one" / "only" / "global"
    relation = ws? "friend"
    tag = "#" name
    datum = name (":" ws expr)?
    condition = name ws "where" ws truthy
    truthy = boolean / inequality
    expr =  inequality / addition / multiplication / subexpr / value
    inequality = (addition / multiplication / subexpr / name / value)
                 comparison ws?
                 (addition / multiplication / subexpr / name / value)
                 (comparison ws? (addition / multiplication / subexpr / name / value))?
    comparison = (ws? (">" / "<") ws?) / (ws ("is" / "not") ws)
    addition = (multiplication / subexpr / value) ws? ("+" / "-") ws? expr
    multiplication = (subexpr / value) ws? "*" ws? expr
    subexpr = "(" ws? expr ws? ")"
    value = number / boolean / name / string
    boolean = "true" / "false"
    string = ~'"[^\"]*"'
    number = ("+" / "-")? digit+ ("." digit+)? ("e" ("+" / "-") digit+)?
    digit = ~"[0-9]"
    name_with_pronouns = name ("/" name)*
    name = !reserved_word ~"[a-z][a-z_-]*(\.[a-z][a-z_-]*)?"
    begin = ws? "["
    end = ws? "]"
    reserved_word = ("as" / "where" / "true" / "false") &ws
    """
)


def not_whitespace(o):
    return not (isinstance(o, RegexNode) and o.expr_name == "ws")


def is_wrapped(value):
    return (
        isinstance(value, list)
        and len(value) is 1
        and value != value[0]
    )


def unwrap(value):
    while is_wrapped(value):
        value = value[0]
    return value


class TinyTalkVisitor(NodeVisitor):
    def visit_app(self, _node, visited_children):
        read, _ws, write = visited_children
        return read, write #TODO command string?
    
    def visit_match(self, node, visited_children):
        [adjectives_opt, relation_opt, _begin, _ws, tags, _ws, data_condition_opt, _end,
         ws_alias_opt] = visited_children
        adjectives = unwrap(adjectives_opt) if isinstance(adjectives_opt, list) else None
        relation = unwrap(relation_opt) if isinstance(relation_opt, list) else None
        data_condition = unwrap(data_condition_opt) if isinstance(data_condition_opt, list) else None
        alias = unwrap(ws_alias_opt)[1] if isinstance(ws_alias_opt, list) else None
        return Command.MATCH.name, adjectives, relation, tags, data_condition, unwrap(alias)
    
    def visit_data_condition(self, node, visited_children):
        _ws, first, rest = visited_children
        data_conds = [unwrap(first)] + [unwrap(data_cond) for [_ws, data_cond] in rest]
        return dict(data_conds)

    def visit_write(self, _node, visited_children):
        first, rest = visited_children
        write = [unwrap(first)]
        if isinstance(rest, list):
            write += [unwrap(pair[2]) for pair in rest]
        return write

    def visit_create(self, _node, visited_children):
        _create, relation_opt, _begin, _ws, tags, _ws, data_opt, _end = visited_children
        relation = unwrap(relation_opt)[1] if isinstance(relation_opt, list) else None
        data = unwrap(data_opt) if isinstance(data_opt, list) else None
        return Command.CREATE.name, tags, relation, data

    def visit_update(self, _node, visited_children):
        _update, _ws, name, _begin, data, _end = visited_children
        return Command.UPDATE.name, name, data

    def visit_read(self, _node, visited_children):
        _when, _ws, first, rest = visited_children
        query = [first]
        if isinstance(rest, list):
            query += [pair[2] for pair in rest]
        return query

    def visit_condition(self, _node, visited_children):
        name, _ws, _where, _ws, truthy = [unwrap(child) for child in visited_children]
        return name, (Command.COND.name, truthy)

    def visit_alias(self, _node, visited_children):
        _as, _ws, name = visited_children
        return name

    def visit_adjectives(self, _node, visited_children):
        _ws, first, rest = visited_children
        adjectives = [unwrap(first)] + [unwrap(adjective) for [_ws, adjective] in rest]
        return adjectives

    def visit_adjective(self, _node, visited_children):
        return visited_children[0].text

    def visit_tags(self, _node, visited_children):
        _ws, first, rest = visited_children
        tags = [unwrap(first)] + [unwrap(tag) for [_ws, tag] in rest]
        return tags

    def visit_tag(self, _node, visited_children):
        _pound, name = visited_children
        return name
    
    def visit_relation(self, _node, visited_children):
        _ws, relation = visited_children
        return relation.text

    def visit_data(self, _node, visited_children):
        _ws, first, rest = visited_children
        data = [unwrap(first)] + [unwrap(datum) for [_ws, datum] in rest]
        return dict(data)

    def visit_datum(self, _node, visited_children):
        name, val_opt = [unwrap(child) for child in visited_children]
        val = "ANY"
        if not hasattr(val_opt, "children"):
            _ws, _colon, val = [unwrap(child) for child in val_opt]
        return name, val

    def visit_expr(self, _node, visited_children):
        return unwrap(visited_children)

    def visit_inequality(self, _node, visited_children):
        left, comp_a, _ws, middle, rest = [unwrap(child) for child in visited_children]
        if not hasattr(rest, 'children'):
            comp_b, _ws, right = [unwrap(child) for child in rest]
            return (Command.AND.name, (comp_a, left, middle), (comp_b, middle, right))
        else:
            return (comp_a, left, middle)

    def visit_comparison(self, node, _visited_children):
        return node.text.strip(whitespace_chars)

    def visit_multiplication(self, _node, visited_children):
        left, _ws, op, _ws, right = [unwrap(child) for child in visited_children]
        return (op.text, left, right)

    def visit_addition(self, _node, visited_children):
        left, _ws, op, _ws, right = [
            unwrap(child) for child in unwrap(visited_children)
        ]
        return (op.text, left, right)

    def visit_subexpr(self, _node, visited_children):
        _paren, _ws, expr, _ws, _paren = unwrap(visited_children)
        return unwrap(expr)

    def visit_number(self, node, _visited_children):
        return float(node.text)

    def visit_name_with_pronouns(self, node, _visited_children):
        return node.text.split("/")

    def visit_name(self, node, _visited_children):
        return node.text

    def visit_digit(self, node, _visited_children):
        return node.text

    def visit_boolean(self, node, _visited_children):
        return node.text == "true"

    def visit_string(self, node, _visited_children):
        return node.text

    def generic_visit(self, node, visited_children):
        """ The generic visit method. """
        return visited_children or node


# DONE data with ranges (eg "when #paddle x where 0 < x < 100, y")
# TODO explore alternative (shorthand?) query string options,
##     eg "mfw #success [epicwin.gif]"
##     equivalent to "when #success x, y [#image x y src: epicwin.gif]"
##     (macro system??)
# DONE pronouns (via QUESTION who is "me" in a given query?? (wrt "friend" or "nearest"))
# TODO DESIGNED namespace declaration syntax (eg "* namespace Pong")
# DONE commit syntax
# CANCELLED maybe locus declaration syntax (eg "** app #paddle")
# TODO paramaterizable adjectives?
# DONE fix rules to block protected namespaces & reserved words?
# DONE expression syntax

# * namespace Pong
# when [#aruco x where 0 < x < 100, y] create friend [#paddle x: 100, y]
#
# when [#paddle y] as me/my; friend [#aruco y] as tag/its update [my y: its y]
#
# when [#paddle x y] as me/my;
#      global [#ball
#               x where (my x - 10) < x < (my x + 10),
#               velocity_x,
#               y where (my y - 50) < y < (my y + 50)]
#             as ball
#      update ball [velocity_x: (ball velocity_x * -1)]
