#include "gcc-c-api/gcc-function.h"
#include "gcc-c-api/gcc-location.h"
#if (GCC_VERSION >= 4009)
#include "context.h"
#include "pass_manager.h"
#endif

// opt_pass
#include <pybind11/pybind11.h>
namespace py = pybind11;

PYBIND11_PLUGIN(example) {
  py::module m("example", "pybind11 example plugin");

  //m.def("add", &add, "A function which adds two numbers");

  return m.ptr();
}
