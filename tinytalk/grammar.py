from parsimonious.grammar import Grammar, NodeVisitor
from parsimonious.nodes import RegexNode
import pprint

grammar = Grammar(
    r"""
    query = "when" condition (";" condition)* ws?
    condition = adjectives? tags data? (ws alias)?
    adjectives = (ws adjective)+
    tags = (ws tag)+
    data = (ws datum)+
    alias = "as" ws name
    ws = ~"([ \t\n,])+"
    adjective = "one" / "only" / "global" / "nearest" / "friend"
    tag = "#" name
    datum = !"as" name (":" ws value)?
    value = number / string / boolean
    boolean = "true" / "false"
    string = ~'"[ ^\"]*"'
    number = ("+" / "-")? digit+ ("." digit+)?
    digit = ~"[0-9]+"
    name  = ~"[a-z][a-z_-]*"
    """)


def not_whitespace(o):
    return not (isinstance(o, RegexNode) and o.expr_name == "ws")


class Condition:

    def __init__(self, *_, adjectives, tags, data, alias):
        self.adjectives = adjectives
        self.tags = tags
        self.data = data
        self.alias = alias

    def __repr__(self):
        return f"{self.__class__.__name__}(adjectives={self.adjectives}, tags={self.tags}, data={self.data}, alias={self.alias})"

    def __str__(self):
        return pprint.pformat(self)


class TinyTalkVisitor(NodeVisitor):
    def visit_query(self, _node, visited_children):
        """ Returns the overall output. """
        _when, first, rest, _ws = visited_children
        query = [first]
        if isinstance(rest, list):
            query += [pair[1] for pair in rest]
        return query

    def visit_condition(self, _node, visited_children):
        adjectives_opt, tags, data_opt, alias_opt = visited_children
        adjectives = set(adjectives_opt[0]) if isinstance(adjectives_opt, list) else None
        data = dict(data_opt[0]) if isinstance(data_opt, list) else None
        alias = alias_opt[0][1] if isinstance(alias_opt, list) else None
        cond = Condition(adjectives=adjectives,
                         tags=set(tags),
                         data=data,
                         alias=alias)
        return cond

    def visit_alias(self, _node, visited_children):
        _as, _ws, name = visited_children
        return name.text

    def visit_adjectives(self, _node, visited_children):
        adjs = [child[1] for child in visited_children]
        return adjs

    def visit_adjective(self, _node, visited_children):
        return visited_children[0].text

    def visit_tags(self, _node, visited_children):
        tags = [child[1] for child in visited_children]
        return tags

    def visit_tag(self, _node, visited_children):
        _pound, name = visited_children
        return name.text

    def visit_data(self, _node, visited_children):
        data = [child[1] for child in visited_children]
        return data

    def visit_datum(self, _node, visited_children):
        _as, name, val_opt = visited_children
        val = "ANY"
        if isinstance(val_opt, list):
            _ws, _colon, val = val_opt[0]
            val = val[0]
        return name.text, val

    def visit_number(self, _node, visited_children):
        sign_opt, integer, decimal_opt = visited_children
        number = integer[0]
        if isinstance(decimal_opt, list):
            point, decimal = decimal_opt[0]
            number += point.text
            number += decimal[0]
        if isinstance(sign_opt, list):
            sign = sign_opt[0][0].text
            number = sign + number
        return float(number)

    def visit_digit(self, node, _visited_children):
        return node.text

    def visit_boolean(self, node, _visited_children):
        return node.text == "true"

    def visit_string(self, node, _visited_children):
        return node.text

    def generic_visit(self, node, visited_children):
        """ The generic visit method. """
        return visited_children or node




# TODO data with ranges (eg "when #paddle x where 0 < x < 100, y")
# TODO explore alternative (shorthand?) query string options,
##     eg "mfw #success [epicwin.gif]"
##     equivalent to "when #success x, y [#image x y src: epicwin.gif]"
##     (macro system??)
# QUESTION who is "me" in a given query?? (wrt "friend" or "nearest")
# TODO namespace declaration syntax (eg "* namespace Pong")
# TODO commit syntax
# TODO maybe locus declaration syntax (eg "** app #paddle")
# TODO paramaterizable adjectives?
# TODO fix rules to block protected namespaces?

# * namespace Pong
# when #aruco x where 0 < x < 100, y [create friend #paddle x: 100, y]
# ** app #paddle x y
# when friend #aruco y as marker [update my y: marker y]
# when global nearby #ball
#   x where 90 < x < 110,
#   velocity_x,
#   y where (my y - 50) < y < (my y + 50)
#   as ball
#   [update ball velocity_x: (ball velocity_x * -1)]

# implies that the #paddle was declared in the Pong namespace
