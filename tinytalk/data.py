from collections import defaultdict
from deep_merge import merge

data = defaultdict(list)

def commit(name, *args):
    global data
    names = [name] + list(args)[:-1]
    commit_data = list(args)[-1]
    for name in names:
        data = merge(data, {name: merge({"names": names}, commit_data)})

def query(search):
    return data[search]
