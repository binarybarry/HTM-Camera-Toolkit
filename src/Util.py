"""
Created on Feb 15, 2011

@author: Barry Maturkanich

Utility methods used by the rest of the package.
For example, a helper to convert a PIL image into
a Wx image.
"""

from StringIO import StringIO

import os
import wx
import cv
import numpy
from PIL import Image, ImageDraw
from scipy import mat, linalg
from math import sqrt, sin, cos, radians

def generateVideoClip(videoDir="./video/"):
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
  suffix = "Rectangle17.avi" #edit this for different file names
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
  for x in range(8,width-25):
    #for y in xrange(15,height-15):
    #for i in range(0,height)+range(height-2,-1,-1):
    #fill frame with black, then draw white lines/dots for the frame
    draw = ImageDraw.Draw(vidFrame)
    draw.rectangle((0,0, width,height), fill="black")
    
    #now that frame is black again, draw a white line in current position
    #draw.line((0,i,width,i), fill="white", width=1)
    draw.rectangle((x,x, x+17,x+17), outline="white")
    
    #we could do other things here instead, such as drawing points:
    #draw.point((x,y), fill="white")
    del draw #done performing drawing for this frame
    
    #now convert the PIL image into an OpenCV image and write to video
    cvImage = cv.CreateImageHeader(vidFrame.size, cv.IPL_DEPTH_8U, 1)
    cv.SetData(cvImage, vidFrame.tostring())
    cv.WriteFrame(videoWriter, cvImage)
    
  del videoWriter #close video stream when done to finish file
  return suffix #return fileName suffix as indicator of success

def findSurfBlobs(cvImg):
  """ 
  Run the OpenCV ExtractSURF algorithm on the given input cvImage. 
  Render the results as circles with directional lines onto a copy of
  the input image and return this cvImage as the result of the method call.
  @param cvImg: input OpenCV image to perform SURF analysis on.
  @return: a copy of the input image with SURF results rendered onto it.
  """
  #Algorithm params tuple (extended, hessianThreshold, nOctaves, nOctaveLayers):
  #extended: 0 means basic descriptors (64 elements each), 1 means extended (128 each)
  #hessianThreshold: only features with hessian larger than that are extracted. 
  #  good default value is ~300-500 (can depend on the average local contrast 
  #  and sharpness of the image). user can further filter out some features based 
  #  on their hessian values and other characteristics.
  #nOctaves: the number of octaves to be used for extraction. 
  #  With each next octave the feature size is doubled (3 by default)
  #nOctaveLayers: The number of layers within each octave (4 by default)
  storage = cv.CreateMemStorage()
  (keypts, descs) = cv.ExtractSURF(cvImg, None, storage, (1, 100, 4, 1))
  
  cimg = cv.CreateImage((80,60), cv.IPL_DEPTH_8U, 3)
  cv.CvtColor(cvImg, cimg, cv.CV_GRAY2BGR)
  
  maxSize = 1
  for ((x, y), laplacian, size, dir, hessian) in keypts:
    maxSize = max(maxSize, size)
  
  for ((x, y), laplacian, size, dir, hessian) in keypts:
    print "x=%d y=%d laplacian=%d size=%d dir=%f hessian=%f" % (x, y, laplacian, size, dir, hessian)
    if size>=maxSize:
      x = int(x)
      y = int(y)
      cv.Circle(cimg, (x,y), size, cv.CV_RGB(0,0,255))
      deg = radians(dir)
      xd = int((x+(size*cos(deg))))
      yd = int(y+(size*sin(deg)*-1))
      cv.Line(cimg, (x,y), (xd,yd), cv.CV_RGB(0,0,255))
  print " "
  return cimg

def findStarKeypointBlobs(cvImg):
  """ 
  Run the OpenCV Star Keypoints algorithm on the given input cvImage.
  Render the results as circles onto a copy of the input image and return
  this cvImage as the result of the method call.
  @param cvImg: input OpenCV image to find Star Keypoints.
  @return: a copy of the input image with Star Keypoints results rendered onto it. 
  """
#  CvMemStorage* storage = cvCreateMemStorage(0);
#  cimg = cvCreateImage( cvGetSize(img), 8, 3 );
#  cvCvtColor( img, cimg, CV_GRAY2BGR );
#
#  keypoints = cvGetStarKeypoints( img, storage, cvStarDetectorParams(45) );
#
#  for( i = 0; i < (keypoints ? keypoints->total : 0); i++ )
#  {
#    CvStarKeypoint kpt = *(CvStarKeypoint*)cvGetSeqElem(keypoints, i);
#    int r = kpt.size/2;
#    cvCircle( cimg, kpt.pt, r, CV_RGB(0,255,0));
#    cvLine( cimg, cvPoint(kpt.pt.x + r, kpt.pt.y + r),
#        cvPoint(kpt.pt.x - r, kpt.pt.y - r), CV_RGB(0,255,0));
#    cvLine( cimg, cvPoint(kpt.pt.x - r, kpt.pt.y + r),
#        cvPoint(kpt.pt.x + r, kpt.pt.y - r), CV_RGB(0,255,0));
#  }
  storage = cv.CreateMemStorage()
  cimg = cv.CreateImage((cvImg.width,cvImg.height), cv.IPL_DEPTH_8U, 3)
  cv.CvtColor(cvImg, cimg, cv.CV_GRAY2BGR)
  
  #Each keypoint is represented by a tuple ((x, y), size, response)
  #maxSize = (4, 6, 8, 11, 12, 16, 22, 23, 32, 45, 46, 64, 90, 128)
#  maxSize = (16, 22, 23, 32, 45, 46, 64, 90, 128)
#  
#  for ms in maxSize:
#    for lp in xrange(0,101,10):
#      for lb in xrange(0,101,10):
#        for sns in xrange(0,51,5):
#          kps = cv.GetStarKeypoints(cvImg, storage, (ms, 0, lp, lb, sns))
#          if len(kps)>0:
#            for kpt in kps:
#              if kpt[1]>20:
#                print (ms, 0, lp, lb, sns, len(kps)), kpt[1]
#                break
  
  keypoints = cv.GetStarKeypoints(cvImg, storage, (32, 0, 80, 80, 0))
  if len(keypoints)==0:
    print keypoints
  for kpt in keypoints:
    if kpt[1]>=22:
      print kpt
      cv.Circle(cimg, kpt[0], kpt[1], cv.CV_RGB(0,0,255))
  print " "
  return cimg
    

def fitEllipse(cvImg):
  """
  Use OpenCV to find the contours of the input cvImage and then proceed to
  find best bit ellipses around the contours.  This is a rough approach to
  identifying the primary 'objects of interest' within an image.
  Render the results as ellipses onto a copy of the input image and return
  this cvImage as the result of the method call.
  @param cvImg: input OpenCV image to find best fit ellipses.
  @return: a copy of the input image with ellipse results rendered onto it. 
  """
  def contourIterator(contour):
    """ Helper method to iterate over cvContours. """
    while contour:
      yield contour
      contour = contour.h_next()
  
  # Find all contours.
  stor = cv.CreateMemStorage()
  cont = cv.FindContours(cvImg, stor, cv.CV_RETR_LIST, cv.CV_CHAIN_APPROX_NONE, (0, 0))
  
  cimg = cv.CreateImage((cvImg.width,cvImg.height), cv.IPL_DEPTH_8U, 3)
  cv.CvtColor(cvImg, cimg, cv.CV_GRAY2BGR)
  
#  clen = 0
#  for c in contourIterator(cont):
#    clen += len(c)
#  ptMat = cv.CreateMat(1, clen, cv.CV_32FC2)
  
#  ci = 0
  for c in contourIterator(cont):
#    for (i, (x, y)) in enumerate(c):
#      ptMat[0, i+ci] = (x, y)
#    ci += len(c)
    
    # Number of points must be more than or equal to 6 for cv.FitEllipse2
    if len(c) >= 6:
      # Copy the contour into an array of (x,y)s
      ptMat = cv.CreateMat(1, len(c), cv.CV_32FC2)
      for (i, (x, y)) in enumerate(c):
        ptMat[0, i] = (x, y)
                    
      # Draw the current contour in gray
      gray = cv.CV_RGB(150, 150, 150)
      cv.DrawContours(cimg, c, gray, gray,0,1,8,(0,0))
      
      # Fits ellipse to current contour.
      (center, size, angle) = cv.FitEllipse2(ptMat)
      
      # Convert ellipse data from float to integer representation.
      center = (cv.Round(center[0]), cv.Round(center[1]))
      size = (cv.Round(size[0] * 0.5), cv.Round(size[1] * 0.5))
      #angle = -angle
      
      # Draw ellipse in random color
      color = cv.CV_RGB(0,0,255)
      cv.Ellipse(cimg, center, size, angle, 0, 360, color, 1, cv.CV_AA, 0)
  
  return cimg

def calculateBlobPCA(array):
  """ 
  Given the 2D numpy array perform Principle Component Analysis
  on the pixels to find the center of gravity as well as the principle
  direction vectors to represent strongest rotation direction.
  """
  S = numpy.sum(array)
  
  ui = 0.0 #first moments
  uj = 0.0
  for i in xrange(array.shape[0]):
    for j in xrange(array.shape[1]):
      ui += array[i][j]*i
      uj += array[i][j]*j
  ui *= (1.0/S)
  uj *= (1.0/S)
  
  oi = 0.0 #second moments
  oj = 0.0
  oij = 0.0
  for i in xrange(array.shape[0]):
    for j in xrange(array.shape[1]):
      oi += array[i][j]*((i-ui)**2)
      oj += array[i][j]*((j-uj)**2)
      oij += array[i][j]*((i-ui)*(j-uj))
  oi *= (1.0/S)
  oj *= (1.0/S)
  oij *= (1.0/S)
  
  C = mat([[oi,oij],[oij,oj]]) #covarience matrix
  la,v = linalg.eig(C)         #eigen vectors/values
  return (ui,uj), (v[:,0]*sqrt(la[0]), v[:,1]*sqrt(la[1]))

def createMeanImage(image, radius=1):
  """ 
  Create a new image from the given image such that
  for every pixel in the input image, calculate the average
  value of all pixels within the radius and store that as 
  the value in the output image for that pixel. 
  """
  array = convertPILtoNumpy(image)
  meanArray = numpy.zeros(array.shape)
  
  for i in xrange(array.shape[0]):
    imin = max(0, i-radius)
    imax = min(array.shape[0], i+radius+1)
    a = array[imin:imax]
    for j in xrange(array.shape[1]):
      jmin = max(0, j-radius)
      jmax = min(array.shape[1], j+radius+1)
      ss = a.take(range(jmin,jmax), axis=1)
      meanArray[i][j] = numpy.mean(ss)
  
  meanArray = meanArray * (1.0 / numpy.max(meanArray))
  
  pt, vecs = calculateBlobPCA(meanArray)
  
  meanImage = convertNumpyToPIL(meanArray)
  
  draw = ImageDraw.Draw(meanImage)
  draw.line((pt, (pt[0]+vecs[0][0], pt[1]+vecs[0][1])), fill="white")
  draw.line((pt, (pt[0]+vecs[1][0], pt[1]+vecs[1][1])), fill="white")
  del draw
  
  return meanImage

#C:\Apps\Numenta\nupic-1.7.1\share\vision\data\ocr\test
ROOTDIR = "C:/Apps/Numenta/nupic-1.7.1/share/vision/data/ocr/test/"
DESTDIR = "C:/Apps/Numenta/CLA32/src/video/ocr/"
def mergeImageFilesToVideo(directory, outputFile="merge.avi", resolution=None, recurse=False):
  """ 
  Scan all files present in the specified directory and sort 
  alphabetically. Look at each file in order and if the file has
  an image extension (bmp, jpg, png) supported by OpenCV, then open
  it and append the image to an output video file.  If the resolution
  parameter is None then set the output video resolution to be the
  resolution of the first image file detected and resize subsequent
  image files to this size.
  @param directory: absolute directory location to scan.
  @param outputFile: name of the output video file to create.
  @param resolution: the output resolution to use for the video, if
  None then auto-detect based on first read image file.
  @param recurse: if true then recurse into all subdirectories and perform
  the same task to create one video file per directory containing images.
  """
  print "Check Dir: ",directory
  if not os.path.isdir(directory):
    raise RuntimeError("The path is not a valid directory.")
  
  cvImg = None
  videoWriter = None
  
  for file in os.listdir(directory):
    absFile = directory+file
    #print absFile
    ex = file[-4:]
    if os.path.isdir(absFile):
      if recurse:
        mergeImageFilesToVideo(absFile+os.sep, recurse=True)
    
    elif ex==".bmp" or ex==".jpg" or ex==".png":
      img = cv.LoadImage(absFile, cv.CV_LOAD_IMAGE_GRAYSCALE)
      if img==None:
        continue
      
      #TODO: what is img set to if file is not valid image?  (None?)
      if resolution==None:
        resolution = (img.width, img.height)
      if resolution[0]<64 or resolution[1]<64:
        resolution = (64,64)
      if videoWriter==None:
        outDir = DESTDIR+directory[len(ROOTDIR):].replace(os.sep, "_")
        print outDir+outputFile
        videoWriter = cv.CreateVideoWriter(outDir+outputFile, cv.CV_FOURCC('I','Y','U','V'), \
                                           15, resolution, 0)
      if cvImg==None:
        cvImg = cv.CreateImage(resolution, cv.IPL_DEPTH_8U, 1)
      
      cv.Resize(img, cvImg)
      cv.WriteFrame(videoWriter, cvImg)
      
  if videoWriter!=None:
    del videoWriter
  

if __name__ == '__main__':
  mergeImageFilesToVideo(ROOTDIR, recurse=True)

def convertPILtoNumpy(image, binary=True):
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
  if binary:
    imgMat /= 255 #255 for white needs to be 1s instead
  return imgMat

def convertNumpyToPIL(array, binary=True):
  """ 
  Convert the specified 2D Numpy array of 1's and 0's into
  a PIL 'L' mode image of the same shape.
  """
  if binary:
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
