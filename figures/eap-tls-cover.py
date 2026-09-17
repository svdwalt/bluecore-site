"""Cover for the EAP-TLS post, 1200x630."""
from sketch import *
s = S(w=1200, h=630, seed=21)
s.text(50, 62, "BlueCore lab notes", fs=22, color=ANN)
s.text(50, 150, "EAP-TLS on Cisco ISE 3.5", fs=64, bold=True)
s.text(50, 200, "What the defaults let through,", fs=30, color="#5a564d")
s.text(50, 236, "tested without a single switch", fs=30, color="#5a564d")
findings = ["revocation off after CA import", "OCSP down: fails open", "24-hour OCSP cache",
            "clientAuth not enforced", "MAC binding is literal"]
y = 300
for i, f in enumerate(findings, 1):
    s.tag(50, y, f"{i}", fill=YEL, fs=18)
    s.text(100, y, f, fs=24)
    y += 50
s.text(50, 590, "bluecore.joburg/blog   -   openssl, eapol_test, radclient", fs=18, color="#5a564d")

# one negative test, drawn as a note card
s.box(660, 110, 490, 400, fill=GREY)
s.text(680, 146, "test host: one negative test", fs=22, bold=True)
lines = ["# responder stopped on purpose", "$ sudo systemctl stop lab-ocsp", "",
         "$ eapol_test -c office-revoked.conf", "     -a 192.0.2.10 -s SECRET -r0",
         "RADIUS message: code=2 (Access-Accept)", "   Attribute 81 (Tunnel-Private-Group-Id)",
         "      Value: 013130", "SUCCESS"]
yy = 186
for l in lines:
    if l: s.text(690, yy, l, fs=18, color="#2b2b2b" if not l.startswith(("#",)) else ANN)
    yy += 28
s.box(680, 436, 440, 50, fill=PINK)
s.cross(706, 461, r=9)
s.text(728, 469, "revoked certificate, office VLAN 10", fs=22, color=RED, bold=True)
print(s.save("eap-tls-cover", height=630))
