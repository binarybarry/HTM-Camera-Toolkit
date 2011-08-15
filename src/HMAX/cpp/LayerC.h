/*
 * LayerC.h
 *
 *  Created on: May 28, 2011
 *      Author: barry
 *
 *  The LayerC will hold the processed C++ data from each of the C++
 *  implemented Filters.  When the code returns back to python we
 *  can copy the result arrays from the LayerC back to the python
 *  Layer.
 */

#ifndef LAYERC_H_
#define LAYERC_H_

class LayerC {
public:
  LayerC(int xSize, int ySize, int fSize, float xStart, float yStart,
      float xSpace, float ySpace, float* data);
  ~LayerC();

  int xSize();
  int ySize();
  int fSize();

  float xSpace();
  float ySpace();

  /**
   * Convert the input layer-space integer x-coordinate into its
   * equivalent in real-valued retinal space.  Since a layer space
   * coordinate represents a cell in retinal-space, the returned
   * value will represent the center point of that cell.
   * @param xi: integer x-coordinate in layer-space.
   * @return: equivalent real-valued x-coordinate in retinal-space.
   */
  float xCenter(int xi);

  /**
   * Convert the input layer-space integer y-coordinate into its
   * equivalent in real-valued retinal space.  Since a layer space
   * coordinate represents a cell in retinal-space, the returned
   * value will represent the center point of that cell.
   * @param xi: integer y-coordinate in layer-space.
   * @return: equivalent real-valued y-coordinate in retinal-space.
   */
  float yCenter(int yi);

  bool getXRFDist(float c, float r, int &i1, int &i2);
  bool getYRFDist(float c, float r, int &i1, int &i2);
  void RFDist(int t, float s, float d, float c, float r,
              int &i1, int &i2, int &j1, int &j2);

  bool getXRFNear(float c, int n, int &i1, int &i2);
  bool getYRFNear(float c, int n, int &i1, int &i2);
  void RFNear(int t, float s, float d, float c, int n,
              int &i1, int &i2, int &j1, int &j2);

  void setValue(int x, int y, int f, float val);
  float getValue(int x, int y, int f);

  float* getLayerData(int f);

  inline int min(int a, int b) {
    return (a <= b) ? a : b;
  }

  inline int max(int a, int b) {
    return (a >= b) ? a : b;
  }

private:
  int _xSize, _ySize, _fSize;
  float _xStart, _yStart, _xSpace, _ySpace;
  float* _data;
};

#endif /* LAYERC_H_ */
