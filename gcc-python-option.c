/*
   Copyright 2011, 2012, 2013 David Malcolm <dmalcolm@redhat.com>
   Copyright 2011, 2012, 2013 Red Hat, Inc.

   This is free software: you can redistribute it and/or modify it
   under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful, but
   WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
   General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see
   <http://www.gnu.org/licenses/>.
*/

#include <Python.h>
#include "gcc-python.h"
#include "gcc-python-wrappers.h"
#include "c-common.h" /* for warn_format */
#include "diagnostic.h"


/*
  Wrapper for GCC's opts.h

  opts.h declares:
    extern const struct cl_option cl_options[];
    extern const unsigned int cl_options_count;
  which suggests that this table is fixed in place and thus not resizable.
  (The definition is in the autogenerated DIR/gcc/options.c)

  We specifically wrap:
    enum opt_code
  and use this to get at the associated "struct cl_option" within the
  "cl_options" table.
*/

int
PyGccOption_init(PyGccOption * self, PyObject *args, PyObject *kwargs)
{
    const char *text;
    static const char *kwlist[] = {"text", NULL};
    unsigned int i;

    /*
      We need to call _track manually as we're not using PyGccWrapper_New():
    */
    //PyGccWrapper_Track(&self->head);

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "s", (char**)kwlist,
                                      &text)) {
        return -1;
    }

    /* Search for text within cl_options */
    for (i = 0; i < cl_options_count; i++) {
        if (0 == strcmp(cl_options[i].opt_text, text)) {
            self->opt = gcc_private_make_option((enum opt_code)i);
            return 0; /* success */
        }
    }

    /* Not found: */
    PyErr_Format(PyExc_ValueError,
                 "Could not find command line argument with text '%s'",
                 text);
    return -1;
}

PyObject *
PyGccOption_repr(PyGccOption * self)
{
    return PyGccString_FromFormat("gcc.Option('%s')",
                                         PyGcc_option_to_cl_option(self)->opt_text);
}

/*
  In GCC 4.6 and 4.7, "warn_format" is a global, declared in
  c-family/c-common.h

  In GCC 4.8, it became a macro in options.h to:
      #define warn_format global_options.x_warn_format
*/

#if (GCC_VERSION < 4008)
/*
  Weakly import warn_format; it's not available in lto1
  (during link-time optimization)
*/
__typeof__ (warn_format) warn_format __attribute__ ((weak));
#endif

int PyGcc_option_is_enabled(enum opt_code opt_code)
{
    /* Returns 1 if option OPT_IDX is enabled in OPTS, 0 if it is disabled,
       or -1 if it isn't a simple on-off switch.  */
#if (GCC_VERSION < 10000)
    int i = option_enabled (opt_code, global_dc->option_state);
#else
    /* Starting with GCC 10, options can be distinguished by language. */
    /* TODO Expose the lang_mask to the user. */
    int i = option_enabled (opt_code, CL_LANG_ALL, global_dc->option_state);
#endif

    if (i == 1) {
        return 1;
    }
    if (i == 0) {
        return 0;
    }

    /* -1: we don't know */
    /*
      Ugly workaround to allow disabling warnings.

      For many options, it doesn't seem to be possible to disable them
      directly.

      Specifically a cl_option with o.flag_var_offset == -1 will return NULL
      from option_flag_var()

      For these options, option_enabled() will return -1 signifying that "it
      isn't a simple on-off switch".

      diagnostic_report_diagnostic() uses
         if (!option_enabled(...))
            return false
      to suppress disabled warnings.

      However, -1 is true for the purpose of this test.

      For GCC's own uses of the options, they are typically guarded by an
      additional test.  For example, "-Wformat" sets "warn_format", and this
      guards the formatting tests.
     */
    switch (opt_code) {
    default:
        /*  We don't know: */
        return -1;

#if (GCC_VERSION >= 4008)
    case OPT_Wformat_:
#else
    case OPT_Wformat:
#endif
        return warn_format;
    }
}

PyObject *
PyGccOption_is_enabled(PyGccOption * self, void *closure)
{
    int i = PyGcc_option_is_enabled(self->opt.inner);

    if (i == 1) {
        return PyBool_FromLong(1);
    }
    if (i == 0) {
        return PyBool_FromLong(0);
    }

    PyErr_Format(PyExc_NotImplementedError,
                 "The plugin does not know how to determine if gcc.Format('%s') is implemented",
                 PyGcc_option_to_cl_option(self)->opt_text);
    return NULL;
}

const struct cl_option*
PyGcc_option_to_cl_option(PyGccOption * self)
{
    assert(self);
    assert(self->opt.inner >= 0);
    assert(self->opt.inner < cl_options_count);

    return &cl_options[self->opt.inner];
}

PyObject *
PyGccOption_New(gcc_option opt)
{
    struct PyGccOption *opt_obj = NULL;

    opt_obj = PyGccWrapper_New(struct PyGccOption, &PyGccOption_TypeObj);
    if (!opt_obj) {
        goto error;
    }

    opt_obj->opt = opt;

    return (PyObject*)opt_obj;

error:
    return NULL;
}

void
PyGcc_WrtpMarkForPyGccOption(PyGccOption *wrapper)
{
    /* empty */
}

/*
  PEP-7
Local variables:
c-basic-offset: 4
indent-tabs-mode: nil
End:
*/
