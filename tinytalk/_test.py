import grammar
import interpreter

app = "when [#marker x y] as m create [#ball x: m.y, y: m.x]"

tree = grammar.grammar.parse(app)
visitor = grammar.TinyTalkVisitor()
app_json = visitor.visit(tree)

scene = {
    "appMarkers": {
        "1": {
            "type": "marker",
            "x": 50,
            "y": 0,
        }
    },
    "virtualObjects": {
    }
}

print(app_json)

new_scene = interpreter.run(app_json, scene)

print(scene)
print(new_scene)