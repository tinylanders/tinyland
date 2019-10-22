from parsimonious.grammar import Grammar

grammar = Grammar(
    r"""
    query = "when" ws condition ((";" / ~"\n") ws? condition)*
    condition = adjective (ws adjective)* (ws tag)+ (ws data)* (ws "as" ws name)? ws?
    ws = ~"([ \t,])+"
    adjective = "one" / "only" / "global" / "nearest" / "friend"
    tag = "#" name
    data = name (":" ws value)?
    value = number / string / boolean
    boolean = "true" / "false"
    string = ~'"[ ^\"]*"'
    number = ("+" / "-")? digit+ ("." digit+)?
    digit = ~"[0-9]+"
    name  = ~"[a-z][a-z_-]*"
    """)
