#pragma once

#include <optix.h>

typedef struct
{
  float *patch_centers_f;
  float *patch_normals_f;
  float *patch_centers_b;
  float *patch_normals_b;
  float *dirs;
  float *weights;
  float *out_front;
  float *out_back;
  unsigned int dir_count;
  unsigned int patch_count;
  OptixTraversableHandle traversable;
} LaunchParams;

extern "C" {
__constant__ LaunchParams params;
}

static __forceinline__ __device__ float3 load3(const float *ptr)
{
  return make_float3(ptr[0], ptr[1], ptr[2]);
}
