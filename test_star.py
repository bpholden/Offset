from __future__ import print_function

import Star


lines = []

lines.append("HR5867 15 46 11.254 15 25 18.6 2000 pmra=65.38 pmdec=-38.61 vmag=3.66 texp=1200 I2=Y lamp=none uth=4 utm=58 expcount=1e+09 decker=B do=Y count=0 foc=0 owner=public")
lines.append("30Doradus 15 46 11.754 15 25 18.6 2000 pmra=0.0 pmdec=0.0 vmag=21 texp=400 I2=Y lamp=none uth=4 utm=58 expcount=1e+09 decker=B do=N count=3 foc=0 owner=A.Siemion blank=yes # this is a comment")
lines.append("M13 15 46 10.754 15 25 18.6 2000 pmra=0.0 pmdec=0.0 vmag=21 texp=400 I2=Y lamp=none uth=4 utm=58 expcount=1e+09 decker=B do=N count=3 foc=0 owner=A.Siemion blank=yes")

stars = []

for l in lines:
    s = Star.Star(starlist_line=l)
    s.parse()
    stars.append(s)

for s in stars:
    print(s)
