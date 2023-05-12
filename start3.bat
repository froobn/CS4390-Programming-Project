call python empty.py

start /B "" python node.py 0 120 0 1 2 3 4 &

start /B "" python node.py 4 120 4 0

start /B "" python node.py 1 120 4 "StringFrom1" 30 0

start /B "" python node.py 2 120 4 "StringFrom2" 30 0

start /B "" python node.py 3 120 4 "StringFrom3" 30 0

