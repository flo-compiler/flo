#!/usr/bin/env python3
iota_counter = 0
def iota(reset=False):
    global iota_counter
    if(reset == True):
        iota_counter = 0
    else:
        iota_counter+=1
    return iota_counter

OP_PUSH=iota(True)
OP_ADD=iota()
OP_DUMP=iota()
OP_COUNT=iota()

def push(n):
    return (OP_PUSH, n)

def add():
    return (OP_ADD, )

def dump():
    return (OP_DUMP, )

def run(program):
    stack = []
    for op in program:
        if op[0] == OP_PUSH:
            stack.append(op[1])
        elif op[0] == OP_ADD:
            a = stack.pop()
            b = stack.pop()
            stack.append(a+b)
        elif op[0] == OP_DUMP:
            x = stack.pop()
            print(x)

program = [
    push(12),
    push(-6),
    add(),
    dump()    
]
run(program)