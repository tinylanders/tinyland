"""Functions for running compiled tinytalk apps on a scene."""

from collections import defaultdict, namedtuple
from deep_merge import merge
import uuid

from .grammar import Command


# Dict mapping adjective names in tinytalk to functions that filter a list
# of tinyland things.
adjectives = {
    "only": lambda l: return l if len(l) == 1 else []
}


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
        return (condition(var_name, context, cond_json[1], row) and
                condition(var_name, context, cond_json[2], row))
    else:
        [operator, left, right] = cond_json

        if isinstance(left, str) and "." in left:
            alias, attribute = left.split(".")
            left = lookup(context[alias], attribute)
        else:
            left = lookup(left, row) or left
        
        if isinstance(right, str) and "." in right:
            alias, attribute = right.split(".")
            right = lookup(context[alias], attribute)
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


def match(match_json: list, context: dict, scene: dict) -> list:
    """Search the tinyland scene for objects that match statement.

    Specifically, return each object in `scene` that satisfies `match_json`
    given `context`.

    Args:
        match_json: json for match.
        context: in apps with multiple match statements, this maps previous
            matched objects to their aliases so that the current match can use
            that data.
        scene: "database" of all that exists in tinyland. The current implementation
            assumes the following structure:
                {
                    "appMarkers": {
                        <marker-id>: {
                            "type": "marker",
                            "id": <marker-id>,
                            ...
                        },
                        ...
                    },
                    "virtualObjects": {
                        <object-id>: {
                            "type": <tags>,
                            ...
                        },
                        ...
                    }
                }
    """
    [_command, adjectives, relation, tags, data_conditions, alias] = match_json

    #TODO: match first appearance of something

    # Filter by tags.
    matches = []
    for key, thing in {**scene["allMarkers"], **scene["virtualObjects"]}.items():
        thing_tup = tup(id=key, **thing)
        if set(thing_tup.type.split(" ")) == set(tags):
            matches.append(thing_tup)
    
    # Filter by adjectives.
    for adjective in adjectives:
        matches = adjectives[adjective](matches)

    #TODO: Filter by relation (requires previous match contexts?)

    # Filter by data_conditions.
    for var_name, cond in data_conditions.items():
        if cond[0] == Command.COND.name:
            # This is currently necessary because condition can be "ANY".
            cond = cond[1]
        matches = filter(lambda row: condition(var_name, context, cond, row), matches)

    # The following format makes it easier for match combinations
    # to be turned into context dictionaries.
    return [(alias, m) for m in matches]


def create(create_json: list, context: dict, scene: dict) -> dict:
    """Create a new tinyland object in the scene.
    
    Args:
        create_json: json for create statement.
        context: aliases mapped to their match statements.
        scene: "database" of all that exists in tinyland.
            See match docstring for schema.
    Returns:
        new_scene: `scene` with the new object added.
    """
    [_command, tags, relation, data] = create_json

    parsed_data = {}
    for var, value in data.items():
        if isinstance(value, str) and "." in value:
            alias, attribute = value.split(".")
            parsed_data[var] = lookup(context[alias], attribute)
        else:
            parsed_data[var] = value

    new_thing = {
        "type": " ".join(tags),
        relation: [tup.id for tup in context],
        **parsed_data
    }

    new_scene = {
        "allMarkers": **scene["allMarkers"],
        "virtualObjects": {
            uuid.UUID(): new_thing,
            **scene["virtualObjects"]
        }
    }

    #TODO: implement relation stuff

    return new_scene


def update(update_json: list, context: dict, scene: dict) -> dict:
    """Update the desired object in tinyland scene.
    
    Args:
        update_json: json for update statement.
        context: aliases mapped to their match statements.
        scene: "database" of all that exists in tinyland.
            See match docstring for schema.
    Returns:
        new_scene: `scene` with the object updated.
        """
    [_command, alias, data] = update_json

    parsed_data = {}
    for var, value in data.items():
        if isinstance(value, str) and "." in value:
            alias, attribute = value.split(".")
            parsed_data[var] = lookup(context[alias], attribute)
        else:
            parsed_data[var] = value
    
    update_id = context[alias].id
    updated_thing = scene["virtualObjects"][update_id]
    updated_thing.update(parsed_data)

    new_scene = scene.copy()
    new_scene["virtualObjects"][update_id] = updated_thing

    return new_scene


def run(app_json: list, scene: dict) -> dict:
    """Run tinyland app on the tinyland scene.
    
    Args:
        app_json: json for tinyland app.
        scene: "database" of all that exists in tinyland.
            See match docstring for schema.
    Returns:
        new_scene: the state of tinyland after running the app on `scene`.
    """
    [reads, writes] = app_json

    new_scene = scene.copy()

    # We need to find all combinations of our match statements.
    # contexts will hold one context for each time we need to run the
    # write portion of our app.
    contexts = [{}]

    # Populate contexts.
    for match_json in reads:
        new_contexts = []
        for context in contexts:
            # For each context holding n-1 matches,
            # find matches and create an new context with the nth match.
            matches = match(match_json, context, scene)
            for alias, tup in matches:
                new_contexts.append({alias: tup, **context})
        contexts = new_contexts

    for context in contexts:
        for write in writes:
            if write[0] == Command.CREATE.name:
                new_scene = create(write, context, new_scene)
            elif write[0] == Command.UPDATE.name:
                new_scene = update(write, context, new_scene)
    
    return new_scene
    


