# -*- coding: utf-8 -*-
import os
import unittest
from subprocess import Popen, PIPE

from testcpybuilder import BuiltModule, PyRuntime, SimpleModule, CompilationError
from cpybuilder import PyMethodTable, PyMethodDef, METH_VARARGS

#FIXME:
pyruntime = PyRuntime('/usr/bin/python2.7', '/usr/bin/python2.7-config')

class ExpectedErrorNotFound(CompilationError):
    def __init__(self, expected_err, actual_err, bm):
        CompilationError.__init__(self, bm)
        self.expected_err = expected_err
        self.actual_err = actual_err


    def _describe_activity(self):
        result = 'This error was expected, but was not found:\n'
        result += '  ' + self._indent(self.expected_err) + '\n'
        result += '  whilst compiling:\n'
        result += '    ' + self.bm.srcfile + '\n'
        result += '  using:\n'
        result += '    ' + ' '.join(self.bm.args) + '\n'
        
        from difflib import unified_diff
        for line in unified_diff(self.expected_err.splitlines(),
                                 self.actual_err.splitlines(),
                                 fromfile='Expected stderr',
                                 tofile='Actual stderr',
                                 lineterm=""):
            result += '%s\n' % line
        return result

class AnalyzerTests(unittest.TestCase):
    def compile_src(self, bm):
        bm.compile_src(extra_cflags=['-fplugin=%s' % os.path.abspath('python.so'),
                                     '-fplugin-arg-python-script=cpychecker.py'])

    def build_module(self, bm):
        bm.write_src()
        self.compile_src(bm)

    def assertNoErrors(self, src):
        if isinstance(src, SimpleModule):
            sm = src
        else:
            sm = SimpleModule()
            sm.cu.add_defn(src)
        bm = BuiltModule(sm, pyruntime)
        self.build_module(bm)
        bm.cleanup()
        return bm

    def assertFindsError(self, src, experr):
        if isinstance(src, SimpleModule):
            sm = src
        else:
            sm = SimpleModule()
            sm.cu.add_defn(src)
        bm = BuiltModule(sm, pyruntime)
        try:
            bm.write_src()
            experr = experr.replace('$(SRCFILE)', bm.srcfile)
            self.compile_src(bm)
        except CompilationError, exc:
            if experr not in exc.err:
                raise ExpectedErrorNotFound(experr, exc.err, bm)
        else:
            raise ExpectedErrorNotFound(experr, bm.err, bm)
        bm.cleanup()
        return bm

class PyArg_ParseTupleTests(AnalyzerTests):
    def test_bogus_format_string(self):
        src = ('PyObject *\n'
               'bogus_format_string(PyObject *self, PyObject *args)\n'
               '{\n'
               '    if (!PyArg_ParseTuple(args, "This is not a valid format string")) {\n'
               '  	    return NULL;\n'
               '    }\n'
               '    Py_RETURN_NONE;\n'
               '}\n')
        experr = ('$(SRCFILE): In function ‘bogus_format_string’:\n'
                  '$(SRCFILE):12:26: error: unknown format char in "This is not a valid format string": \'T\' [-fpermissive]\n')
        self.assertFindsError(src, experr)
                   
    def test_finding_htons_error(self):
        #  Erroneous argument parsing of socket.htons() on 64bit big endian
        #  machines from CPython's Modules/socket.c; was fixed in svn r34931
        #  FIXME: the original had tab indentation, but what does this mean
        # for "column" offsets in the output?
        src = """
extern uint16_t htons(uint16_t hostshort);

PyObject *
socket_htons(PyObject *self, PyObject *args)
{
    unsigned long x1, x2;

    if (!PyArg_ParseTuple(args, "i:htons", &x1)) {
        return NULL;
    }
    x2 = (int)htons((short)x1);
    return PyInt_FromLong(x2);
}
"""
        self.assertFindsError(src,
                              '$(SRCFILE): In function ‘socket_htons’:\n'
                              '$(SRCFILE):17:26: error: Mismatching type in call to PyArg_ParseTuple with format string "i:htons":'
                              ' argument 3 ("&x1") had type "long unsigned int *" (pointing to 64 bits)'
                              ' but was expecting "int *" (pointing to 32 bits) for format code "i"'
                              ' [-fpermissive]\n')

    def test_not_enough_varargs(self):
        src = """
PyObject *
not_enough_varargs(PyObject *self, PyObject *args)
{
   if (!PyArg_ParseTuple(args, "i")) {
       return NULL;
   }
   Py_RETURN_NONE;
}
"""
        self.assertFindsError(src,
                              '$(SRCFILE): In function ‘not_enough_varargs’:\n'
                              '$(SRCFILE):13:25: error: Not enough arguments in call to PyArg_ParseTuple with format string "i" : expected 1 extra arguments (int *), but got 0 [-fpermissive]\n')

    def test_too_many_varargs(self):
        src = """
PyObject *
too_many_varargs(PyObject *self, PyObject *args)
{
    int i, j;
    if (!PyArg_ParseTuple(args, "i", &i, &j)) {
	 return NULL;
    }
    Py_RETURN_NONE;
}
"""
        self.assertFindsError(src,
                              '$(SRCFILE): In function ‘too_many_varargs’:\n'
                              '$(SRCFILE):14:26: error: Too many arguments in call to PyArg_ParseTuple with format string "i" : expected 1 extra arguments (int *), but got 2 [-fpermissive]\n')

    def test_correct_usage(self):
        src = """
PyObject *
correct_usage(PyObject *self, PyObject *args)
{
    int i;
    if (!PyArg_ParseTuple(args, "i", &i)) {
	 return NULL;
    }
    Py_RETURN_NONE;
}
"""
        self.assertNoErrors(src)

    def _test_simple_code(self, code, typename, exptypename=None):
        if not exptypename:
            exptypename = typename

        def _test_correct_usage_of_simple_code(self, code, typename):
            src = ('PyObject *\n'
                   'correct_usage_of_%(code)s(PyObject *self, PyObject *args)\n'
                   '{\n'
                   '    %(typename)s val;\n'
                   '    if (!PyArg_ParseTuple(args, "%(code)s", &val)) {\n'
                   '  	    return NULL;\n'
                   '    }\n'
                   '    Py_RETURN_NONE;\n'
                   '}\n') % locals()
            self.assertNoErrors(src)

        def _test_incorrect_usage_of_simple_code(self, code, typename, exptypename):
            src = ('PyObject *\n'
                   'incorrect_usage_of_%(code)s(PyObject *self, PyObject *args)\n'
                   '{\n'
                   '    void *val;\n'
                   '    if (!PyArg_ParseTuple(args, "%(code)s", &val)) {\n'
                   '  	    return NULL;\n'
                   '    }\n'
                   '    Py_RETURN_NONE;\n'
                   '}\n') % locals()
            experr = ('$(SRCFILE): In function ‘incorrect_usage_of_%(code)s’:\n'
                      '$(SRCFILE):13:26: error: Mismatching type in call to PyArg_ParseTuple with format string "%(code)s": argument 3 ("&val") had type "void * *" but was expecting "%(exptypename)s *"' % locals())
            bm = self.assertFindsError(src, experr)
                                       

        _test_correct_usage_of_simple_code(self, code, typename)
        _test_incorrect_usage_of_simple_code(self, code, typename, exptypename)

        
    def test_simple_code_b(self):
        self._test_simple_code('b', 'unsigned char')

    def test_simple_code_B(self):
        self._test_simple_code('B', 'unsigned char')

    def test_simple_code_h(self):
        self._test_simple_code('h', 'short', 'short int')

    def test_simple_code_H(self):
        self._test_simple_code('H', 'unsigned short', 'short unsigned int')

    def test_simple_code_i(self):
        self._test_simple_code('i', 'int')

    def test_simple_code_I(self):
        self._test_simple_code('I', 'unsigned int')

    # ('n','Py_ssize_t'),,

    def test_simple_code_l(self):
        self._test_simple_code('l', 'long', 'long int')

    def test_simple_code_k(self):
        self._test_simple_code('k', 'unsigned long', 'long unsigned int')

    # ('L','PY_LONG_LONG'),

    # ('K','unsigned PY_LONG_LONG'),

    def test_simple_code_f(self):
        self._test_simple_code('f', 'float')

    def test_simple_code_d(self):
        self._test_simple_code('d', 'double')

    # ('D','Py_complex'),

    def test_simple_code_c(self):
        self._test_simple_code('c', 'char')

class RefcountErrorTests(AnalyzerTests):
    def test_correct_py_none(self):
        sm = SimpleModule()
        sm.cu.add_defn(
            'PyObject *\n'
            'correct_none(PyObject *self, PyObject *args)\n'
            '{\n'
            '    Py_RETURN_NONE;\n'
            '}\n')
        methods = PyMethodTable('test_methods',
                                [PyMethodDef('test_method', 'correct_none',
                                             METH_VARARGS, None)])
        sm.cu.add_defn(methods.c_defn())
        sm.add_module_init('buggy', modmethods=methods, moddoc=None)
        self.assertNoErrors(sm)

    @unittest.skip("Refcount tracker doesn't yet work")
    def test_incorrect_py_none(self):
        sm = SimpleModule()
        sm.cu.add_defn(
            'PyObject *\n'
            'losing_refcnt_of_none(PyObject *self, PyObject *args)\n'
            '{\n'
            '    /* Bug: this code is missing a Py_INCREF on Py_None */\n'
            '    return Py_None;\n'
            '}\n')
        methods = PyMethodTable('buggy_methods',
                                [PyMethodDef('show_the_bug', 'losing_refcnt_of_none',
                                             METH_VARARGS, 'Show the bug.')])
        sm.cu.add_defn(methods.c_defn())
        sm.add_module_init('buggy', modmethods=methods, moddoc='This is a doc string')
        
        experr = ('$(SRCFILE): In function ‘losing_refcnt_of_none’:\n'
                  '$(SRCFILE):19:5: error: return of PyObject* without Py_INCREF() [-fpermissive]\n'
                  )
        self.assertFindsError(sm, experr)

# Test disabled for now: we can't easily import this under gcc anymore:
class TestArgParsing: # (unittest.TestCase):
    def assert_args(self, arg_str, exp_result):
        result = get_types(None, arg_str)
        self.assertEquals(result, exp_result)

    def test_simple_cases(self):
        self.assert_args('c',
                         ['char *'])

    def test_socketmodule_socket_htons(self):
        self.assert_args('i:htons',
                         ['int *'])

    def test_fcntlmodule_fcntl_flock(self):
        # FIXME: somewhat broken, we can't know what the converter callback is
        self.assert_args("O&i:flock", 
                         ['int ( PyObject * object , int * target )', 
                          'int *', 
                          'int *'])

    def test_posixmodule_listdir(self):
        self.assert_args("et#:listdir",
                         ['const char *', 'char * *', 'int *'])

    def test_bsddb_DBSequence_set_range(self):
        self.assert_args("(LL):set_range",
                         ['PY_LONG_LONG *', 'PY_LONG_LONG *'])


if __name__ == '__main__':
    unittest.main()
