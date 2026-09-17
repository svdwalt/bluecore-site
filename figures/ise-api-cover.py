"""Cover for the ISE API coverage post, 1200x630."""
from sketch import *
s = S(w=1200, h=630, seed=33)
s.text(50, 62, "BlueCore lab notes", fs=22, color=ANN)
s.text(50, 150, "Cisco ISE 3.5 by API", fs=64, bold=True)
s.text(50, 200, "How much you can automate,", fs=30, color="#5a564d")
s.text(50, 236, "and where the API stops", fs=30, color="#5a564d")
points = ["more coverage than assumed", "a short GUI-only list", "errors that point the wrong way",
          "accepted is not working", "side effects: restarts, lockout"]
y = 300
for p in points:
    s.text(50, y, "- " + p, fs=24)
    y += 46
s.text(50, 590, "bluecore.joburg/blog   -   ERS and OpenAPI, measured not assumed", fs=18, color="#5a564d")

# checklist card
s.box(680, 90, 470, 440, fill=BLUE)
s.text(700, 126, "ISE 3.5 p3: coverage, measured", fs=22, bold=True)
items = [("network devices", 1), ("endpoints + identity groups", 1), ("authorization profiles", 1),
         ("certificate auth profiles", 1), ("identity source sequences", 1), ("trusted + system certificates", 1),
         ("policy sets + rules", 1), ("allowed protocols (EAP methods)", 1), ("ODBC identity source", 0)]
yy = 168
for name, ok in items:
    if ok: s.tick(716, yy - 4)
    else: s.cross(716, yy - 6, r=8)
    s.text(740, yy, name, fs=20)
    yy += 36
s.box(700, 478, 430, 40, fill=PINK)
s.text(714, 505, "allowedAsUserName: true  ->  HTTP 500", fs=19, color=RED, bold=True)
print(s.save("ise-api-cover", height=630))
