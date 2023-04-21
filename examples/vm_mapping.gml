graph [
  Version "1.0"
  node [
    id 0
    hostname "vm0"
    type "machine"
    phys_hostname "node0"
  ]
  node [
    id 1
    hostname "vm1"
    type "machine"
    phys_hostname "node1"
  ]
  node [
    id 2
    hostname "vm2"
    type "machine"
    phys_hostname "node1"
  ]
  node [
    id 3
    hostname "vm3"
    type "machine"
    phys_hostname "node0"
  ]
  edge [
    source 0
    target 1
    speed 1000
    delay 40.0
    phys_hosts "['node1', 'node0', 'node2']"
  ]
  edge [
    source 0
    target 2
    speed 1000
    delay 40.0
    phys_hosts "['node1', 'node0', 'node2']"
  ]
    edge [
    source 1
    target 3
    speed 1000
    delay 40.0
    phys_hosts "['node1', 'node0', 'node2']"
  ]
    edge [
    source 2
    target 3
    speed 1000
    delay 40.0
    phys_hosts "['node1', 'node0', 'node2']"
  ]
]