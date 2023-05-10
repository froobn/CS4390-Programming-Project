call python empty.py

start /B "" python node.py 0 30 1 "this is a message from 0" 30 [1]

start /B "" python node.py 2 30 1 "this is a message from 2" 30 [1]
start /B "" python node.py 3 30 1 "this is a message from 3" 30 [1]

start /B "" python node.py 1 30 0 [0]


pause
