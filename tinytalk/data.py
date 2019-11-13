from collections import defaultdict, namedtuple
from deep_merge import merge

from .grammar import Command

data = defaultdict(list)


def lookup(name: str, namespace: namedtuple):
    if hasattr(namespace, str(name)):
        return getattr(namespace, name)
    return None


def condition(var_name, cond, row: namedtuple) -> bool:
    if not hasattr(row, var_name):
        return False
    elif cond == "ANY":
        return True
    elif cond[0] == Command.AND.name:
        return condition(var_name, cond[1], row) and condition(var_name, cond[2], row)
    else:
        [operator, left, right] = cond

        # Check if left and right are variable names and access their values if so
        left = lookup(left, row) or left
        right = lookup(right, row) or right

        if operator in ["is"]:
            return left == right
        elif operator in ["<"]:
            return left < right
        elif operator in [">"]:
            return left > right
        elif operator in ["not"]:
            return left != right


def match(mat: list) -> None:
    """Retrieve each matching entry in the database.

    Assumes database var, `data`, is of the form:
    {
        <tag>(str): [
            <entry>(namedtuple),
            <entry>(namedtuple),
            ...
        ],
        <tag>(str): [...]
    }
    
    Args:
        mat (list): [
            _command: "MATCH"
            adjectives: list of adjectives
            relation: relation to previous matched items
            tags: list of tags
            data_conditions: dict mapping var names to condition (list or "ANY")
            alias: str alias for entries that match above criteria
        ]
    Returns:
        alias: str alias for the matches
        matches (list<tuple>): database rows that match criteria
    """
    [_command, adjectives, relation, tags, data_conditions, alias] = mat

    # Filter by tags, there must be at least one.
    matches = set(data[tags[0]])
    for tag in tags[1:]:
        matches &= set(data[tag])
    
    #TODO: Filter by adjectives
    #TODO: Filter by relation (requires previous match contexts?)

    # Filter by data_conditions
    for var_name, cond in data_conditions.items():
        if cond[0] == Command.COND.name:
            cond = cond[1]
        matches = filter(lambda row: condition(var_name, cond, row), matches)

    return alias, matches


def commit(name, *args):
    global data
    names = [name] + list(args)[:-1]
    commit_data = list(args)[-1]
    for name in names:
        data = merge(data, {name: merge({"names": names}, commit_data)})


def query(search):
    return data[search]
