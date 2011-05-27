#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"
#include "gimple.h"
#include "tree-flow.h"
#include "tree-flow-inline.h"

PyObject *
gcc_Gimple_repr(struct PyGccGimple * self)
{
    return gcc_python_string_from_format("%s()", Py_TYPE(self)->tp_name);
}

/* FIXME:
   This is declared in gimple-pretty-print.c, but not exposed in any of the plugin headers AFAIK:
*/
void
dump_gimple_stmt (pretty_printer *buffer, gimple gs, int spc, int flags);

PyObject *
gcc_Gimple_str(struct PyGccGimple * self)
{
    PyObject *ppobj = gcc_python_pretty_printer_new();
    PyObject *result = NULL;
    if (!ppobj) {
	return NULL;
    }

    dump_gimple_stmt(gcc_python_pretty_printer_as_pp(ppobj),
		     self->stmt,
		     0, 0);
    result = gcc_python_pretty_printer_as_string(ppobj);
    if (!result) {
	goto error;
    }
    
    Py_XDECREF(ppobj);
    return result;
    
 error:
    Py_XDECREF(ppobj);
    return NULL;
}

PyObject *
gcc_Gimple_get_rhs(struct PyGccGimple *self, void *closure)
{
    PyObject * result = NULL;
    int i;

    assert(gimple_has_ops(self->stmt));

    assert(gimple_num_ops(self->stmt) > 0);
    result = PyList_New(gimple_num_ops (self->stmt) - 1);
    if (!result) {
	goto error;
    }
    
    for (i = 1 ; i < gimple_num_ops(self->stmt); i++) {
	tree t = gimple_op(self->stmt, i);
	PyObject *obj = gcc_python_make_wrapper_tree(t);
	if (!obj) {
	    goto error;
	}
	PyList_SetItem(result, i-1, obj);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

PyObject *
gcc_GimpleCall_get_args(struct PyGccGimple *self, void *closure)
{
    PyObject * result = NULL;
    int num_args = gimple_call_num_args (self->stmt);
    int i;

    result = PyList_New(num_args);
    if (!result) {
	goto error;
    }
    
    for (i = 0 ; i < num_args; i++) {
	tree t = gimple_call_arg(self->stmt, i);
	PyObject *obj = gcc_python_make_wrapper_tree(t);
	if (!obj) {
	    goto error;
	}
	PyList_SetItem(result, i, obj);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

PyObject *
gcc_GimplePhi_get_args(struct PyGccGimple *self, void *closure)
{
    /* See e.g. gimple-pretty-print.c:dump_gimple_phi */
    PyObject * result = NULL;
    int num_args = gimple_phi_num_args (self->stmt);
    int i;

    result = PyList_New(num_args);
    if (!result) {
        goto error;
    }

    for (i = 0 ; i < num_args; i++) {
        tree arg_def = gimple_phi_arg_def(self->stmt, i);
        edge arg_edge = gimple_phi_arg_edge(self->stmt, i);
        /* fwiw, there's also gimple_phi_arg_has_location and gimple_phi_arg_location */
        PyObject *tuple_obj;
        tuple_obj = Py_BuildValue("O&O&",
                                  gcc_python_make_wrapper_tree, arg_def,
                                  gcc_python_make_wrapper_edge, arg_edge);
        if (!tuple_obj) {
            goto error;
        }
        PyList_SET_ITEM(result, i, tuple_obj);
    }

    return result;

 error:
    Py_XDECREF(result);
    return NULL;
}

PyObject*
gcc_python_make_wrapper_gimple(gimple stmt)
{
    struct PyGccGimple *gimple_obj = NULL;
    PyTypeObject* tp;
  
    tp = gcc_python_autogenerated_gimple_type_for_stmt(stmt);
    assert(tp);
    //printf("tp:%p\n", tp);
  
    gimple_obj = PyObject_New(struct PyGccGimple, tp);
    if (!gimple_obj) {
        goto error;
    }

    gimple_obj->stmt = stmt;
    /* FIXME: do we need to do something for the GCC GC? */

    return (PyObject*)gimple_obj;
      
error:
    return NULL;
}

/*
  PEP-7  
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
