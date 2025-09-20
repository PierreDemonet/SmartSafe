#pragma once

#include <vector>
#include <cuda.h>
#include <optix.h>

struct MeshData {
  std::vector<float> vertices; // xyz
  std::vector<int> faces;       // triangle indices
};

struct PatchData {
  std::vector<float> centers_f;
  std::vector<float> normals_f;
  std::vector<float> centers_b;
  std::vector<float> normals_b;
};

class OptixEngine {
public:
  OptixEngine();
  ~OptixEngine();

  void build_scene(const MeshData &mesh);
  void set_patches(const PatchData &patches);
  void compute_poa(const std::vector<float> &dirs,
                   const std::vector<float> &weights,
                   std::vector<float> &out_front,
                   std::vector<float> &out_back);

private:
  void init_context();
  void destroy_context();
  void build_accel(const MeshData &mesh);
  void create_pipeline();
  void allocate_buffers(size_t rays, size_t patches);

  OptixDeviceContext context_{};
  CUstream stream_{};
  OptixTraversableHandle tlas_{};
  CUdeviceptr d_vertices_{};
  CUdeviceptr d_indices_{};
  CUdeviceptr d_patch_centers_f_{};
  CUdeviceptr d_patch_normals_f_{};
  CUdeviceptr d_patch_centers_b_{};
  CUdeviceptr d_patch_normals_b_{};
  CUdeviceptr d_dirs_{};
  CUdeviceptr d_weights_{};
  CUdeviceptr d_out_front_{};
  CUdeviceptr d_out_back_{};
  unsigned int patch_count_ = 0;

  std::vector<float> h_centers_f_;
  std::vector<float> h_normals_f_;
  std::vector<float> h_centers_b_;
  std::vector<float> h_normals_b_;
};
