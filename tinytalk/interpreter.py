from collections import namedtuple
import uuid

from grammar import Command

# Dict mapping adjective names in tinytalk to functions that filter a list
# of tinyland things.
adjectives = {"only": lambda l: l if len(l) == 1 else []}


def tup(**kwargs) -> namedtuple:
    """Convert an arbitrary number of kwargs to a namedtuple."""
    tup = namedtuple("tinyTuple", list(kwargs))
    return tup(**kwargs)


def lookup(name: str, namespace: namedtuple):
    if hasattr(namespace, str(name)):
        return getattr(namespace, name)
    return None


def condition(var_name: str, context: dict, cond_json, row: namedtuple) -> bool:
    """Check if condition holds true for the given parameters.

    Specifically, if the `var_name` attribute of `row` satisfies `cond_json` given
    `context`.
    
    Args:
        var_name: the attribute in row to which the condition will be applied.
        context: in apps with multiple match statements, this maps previous
            matched objects to their aliases so that the current match can use
            that data.
        cond_json: json object for data_condition.
        row: the tinyland object to which the condition is being applied.
    
    Returns:
        bool: Whether the condition is satisfied.
    """
    if not hasattr(row, var_name):
        return False
    elif cond_json == "ANY":
        return True
    elif cond_json[0] == Command.AND.name:
        return condition(var_name, context, cond_json[1], row) and condition(
            var_name, context, cond_json[2], row
        )
    else:
        [operator, left, right] = cond_json

        if isinstance(left, str) and "." in left:
            alias, attribute = left.split(".")
            left = lookup(attribute, context[alias])
        else:
            left = lookup(left, row) or left

        if isinstance(right, str) and "." in right:
            alias, attribute = right.split(".")
            right = lookup(attribute, context[alias])
        else:
            right = lookup(right, row) or right

        if operator in ["is"]:
            return left == right
        elif operator in ["<"]:
            return left < right
        elif operator in [">"]:
            return left > right
        elif operator in ["not"]:
            return left != right


def expression(expr_json: list, var_name: str, context: dict, row: namedtuple):
    """Parse compiled app JSON expression and return value.
    
    Args:
        expr_json: json representing visited expr node.
        var_name: name of the variable set to this expression.
        context: dict for looking up aliases and names used in expression.
        row: named tuple for looking up attributes referenced in expression.
    """
    if type(expr_json) not in [list, tuple]:
        if isinstance(expr_json, str) and "." in expr_json:
            alias, attribute = expr_json.split(".")
            result = lookup(attribute, context[alias])
        else:
            result = lookup(expr_json, row) or expr_json
        # print(f"\n\n{result}\n\n")
        return result
    else:
        [operator, left, right] = expr_json
        left = expression(left, var_name, context, row)
        right = expression(right, var_name, context, row)
        if operator in ["*"]:
            return left * right
        elif operator in ["+"]:
            return left + right
        elif operator in ["-"]:
            return left - right


def match(match_json: list, context: dict, scene: dict) -> list:
    """Search the tinyland scene for objects that match statement.

    Specifically, return each object in `scene` that satisfies `match_json`
    given `context`.

    Args:
        match_json: json for match.
        context: in apps with multiple match statements, this maps previous
            matched objects to their aliases so that the current match can use
            that data.
        scene: "database" of all that exists in tinyland.
    """
    [_command, adjectives, relation, tags, data_conditions, alias] = match_json

    # TODO: match first appearance of something

    # Filter by tags.
    matches = []
    for key, thing in scene.items():
        if "id" not in thing:
            thing["id"] = key
        thing_tup = tup(**thing)
        if set(thing_tup.type.split(" ")) == set(tags):
            matches.append(thing_tup)

    # Filter by adjectives.
    if adjectives is not None:
        for adjective in adjectives:
            matches = adjectives[adjective](matches)

    # TODO: Filter by relation (requires previous match contexts?)

    # Filter by data_conditions.
    if data_conditions is not None:
        for var_name, cond in data_conditions.items():
            if cond[0] == Command.COND.name:
                # This is currently necessary because condition can be "ANY".
                cond = cond[1]
            matches = list(
                filter(lambda row: condition(var_name, context, cond, row), matches)
            )

    # The following format makes it easier for match combinations
    # to be turned into context dictionaries.
    return [(alias, m) for m in matches]


def create_from_json(create_json: list, context: dict, create_id: str = None):
    """Create a new tinyland object in the scene.
    
    Args:
        create_json: json for create statement.
        context: aliases mapped to their match statements.
    """
    [_command, tags, relation, data] = create_json

    parsed_data = {}
    for var, value in data.items():
        parsed_data[var] = expression(value, var, context, ())

    create_id = create_id or str(uuid.uuid4())

    new_thing = {"tags": tags, "type": " ".join(tags), "id": create_id, **parsed_data}

    if relation:
        new_thing[relation] = ([tup.id for tup in context.values()],)

    return create_id, new_thing


def update_from_json(update_json: list, context: dict) -> dict:
    # print("UPDATE TRIGGERED BY APP")
    """Update the desired object in tinyland scene.
    
    Args:
        update_json: json for update statement.
        context: aliases mapped to their match statements.
    """
    [_command, alias, data] = update_json

    parsed_data = {}
    for var, value in data.items():
        parsed_data[var] = expression(value, var, context, ())
    return context[alias].id, parsed_data
