breed [plants plant]
breed [foragers forager]

foragers-own
[eattype
 energy
 flockmates
 mypatch
 strategy]

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
 costchild
]

to setup
  clear-all

  set patch-width Size-Resource-Areas
  set gap Distance-Resource-Areas
  set growth-rate 0.2
  set carryingcap 10

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
      set strategy "cooperator"
      set color green
      set mypatch [foodpatchnum] of patch-here ]
  ]

   ask n-of (Number-Agents * ( 100 - Percent-Sustainables) / 100) patches with [foodpatch? = true]
  [sprout-foragers 1
    [
      set eattype "high"
      set strategy "defector"
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
  set flockmates other foragers in-radius group-dispersal-range with [strategy = [strategy] of myself]
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
  [
    let new-strategy one-of ["cooperator" "defector"]
    set strategy new-strategy

    ifelse strategy = "cooperator"
      [set eattype "low"]
      [set eattype "high"]

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

to recolor
  set pcolor scale-color brown resource 0 (carryingcap + 10)
end

to update-color
  if strategy = "cooperator" [set color green]
  if strategy = "defector" [set color red]
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
