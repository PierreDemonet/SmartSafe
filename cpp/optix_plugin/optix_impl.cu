#include "optix_impl.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

OptixEngine::OptixEngine() { init_context(); }

OptixEngine::~OptixEngine() { destroy_context(); }

void OptixEngine::init_context() { /* Stub: context would be created here. */ }

void OptixEngine::destroy_context() { /* Stub cleanup. */ }

void OptixEngine::build_scene(const MeshData &mesh)
{
  (void)mesh;
}

void OptixEngine::set_patches(const PatchData &patches)
{
  h_centers_f_ = patches.centers_f;
  h_normals_f_ = patches.normals_f;
  h_centers_b_ = patches.centers_b;
  h_normals_b_ = patches.normals_b;
  patch_count_ = static_cast<unsigned int>(h_centers_f_.size() / 3);
}

void OptixEngine::allocate_buffers(size_t rays, size_t patches)
{
  (void)rays;
  (void)patches;
}

void OptixEngine::create_pipeline() {}

void OptixEngine::build_accel(const MeshData &mesh)
{
  (void)mesh;
}

void OptixEngine::compute_poa(const std::vector<float> &dirs,
                              const std::vector<float> &weights,
                              std::vector<float> &out_front,
                              std::vector<float> &out_back)
{
  if (weights.size() * 3 != dirs.size())
  {
    throw std::runtime_error("Directions and weights sizes mismatch");
  }
  out_front.assign(patch_count_, 0.0f);
  out_back.assign(patch_count_, 0.0f);
  for (unsigned int p = 0; p < patch_count_; ++p)
  {
    float nfx = h_normals_f_[3 * p + 0];
    float nfy = h_normals_f_[3 * p + 1];
    float nfz = h_normals_f_[3 * p + 2];
    float nbx = h_normals_b_[3 * p + 0];
    float nby = h_normals_b_[3 * p + 1];
    float nbz = h_normals_b_[3 * p + 2];
    for (size_t r = 0; r < weights.size(); ++r)
    {
      float wx = dirs[3 * r + 0];
      float wy = dirs[3 * r + 1];
      float wz = dirs[3 * r + 2];
      float w = weights[r];
      float dot_front = nfx * wx + nfy * wy + nfz * wz;
      if (dot_front > 0.0f)
      {
        out_front[p] += w * dot_front;
      }
      float dot_back = nbx * wx + nby * wy + nbz * wz;
      if (dot_back > 0.0f)
      {
        out_back[p] += w * dot_back;
      }
    }
  }
}
