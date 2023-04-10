graph [
  Version "1.0"
  node [
    id 0
    hostname "node0"
    type "machine"
  ]
  node [
    id 1
    hostname "node1"
    type "machine"
  ]
  node [
    id 2
    hostname "node2"
    type "machine"
  ]
  node [
    id 3
    hostname "node3"
    type "link"
  ]
  node [
    id 4
    hostname "node4"
    type "link"
  ]
  node [
    id 5
    hostname "node5"
    type "machine"
  ]
  node [
    id 6
    hostname "node6"
    type "machine"
  ]
  node [
    id 7
    hostname "node7"
    type "machine"
  ]
  node [
    id 8
    hostname "node8"
    type "link"
  ]
  node [
    id 9
    hostname "node9"
    type "machine"
  ]
  node [
    id 10
    hostname "node10"
    type "machine"
  ]
  edge [
    source 0
    target 1
  ]
  edge [
    source 0
    target 2
  ]
  edge [
    source 1
    target 2
  ]
  edge [
    source 0
    target 3
  ]
  edge [
    source 1
    target 3
  ]
  edge [
    source 2
    target 3
  ]
  edge [
    source 3
    target 4
  ]
  edge [
    source 3
    target 5
  ]
  edge [
    source 4
    target 6
  ]
  edge [
    source 5
    target 7
  ]
  edge [
    source 7
    target 8
  ]
  edge [
    source 8
    target 9
  ]
  edge [
    source 8
    target 10
  ]
]