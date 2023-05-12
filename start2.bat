call python empty.py

start /B "" python node.py 0 120 5 "Message Sent Over" 30 1 2
start /B "" python node.py 1 120 1 0 2
start /B "" python node.py 2 120 2 0 1 3 4
start /B "" python node.py 3 120 3 2 4 6
start /B "" python node.py 4 20 4 2 3 5
start /B "" python node.py 5 120 5 4 6
start /B "" python node.py 6 120 6 3 5