#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>

#include <cstring>

#include "optix_impl.h"

namespace py = pybind11;

class PyOptixEngine
{
public:
  PyOptixEngine() = default;

  void build_scene(py::dict mesh, py::dict materials)
  {
    (void)materials;
    MeshData m;
    auto vertices = mesh["vertices"].cast<py::array_t<float>>();
    auto faces = mesh["faces"].cast<py::array_t<int>>();
    m.vertices.assign(vertices.data(), vertices.data() + vertices.size());
    m.faces.assign(faces.data(), faces.data() + faces.size());
    engine_.build_scene(m);
  }

  void set_module_patches(py::array_t<float> centers_f, py::array_t<float> normals_f,
                          py::array_t<float> centers_b, py::array_t<float> normals_b)
  {
    PatchData p;
    p.centers_f.assign(centers_f.data(), centers_f.data() + centers_f.size());
    p.normals_f.assign(normals_f.data(), normals_f.data() + normals_f.size());
    p.centers_b.assign(centers_b.data(), centers_b.data() + centers_b.size());
    p.normals_b.assign(normals_b.data(), normals_b.data() + normals_b.size());
    engine_.set_patches(p);
  }

  py::tuple compute_poa(py::array_t<float> dirs, py::array_t<float> weights)
  {
    std::vector<float> out_front;
    std::vector<float> out_back;
    std::vector<float> dirs_vec(dirs.size());
    std::vector<float> weights_vec(weights.size());
    std::memcpy(dirs_vec.data(), dirs.data(), dirs.nbytes());
    std::memcpy(weights_vec.data(), weights.data(), weights.nbytes());
    engine_.compute_poa(dirs_vec, weights_vec, out_front, out_back);
    auto arr_front = py::array_t<float>(out_front.size(), out_front.data());
    auto arr_back = py::array_t<float>(out_back.size(), out_back.data());
    return py::make_tuple(arr_front, arr_back);
  }

private:
  OptixEngine engine_{};
};

PYBIND11_MODULE(pvrtx_optix, m)
{
  py::class_<PyOptixEngine>(m, "OptixEngine")
      .def(py::init<>())
      .def("build_scene", &PyOptixEngine::build_scene)
      .def("set_module_patches", &PyOptixEngine::set_module_patches)
      .def("compute_poa", &PyOptixEngine::compute_poa);
}
