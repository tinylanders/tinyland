from collections import defaultdict, namedtuple
from deep_merge import merge
import uuid

from .grammar import Command


adjectives = {
    "only": lambda l: return l if len(l) == 1 else []
}


def tup(**kwargs):
    tup = namedtuple("tinyTuple", list(kwargs))
    return tup(**kwargs)


def lookup(name: str, namespace: namedtuple):
    if hasattr(namespace, str(name)):
        return getattr(namespace, name)
    return None


def condition(var_name, context, cond, row: namedtuple) -> bool:
    if not hasattr(row, var_name):
        return False
    elif cond == "ANY":
        return True
    elif cond[0] == Command.AND.name:
        return (condition(var_name, context, cond[1], row) and
                condition(var_name, context, cond[2], row))
    else:
        [operator, left, right] = cond

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


def match(m: list, context: dict, scene: dict) -> tuple:
    [_command, adjectives, relation, tags, data_conditions, alias] = m


    # Filter by tags, there must be at least one.
    matches = []
    for key, thing in {**scene["allMarkers"], **scene["virtualObjects"]}.items():
        thing_tup = tup(id=key, **thing)
        if set(thing_tup.type.split(" ")) == set(tags):
            matches.append(thing_tup)
    
    for adjective in adjectives:
        matches = adjectives[adjective](matches)

    #TODO: Filter by relation (requires previous match contexts?)

    # Filter by data_conditions
    for var_name, cond in data_conditions.items():
        if cond[0] == Command.COND.name:
            cond = cond[1]
        matches = filter(lambda row: condition(var_name, context, cond, row), matches)

    return [(alias, m) for m in matches]


def create(c: list, context: dict, scene: dict) -> dict:
    [_command, tags, relation, data] = c

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


def update(u: list, context: dict, scene: dict) -> dict:
    [_command, alias, data] = u

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
    [reads, writes] = app_json
    context = {}

    new_scene = scene.copy()

    contexts = [{}]

    for match_json in reads:
        new_contexts = []
        for context in contexts:
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
    


