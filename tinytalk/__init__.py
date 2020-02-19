# sample tinytalk programs

# syntax for data:
# key(: val)?

# syntax for a search:
# "WHEN" adjective* tag+ (data([, ]+ data)+)? ("as" name)?

## query-only visible aruco markers database (owned by aruco detection layer
## outside tinytalk)
# aruco = [#aruco #visible "id": 111, "x": 0, "y": 0],
#         [#aruco #visible "id": 215, "x": 500, "y": 101]

## add arucos to vessels
# when:
#   [#aruco id x y]
# claim:
#   [#vessel "id": id, "x": x, "y": y]

## yields this vessels database:
# vessels = [#vessel "id": 111, "x": 0, "y": 0],
#           [#vessel "id": 215, "x": 500, "y": 101]

## this is a valid claim
# when:
#   vessel = [#vessel "x": 0, "y": 0]
# wish:
#   vessel.affinity = vessel.affinity + 1
#   vessel.element = "fire"
