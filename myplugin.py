# def
import python_example
from python_example import Context
#from python_example import GCC

def main(**kvargs) :
    print("hello world")
    print(kvargs)
    print("step1")
    import pdb
    pdb.set_trace()
    ctx = Context()
    aall =  ctx.get_all_passes()
    print("step4")
    p1 = aall[0] 
    #print(gcc.get().get_all_passes()[0])
    #print(dir(python_example))
    #ctx = python_example.Context()
    #context = gcc.Context()
