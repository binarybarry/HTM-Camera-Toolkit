/*
 * GRBFFilter.h
 *
 *  Created on: Jul 31, 2011
 *      Author: barry
 *
 *  Implementation of the GRBFFilter (S2) used by the HMAX algorithm.
 *  The GRBF stands for Gaussian Radial-Basis-Function.
 *
 *  This filter has both a learning and inference phase.  In the learning phase
 *  we are learning small (typically 4x4) patches of inputs from the C1 MaxFilter
 *  layers and storing them as templates to compare against during inference.
 *
 *  When this filter reads input from C1 it will only use the maximum response
 *  across all orientations per position.  This can be thought of as viewing the
 *  input as a "C1 Composite" where only the strongest orientation per location
 *  are considered and the rest ignored.
 *
 *  In either phase we start by creating the C1 Composite.
 *
 *  In learning we then select a random 4x4 input patch from the composite and
 *  we only store it as a learned template patch if:
 *  1) At least 25% of the cells are non-zero and
 *  2) The patch has less than x% similarity to any existing learned patch.
 *     Meaning if we have 10 learned patches already, and our similarly threshold
 *     is 90%, then we will not accept a new patch unless its RBF value is below 90%
 *     similar to all the existing patches.
 *     This helps ensure a minimal level of uniqueness/variety among learned
 *     patch templates.
 *  If a candidate patch fails, we will retry up to x (default 25) other patches
 *  within the C1 Composite before giving up and assuming the layer is too similar.
 *
 *  Once we have enough template patches learned we can run the filter in inference.
 *  For inference each patch in the current C1 Composite is compared against all
 *  learned template patches and scored using a Gaussian Radial-Basis-Function
 *  similarity value.  All of these values are sent as output to the next layer.
 *
 *  The GRBF response of a patch of C1 units X to a particular S2 template/patch P is:
 *  R(X,P) = exp(-(||X-P||^2) / 2sg^2*a)
 *
 *  sg = sigma (set to 1.0 currently)
 *  a = alpha normalizing factor if patch sizes can vary (1.0 currently)
 */

#ifndef GRBFFILTER_H_
#define GRBFFILTER_H_

#include "LayerC.h"

class GRBFFilterC {
public:

  GRBFFilterC(int xyCount, float sigma);
  ~GRBFFilterC();

  void computeLayer(float* learnedW, float* learnedPF, int learnedCount,
                    LayerC* layerIn, LayerC* layerOut);

private:
  int _xyCount;
  float _sigma;
};

#endif /* GRBFFILTER_H_ */
