"""
Created on May 3, 2011

@author: Barry Maturkanich

This file contains the definition of a single data layer within
a given hierarchical level within an HMAX network.

An HMAX network is designed to take an input image and produce multiple
resized versions (scales) of the image.  The intent is that a range of
image sizes will help the algorithm become exposed to a greater range
of object sizes.  Since we keep the Gabor filter size fixed (at say 9x9),
as we decrease the image resolution the Gabor filter is effectively 
covering a larger and larger area of the image.  In this way we can
detect orientated lines at a range of sizes from rather small to
rather large.

A single layer then contains a set of data usually to represent a given
size scaling.  By having multiple layers we can store multiple image scales
at once and process then in parallel.  As we ascend the hierarchy we slowly
combine the scale layers by selecting the best responses between 2 neighboring
scales resulting in an overall best response across many sizes.

Layers have a concept of both discrete-space and what we call retinal-space.
The discrete space is simply the actual indicies corresponding to a numpy 2d
matrix that is storing the actual layer values (i.e. the pixel values for
the image).  While retinal-space is a real-valued global space, where (0.0,0.0)
indicate the center of the image and this location is consistent across all
hierarchical levels despite that each level will have discrete matricies
of differing dimensions.  Using the retinal-space we have a way of ensuring
accurate comparisons of locations across different layers in different levels.

Layers are also given an ability to render themselves to a wx canvas image.
The default rendering simply maps the layer values to a 0-255 range and
colors the cells between black and white to show the range of values present.

However some layers can implement more elaborate rendering schemes to help
visualize more specific results.  For example the C2 SVM can render a bar
graph depicting its classification results. 
"""

import hmaxc
import numpy
import wx
from PIL import Image, ImageDraw
import Util

SIGF1 = "{0:.1f}" #1 significant digits float string format code

class Layer(object):
  """
  Implementation of a single Layer within a given hierarchical level
  in an HMAX network.  A single layer usually stores a single size-scale
  worth of data within a level.
  """
  canvasSize = (320,240) #size of wx canvas to render layer results into
  
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
    @param inputLayers: list of Layers that are connected as the inputs to
    this current layer.
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
  
  @property
  def label(self):
    """ Return a simple string that can be used to label this layer in a UI. """
    return self.level.name+" ("+str(self.xSize)+"x"+str(self.ySize)+")"
  
  def __repr__(self):
    return self.level.name+", Layer"+str(self.index)+" ("+ \
           str(self.xSize)+"x"+str(self.ySize)+") f="+str(self.fSize)+ \
           " rxw:"+str(self.xyStart[0])+","+str(self.xySpace[0])
  
  def set(self, ipos, f, val):
    """ 
    Assign the value 'val' into this layer's data matrix at location 
    ipos (x,y) in feature f. 
    """
    self.array[f][ipos] = val
  
  def get(self, ipos, f):
    """ 
    Return the value stored in this layer's data matrix at location 
    ipos (x,y) for feature f. 
    """
    return self.array[f][ipos]
  
  def setLayerData(self, arrayInput, f=0):
    """ Assign the entire matrix of layer data for feature f. """
    assert arrayInput.shape[0]==self.__xySize[0] and \
           arrayInput.shape[1]==self.__xySize[1]
    self.array[f] = arrayInput #TODO copy into existing array?
  
  def getLayerData(self, f=0):
    """ Return the entire matrix of layer data for feature f. """
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
    """ 
    For the render display position (x,y) return the corresponding 
    position bounding box in layer discrete space. 
    """
    xBin = 1.0*Layer.canvasSize[0] / self.xSize
    yBin = 1.0*Layer.canvasSize[1] / self.ySize
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
    xBin = 1.0*Layer.canvasSize[0] / self.xSize
    yBin = 1.0*Layer.canvasSize[1] / self.ySize
    
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
    be returned in I1 and I2, and the function's return value will include false.  
    If N valid indices can be returned, the return value will include true.
    @return: ((i1,i2), isOK)
    """
    i1,i2,j1,j2 = self.__getRFNear(self.xSize, self.xyStart[0], self.xySpace[0], c, n)
    return ((i1,i2), (i1==j1) and (i2==j2))
  
  def getYRFNear(self, c, n):
    """
    For the Y dimension, find the N nearest indices to position C in the 
    real-valued retinal coordinate system.  The range of indices will be 
    returned in I1 and I2.  If any of the found indices are outside the valid
    range [0 YSIZE-1] or [0 XSIZE-1], only the valid part of the range will 
    be returned in I1 and I2, and the function's return value will include false.  
    If N valid indices can be returned, the return value will include true.
    @return: ((i1,i2), isOK)
    """
    i1,i2,j1,j2 = self.__getRFNear(self.ySize, self.xyStart[1], self.xySpace[1], c, n)
    return ((i1,i2), (i1==j1) and (i2==j2))
    
  def __getRFNear(self, t, s, d, c, n):
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
    @return: ((i1,i2), isOK)
    """
    i1,i2,j1,j2 = self.__getRFDist(self.xSize, self.xyStart[0], self.xySpace[0], c, r)
    return ((i1,i2), (i1==j1) and (i2==j2))
  
  def getYRFDist(self, c, r):
    """
    Similar to getYRFNear above, except instead of finding the N nearest 
    indices, we find all indices within distance R of C, both specified 
    in real-value retinal coordinates.  If any of the indices found are 
    invalid, the range in I1/I2 is truncated and the return value will 
    be false, otherwise we return true.
    @return: ((i1,i2), isOK)
    """
    i1,i2,j1,j2 = self.__getRFDist(self.ySize, self.xyStart[1], self.xySpace[1], c, r)
    return ((i1,i2), (i1==j1) and (i2==j2))
  
  def __getRFDist(self, t, s, d, c, r):
    dd = 1.0 / d
    j1 = int(numpy.ceil( (c - r - s) * dd - 0.001))
    j2 = int(numpy.floor((c + r - s) * dd + 0.001))
    i1 = min(max(j1, 0), t)
    i2 = min(max(j2,-1), t-1)
    return i1,i2,j1,j2
  
  def renderLayer(self, canvas, f=0, normalize=False, normVal=1.0):
    """ 
    Render the layer data array onto the specified wx canvas. 
    @param canvas: the wx canvas to render the layer data onto.
    @param f: the feature index of the layer data to render.
    @param normalize: if true normalize the layer's data to 0-255 range.
    @param normVal: the maximum layer value to map to 255 when normalizing.
    @return: the PIL image that was rendered to the wx canvas.
    """
    array = self.getLayerData(f)
    if normalize:
      array = numpy.array(array)
      array *= (255.0/normVal)
    img = Util.convertNumpyToPIL(array, binary=False)
    imgFull = img.resize(Layer.canvasSize)
    imageOut = Util.convertToWxImage(imgFull)
    canvas.setBitmap(wx.BitmapFromImage(imageOut))
    return imgFull


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
  
  def setLayerDataFromCArray(self, checkSame=False):
    """ 
    Copy the layer data from the flattened 1D C float[] into the normal
    numpy array for this layer so it can be used by regular python code.
    It is assumed that the input float[] has length == xSize*ySize for
    the layer, the code will hard-crash if the float[] is too short.
    @param checkSame: optional parameter used during testing to check
    that values returned from C++ code match that of python code.
    """
    for f in xrange(self.fSize):
      fi = f * (self.xSize*self.ySize)
      for j in xrange(self.ySize):
        for i in xrange(self.xSize):
          #val = self.array[f][i][j]
          self.array[f][i][j] = self.cArray[fi + (j*self.xSize) + i]
          #if checkSame and val!=self.array[f][i][j]:
          #  print "Mismatch: ",val,self.array[f][i][j]


class LayerS2(LayerC):
  """
  Subclass of Layer with extra data content for layer S2.
  Specifically we have special rendering needs to S2 which include
  generating a rendering of the C1 Composite layer used by S2.
  """
  
  def __init__(self, level, xySize, fSize, xyStart, xySpace, inputLayers=[]):
    LayerC.__init__(self, level, xySize, fSize, xyStart, xySpace, inputLayers)
    
    layerC1 = inputLayers[0]
    cxSize, cySize = layerC1.xSize, layerC1.ySize
    self.arrayC1 = numpy.zeros((cxSize,cySize,2))
    self.arrayS2 = numpy.empty(xySize, dtype=numpy.object)
  
  def renderLayer(self, canvas, f=0, normalize=False, normVal=1.0):
    """ Render the layer data array onto the specified wx canvas. """
    imgFull = Layer.renderLayer(self, canvas, f, normalize, normVal)
    
    #Experimental: render selection border around S2 Cells representing cluster
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
    #C1 Composite, S2 Selection, (S2 Composite, S2 Match)
    overlays = []
    bbox = self.getBBoxDisplayToLayer(mousePos)
    pos = bbox[0:2]
    boxMap = self.getBoundBoxHierarchy(bbox)
    dbbox = boxMap[self.inputLayers[0]]
    
    dbbox = (int(dbbox[0]), int(dbbox[1]), int(dbbox[2]), int(dbbox[3]))
    
    w,h = dbbox[2]/4.0,dbbox[3]/4.0
    r = min(w-2, h-2) / 2.0
    thetas = self.level.network.thetas
    
    #cluster = None
    #c2Filter = self.level.network.C2
    maxS1 = self.level.network.levels[1].getMaxLayerValue()
    
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
      imgSize = Layer.canvasSize
      bboxOut = (0,0, imgSize[0],imgSize[1])
      vC1 = numpy.array(self.arrayC1[:,:,0])
      fC1 = self.arrayC1[:,:,1]
    elif c1Type=="S2 Selection": #S2 Selection
      imgSize = dbbox[2:4]
      bboxOut = dbbox
      vC1 = numpy.array(self.arrayS2[pos].s4x4[:,:,0])
      fC1 = self.arrayS2[pos].s4x4[:,:,1]
    #Experimental: rendering 'multi-patches', leave out for now..
#    elif c1Type=="S2 Composite": #S2 Composite
#      if c2Filter.lastCluster==None:
#        return None
#      cluster = c2Filter.lastCluster
#    elif c1Type=="S2 Match": #S2 Match
#      if c2Filter.bestCluster==None:
#        return None
#      cluster = c2Filter.bestCluster
#    
#    #Render the current or best-matching S2 cell cluster
#    if cluster!=None:
#      c1Layer = self.inputLayers[0]
#      x0,y0 = c2Filter.lastClusterPos
#      for cell in cluster:
#        #figure out the displayBBox for the S2 pos (x+rx)
#        rx,ry = cell.rpos
#        dbbox = c1Layer.getBBoxLayerToDisplay([x0+rx, y0+ry, 3,3])
#        vC1 = numpy.array(cell.s4x4[:,:,0])
#        fC1 = cell.s4x4[:,:,1]
#        
#        vC1 *= (255.0 / maxS1)
#        img = renderS2Cell(vC1, fC1, dbbox[2:4])
#        overlays.append((wx.BitmapFromImage(Util.convertToWxImage(img)), dbbox))
#      return overlays
    
    vC1 *= (255.0 / maxS1)
    img = renderS2Cell(vC1, fC1, imgSize)
    overlays.append((wx.BitmapFromImage(Util.convertToWxImage(img)), bboxOut))
    return overlays
    

class LayerC2(Layer):
  """
  Subclass of Layer with extra data content for layer C2.
  Specifially layer C2 uses custom rendering for its SVM inference
  results.
  """
  
  def __init__(self, level, xySize, fSize, xyStart, xySpace, inputLayers=[]):
    Layer.__init__(self, level, xySize, fSize, xyStart, xySpace, inputLayers)
    
    self.__buffer = Image.new('RGB', Layer.canvasSize)
    self.__lastResult = {}
    self.__classImages = {}
  
  def renderLayer(self, canvas, f=0, normalize=False, normVal=1.0):
    """ 
    Render the layer data array onto the specified wx canvas. 
    For C2, we render the SVM inference results as a bar graph
    showing how well the current input has matched the learned SVM
    classes.
    """
    xw, yh = Layer.canvasSize
    side = xw / 4
    spacing = side / 4
    
    draw = ImageDraw.Draw(self.__buffer)
    draw.rectangle((0,0,xw-1,yh-1), fill="white", outline="black")
    
    i = 1
    for acc,id in self.__lastResult:
      if i>3:
        break
      x = spacing*i+((i-1)*side)
      y = 50+side
      bh = int(round((y-10) * acc))
      img = self.__classImages[id]
      self.__buffer.paste(img, (x,y))
      draw.rectangle((x+5,y-5-bh, x+side-10, y-5), fill="blue", outline="black")
      draw.text((x+side/3, y+side+10), SIGF1.format(acc*100.0)+"%", fill="black")
      i += 1
    
    del draw
    imageOut = Util.convertToWxImage(self.__buffer)
    canvas.setBitmap(wx.BitmapFromImage(imageOut))
  
  def setAccuracyResult(self, lastResult):
    """ 
    Set the SVM accuracy results to be rendered by the layer. 
    The lastResult parameter is expected to be a list of (accuracy, classID)
    pairs where accuracy is a probability value between 0.0-1.0 and classID
    is the integer class corresponding to that accuracy.
    """
    #accuracies is map of classID to its probability for last result
    #lastResult should become sorted list of (id,prob), best first
    self.__lastResult = lastResult
  
  def saveExampleImage(self, classID):
    """ 
    Assign example images to be rendered when displaying SVM class 
    identifiers. Instead of integers we would like to show the user an
    example input image (from images that the SVM trained with) for each
    class.  The method will access the base level and save a snapshot of
    the raw input image and associate it with the classID integer provided.
    @param classID: integer class id for the image most recently processed
    by the network.
    """
    layer0 = self.inputLayers[0]
    while len(layer0.inputLayers)>0:
      layer0 = layer0.inputLayers[0]
      
    img = Util.convertNumpyToPIL(layer0.getLayerData(), False)
    side = Layer.canvasSize[0] / 4
    imgFinal = img.resize((side,side))
    self.__classImages[classID] = imgFinal



