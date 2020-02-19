from collections import defaultdict
from functools import reduce

from interpreter import *


class TinylandScene:
    def __init__(self):
        self.scene = {}

        self.create_triggers = defaultdict(set)
        self.update_triggers = defaultdict(set)

        self.apps_by_id = {}  # id integer -> app JSON

        self.cur_loop = set()
        self.next_loop = set()
        self.executed = set()
        self.app_runs = defaultdict(lambda: 0)

    def load_app(self, app_json):
        """Process app and store in self.create_triggers or self.update_triggers."""
        [reads, writes] = app_json
        app_id = len(self.apps_by_id)
        if app_json not in self.apps_by_id.values():
            self.apps_by_id[app_id] = app_json
            for match_json in reads:
                [
                    _command,
                    adjectives,
                    relation,
                    tags,
                    data_conditions,
                    alias,
                ] = match_json
                if data_conditions is None:
                    for tag in tags:
                        self.create_triggers[tag].add(app_id)
                else:
                    for tag in tags:
                        self.update_triggers[tag].add(app_id)
                        self.create_triggers[tag].add(app_id)

    def cascade(self, triggers, id_string, tags):
        """Trigger apps based on tags.

        Make sure an app is only triggered once this loop for this id.

        Args:
            triggers: self.create_triggers or self.update_triggers.
            id_string: the id of the object that triggered this cascade.
            tags: the tags of that same object.
        """
        apps_triggered = reduce((lambda x, y: x | y), [triggers[tag] for tag in tags])
        for app_id in apps_triggered:
            execute_args = (app_id, id_string)
            if execute_args not in self.executed:
                self.executed.add(execute_args)
                self.run(*execute_args)
            else:
                self.next_loop.add(execute_args)

    def create(self, id_string: str, thing: dict):
        """Create object in the scene and trigger apps."""
        self.scene[id_string] = thing
        self.cascade(self.create_triggers, id_string, thing["tags"])

    def update(self, id_string: str, data: dict):
        """Update object in the scene and trigger apps."""
        thing = self.scene[id_string]
        self.scene[id_string].update(data)
        self.cascade(self.update_triggers, id_string, thing["tags"])

    def run(self, app_id: int, trigger_id: str) -> dict:
        """Run tinyland app on the tinyland scene.
        
        Args:
            app_id: id for tinyland app. (key in self.apps_by_id)
        """
        app_json = self.apps_by_id[app_id]
        [reads, writes] = app_json

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
                matches = match(match_json, context, self.scene)
                for alias, tup in matches:
                    if tup.id not in [t.id for t in context.values()]:
                        new_contexts.append({alias: tup, **context})
            contexts = new_contexts

        for context in contexts:
            if trigger_id is None or trigger_id in [tup.id for tup in context.values()]:
                for write in writes:
                    if write[0] == Command.CREATE.name:
                        create_id, new_thing = create_from_json(write, context)
                        self.create(create_id, new_thing)
                    elif write[0] == Command.UPDATE.name:
                        update_id, update_data = update_from_json(write, context)
                        self.update(update_id, update_data)

    def execute_loop(self):
        """Run all apps currently in self.cur_loop and prepare next loop.
        
        Returns:
            apps_run (bool): if any apps were run this loop.
        """
        apps_run = False
        while self.cur_loop:
            apps_run = True
            self.run(*self.cur_loop.pop())
        self.executed = set()
        self.cur_loop, self.next_loop = self.next_loop, set()
        return apps_run
