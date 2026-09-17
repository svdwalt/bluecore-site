import random, math, subprocess, os
FONT="Patrick Hand, Chalkboard SE, Comic Sans MS, cursive"
PAPER="#ffffff"
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","assets","blog")
FONTS_CSS="https://fonts.googleapis.com/css2?family=Patrick+Hand&display=swap"
INK="#2b2b2b"; BLUE="#dbe9f7"; GREEN="#e3f2df"; YEL="#fff2c2"; PINK="#fbe0e0"; GREY="#eeeeee"; RED="#c0392b"; ANN="#8a6d1f"; PURP="#ece3f7"
class S:
    def __init__(s, w=1000, h=1000, seed=3):
        s.w,s.h=w,h; s.r=random.Random(seed); s.o=[]; s.top=0
    def j(s,a=1.6): return s.r.uniform(-a,a)
    def path(s, pts, close=False, stroke=INK, sw=2.4, fill="none", dash=None, twice=True):
        def one(off):
            d=""; 
            for i,(x,y) in enumerate(pts):
                x+=s.j(off); y+=s.j(off)
                if i==0: d+=f"M{x:.1f} {y:.1f}"
                else:
                    px,py=pts[i-1]; mx=(px+x)/2+s.j(3); my=(py+y)/2+s.j(3)
                    d+=f" Q{mx:.1f} {my:.1f} {x:.1f} {y:.1f}"
            if close: d+=" Z"
            return d
        da=f' stroke-dasharray="{dash}"' if dash else ""
        s.o.append(f'<path d="{one(1.2)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{da}/>')
        if twice: s.o.append(f'<path d="{one(1.8)}" fill="none" stroke="{stroke}" stroke-width="{sw*0.55}" opacity="0.55" stroke-linecap="round"{da}/>')
    def box(s,x,y,w,h,title="",sub=None,fill=BLUE,fs=22,hatch=False,stroke=INK,dash=None):
        pts=[(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]
        s.path(pts,close=True,fill=fill if not hatch else "url(#hatch)",stroke=stroke,dash=dash)
        if title:
            ty=y+h/2+(fs*0.35 if not sub else fs*0.05) - (0 if not sub else 6*len(sub)/2)
            s.text(x+w/2,ty,title,fs=fs,anchor="middle",bold=True)
            if sub:
                for i,line in enumerate(sub): s.text(x+w/2,ty+fs*0.9+i*17,line,fs=14,anchor="middle")
        s.top=max(s.top,y+h)
    def text(s,x,y,t,fs=16,anchor="start",color=INK,bold=False,rot=0):
        t=t.replace("&","&amp;").replace("<","&lt;")
        fw=' font-weight="bold"' if bold else ""; tr=f' transform="rotate({rot} {x} {y})"' if rot else ""
        s.o.append(f'<text x="{x}" y="{y}" font-size="{fs}" text-anchor="{anchor}" fill="{color}"{fw}{tr}>{t}</text>'); s.top=max(s.top,y+4)
    def note(s,x,y,t,fs=15,color=ANN,anchor="start"): s.text(x,y,t,fs=fs,color=color,anchor=anchor)
    def line(s,x1,y1,x2,y2,stroke=INK,sw=2.4,dash=None,arrow=False,arrow2=False,label=None,lfs=14,loff=-8,lcolor=INK):
        s.path([(x1,y1),(x2,y2)],stroke=stroke,sw=sw,dash=dash)
        a=math.atan2(y2-y1,x2-x1)
        def head(x,y,ang):
            L=13; s.path([(x-L*math.cos(ang-0.45),y-L*math.sin(ang-0.45)),(x,y),(x-L*math.cos(ang+0.45),y-L*math.sin(ang+0.45))],stroke=stroke,sw=sw,twice=False)
        if arrow: head(x2,y2,a)
        if arrow2: head(x1,y1,a+math.pi)
        if label:
            mx,my=(x1+x2)/2,(y1+y2)/2
            s.text(mx+loff*math.sin(a),my-loff*math.cos(a)+5,label,fs=lfs,anchor="middle",color=lcolor)
        s.top=max(s.top,y1,y2)
    def curve(s,pts,stroke=INK,sw=2.4,dash=None,arrow=False):
        s.path(pts,stroke=stroke,sw=sw,dash=dash)
        if arrow:
            (x1,y1),(x2,y2)=pts[-2],pts[-1]; a=math.atan2(y2-y1,x2-x1); L=13
            s.path([(x2-L*math.cos(a-0.45),y2-L*math.sin(a-0.45)),(x2,y2),(x2-L*math.cos(a+0.45),y2-L*math.sin(a+0.45))],stroke=stroke,sw=sw,twice=False)
    def blob(s,cx,cy,rx,ry,fill="none",stroke=INK,dash="7 6",label=None,lfs=18,lpos="top"):
        pts=[(cx+rx*math.cos(t)+s.j(4),cy+ry*math.sin(t)+s.j(4)) for t in [i*2*math.pi/28 for i in range(29)]]
        s.path(pts,close=True,fill=fill,stroke=stroke,dash=dash,sw=2)
        if label: s.text(cx,cy-ry-8 if lpos=="top" else cy+ry+22,label,fs=lfs,anchor="middle",color=stroke,bold=True)
        s.top=max(s.top,cy+ry)
    def cloud(s,cx,cy,w,h,label=None,fill=GREY):
        pts=[]
        for i in range(24):
            t=i*2*math.pi/24; r=1+0.12*math.sin(t*5)
            pts.append((cx+w/2*r*math.cos(t),cy+h/2*r*math.sin(t)))
        pts.append(pts[0]); s.path(pts,close=True,fill=fill)
        if label: s.text(cx,cy+6,label,fs=17,anchor="middle",bold=True)
    def strike(s,x1,y,x2): s.line(x1,y,x2,y,stroke=RED,sw=3)
    def cross(s,x,y,r=10): s.line(x-r,y-r,x+r,y+r,stroke=RED,sw=3); s.line(x-r,y+r,x+r,y-r,stroke=RED,sw=3)
    def tick(s,x,y): s.path([(x-8,y),(x-2,y+7),(x+10,y-9)],stroke="#2e7d32",sw=3,twice=False)
    def tag(s,x,y,t,fill=YEL,fs=14):
        w=len(t)*fs*0.55+18; s.box(x,y-fs-4,w,fs+12,fill=fill); s.text(x+9,y+2,t,fs=fs)
    def save(s,name,height=None,scale=2):
        h=height or int(s.top+30)
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{s.w}" height="{h}" viewBox="0 0 {s.w} {h}" font-family="{FONT}"><defs><filter id="wob" x="-3%" y="-3%" width="106%" height="106%"><feTurbulence type="fractalNoise" baseFrequency="0.015" numOctaves="2" seed="5" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="3" xChannelSelector="R" yChannelSelector="G"/></filter><pattern id="hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="9" stroke="#c9a227" stroke-width="1.4"/></pattern></defs><rect width="{s.w}" height="{h}" fill="{PAPER}"/><g filter="url(#wob)">{"".join(s.o)}</g></svg>'
        d=os.path.join(os.path.dirname(os.path.abspath(__file__)),"build"); os.makedirs(d,exist_ok=True); os.makedirs(OUT,exist_ok=True)
        open(os.path.join(d,name+".svg"),"w").write(svg)
        html=os.path.join(d,name+".html")
        open(html,"w").write(f'<html><head><link rel="stylesheet" href="{FONTS_CSS}"></head><body style="margin:0;background:{PAPER}">{svg}</body></html>')
        out=os.path.abspath(os.path.join(OUT,name+".png"))
        subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome","--headless=new","--disable-gpu","--hide-scrollbars",f"--force-device-scale-factor={scale}",f"--window-size={s.w},{h}","--virtual-time-budget=8000",f"--screenshot={out}","file://"+html],capture_output=True,timeout=90)
        return out
