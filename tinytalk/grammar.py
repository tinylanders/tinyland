import pprint

from parsimonious.grammar import Grammar, NodeVisitor
from parsimonious.nodes import RegexNode

grammar = Grammar(
    r"""
    start = expr
    app = read write
    read = "when" match (";" match)*
    write = (create / update) (";" (create / update))*
    match = adjectives? relation? begin tags ws data_condition? end (ws alias)?
    create = ws "create" (ws relation)? begin tags ws data? end
    update = ws "update" ws name begin data end
    adjectives = (ws adjective)+
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
    inequality = (subexpr / name / value) ws? comparison ws? expr
    comparison = ">" / "<" / "is" / "not"
    expr =  multiplication / addition / subexpr / inequality / name / value
    addition = (subexpr / multiplication / name / value) ws? ("+" / "-") ws? expr
    multiplication = (subexpr / value / name) ws? "*" ws? expr
    subexpr = "(" ws? expr ws? ")"
    value = number / string / boolean
    boolean = "true" / "false"
    string = ~'"[ ^\"]*"'
    number = ("+" / "-")? digit+ ("." digit+)?
    digit = ~"[0-9]"
    name_with_pronouns = name ("/" name)*
    name = !reserved_word ~"[a-z][a-z_-]*"
    begin = ws? "["
    end = ws? "]"
    reserved_word = "as" / "where"
    """)


def not_whitespace(o):
    return not (isinstance(o, RegexNode) and o.expr_name == "ws")


class Entry:
    def __init__(self, *_, adjectives, tags, data, alias=None):
        self.adjectives = adjectives
        self.tags = tags
        self.data = data
        self.alias = alias

    def __str__(self):
        return pprint.pformat(self)

    def __repr__(self):
        return f"{self.__class__.__name__}(adjectives={self.adjectives}, " \
               f"tags={self.tags}, " \
               f"data={self.data}, " \
               f"alias={self.alias})"


class Update:

    def __init__(self, *_, alias, data):
        self.data = data
        self.alias = alias

    def __repr__(self):
        return f"{self.__class__.__name__}(alias={self.alias}, " \
               f"data={self.data})"


class TinyTalkVisitor(NodeVisitor):
    def visit_program(self, _node, visited_children):
        query, write = visited_children
        return {"query": query, "write": write}

    def visit_write(self, _node, visited_children):
        first, rest = visited_children
        write = [first[0]]
        if isinstance(rest, list):
            write += [pair[1][0] for pair in rest]
        return write

    def visit_create(self, _node, visited_children):
        ws1, _create, entry = visited_children
        return entry

    def visit_update(self, _node, visited_children):
        _ws1, _update, _ws2, alias, data = visited_children
        return Update(alias=alias, data=data)

    def visit_query(self, _node, visited_children):
        """ Returns the overall output. """
        _when, first, rest = visited_children
        query = [first]
        if isinstance(rest, list):
            query += [pair[1] for pair in rest]
        return query

    def visit_entry(self, _node, visited_children):
        adjectives_opt, tags, data_opt, alias_opt = visited_children
        adjectives = set(adjectives_opt[0]) if isinstance(adjectives_opt, list) else None
        data = data_opt[0] if isinstance(data_opt, list) else None
        alias = alias_opt[0][1] if isinstance(alias_opt, list) else None
        cond = Entry(adjectives=adjectives,
                     tags=set(tags),
                     data=data,
                     alias=alias)
        return cond

    def visit_alias(self, _node, visited_children):
        _as, _ws, name = visited_children
        return name

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
        return name

    def visit_data(self, _node, visited_children):
        data = [child[1] for child in visited_children]
        return dict(data)

    def visit_datum(self, _node, visited_children):
        _as, name, val_opt = visited_children
        val = "ANY"
        if isinstance(val_opt, list):
            _ws, _colon, val = val_opt[0]
            val = val[0]
        return name, val

    def visit_number(self, node, _visited_children):
        return float(node.text)

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
