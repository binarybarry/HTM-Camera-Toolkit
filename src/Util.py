"""
Created on Feb 15, 2011

@author: Barry Maturkanich

Utility methods used by the rest of the package.
For example, a helper to convert a PIL image into
a Wx image.
"""

from StringIO import StringIO

import wx
import cv
import numpy
from PIL import Image, ImageDraw

def generateVideoClip(videoDir="."):
  """ 
  Generate a simple example black and white video clip that can be used
  as input to the Camera Toolkit for performing basic experiments.
  By default the method is writing a video file consisting of a horizontal
  white line against a black background. The line moves from top to 
  bottom and back again 1 pixel at a time.
  The code can be edited by changing the looping parameters on line 46
  and what is painted per frame on line 53.
  @param videoDir: the directory the video will be created in.
  """
  suffix = "LineHorizontal.avi" #edit this for different file names
  fileName = videoDir+suffix
  width = 80  #the Region prefers 80x60 resolution video frames
  height = 60
      
  #Create a videoWriter to use to write out the generated video file
  #Always use uncompressed YUV codec for universal playback
  #method doc: CreateVideoWriter(filename, fourcc, fps, frame_size, is_color)
  videoWriter = cv.CreateVideoWriter(fileName, cv.CV_FOURCC('I','Y','U','V'), \
                                     15, (width,height), 0)
  
  #Allocate a PIL image to paint into for each video frame
  vidFrame = Image.new('L', (width,height))
  
  print "writing video",fileName
  
  #Each pass in this loop will generate a subsequent video frame
  #For a horizontal line, loop from top to bottom, and back again
  for i in range(0,height)+range(height-2,-1,-1):
    #fill frame with black, then draw white lines/dots for the frame
    draw = ImageDraw.Draw(vidFrame)
    draw.rectangle((0,0, width,height), fill="black")
    
    #now that frame is black again, draw a white line in current position
    draw.line((0,i,width,i), fill="white", width=1)
    #we could do other things here instead, such as drawing points:
    #draw.point((x,y), fill="white")
    del draw #done performing drawing for this frame
    
    #now convert the PIL image into an OpenCV image and write to video
    cvImage = cv.CreateImageHeader(vidFrame.size, cv.IPL_DEPTH_8U, 1)
    cv.SetData(cvImage, vidFrame.tostring())
    cv.WriteFrame(videoWriter, cvImage)
    
  del videoWriter #close video stream when done to finish file
  return suffix #return fileName suffix as indicator of success

def convertPILtoNumpy(image):
  """ 
  Convert the specified PIL 'L' mode image into a 2D Numpy array.
  It is assumed the 'L' mode input image has only 255 and 0
  (black and white).  The output numpy array will convert the
  255 down to 1 (divide all values by 255).  The numpy array
  will have the same size/shape as the input image.
  """
  imgMat = numpy.array(numpy.asarray(image, dtype=numpy.uint8))
  imgMat = imgMat.reshape((image.size[1],image.size[0]))
  imgMat = numpy.swapaxes(imgMat, 0, 1)
  imgMat /= 255 #255 for white needs to be 1s instead
  return imgMat

def convertNumpyToPIL(array):
  """ 
  Convert the specified 2D Numpy array of 1's and 0's into
  a PIL 'L' mode image of the same shape.
  """
  array *= 255
  array = numpy.swapaxes(array, 0, 1)
  return Image.fromarray(array)

def convertPILToCV(image):
  """ Convert the specified PIL 'L' mode image into an OpenCV IplImage. """
  cvImage = cv.CreateImageHeader(image.size, cv.IPL_DEPTH_8U, 1)
  cv.SetData(cvImage, image.tostring())
  return cvImage

def convertToWxImage(image):
  """Convert the value (string or PIL image) to a wx image."""

  if type(image) is str:
    # Load from stream
    return wx.ImageFromStream(StringIO(image))

  else:
    # Convert from PIL
    if 'A' in image.mode:
      if image.mode != 'RGBA':
        image = image.convert('RGBA')
      wxImage = wx.EmptyImage(*image.size)
      wxImage.SetData(image.convert('RGB').tostring())
      wxImage.SetAlphaData(image.tostring()[3::4])
    else:
      if image.mode != 'RGB':
        image = image.convert('RGB')
      wxImage = wx.EmptyImage(*image.size)
      wxImage.SetData(image.tostring())
    return wxImage