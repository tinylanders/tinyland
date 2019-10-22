from parsimonious.grammar import Grammar, NodeVisitor

grammar = Grammar(
    r"""
    query = "when" condition (";" condition)*
    condition = adjectives? tags data? (ws alias)?
    adjectives = (ws adjective)+
    tags = (ws tag)+
    data = (ws datum)+
    alias = "as" ws name
    ws = ~"([ \t\n,])+"
    adjective = "one" / "only" / "global" / "nearest" / "friend"
    tag = "#" name
    datum = name (":" ws value)?
    value = number / string / boolean
    boolean = "true" / "false"
    string = ~'"[ ^\"]*"'
    number = ("+" / "-")? digit+ ("." digit+)?
    digit = ~"[0-9]+"
    name  = ~"[a-z][a-z_-]*"
    """)

class TinyTalkVisitor(NodeVisitor):
    # def visit_query(self, node, visited_children):
    #     """ Returns the overall output. """
    #     output = {}
    #     for child in visited_children:
    #         output.update(child[0])
    #     return output

    def visit_condition(self, node, visited_children):
        _, tags, *_ = visited_children
        return tags

    def visit_tags(self, node, visited_children):
        return visited_children

    def visit_tag(self, node, visited_children):
        print("***** the node's children:")
        print(node.children)
        _, name = node.children
        print("***** name.text")
        print(name.text)
        return name.text

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
