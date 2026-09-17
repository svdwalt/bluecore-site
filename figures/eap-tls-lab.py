"""Lab diagram for the EAP-TLS post: test host, ISE, services host, workstation."""
from sketch import *
s = S(w=1000, h=780, seed=7)

def panel(x, y, w, h, title, sub, rows, fill, col2=None):
    s.box(x, y, w, h, fill=fill)
    s.text(x+18, y+34, title, fs=22, bold=True)
    if sub: s.text(x+18, y+56, sub, fs=14, color="#5a564d")
    yy = y + (84 if sub else 66)
    for r in rows:
        if isinstance(r, tuple):
            s.text(x+18, yy, r[0], fs=16, bold=True); s.text(x+(col2 or 130), yy, r[1], fs=15)
        else:
            s.text(x+18, yy, "- " + r, fs=15)
        yy += 27

# workstation
panel(30, 30, 270, 108, "Workstation", None, ["git repo: cases, runner,", "results, config snapshot"], GREY)
# test host
panel(30, 220, 320, 260, "Test host  (Linux VM)", "stands in for switches and devices",
      [("eapol_test", "802.1X, EAP-TLS"), ("radclient", "MAB"), ("corpus", "27 test certificates"),
       ("runner", "YAML cases, results"), ("tcpdump", "RADIUS captures")], BLUE, col2=140)
# ISE
panel(640, 220, 330, 260, "Policy server  (Cisco ISE 3.5)", "the device under test",
      ["network device = test host", "trusted CA + OCSP check", "EAP server certificate",
       "policy sets, authz rules", "ERS + OpenAPI"], GREEN)
# services host
panel(190, 590, 640, 120, "Services host  (Linux VM)", None,
      ["root + issuing CA (openssl)", "CRL + CA cert web :80"], PURP)
s.text(520, 656, "- OCSP responder :2560", fs=15); s.tag(730, 656, "stoppable", fill=YEL, fs=13)
s.text(520, 683, "- DNS + NTP time source", fs=15)

# the test itself, solid
s.line(350, 330, 640, 330, arrow=True, sw=2.8)
s.text(495, 318, "1  RADIUS Access-Request", fs=17, anchor="middle", bold=True)
s.text(495, 352, "udp/1812, EAP-TLS or MAB", fs=13, anchor="middle", color="#5a564d")
s.line(640, 420, 350, 420, arrow=True, sw=2.8)
s.text(495, 446, "4  Accept + VLAN, or Reject", fs=17, anchor="middle", bold=True)
s.line(740, 480, 740, 590, arrow=True, sw=2.8)
s.text(730, 528, "2  OCSP: revoked?", fs=16, anchor="end", bold=True)
s.text(730, 548, "tcp/2560", fs=13, anchor="end", color="#5a564d")
s.line(820, 590, 820, 480, arrow=True, sw=2.8)
s.text(832, 540, "3  good / revoked", fs=16, bold=True)

# setup and results, dashed
s.line(165, 138, 165, 220, dash="6 6", arrow=True, arrow2=True, sw=2)
s.text(178, 172, "rsync cases in,", fs=13, color=ANN); s.text(178, 190, "results back", fs=13, color=ANN)
s.curve([(300, 84), (600, 84), (805, 84), (805, 220)], dash="6 6", arrow=True, sw=2)
s.text(552, 72, "API: build config, import CA + EAP cert, capture snapshot", fs=13, anchor="middle", color=ANN)
s.line(270, 590, 270, 480, dash="6 6", arrow=True, sw=2)
s.text(282, 528, "certificates + keys", fs=13, color=ANN); s.text(282, 546, "copied to test host", fs=13, color=ANN)

s.text(500, 748, "solid 1 to 4: one test, e.g. a revoked certificate must come back Access-Reject", fs=14, anchor="middle", color="#5a564d")
s.text(500, 768, "dashed: setup and results", fs=14, anchor="middle", color="#5a564d")
print(s.save("eap-tls-lab", height=780))
