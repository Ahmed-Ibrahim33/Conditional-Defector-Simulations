breed [plants plant]
breed [foragers forager]

foragers-own
[eattype
 energy
 flockmates
 mypatch]

patches-own [
  is-gap?
  seedpatch?
  seedpatchnum
  foodpatch?
  foodpatchnum
  assortindex
  resource]

globals
[patch-width
 gap
 foodpatchlist
 growth-rate
 carryingcap
 ;;maxpop
 costchild
]

to setup
  clear-all

  set patch-width Size-Resource-Areas
  set gap Distance-Resource-Areas
  set growth-rate 0.2
  set carryingcap 10
  ;;set maxpop 400

  setup-plants
  setup-frgs
  set costchild 10

  reset-ticks
end

to setup-plants
 foreach [ 0 1 2 3 4 5 6 7 8 9 10 11 12 13]
  [ x  ->
      foreach [ 0 1 2 3 4 5 6 7 8 9 10 11 12 13] [ y  ->
  ask patches with [ pxcor = ( gap / 2 ) + (x * ( gap + (patch-width )))  and pycor =  ( gap / 2 ) + (y * (gap + (patch-width))) ]
  [set seedpatch? true
        sprout-plants 1 [set hidden? true]
        set seedpatchnum [who] of plants-here
   ]
  ]
  ]

  ask patches with [seedpatch? = true]
  [ let localpatch (patch-set self patches in-radius patch-width)
    ask localpatch
     [ set resource carryingcap

       if resource = 0 [set resource 0.1]
        set pcolor scale-color brown resource 0 (carryingcap + 10)
        set foodpatch? true
        set foodpatchnum [seedpatchnum] of localpatch with [seedpatch? = true]

    ]
  ]

  set foodpatchlist (  [who] of plants )


end

to setup-frgs
  ask n-of (Number-Agents * Percent-Sustainables / 100) patches with [foodpatch? = true]
  [sprout-foragers 1
    [
      set eattype "low"

    set color green
    set mypatch [foodpatchnum] of patch-here ]
  ]

   ask n-of (Number-Agents * ( 100 - Percent-Sustainables) / 100) patches with [foodpatch? = true]
  [sprout-foragers 1
    [
      set eattype "high"

      set color red
      set mypatch [foodpatchnum] of patch-here
    ]
  ]

  ask foragers [
    if Agents = "People" [ set shape "person"]
    if Agents = "Bacteria" [ set shape "bacteria" ]
    if Agents = "Cows" [ set shape "cow"]
    if Agents = "Cells" [ set shape "cell"]
  set size 2
  set energy Living-costs]
   ask foragers
  [ ask  patches in-radius patch-width [ set is-gap? false ] ]

end

to go

   ask foragers [ flock ]
   ask foragers [
    if Agents = "People" [ set shape "person"]
    if Agents = "Bacteria" [ set shape "bacteria" ]
    if Agents = "Cows" [ set shape "cow"]
    if Agents = "Cells" [ set shape "cell"]]

  move
  eat
  if Evolution? [reproduce]
  expend-energy
  if Evolution? [death]

  ask patches with [foodpatch? = true]
  [regrow
    recolor]

  tick
end

to flock
  find-flockmates
end


to find-flockmates
  set flockmates other foragers in-radius group-dispersal-range  with [color = [color] of myself]
end


to move
  ask foragers
  [let local ( patch-set patch-here ( patches in-radius 2 with [not any? foragers-here] ))
   if local != nobody
    [let local-max  ( max-one-of local [resource]  )
    ifelse local-max != nobody and [resource] of local-max >= Living-costs
      [face local-max
        move-to local-max
        set mypatch [foodpatchnum] of patch-here
      ]
      [if any? ( patches in-radius 2 with [not any? foragers-here] )
        [move-to one-of ( patches in-radius 2 with [not any? foragers-here] )]]
      if is-gap? != false and (count flockmates >= 1) [set energy (energy - (dispersal-costs / (count flockmates + 1)) )]
      if is-gap? != false and (count flockmates = 0) [set energy (energy - dispersal-costs)]
  ]
  ]
end

to eat
  ask foragers
  [ifelse eattype = "low"
    [ set  energy energy + ([resource] of patch-here * 0.5)
      ask patch-here [set resource resource / 2]]
    [ set  energy energy + ([resource] of patch-here * 0.99)
      ask patch-here [set resource resource - (0.99 * resource) ]]
  ]

end

to reproduce
 ask foragers
  [ let birthrate 0.0005 * energy
  if energy > costchild and random-float 1 < birthrate [
     let destination one-of neighbors with [not any? turtles-here]
     if destination != nobody [
        hatch 1 [
          move-to destination
          mutate
          set energy costchild ]
        set energy (energy - costchild)
       ]
      ]
      ]
end

to mutate
  if random-float 1 < Mutation-rate
  [ifelse eattype = "low"
    [set eattype "high"]
    [set eattype "low"]
    update-color
  ]
end

to expend-energy
  ask foragers [set energy energy - Living-costs ]
end

to death
  ask foragers
  [if energy <= 0 [die]
  ]
end

to regrow
  ifelse resource >= 0.1
  [set resource precision (resource + ((growth-rate * resource) * (1 - (resource / carryingcap )))) 3]
  [set resource 0.1]
end

to recolor ;; patch
  set pcolor scale-color brown resource 0 (carryingcap + 10)
end

to update-color
  ifelse eattype = "low"
    [set color green]
    [set color red]
end

to calcassort
  foreach (foodpatchlist) [ x ->
    let foodpatch patches with [foodpatchnum = x]
    let lowfrgs count foragers with [eattype = "low" and mypatch = x]
    let frgs count foragers with [ mypatch = x]
    ask patches with [seedpatch? = true and seedpatchnum = x]
      [ set assortindex (lowfrgs / frgs) ]
    ]


end

;;;;;;;;;;;;;;;;;;reporters;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

to-report avenhigh
  report sum [energy] of foragers with [eattype = "high"] / count foragers with [eattype = "high"]
end

to-report avenlow
  report sum [energy] of foragers with [eattype = "low"] / count foragers with [eattype = "low"]
end

to-report gensim-pop
  report ( count patches with [seedpatch? = true] - 1) / (count foragers - 1)

end

to-report avassort
  report sum [assortindex] of patches with [seedpatch? = true] / count patches with [seedpatch? = true]
end
@#$#@#$#@
GRAPHICS-WINDOW
207
10
775
579
-1
-1
5.0
1
10
1
1
1
0
0
0
1
0
111
0
111
0
0
1
Iterations
30.0

BUTTON
15
10
112
43
Setup
setup
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
15
87
111
120
Start
go
T
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
15
48
112
81
Once
go
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

SLIDER
14
298
187
331
Percent-Sustainables
Percent-Sustainables
0
100
90.0
1
1
NIL
HORIZONTAL

SLIDER
15
264
187
297
Number-Agents
Number-Agents
0
count patches with [foodpatch? = true] / 2
80.0
1
1
NIL
HORIZONTAL

PLOT
781
10
1166
215
Average Energy of Agents
NIL
NIL
0.0
10.0
0.0
10.0
true
true
"" ""
PENS
"Sustainable" 1.0 0 -10899396 true "" "carefully [plot avenlow][plot 0]"
"Greedy" 1.0 0 -2674135 true "" "carefully  [plot avenhigh] [plot 0]"

PLOT
781
217
1164
428
Trait frequencies (global, %)
NIL
NIL
0.0
10.0
0.0
100.0
true
true
"" ""
PENS
"Sustainable" 1.0 0 -10899396 true "" "carefully [plot ( count foragers with [eattype = \"low\"] / count foragers ) * 100][plot 0]"
"Greedy" 1.0 0 -2674135 true "" "carefully [plot (count foragers with [eattype = \"high\"] / count foragers ) * 100] [plot 0]"

SWITCH
785
459
897
492
Evolution?
Evolution?
0
1
-1000

CHOOSER
13
365
151
410
Agents
Agents
"People" "Bacteria" "Cells" "Cows"
1

SLIDER
12
411
196
444
Distance-Resource-Areas
Distance-Resource-Areas
8
40
20.0
2
1
NIL
HORIZONTAL

SLIDER
11
445
195
478
Size-Resource-Areas
Size-Resource-Areas
1
20
4.0
1
1
NIL
HORIZONTAL

SLIDER
11
479
194
512
Living-costs
Living-costs
0
5
1.0
0.5
1
NIL
HORIZONTAL

TEXTBOX
1180
14
1348
140
Resource carrying capacity: 10\nResource growth rate: 0.2\n\nResource consumption of sustainables: \n50% of resources of a patch\n\nResource consumption of greedy: \n99% of resources of a patch
11
0.0
1

SLIDER
11
512
197
545
Mutation-rate
Mutation-rate
0
10
0.0
0.1
1
%
HORIZONTAL

PLOT
934
431
1163
581
Agent Population
NIL
NIL
0.0
10.0
0.0
100.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot count foragers"

TEXTBOX
786
501
915
543
Agents reproduce with a probability of \n(0.0005 * Energy)
11
0.0
1

SLIDER
13
332
185
365
group-dispersal-range
group-dispersal-range
0
200
0.0
1
1
NIL
HORIZONTAL

SLIDER
13
331
185
364
dispersal-costs
dispersal-costs
0
10
8.0
0.5
1
NIL
HORIZONTAL

MONITOR
15
218
95
263
cooperators
count foragers with [eattype = \"low\"]
17
1
11

MONITOR
97
219
154
264
greedy
count foragers with [eattype = \"high\"]
17
1
11

MONITOR
15
173
72
218
total
count foragers
17
1
11

SLIDER
11
545
183
578
group-dispersal-range
group-dispersal-range
0
200
0.0
10
1
NIL
HORIZONTAL

@#$#@#$#@
## Model Information and Materials

Model Google Drive Link: https://drive.google.com/open?id=146kpnta3oq6AjH-rZXyzYzOIW5XWXw7f

Model GUI overview: https://drive.google.com/open?id=146kpnta3oq6AjH-rZXyzYzOIW5XWXw7f

## References and Citation


Model elements based on:

* Pepper, J. W., & Smuts, B. (2001). Agent-based modeling of multilevel selection: The evolution of feeding restraint as a case study. Natural Resources and Environmental Issues, 8, 57–68. Retrieved from http://digitalcommons.usu.edu/cgi/viewcontent.cgi?article=1340&context=nrei

* Pepper, J. W., & Smuts, B. B. (2002). A mechanism for the evolution of altruism among nonkin: Positive assortment through environmental feedback. American Naturalist, 160(2), 205–213. http://doi.org/10.1086/341018



For this model:

* Hanisch, S. (2017). Evolution and patchy resource. GlobalESD NetLogo Models.   http://NetLogo.GlobalESD.org

For the NetLogo-Software:

* Wilensky, U. (1999). NetLogo. http://ccl.northwestern.edu/netlogo/. Center for Connected Learning and Computer-Based Modeling, Northwestern University, Evanston, IL.


## Licence

![CC BY-NC-SA 3.0](http://ccl.northwestern.edu/images/creativecommons/byncsa.png)

This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. http://creativecommons.org/licenses/by-nc-sa/4.0/
@#$#@#$#@
default
true
0
Polygon -7500403 true true 150 5 40 250 150 205 260 250

airplane
true
0
Polygon -7500403 true true 150 0 135 15 120 60 120 105 15 165 15 195 120 180 135 240 105 270 120 285 150 270 180 285 210 270 165 240 180 180 285 195 285 165 180 105 180 60 165 15

arrow
true
0
Polygon -7500403 true true 150 0 0 150 105 150 105 293 195 293 195 150 300 150

bacteria
true
0
Polygon -7500403 true true 135 210 120 285 135 240 135 285 150 240 150 285 150 240 165 285 165 240 180 285 165 210
Circle -7500403 true true 105 122 90
Circle -7500403 true true 110 75 80
Circle -7500403 false true 45 60 0

box
false
0
Polygon -7500403 true true 150 285 285 225 285 75 150 135
Polygon -7500403 true true 150 135 15 75 150 15 285 75
Polygon -7500403 true true 15 75 15 225 150 285 150 135
Line -16777216 false 150 285 150 135
Line -16777216 false 150 135 15 75
Line -16777216 false 150 135 285 75

bug
true
0
Circle -7500403 true true 96 182 108
Circle -7500403 true true 110 127 80
Circle -7500403 true true 110 75 80
Line -7500403 true 150 100 80 30
Line -7500403 true 150 100 220 30

butterfly
true
0
Polygon -7500403 true true 150 165 209 199 225 225 225 255 195 270 165 255 150 240
Polygon -7500403 true true 150 165 89 198 75 225 75 255 105 270 135 255 150 240
Polygon -7500403 true true 139 148 100 105 55 90 25 90 10 105 10 135 25 180 40 195 85 194 139 163
Polygon -7500403 true true 162 150 200 105 245 90 275 90 290 105 290 135 275 180 260 195 215 195 162 165
Polygon -16777216 true false 150 255 135 225 120 150 135 120 150 105 165 120 180 150 165 225
Circle -16777216 true false 135 90 30
Line -16777216 false 150 105 195 60
Line -16777216 false 150 105 105 60

car
false
0
Polygon -7500403 true true 300 180 279 164 261 144 240 135 226 132 213 106 203 84 185 63 159 50 135 50 75 60 0 150 0 165 0 225 300 225 300 180
Circle -16777216 true false 180 180 90
Circle -16777216 true false 30 180 90
Polygon -16777216 true false 162 80 132 78 134 135 209 135 194 105 189 96 180 89
Circle -7500403 true true 47 195 58
Circle -7500403 true true 195 195 58

cell
true
0
Circle -7500403 true true 8 8 284
Circle -16777216 true false 19 18 262
Circle -7500403 false true 234 89 28
Circle -7500403 false true 103 120 98
Line -7500403 true 175 154 165 170
Line -7500403 true 174 137 186 155
Line -7500403 true 154 159 145 176
Line -7500403 true 136 184 154 191
Line -7500403 true 151 153 131 162
Line -7500403 true 171 181 159 206
Circle -7500403 false true 126 36 48
Polygon -7500403 true true 218 187 224 176 226 162 220 146 214 130 217 121 224 118 232 122 244 136 252 158 248 190 228 221 216 230 204 227 204 213 205 207 209 201 213 194
Circle -7500403 true true 138 45 16
Circle -7500403 false true 39 84 42

circle
false
0
Circle -7500403 true true 0 0 300

circle 2
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240

cow
false
0
Polygon -7500403 true true 200 193 197 249 179 249 177 196 166 187 140 189 93 191 78 179 72 211 49 209 48 181 37 149 25 120 25 89 45 72 103 84 179 75 198 76 252 64 272 81 293 103 285 121 255 121 242 118 224 167
Polygon -7500403 true true 73 210 86 251 62 249 48 208
Polygon -7500403 true true 25 114 16 195 9 204 23 213 25 200 39 123

cylinder
false
0
Circle -7500403 true true 0 0 300

dot
false
0
Circle -7500403 true true 90 90 120

face happy
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 255 90 239 62 213 47 191 67 179 90 203 109 218 150 225 192 218 210 203 227 181 251 194 236 217 212 240

face neutral
false
0
Circle -7500403 true true 8 7 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Rectangle -16777216 true false 60 195 240 225

face sad
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 168 90 184 62 210 47 232 67 244 90 220 109 205 150 198 192 205 210 220 227 242 251 229 236 206 212 183

fish
false
0
Polygon -1 true false 44 131 21 87 15 86 0 120 15 150 0 180 13 214 20 212 45 166
Polygon -1 true false 135 195 119 235 95 218 76 210 46 204 60 165
Polygon -1 true false 75 45 83 77 71 103 86 114 166 78 135 60
Polygon -7500403 true true 30 136 151 77 226 81 280 119 292 146 292 160 287 170 270 195 195 210 151 212 30 166
Circle -16777216 true false 215 106 30

flag
false
0
Rectangle -7500403 true true 60 15 75 300
Polygon -7500403 true true 90 150 270 90 90 30
Line -7500403 true 75 135 90 135
Line -7500403 true 75 45 90 45

flower
false
0
Polygon -10899396 true false 135 120 165 165 180 210 180 240 150 300 165 300 195 240 195 195 165 135
Circle -7500403 true true 85 132 38
Circle -7500403 true true 130 147 38
Circle -7500403 true true 192 85 38
Circle -7500403 true true 85 40 38
Circle -7500403 true true 177 40 38
Circle -7500403 true true 177 132 38
Circle -7500403 true true 70 85 38
Circle -7500403 true true 130 25 38
Circle -7500403 true true 96 51 108
Circle -16777216 true false 113 68 74
Polygon -10899396 true false 189 233 219 188 249 173 279 188 234 218
Polygon -10899396 true false 180 255 150 210 105 210 75 240 135 240

house
false
0
Rectangle -7500403 true true 45 120 255 285
Rectangle -16777216 true false 120 210 180 285
Polygon -7500403 true true 15 120 150 15 285 120
Line -16777216 false 30 120 270 120

leaf
false
0
Polygon -7500403 true true 150 210 135 195 120 210 60 210 30 195 60 180 60 165 15 135 30 120 15 105 40 104 45 90 60 90 90 105 105 120 120 120 105 60 120 60 135 30 150 15 165 30 180 60 195 60 180 120 195 120 210 105 240 90 255 90 263 104 285 105 270 120 285 135 240 165 240 180 270 195 240 210 180 210 165 195
Polygon -7500403 true true 135 195 135 240 120 255 105 255 105 285 135 285 165 240 165 195

line
true
0
Line -7500403 true 150 0 150 300

line half
true
0
Line -7500403 true 150 0 150 150

pentagon
false
0
Polygon -7500403 true true 150 15 15 120 60 285 240 285 285 120

person
false
0
Circle -7500403 true true 110 5 80
Polygon -7500403 true true 105 90 120 195 90 285 105 300 135 300 150 225 165 300 195 300 210 285 180 195 195 90
Rectangle -7500403 true true 127 79 172 94
Polygon -7500403 true true 195 90 240 150 225 180 165 105
Polygon -7500403 true true 105 90 60 150 75 180 135 105

plant
false
0
Rectangle -7500403 true true 135 90 165 300
Polygon -7500403 true true 135 255 90 210 45 195 75 255 135 285
Polygon -7500403 true true 165 255 210 210 255 195 225 255 165 285
Polygon -7500403 true true 135 180 90 135 45 120 75 180 135 210
Polygon -7500403 true true 165 180 165 210 225 180 255 120 210 135
Polygon -7500403 true true 135 105 90 60 45 45 75 105 135 135
Polygon -7500403 true true 165 105 165 135 225 105 255 45 210 60
Polygon -7500403 true true 135 90 120 45 150 15 180 45 165 90

sheep
false
15
Circle -1 true true 203 65 88
Circle -1 true true 70 65 162
Circle -1 true true 150 105 120
Polygon -7500403 true false 218 120 240 165 255 165 278 120
Circle -7500403 true false 214 72 67
Rectangle -1 true true 164 223 179 298
Polygon -1 true true 45 285 30 285 30 240 15 195 45 210
Circle -1 true true 3 83 150
Rectangle -1 true true 65 221 80 296
Polygon -1 true true 195 285 210 285 210 240 240 210 195 210
Polygon -7500403 true false 276 85 285 105 302 99 294 83
Polygon -7500403 true false 219 85 210 105 193 99 201 83

square
false
0
Rectangle -7500403 true true 30 30 270 270

square 2
false
0
Rectangle -7500403 true true 30 30 270 270
Rectangle -16777216 true false 60 60 240 240

star
false
0
Polygon -7500403 true true 151 1 185 108 298 108 207 175 242 282 151 216 59 282 94 175 3 108 116 108

target
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240
Circle -7500403 true true 60 60 180
Circle -16777216 true false 90 90 120
Circle -7500403 true true 120 120 60

tree
false
0
Circle -7500403 true true 118 3 94
Rectangle -6459832 true false 120 195 180 300
Circle -7500403 true true 65 21 108
Circle -7500403 true true 116 41 127
Circle -7500403 true true 45 90 120
Circle -7500403 true true 104 74 152

triangle
false
0
Polygon -7500403 true true 150 30 15 255 285 255

triangle 2
false
0
Polygon -7500403 true true 150 30 15 255 285 255
Polygon -16777216 true false 151 99 225 223 75 224

truck
false
0
Rectangle -7500403 true true 4 45 195 187
Polygon -7500403 true true 296 193 296 150 259 134 244 104 208 104 207 194
Rectangle -1 true false 195 60 195 105
Polygon -16777216 true false 238 112 252 141 219 141 218 112
Circle -16777216 true false 234 174 42
Rectangle -7500403 true true 181 185 214 194
Circle -16777216 true false 144 174 42
Circle -16777216 true false 24 174 42
Circle -7500403 false true 24 174 42
Circle -7500403 false true 144 174 42
Circle -7500403 false true 234 174 42

turtle
true
0
Polygon -10899396 true false 215 204 240 233 246 254 228 266 215 252 193 210
Polygon -10899396 true false 195 90 225 75 245 75 260 89 269 108 261 124 240 105 225 105 210 105
Polygon -10899396 true false 105 90 75 75 55 75 40 89 31 108 39 124 60 105 75 105 90 105
Polygon -10899396 true false 132 85 134 64 107 51 108 17 150 2 192 18 192 52 169 65 172 87
Polygon -10899396 true false 85 204 60 233 54 254 72 266 85 252 107 210
Polygon -7500403 true true 119 75 179 75 209 101 224 135 220 225 175 261 128 261 81 224 74 135 88 99

wheel
false
0
Circle -7500403 true true 3 3 294
Circle -16777216 true false 30 30 240
Line -7500403 true 150 285 150 15
Line -7500403 true 15 150 285 150
Circle -7500403 true true 120 120 60
Line -7500403 true 216 40 79 269
Line -7500403 true 40 84 269 221
Line -7500403 true 40 216 269 79
Line -7500403 true 84 40 221 269

wolf
false
0
Polygon -16777216 true false 253 133 245 131 245 133
Polygon -7500403 true true 2 194 13 197 30 191 38 193 38 205 20 226 20 257 27 265 38 266 40 260 31 253 31 230 60 206 68 198 75 209 66 228 65 243 82 261 84 268 100 267 103 261 77 239 79 231 100 207 98 196 119 201 143 202 160 195 166 210 172 213 173 238 167 251 160 248 154 265 169 264 178 247 186 240 198 260 200 271 217 271 219 262 207 258 195 230 192 198 210 184 227 164 242 144 259 145 284 151 277 141 293 140 299 134 297 127 273 119 270 105
Polygon -7500403 true true -1 195 14 180 36 166 40 153 53 140 82 131 134 133 159 126 188 115 227 108 236 102 238 98 268 86 269 92 281 87 269 103 269 113

x
false
0
Polygon -7500403 true true 270 75 225 30 30 225 75 270
Polygon -7500403 true true 30 75 75 30 270 225 225 270
@#$#@#$#@
NetLogo 6.1.1
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
<experiments>
  <experiment name="experiment" repetitions="8" runMetricsEveryStep="true">
    <setup>setup</setup>
    <go>go</go>
    <timeLimit steps="25000"/>
    <exitCondition>count foragers with [eattype = "low"] = 0</exitCondition>
    <metric>count foragers with [eattype = "high"]</metric>
    <metric>count foragers with [eattype = "low"]</metric>
    <enumeratedValueSet variable="Mutation-rate">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="dispersal-costs">
      <value value="8"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="Agents">
      <value value="&quot;Bacteria&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="Size-Resource-Areas">
      <value value="4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="Living-costs">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="Percent-Sustainables">
      <value value="90"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="Number-Agents">
      <value value="80"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="Distance-Resource-Areas">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="Evolution?">
      <value value="true"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="group-dispersal-range">
      <value value="0"/>
      <value value="20"/>
      <value value="50"/>
      <value value="70"/>
      <value value="100"/>
      <value value="150"/>
      <value value="200"/>
    </enumeratedValueSet>
  </experiment>
</experiments>
@#$#@#$#@
@#$#@#$#@
default
0.0
-0.2 0 0.0 1.0
0.0 1 1.0 0.0
0.2 0 0.0 1.0
link direction
true
0
Line -7500403 true 150 150 90 180
Line -7500403 true 150 150 210 180
@#$#@#$#@
0
@#$#@#$#@
