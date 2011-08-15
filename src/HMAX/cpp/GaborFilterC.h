/*
 * GaborFilterC.h
 *
 *  Created on: May 25, 2011
 *      Author: barry
 *
 * Implementation of Gabor filters (S1) used by the HMAX algorithm.
 * The Gabor filter is used to detect how strongly a patch of pixels
 * matches lines of particular orientations.  The Gabor filter is
 * commonly used to approximate the V1 area of neocortex.
 *
 * The equation to generate a Gabor filter is as follows:
 * G(x,y) = exp(-(X^2 + r^2*Y^2) / 2sg^2) * cos(2pi*X / ld)
 *
 * where:
 *  X = x*cos(theta) - y*sin(theta)
 *  Y = x*sin(theta) + y*cos(theta)
 *  r = aspectRatio
 *  sg = sigma (effective width)
 *  ld = lamda (wavelength)
 *
 * The response of a patch of pixels X to a particular S1/Gabor
 * filter is given by:
 * R(X,G) = | sum(Xi*Gi) / sqrt(sum(Xi^2)) |
 *
 * Some common values used for various gabor filter sizes are as
 * follows (obtained through trial-and-error experimentation):
 * size --- sigma --- lambda -- C1
 *   7       2.8       3.5
 *   9       3.6       4.6     8x8 4over
 *  11       4.5       5.6
 *  13       5.4       6.8     10x10 5over
 *  15       6.3       7.9
 *  17       7.3       9.1     12x12 6over
 */

#ifndef GABORFILTERC_H_
#define GABORFILTERC_H_

#include "LayerC.h"

/***********************************************************************************************************************
Applies a set of gabor filters at each position in a single image.
***********************************************************************************************************************/

class GaborFilterC {
public:

  //def __init__(self, thetas, size=11, lam=5.6, sigma=4.5, aspect=0.3):
  GaborFilterC(float* thetas, int thetaCount, int size=11, float lam=5.6, float sigma=4.5, float aspect=0.3);
  ~GaborFilterC();

  int thetaCount() const { return _thetaCount; };

  void computeLayer(float* layerIn, int wi, int hi,
                    LayerC* layerOut);

  void computeLayer(float* layerIn, int wi, int hi,
                    float* layerOut, int wo, int ho, int thetaIndex);

private:

  int    _size;
  int    _thetaCount;
  float *_gabors;
};

#endif /* GABORFILTERC_H_ */
