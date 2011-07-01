'''
Created on May 3, 2011

@author: barry
'''

import hmaxc
import numpy
import wx
from PIL import ImageDraw
import Util

class Layer(object):
  """
  doc
  """
  displaySize = (320,240)
  
  def __init__(self, level, xySize, fSize, xyStart, xySpace, inputLayers=[]):
    """
    Allocate a new layer of size [(xySize) by fSize].  The remaining four 
    parameters determine the (X, Y) grid positions in the common, 
    real-valued coordinate system.  xyStart is the position of XY index 0, 
    and xySpace determines the spacing between adjacent grid points along XY.  
    @param xySize: (x,y) integer tuple of size for this layer. 
    @param fSize: integer describing how many features (i.e. orientations, 
    templates, variations) this layer will contain.  Each feature is basically
    representing a different way to populate the values of the layer.
    @param xyStart: (xr,yr) real-value tuple mapping the upper-left (0,0) corner
    of the layer to its real-coordinate space equivalent.
    @param xySpace: (xs,ys) real-value tuple describing the spacing between
    layer cells in terms of real-coordinate space.
    """
    self.__xySize = xySize
    self.__fSize = fSize
    self.__level = level
    self.xyStart = xyStart
    self.xySpace = xySpace
    self.array = numpy.zeros((self.fSize,self.xSize,self.ySize))
    self.cArray = None #Lazy-load on first access if needed
    self.inputLayers = inputLayers
  
  @property
  def level(self):
    return self.__level
  
  @property
  def index(self):
    return self.level.layers.index(self)
  
  @property
  def xySize(self):
    return self.__xySize
  
  @property
  def xSize(self):
    return self.__xySize[0]
  
  @property
  def ySize(self):
    return self.__xySize[1]
  
  @property
  def fSize(self):
    return self.__fSize
  
  def __repr__(self):
    return self.level.name+", Layer"+str(self.index)+" ("+ \
           str(self.xSize)+"x"+str(self.ySize)+") f="+str(self.fSize)+ \
           " rxw:"+str(self.xyStart[0])+","+str(self.xySpace[0])
  
  def set(self, ipos, f, val):
    self.array[f][ipos] = val
  
  def get(self, ipos, f):
    return self.array[f][ipos]
  
  def setLayerData(self, arrayInput, f=0):
    assert arrayInput.shape[0]==self.__xySize[0] and \
           arrayInput.shape[1]==self.__xySize[1]
    self.array[f] = arrayInput #TODO copy into existing array?
  
  def getLayerData(self, f=0):
    return self.array[f]
  
  def getLayerDataAsCArray(self, f=0):
    """ 
    Return a copy of the layer's data matrix for index f converted 
    into a flattened 1D float array (C float[]).
    """
    if self.cArray==None:
      self.cArray = hmaxc.floatCArray(self.xSize*self.ySize)
    for j in xrange(self.ySize):
      for i in xrange(self.xSize):
        self.cArray[(j*self.xSize) + i] = self.array[f][i][j]
    return self.cArray
  
  def xyCenter(self, xyi):
    """
    Convert the input layer-space integer xy-coordinate into its
    equivalent in real-valued retinal space.  Since a layer space
    coordinate represents a cell in retinal-space, the returned
    value will represent the center point of that cell.
    @param xyi: tuple (x,y) of an integer xy-coordinate in layer-space.
    @return: tuple (rx,ry) of the real-valued xy-coordinate in retinal-space.
    """
    return (self.xCenter(xyi[0]), self.yCenter(xyi[1]))
  
  def xCenter(self, xi):
    """ 
    Convert the input layer-space integer x-coordinate into its
    equivalent in real-valued retinal space.  Since a layer space
    coordinate represents a cell in retinal-space, the returned
    value will represent the center point of that cell.
    @param xi: integer x-coordinate in layer-space.
    @return: equivalent real-valued x-coordinate in retinal-space.
    """
    return self.xyStart[0] + (xi*self.xySpace[0])
  
  def yCenter(self, yi):
    """ 
    Convert the input layer-space integer y-coordinate into its
    equivalent in real-valued retinal space.  Since a layer space
    coordinate represents a cell in retinal-space, the returned
    value will represent the center point of that cell.
    @param xi: integer x-coordinate in layer-space.
    @return: equivalent real-valued x-coordinate in retinal-space.
    """
    return self.xyStart[1] + (yi*self.xySpace[1])
  
  def getBoundBoxHierarchy(self, layerBBox):
    """ 
    For the input bound box (in integer layer space) for this layer,
    walk down the hierarchy of layer inputs to the layer and return the
    bounding boxes in all child layers that correspond to what was used
    as input to generate the original layer bound box parameter.
    @param layerBBox: bound box tuple (x,y,w,h) in integer layer space.
    @return: a dictionary of {layer : displayBBox} that maps each layer in
    the hierarchy to a bounding box in display space for the relevent areas.
    """
    boxMap = {self : self.getBBoxLayerToDisplay(layerBBox)}
    
    bbox = layerBBox
    for layer in self.inputLayers:
      rx, ry =  self.xyCenter(bbox[0:2])
      rx2,ry2 = self.xyCenter((bbox[0]+bbox[2],bbox[1]+bbox[3]))
      rbbox = (rx,ry, rx2-rx, ry2-ry)
      ibbox = self.level.filter.getInputBoundBox(layer, rbbox)
      bMap = layer.getBoundBoxHierarchy(ibbox) #recurse to get all children
      
      for k in bMap.keys():
        boxMap[k] = bMap[k]
    
    return boxMap
  
  def getBBoxDisplayToLayer(self, displayPos):
    """ doc """
    xBin = 1.0*Layer.displaySize[0] / self.xSize
    yBin = 1.0*Layer.displaySize[1] / self.ySize
    return (numpy.floor(displayPos[0] / xBin), \
            numpy.floor(displayPos[1] / yBin), 0.0, 0.0)
  
  def getBBoxLayerToDisplay(self, layerBBox):
    """ 
    Convert the input bounding box (x,y,w,h) from integer layer space
    into the corresponding bounding box in visual display space appropriate
    for a graphics display.
    @param layerBBox: bound box tuple (x,y,w,h) in integer layer space.
    @return: an integer bound box tuple (x,y,w,h) in visual display space.
    """
    xBin = 1.0*Layer.displaySize[0] / self.xSize
    yBin = 1.0*Layer.displaySize[1] / self.ySize
    
    lpos = (layerBBox[0], layerBBox[1])
    lsize = (layerBBox[2]+1.0, layerBBox[3]+1.0) #Add 1 for node-->cell
    return (numpy.round(xBin*lpos[0]), numpy.round(yBin*lpos[1]), \
            numpy.round(xBin*lsize[0]), numpy.round(yBin*lsize[1]))
  
  def getXRFNear(self, c, n):
    """
    For the X dimension, find the N nearest indices to position C in the 
    real-valued retinal coordinate system.  The range of indices will be 
    returned in I1 and I2.  If any of the found indices are outside the valid
    range [0 YSIZE-1] or [0 XSIZE-1], only the valid part of the range will 
    be returned in I1 and I2, and the function's return value will be false.  
    If N valid indices can be returned, the return value will be true.
    """
    i1,i2,j1,j2 = self.getRFNear(self.xSize, self.xyStart[0], self.xySpace[0], c, n)
    return ((i1,i2), (i1==j1) and (i2==j2))
  
  def getYRFNear(self, c, n):
    i1,i2,j1,j2 = self.getRFNear(self.ySize, self.xyStart[1], self.xySpace[1], c, n)
    return ((i1,i2), (i1==j1) and (i2==j2))
    
  def getRFNear(self, t, s, d, c, n):
    dd = 1.0 / d
    j1 = int(numpy.ceil((c - s) * dd - 0.5 * n - 0.001))
    j2 = j1 + n - 1
    i1 = min(max(j1, 0), t)
    i2 = min(max(j2,-1), t-1)
    return i1,i2,j1,j2
  
  
  def getXRFDist(self, c, r):
    """
    Similar to getXRFNear above, except instead of finding the N nearest 
    indices, we find all indices within distance R of C, both specified 
    in real-value retinal coordinates.  If any of the indices found are 
    invalid, the range in I1/I2 is truncated and the return value will 
    be false, otherwise we return true.
    """
    i1,i2,j1,j2 = self.getRFDist(self.xSize, self.xyStart[0], self.xySpace[0], c, r)
    return ((i1,i2), (i1==j1) and (i2==j2))
  
  def getYRFDist(self, c, r):
    i1,i2,j1,j2 = self.getRFDist(self.ySize, self.xyStart[1], self.xySpace[1], c, r)
    return ((i1,i2), (i1==j1) and (i2==j2))
  
  def getRFDist(self, t, s, d, c, r):
    dd = 1.0 / d
    j1 = int(numpy.ceil( (c - r - s) * dd - 0.001))
    j2 = int(numpy.floor((c + r - s) * dd + 0.001))
    i1 = min(max(j1, 0), t)
    i2 = min(max(j2,-1), t-1)
    return i1,i2,j1,j2
  
  def renderLayer(self, canvas, f=0, normalize=False, normVal=1.0):
    """ 
    Render the layer data array onto the specified wx canvas. 
    """
    array = self.getLayerData(f)
    if normalize:
      array = numpy.array(array)
      array *= (255.0/normVal)
    img = Util.convertNumpyToPIL(array, binary=False)
    imgFull = img.resize(Layer.displaySize)
    imageOut = Util.convertToWxImage(imgFull)
    canvas.setBitmap(wx.BitmapFromImage(imageOut))
    return imgFull


class LayerS2(Layer):
  """
  Subclass of Layer with extra data content for layer S2.
  """
  
  def __init__(self, level, xySize, fSize, xyStart, xySpace, inputLayers=[]):
    Layer.__init__(self, level, xySize, fSize, xyStart, xySpace, inputLayers)
    
    layerC1 = inputLayers[0]
    cxSize, cySize = layerC1.xSize, layerC1.ySize
    self.arrayC1 = numpy.zeros((cxSize,cySize,2))
    self.arrayS2 = numpy.empty(xySize, dtype=numpy.object)
  
  def renderLayer(self, canvas, f=0, normalize=False, normVal=1.0):
    """ Render the layer data array onto the specified wx canvas. """
    imgFull = Layer.renderLayer(self, canvas, f, normalize, normVal)
    
    #Now render selection border around S2 Cells representing cluster
#    c2Filter = self.level.network.levels[4].filter
#    if c2Filter.lastCluster!=None:
#      img = imgFull.convert("RGB")
#      draw = ImageDraw.Draw(img)
#      
#      x0,y0 = c2Filter.lastClusterPos
#      for cell in c2Filter.lastCluster:
#        rx,ry = cell.rpos
#        dbbox = self.getBBoxLayerToDisplay([x0+rx, y0+ry, 0,0])
#        dbbox = [dbbox[0], dbbox[1], dbbox[0]+dbbox[2], dbbox[1]+dbbox[3]]
#        draw.rectangle(dbbox, outline="green")
#      
#      imageOut = Util.convertToWxImage(img)
#      canvas.setBitmap(wx.BitmapFromImage(imageOut))
      
  
  def generateS2InputBitmap(self, mousePos, c1Type="C1 Composite"):
    """ 
    If S2 was clicked, find the 4x4 (vmax,f) matrix and generate a bitmap
    that can be drawn on top of C1 with composite of input thetas/values .
    If the "Show C1 Composite" option is enabled, then generate the bitmap
    for the entire C1 layer and render it as the visualization of C1.
    """
    #C1 Composite, S2 Selection, S2 Composite, S2 Match
    overlays = []
    bbox = self.getBBoxDisplayToLayer(mousePos)
    pos = bbox[0:2]
    boxMap = self.getBoundBoxHierarchy(bbox)
    dbbox = boxMap[self.inputLayers[0]]
    
    dbbox = (int(dbbox[0]), int(dbbox[1]), int(dbbox[2]), int(dbbox[3]))
    
    w,h = dbbox[2]/4.0,dbbox[3]/4.0
    r = min(w-2, h-2) / 2.0
    thetas = self.level.network.thetas
    
    c2Filter = self.level.network.levels[4].filter
    maxL1 = self.level.network.levels[1].getMaxLayerValue()
    cluster = None
    
    def renderS2Cell(vC1, fC1, imgSize):
      """ Render the S2Cell specified by its vmax[] and f[] arrays. """
      imgSize = (int(imgSize[0]), int(imgSize[1]))
      img = Util.convertNumpyToPIL(vC1, binary=False)
      img = img.resize(imgSize).convert("RGB")
      draw = ImageDraw.Draw(img)
    
      for xi in xrange(len(fC1)):
        for yi in xrange(len(fC1[xi])):
          if vC1[xi][yi] > 0.0:
            theta = thetas[int(fC1[xi][yi])] # + (numpy.pi/2.0)
            rx = numpy.cos(theta)*r
            ry = numpy.sin(theta)*r
            x = w*xi + (w/2)
            y = h*yi + (h/2)
            draw.line(((x-rx,y-ry),(x+rx,y+ry)), fill="blue", width=2)
      del draw
      return img
    
    if c1Type=="C1 Composite": #C1 Composite
      imgSize = Layer.displaySize
      bboxOut = (0,0, imgSize[0],imgSize[1])
      vC1 = numpy.array(self.arrayC1[:,:,0])
      fC1 = self.arrayC1[:,:,1]
    elif c1Type=="S2 Selection": #S2 Selection
      imgSize = dbbox[2:4]
      bboxOut = dbbox
      vC1 = numpy.array(self.arrayS2[pos].s4x4[:,:,0])
      fC1 = self.arrayS2[pos].s4x4[:,:,1]
    elif c1Type=="S2 Composite": #S2 Composite
      if c2Filter.lastCluster==None:
        return None
      cluster = c2Filter.lastCluster
    elif c1Type=="S2 Match": #S2 Match
      if c2Filter.bestCluster==None:
        return None
      cluster = c2Filter.bestCluster
    
    #Render the current or best-matching S2 cell cluster
    if cluster!=None:
      c1Layer = self.inputLayers[0]
      x0,y0 = c2Filter.lastClusterPos
      for cell in cluster:
        #figure out the displayBBox for the S2 pos (x+rx)
        rx,ry = cell.rpos
        dbbox = c1Layer.getBBoxLayerToDisplay([x0+rx, y0+ry, 3,3])
        vC1 = numpy.array(cell.s4x4[:,:,0])
        fC1 = cell.s4x4[:,:,1]
        
        vC1 *= (255.0 / maxL1)
        img = renderS2Cell(vC1, fC1, dbbox[2:4])
        overlays.append((wx.BitmapFromImage(Util.convertToWxImage(img)), dbbox))
      return overlays
    
    vC1 *= (255.0 / maxL1)
    img = renderS2Cell(vC1, fC1, imgSize)
    overlays.append((wx.BitmapFromImage(Util.convertToWxImage(img)), bboxOut))
    return overlays
    


class LayerC(Layer):
  """
  Wrapper class for the C++ hmaxc.LayerC object.  This class extends the
  standard python Layer class so all the non-performance sensitive code is
  shared.  LayerC objects can only be used if the filter object that
  processes the Layer is also using C++ internals (if it is not the LayerC
  behaves like a standard Layer).  For example, GaborFilterC can make use
  of LayerC inputs to perform fast filtering on the layer data.
  """
  def __init__(self, level, xySize, fSize, xyStart, xySpace, inputLayers=[]):
    Layer.__init__(self, level, xySize, fSize, xyStart, xySpace, inputLayers)
    
    #int xSize, int ySize, int fSize, float xStart, float yStart,
    #  float xSpace, float ySpace
    self.cArray = hmaxc.floatCArray(self.fSize * self.xSize*self.ySize)
    self.cLayer = hmaxc.LayerC(xySize[0], xySize[1], fSize, xyStart[0], \
                               xyStart[1], xySpace[0], xySpace[1], self.cArray)
  
  def setLayerDataFromCArray(self):
    """ 
    Copy the layer data from the flattened 1D C float[] into the normal
    numpy array for this layer so it can be used by regular python code.
    It is assumed that the input float[] has length == xSize*ySize for
    the layer, things will crash if the float[] is too short.
    """
    for f in xrange(self.fSize):
      fi = f * (self.xSize*self.ySize)
      for j in xrange(self.ySize):
        for i in xrange(self.xSize):
          self.array[f][i][j] = self.cArray[fi + (j*self.xSize) + i]

