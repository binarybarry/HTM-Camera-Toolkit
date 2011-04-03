"""
Created on Feb 15, 2011

@author: Barry Maturkanich

This file contains the main window UI for the HTM Camera Toolkit.

The main window includes a panel for video playback control, either from a live
camera/webcam or from a previously recorded video file.  Video files can
be created by recording video from the camera option.

There are 2 video displays showing both the raw video from the camera (if
applicable) as well as the processed binarized video input that is to be
fed into the base Region.

The video from the camera is processed using basic motion detection and
some thresholding to produce a binary (black and white only) image since
this is all the Region is currently able to easily understand at the moment.

The panels on the right allow the user to specify all the parameters used
to initialize a Region in order to maximize experimentation ability.
Multiple Regions can be built to form a hierarchy where the output from
a previous Region is used as the input to the next Region.

Finally, Regions can be optionally visualized in detail to examine how
learning is taking place and evaluate what is going on inside the Region
as time steps progress.
"""

import wx
import cv
import numpy
import os
from time import clock
from PIL import Image, ImageOps, ImageDraw
from Util import convertToWxImage
from RegionFrame import RegionFrame
from HTM.Region import Region
from HTM.Synapse import Synapse

SIGF = "{0:.2f}" #2 significant digits float string format code

class CameraFrame(wx.Frame):
  """
  The main Camera Toolkit wxFrame window.  We include the main menu bar and 
  attach the CameraWindow panel which contains all the real UI.
  """

  def __init__(self, parent=None):
    """
    Constructor to build the CameraFrame top-level window frame.
    """
    super(CameraFrame, self).__init__(parent, title="HTM Camera Toolkit",
          size=(950,720), 
          style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
    
    #Create the top-level application menu bar
    menubar = wx.MenuBar()
    
    file = wx.Menu()
    file.Append(wx.ID_EXIT, 'Exit', 'Exit application')
    self.Bind(wx.EVT_MENU, self.onExit, id=wx.ID_EXIT)
    
    options = wx.Menu()
    self.miShowAll = wx.MenuItem(options, wx.ID_DEFAULT, 'Show Regions 3 and 4', \
                                 'Show Regions 3 and 4', wx.ITEM_CHECK)
    options.AppendItem(self.miShowAll)
    self.Bind(wx.EVT_MENU, self.onShowAll, id=wx.ID_DEFAULT)
    
    help = wx.Menu()
    help.Append(wx.ID_HELP, 'About HTM Camera Toolkit', 'Help actions')
    self.Bind(wx.EVT_MENU, self.onHelp, id=wx.ID_HELP)
    
    menubar.Append(file, "&File")
    menubar.Append(options, "&Options")
    menubar.Append(help, "&Help")
    self.SetMenuBar(menubar)
    
    self.cameraWin = CameraWindow(self)
    size = self.cameraWin.GetBestSize().Get()
    self.SetSize((size[0]+20,size[1]+60))

  def onExit(self, evt=None):
    """ Top-level menu exit command was issued by user. """
    exit()
  
  def onShowAll(self, evt=None):
    """ Top-level menu Show Regions 3 and 4 was issued by user. """
    self.cameraWin.showRegions3And4(self.miShowAll.IsChecked())
    size = self.cameraWin.GetBestSize().Get()
    self.SetSize((size[0]+20,size[1]+60))
  
  def onHelp(self, evt=None):
    """ Top-level menu help about command was issued by user. """
    text = "HTM Camera Toolkit 1.0 by Barry Maturkanich (binarybarry@gmail.com).\n\n" + \
           "The HTM (Hierarchical Temporal Memory) Region learning algorithm "+ \
           "concept and design are the work of Numenta (www.numenta.com).  All "+ \
           "code used in this application is my personal implementation of the HTM "+ \
           "based heavily on documentation released by Numenta for free "+ \
           "(non-commercial) experimentation by interested developers.\n\n"+ \
           "The toolkit also uses code from several other open-source projects "+ \
           "including the Python Imaging Library, Numpy, wxPython, and OpenCV."
    msg = wx.MessageDialog(self, text, "About HTM Camera Toolkit", wx.OK | wx.ICON_INFORMATION)
    msg.ShowModal()

class CameraWindow(wx.Panel):
  """
  wxPython Panel for user to control and visualize a CLA Region Camera Input.
  This window includes a panel for video playback control, either from a live
  camera/webcam or from a previously recorded video file.  Video files can
  be created by recording video from the camera option.
  
  There are 2 video displays showing both the raw video from the camera (if
  applicable) as well as the processed binarized video input that is to be
  fed into the base Region.
  
  The video from the camera is processed using basic motion detection and
  some thresholding to produce a binary (black and white only) image since
  this is all the Region is currently able to easily understand for the moment.
  
  The panels on the right allow the user to specify all the parameters used
  to initialize a Region in order to maximize experimentation ability.
  Multiple Regions can be built to form a hierarchy where the output from
  a previous Region is used as the input to the next Region.
  
  Finally, Regions can be optionally visualized in detail to examine how
  learning is taking place and evaluate what is going on inside the Region
  as time steps progress.
  """
  
  def __init__(self, parent):
    super(CameraWindow, self).__init__(parent)
    
    self._isPlaying = False
    self._isPaused = False
    self._isLooping = False
    self._capture = None
    self._frameOut = None
    self._videoWriter = None
    self._videoDir = os.getcwd()+os.sep+"video"+os.sep
    self._lastFrameTime = clock()
    self._secPerFrame = 1.0 / 15.0
    self._regionShape = (80,60)
    
    self._prevImage = None
    self._normalImage = None
    self._width = 320
    self._height = 240
    
    self._imgSize = (self._width,self._height)
    self._inputImage = cv.CreateImage(self._imgSize, cv.IPL_DEPTH_8U, 1 )
    self._diffImage = cv.CreateImage(self._imgSize, cv.IPL_DEPTH_8U, 1)
    self._prevIplImage = cv.CreateImage(self._imgSize, cv.IPL_DEPTH_8U, 1)
    self._threshImage = cv.CreateImage(self._imgSize, cv.IPL_DEPTH_8U, 1)
    self._motionImage = Image.new('L', (self._width,self._height))
    
    self._historyImage = cv.CreateImage(self._imgSize, cv.IPL_DEPTH_32F, 1 )
    self._segMaskImage = cv.CreateImage(self._imgSize, cv.IPL_DEPTH_32F, 1 )
    self._memStorage = cv.CreateMemStorage()
    
    self._camImage = None
    self._fileImage = None
    self._frame80 = cv.CreateImage(self._regionShape, cv.IPL_DEPTH_8U, 1 )
    
    imgDir = "images"+os.sep
    playImg = Image.open(imgDir+"play_36_26.png")
    playDimImg = Image.open(imgDir+"play_dim_36_26.png")
    pauseImg = Image.open(imgDir+"pause_36_26.png")
    pauseDimImg = Image.open(imgDir+"pause_dim_36_26.png")
    forwardImg = Image.open(imgDir+"forward_36_26.png")
    forwardDimImg = Image.open(imgDir+"forward_dim_36_26.png")
    stopImg = Image.open(imgDir+"stop_36_26.png")
    stopDimImg = Image.open(imgDir+"stop_dim_36_26.png")
    loopImg = Image.open(imgDir+"loop_32_26.png")
    loopDimImg = Image.open(imgDir+"loop_dim_32_26.png")
    
    playIcon = wx.BitmapFromImage(convertToWxImage(playImg))
    playDimIcon = wx.BitmapFromImage(convertToWxImage(playDimImg))
    pauseIcon = wx.BitmapFromImage(convertToWxImage(pauseImg))
    pauseDimIcon = wx.BitmapFromImage(convertToWxImage(pauseDimImg))
    forwardIcon = wx.BitmapFromImage(convertToWxImage(forwardImg))
    forwardDimIcon = wx.BitmapFromImage(convertToWxImage(forwardDimImg))
    stopIcon = wx.BitmapFromImage(convertToWxImage(stopImg))
    stopDimIcon = wx.BitmapFromImage(convertToWxImage(stopDimImg))
    loopIcon = wx.BitmapFromImage(convertToWxImage(loopImg))
    loopDimIcon = wx.BitmapFromImage(convertToWxImage(loopDimImg))
    
    
    #set UI controls
    inputBox = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Video Input Control"), \
                                 orient=wx.VERTICAL)
    inputBox.SetMinSize((self._width+14, -1))
    
    camPanel = wx.Panel(self, -1)
    hSizerCam = wx.BoxSizer(wx.HORIZONTAL)
    
    videoDirUI = "."+os.sep+"video"+os.sep #"./video/"
    self.cameraButton = wx.RadioButton(camPanel, 1, "Camera")
    self.recordToggle = wx.CheckBox(camPanel, -1, "Record to "+videoDirUI)
    self.recordToggle.SetToolTipString("Record to directory "+self._videoDir)
    self.recordCombo = wx.ComboBox(camPanel, -1, style=wx.CB_DROPDOWN)
    
    self.cameraButton.Bind(wx.EVT_RADIOBUTTON, self.modeToggleRun)
    self.recordToggle.Bind(wx.EVT_CHECKBOX, self.recordToggleRun)
    
    hSizerCam.Add(self.cameraButton, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
    hSizerCam.Add(self.recordToggle, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
    hSizerCam.Add(self.recordCombo, 1, wx.EXPAND | wx.TOP, border=1)
    camPanel.SetSizer(hSizerCam)
    
    filePanel = wx.Panel(self, -1)
    hSizerFile = wx.BoxSizer(wx.HORIZONTAL)
    
    self.fileButton = wx.RadioButton(filePanel, 2, "Video file from "+videoDirUI)
    self.fileButton.SetToolTipString("Read from directory "+self._videoDir)
    self.fileCombo = wx.ComboBox(filePanel, -1, style=wx.CB_READONLY)
    
    self.fileButton.Bind(wx.EVT_RADIOBUTTON, self.modeToggleRun)
    
    hSizerFile.Add(self.fileButton, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
    hSizerFile.Add(self.fileCombo, 1, wx.EXPAND | wx.TOP, border=1)
    filePanel.SetSizer(hSizerFile)
    
    playPanel = wx.Panel(self, -1)
    hSizerPlay = wx.BoxSizer(wx.HORIZONTAL)
    
    self.playButton = wx.BitmapButton(playPanel, 0, playIcon)
    self.playButton.SetToolTipString("Play")
    self.playButton.SetBitmapDisabled(playDimIcon)
    self.playButton.Bind(wx.EVT_BUTTON, self.playRun)
    
    self.pauseButton = wx.BitmapButton(playPanel, 1, pauseIcon)
    self.pauseButton.SetToolTipString("Pause")
    self.pauseButton.SetBitmapDisabled(pauseDimIcon)
    self.pauseButton.Bind(wx.EVT_BUTTON, self.pauseRun)
    
    self.forwardButton = wx.BitmapButton(playPanel, 2, forwardIcon)
    self.forwardButton.SetToolTipString("Forward 1 Frame")
    self.forwardButton.SetBitmapDisabled(forwardDimIcon)
    self.forwardButton.Bind(wx.EVT_BUTTON, self.forwardRun)
    
    self.stopButton = wx.BitmapButton(playPanel, 3, stopIcon)
    self.stopButton.SetToolTipString("Stop")
    self.stopButton.SetBitmapDisabled(stopDimIcon)
    self.stopButton.Bind(wx.EVT_BUTTON, self.stopRun)
    
    self.loopButton = wx.BitmapButton(playPanel, 4, loopIcon)
    self.loopButton.SetToolTipString("Loop")
    self.loopButton.SetBitmapDisabled(loopDimIcon)
    self.loopButton.Bind(wx.EVT_BUTTON, self.loopRun)
    
    self.loopSpin = wx.SpinCtrl(playPanel, size=(60,-1), style=wx.SP_ARROW_KEYS)
    self.loopSpin.SetToolTipString("Playback for this many iterations if loop is enabled")
    self.loopSpin.SetRange(0, 1000)
    self.loopSpin.SetValue(10)
    
    hSizerPlay.Add(self.playButton, 0, wx.ALIGN_CENTER | wx.RIGHT, border=5)
    hSizerPlay.Add(self.pauseButton, 0, wx.ALIGN_CENTER | wx.RIGHT, border=5)
    hSizerPlay.Add(self.forwardButton, 0, wx.ALIGN_CENTER | wx.RIGHT, border=5)
    hSizerPlay.Add(self.stopButton, 0, wx.ALIGN_CENTER | wx.LEFT, border=10)
    hSizerPlay.Add(self.loopButton, 0, wx.ALIGN_CENTER | wx.LEFT, border=10)
    hSizerPlay.Add(self.loopSpin, 0, wx.ALIGN_CENTER | wx.LEFT, border=5)
    playPanel.SetSizer(hSizerPlay)
    
    inputBox.Add(camPanel, 1, wx.EXPAND | wx.BOTTOM, border=5)
    inputBox.Add(filePanel, 1, wx.EXPAND | wx.BOTTOM, border=5)
    inputBox.Add(playPanel, 0, wx.ALIGN_CENTER_HORIZONTAL)
    
    #Parameters common to all Regions
    paramBox = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Synapse Permanence Parameters (0-100)"), \
                                 orient=wx.VERTICAL)
    
    permConText = wx.StaticText(self, label="Connected Perm")
    permInitText = wx.StaticText(self, label="Initial Perm")
    permIncText = wx.StaticText(self, label="Perm Increase")
    permDecText = wx.StaticText(self, label="Perm Decrease")
    
    permConText.SetToolTipString("Synapses with permanences equal or above this value are connected.")
    permInitText.SetToolTipString("Initial permanence for 'new' distal synapses.")
    permIncText.SetToolTipString("Amount permanences of synapses are incremented while learning.")
    permDecText.SetToolTipString("Amount permanences of synapses are decremented while learning.")
    
    self.permConSpin = wx.SpinCtrl(self, 0, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.permConSpin.SetValue(20)
    self.permInitSpin = wx.SpinCtrl(self, 1, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.permInitSpin.SetValue(22)
    self.permIncSpin = wx.SpinCtrl(self, 2, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.permIncSpin.SetValue(5)
    self.permDecSpin = wx.SpinCtrl(self, 3, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.permDecSpin.SetValue(2)
    
    self.permConSpin.Bind(wx.EVT_SPINCTRL, self.onPermConnectedSpin)
    self.permInitSpin.Bind(wx.EVT_SPINCTRL, self.onPermInitSpin)
    self.permIncSpin.Bind(wx.EVT_SPINCTRL, self.onPermIncSpin)
    self.permDecSpin.Bind(wx.EVT_SPINCTRL, self.onPermDecSpin)
    
    fgsParam = wx.FlexGridSizer(2, 4, 5, 5)
    fgsParam.AddMany([(permConText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.permConSpin, 0, wx.ALIGN_CENTER_VERTICAL),
                     (permIncText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.permIncSpin, 0, wx.ALIGN_CENTER_VERTICAL),
                     (permInitText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.permInitSpin, 0, wx.ALIGN_CENTER_VERTICAL),
                     (permDecText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.permDecSpin, 0, wx.ALIGN_CENTER_VERTICAL)])
    paramBox.Add(fgsParam, 0, flag=wx.ALL|wx.EXPAND, border=5)
    
    #Add the 2 image canvases for the camera and region input
    canvasBox0 = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Camera View"), \
                                   orient=wx.VERTICAL)
    self.canvas0 = ImageCanvas(self, -1, self._width, self._height)
    canvasBox0.Add(self.canvas0, 0, wx.BOTTOM | wx.LEFT| wx.RIGHT, border=2)
    
    canvasBox1 = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Input to Region 1"), \
                                   orient=wx.VERTICAL)
    self.canvas1 = ImageCanvas(self, -1, self._width, self._height)
    canvasBox1.Add(self.canvas1, 0, wx.BOTTOM | wx.LEFT| wx.RIGHT, border=2)
    
    #Add the Region Parameter Panels
    region1Panel = RegionParamsPanel(self, 1, self._regionShape)
    region2Panel = RegionParamsPanel(self, 2, (40,30))
    self._region3Panel = RegionParamsPanel(self, 3, (20,15))
    self._region4Panel = RegionParamsPanel(self, 4, (10,7))
    
    region1Panel.setNextRegionParams(region2Panel)
    region2Panel.setNextRegionParams(self._region3Panel)
    self._region3Panel.setNextRegionParams(self._region4Panel)
    
    self.regionPanels = []
    self.regionPanels.append(region1Panel)
    self.regionPanels.append(region2Panel)
    self.regionPanels.append(self._region3Panel)
    self.regionPanels.append(self._region4Panel)
    
    self._fgsMain = wx.FlexGridSizer(2, 3, 5, 5)
    self._fgsMain.AddMany([(canvasBox1, 0, wx.EXPAND),
                    (region1Panel, 0, wx.EXPAND),
                    (self._region3Panel, 0, wx.EXPAND),
                    (canvasBox0, 0, wx.EXPAND),
                    (region2Panel, 0, wx.EXPAND),
                    (self._region4Panel, 0, wx.EXPAND)])
    
    self._fgsMain.Show(self._region3Panel, False)
    self._fgsMain.Show(self._region4Panel, False)
    
    hSizerTop = wx.BoxSizer(wx.HORIZONTAL)
    hSizerTop.Add(inputBox, 0, wx.ALIGN_TOP | wx.RIGHT, border=5)
    hSizerTop.Add(paramBox, 0, wx.EXPAND)

    vSizerMain = wx.BoxSizer(wx.VERTICAL)
    vSizerMain.Add(hSizerTop, 0, wx.ALIGN_TOP | wx.BOTTOM | wx.LEFT, border=5)
    vSizerMain.Add(self._fgsMain, 0, wx.EXPAND | wx.LEFT, border=5)
    
    self.SetSizer(vSizerMain)
    self.SetAutoLayout(1)
  
  def showRegions3And4(self, show=True):
    """ Choose whether or not to show Region 3 and 4 in the UI. """
    self._fgsMain.Show(self._region3Panel, show)
    self._fgsMain.Show(self._region4Panel, show)
  
  def onPermConnectedSpin(self, evt=None):
    """ User changed the value of Connected Permanence spinbox. """
    Synapse.CONNECTED_PERM = self.permConSpin.GetValue() / 100.0
  
  def onPermInitSpin(self, evt=None):
    """ User changed the value of Initial Permanence spinbox. """
    Synapse.INITIAL_PERMANENCE = self.permInitSpin.GetValue() / 100.0
  
  def onPermIncSpin(self, evt=None):
    """ User changed the value of Increase Permanence spinbox. """
    Synapse.PERMANENCE_INC = self.permIncSpin.GetValue() / 100.0
  
  def onPermDecSpin(self, evt=None):
    """ User changed the value of Decrease Permanence spinbox. """
    Synapse.PERMANENCE_DEC = self.permDecSpin.GetValue() / 100.0
  
  def runRegionsOnce(self):
    """ 
    If Regions are enabled to run, then run the Regions for one time step
    using the last processed video frame.  The Region parameters are set
    in their respective UI panels.
    """
    if self._frameOut:
      imgMat = numpy.array(numpy.asarray(self._frameOut, dtype=numpy.uint8))
      imgMat = imgMat.reshape((self._regionShape[1],self._regionShape[0]))
      imgMat = numpy.swapaxes(imgMat, 0, 1)
      imgMat /= 255 #255 for white needs to be 1s instead
      
      rInput = imgMat
      for i in xrange(len(self.regionPanels)):
        if rInput==None: #stop here if no input for next Region
          break
        rInput = self.regionPanels[i].runRegionOnce(rInput)
  
  def modeToggleRun(self, evt=None):
    """ User clicked to toggle between Camera and Video File modes. """
    isCamera = not evt or evt.Id==1 #camera input was selected
    if not isCamera: 
      self.recordToggle.SetValue(False)
    
    self.fileButton.SetValue(not isCamera)
    self.cameraButton.SetValue(isCamera)
    
    self.refreshPlaybackEnablement()
    
    #Create video directory if not present
    if not os.path.isdir(self._videoDir):
      os.mkdir(self._videoDir)
    
    self.recordCombo.SetItems(os.listdir(self._videoDir))
    self.fileCombo.SetItems(os.listdir(self._videoDir))
    if self.fileCombo.GetValue()=="":
      self.fileCombo.SetSelection(0)
    
    self.recordToggle.Enable(isCamera)
    self.recordCombo.Enable(isCamera)
    self.fileCombo.Enable(not isCamera)
  
  def refreshPlaybackEnablement(self):
    """ 
    Refresh the enablement states of the playback buttons based on the current
    state of the video playback. 
    """
    self.playButton.Enable(not self._isPlaying)
    self.pauseButton.Enable(self._isPlaying or self._isPaused)
    self.forwardButton.Enable(not self._isPlaying)
    self.stopButton.Enable(self._isPlaying or self._isPaused)
    self.loopButton.Enable(self.fileButton.GetValue())
    
    self.loopSpin.Enable(self.fileButton.GetValue() and not self._isLooping)
    
    self.cameraButton.Enable(not self._isPlaying and not self._isPaused)
    self.fileButton.Enable(not self._isPlaying and not self._isPaused)
    self.fileCombo.Enable(not self._isPlaying and not self._isPaused)
  
  def createCapture(self):
    """ 
    Create a new OpenCV video capture from either a camera or a video file
    based on the current UI button selection. If a valid capture object cannot
    be created successfully an error dialog will be displayed and the capture
    object will remain as None. 
    """
    if self.fileButton.GetValue():
      fileName = self._videoDir+self.fileCombo.GetValue()
      self._capture = cv.CaptureFromFile(fileName)
    else:
      self._capture = cv.CaptureFromCAM(-1)
    
    #reset running average accuracy values per Region on new capture
    for i in xrange(len(self.regionPanels)):
      self.regionPanels[i].resetRunningAverages()
    
    #test if we can get frames from the input; error dialog if not
    try:
      frame = cv.QueryFrame(self._capture)
      frame.width #if frame is invalid, asking for width will fail
    except:
      self._capture = None
      if self.fileButton.GetValue():
        fileName = self._videoDir+self.fileCombo.GetValue()
        error = "Unable to read the video file \""+fileName+"\". The format "+ \
                "may not be supported.  It is recommended that only files that "+ \
                "were recorded by this application be used for playback."
      else:
        error = "No suitable camera/webcam was detected by the system.  "+ \
                "If you have more than 1 camera installed, try disabling all "+ \
                "but the one you wish to use."
      msg = wx.MessageDialog(self, error, "Video Input Error", wx.OK | wx.ICON_ERROR)
      msg.ShowModal()
  
  def playRun(self, evt=None):
    """ Perform the 'Play' action, either from user button click or internal force. """
    if not self._capture:
      self.createCapture()
    if self._capture and not self._isPlaying:
      self._isPlaying = True
      self._isPaused = False
      self.Bind(wx.EVT_IDLE, self.capture)
    self.refreshPlaybackEnablement()
  
  def pauseRun(self, evt=None):
    """ Perform the 'Pause' action, either from user button click or internal force. """
    if self._capture:
      if self._isPlaying:
        self.Unbind(wx.EVT_IDLE)
        self._isPlaying = False
        self._isPaused = True
      else:
        self.playRun()
    self.refreshPlaybackEnablement()
  
  def forwardRun(self, evt=None):
    """ Perform the 'Forward' action, either from user button click or internal force. """
    if not self._capture:
      self.createCapture()
    if self._capture:
      self._isPaused = True
      self.capture()
      self.refreshPlaybackEnablement()
  
  def stopRun(self, evt=None):
    """ Perform the 'Stop' action, either from user button click or internal force. """
    if self._isPlaying or self._isPaused:
      self.Unbind(wx.EVT_IDLE)
      self._isPlaying = False
      self._isPaused = False
      if self._capture!=None:
        del self._capture
      self._capture = None
      if self.recordToggle.GetValue():
        self.recordToggle.SetValue(False)
        self.recordToggleRun()
      self.canvas0.setBitmap(wx.NullBitmap)
      self.canvas1.setBitmap(wx.NullBitmap)
    self.refreshPlaybackEnablement()
  
  def loopRun(self, evt=None):
    """ Perform the 'Loop' action, either from user button click or internal force. """
    if self._isLooping:
      self._isLooping = False
    else:
      self._isLooping = True
    self.refreshPlaybackEnablement()
  
  def recordToggleRun(self, evt=None):
    """ Camera Recording on/off was toggled by user. """
    if not self.recordToggle.GetValue():
      if self._videoWriter!=None:
        del self._videoWriter
      self._videoWriter = None
      self.recordCombo.Enable(True)
    else:
      #if name is empty, generate a unique file name for the directory
      name = self.recordCombo.GetValue()
      if name=="":
        tag = 1
        name = "video"+str(tag)+".avi"
        while name in os.listdir(self._videoDir):
          tag += 1
          name = "video"+str(tag)+".avi"
        self.recordCombo.SetValue(name)
      if '.' not in name: #append .avi if no dot extension
        name += ".avi"
        self.recordCombo.SetValue(name)
      
      fileName = self._videoDir+name
      
      #Create a videoWriter to save processed camera inputs
      #CreateVideoWriter(filename, fourcc, fps, frame_size, is_color)
      self._videoWriter = cv.CreateVideoWriter(fileName, cv.CV_FOURCC('I','Y','U','V'), \
                                               15, self._regionShape, 0)
      self.recordCombo.Disable()
  
  def capture(self, event=None):
    """
    Capture a frame from either the active camera or the active video file.
    This will be called by either the IDLE event (if Playing) or individually
    by the Forward Button.
    """
    if not self._capture: #no valid capture device to use
      return
    
    frameOut = None
    if self.fileButton.GetValue():
      frameOut = self.captureFromFile()
    else:
      frameOut = self.captureFromCamera()
    
    #if we have a valid processed image frame, pass it to the Region
    if frameOut:
      #draw the region input image to the screen canvas
      imageOut = convertToWxImage(frameOut.resize((self._width,self._height)))
      self.canvas1.setBitmap(wx.BitmapFromImage(imageOut))
      
      #update last processed frame, and process Regions if enabled
      self._frameOut = frameOut
      self.runRegionsOnce()
    
    if self._isPlaying and event:
      event.RequestMore()
  
  def captureFromFile(self):
    """ 
    Capture a frame from the active video file and return it so it can
    then be passed into the Region for analysis.
    """
    #when playing files, cap playback at necessary FPS
    tsec = clock()
    if tsec-self._lastFrameTime < self._secPerFrame:
      return
    self._lastFrameTime = tsec
    
    frame = cv.QueryFrame(self._capture)
    if not frame: #if no more frames, restart if looping else stop stream
      if self._isLooping:
        loopCount = self.loopSpin.GetValue()
        if loopCount <= 0:
          self._isLooping = False
          self.stopRun()
        else:
          loopCount -= 1
          self.loopSpin.SetValue(loopCount)
          del self._capture
          self.createCapture()
          frame = cv.QueryFrame(self._capture)
      else:
        self.stopRun()
      return
    
    #if video file's frame size is not 80x60, then assume video is unprocessed
    #and instead pretend it came from the live camera by doing motion detection
    if frame.width!=self._frame80.width or frame.height!=self._frame80.height:
      return self.captureFromCamera()
    
    #convert file to gray-scale and build a PIL image from it
    cv.CvtColor(frame, self._frame80, cv.CV_RGB2GRAY)
    
    frameOut = Image.fromstring('L', (self._frame80.width, self._frame80.height), \
                                self._frame80.tostring(), 'raw', 'L', 0, 1)
    return frameOut
  
  def captureFromCamera(self):
    """ 
    Capture a live frame from the camera and perform motion processing
    on the acquired image.  If recording is enabled, also write the processed
    frame to an output video file. 
    """
    frameOut = None
    frame = cv.QueryFrame(self._capture) # Grab the frame from the capture
    
    #if camera's frame size is incorrect, resize to what we need
    if frame.width!=self._imgSize[0] or frame.height!=self._imgSize[1]:
      if self._camImage==None:
        self._camImage = cv.CreateImage( self._imgSize, cv.IPL_DEPTH_8U, 3)
      cv.Resize(frame, self._camImage)
    else: #size is already correct, use frame as-is
      self._camImage = frame
    
    #convert camera image to gray-scale to perform motion analysis
    cv.CvtColor(self._camImage, self._inputImage, cv.CV_RGB2GRAY)
    
    # perform motion detection and get the processed image frame
    # the new frame will either be None (no motion) or the motion box subset image
    rect = self.processMotion()
    
    if rect:
      image0 = Image.fromstring('RGB', (frame.width, frame.height), 
                                frame.tostring(), 'raw', 'BGR', 0, 1)
      image0 = image0.resize((self._width, self._height))
      mask0 = Image.fromstring('L', (self._threshImage.width, 
                                     self._threshImage.height), 
                               self._threshImage.tostring(), 'raw', 'L', 0, 1)
      xy = (rect[0], rect[1], rect[0]+rect[2], rect[1]+rect[3])
      draw = ImageDraw.Draw(image0)
      draw.rectangle(xy, outline="white")
      del draw
      
      #crop out motion box and mask out non-motion, then centerize in new image
      #fHalf = (rect[2]/2, rect[3]/2)
      #movePos = ((self._width/2)-fHalf[0], (self._height/2)-fHalf[1])
      movePos = xy
      
      draw = ImageDraw.Draw(self._motionImage)
      draw.rectangle((0,0,self._width,self._height), fill="black")
      del draw
      #imgBox = image0.crop(xy)
      imgMask = mask0.crop(xy)
      #self._motionImage.paste(imgBox, movePos, imgMask)
      self._motionImage.paste(imgMask, movePos)
      image = self._motionImage
      
      # Mirror, which is more intuitive for built-in cameras
      image = ImageOps.mirror(image)
      image0 = ImageOps.mirror(image0)
      
      imageOut = convertToWxImage(image0)
      self.canvas0.setBitmap(wx.BitmapFromImage(imageOut))
      
      frameOut = image.resize(self._regionShape)
      if self._videoWriter:
        cvImage = cv.CreateImageHeader(frameOut.size, cv.IPL_DEPTH_8U, 1)
        cv.SetData(cvImage, frameOut.tostring())
        cv.WriteFrame(self._videoWriter, cvImage)
    
    return frameOut
  
  def processMotion(self):
    """
    Take a raw input image frame from the camera and perform motion detection using
    the current frame plus considering several previous frames and return the CV
    image that should be given to the Region network.
    """
    #find motion image, then find feature corners from that
    if self._prevIplImage:
      cv.AbsDiff(self._inputImage, self._prevIplImage, self._diffImage)
    else:
      cv.Copy(self._inputImage, self._diffImage)
      
    cv.Copy(self._inputImage, self._prevIplImage) #save as t-1 image for next frame
    
#    cv.GoodFeaturesToTrack(self._diffImage, self._eigImage, self._tmpImage, cornersAPtr, \
#                    countPtr, c_double(0.05), c_double(5.0), None, 3, 0, c_double(0.04))
    
    #(src, dest, threshold, maxVal, type)
    cv.Threshold(self._diffImage, self._threshImage, 16.0, 255.0, cv.CV_THRESH_BINARY)
    
    #For now, disable segmentMotion and return all motion in frame...
    if self._threshImage!=None:
      return (0,0, self._threshImage.width, self._threshImage.height)
    
    ###Experimental: segment motion to return only the most 'interesting' area
    tsec = clock()
    #(silhouette, mhi, timestamp, duration)
    cv.UpdateMotionHistory(self._threshImage, self._historyImage, tsec, 0.3)

    #(mhi, segMask, storage, timestamp, segThresh)
    #return: [tuple(area, value, rect)], (float, CvScalar, CvRect)
    seqs = cv.SegmentMotion(self._historyImage, self._segMaskImage, \
                            self._memStorage, tsec, 1.0)
    
    #cv.Copy(self._threshImage, self._inputImage)
    #cv.Threshold(self._segMaskImage, self._threshImage, 0.0, 250.0, CV_THRESH_BINARY)
    
    rects = []
    for seq in seqs:
      seqRect = seq[2] #CvRect = tuple (x, y, width, height)
      if(seqRect[2] > 4 and seqRect[3] > 4):
        rects.append(seqRect)
    
    #find the 3rd largest area and only keep those rects
    if len(rects) > 0:
      areas = [x[2]*x[3] for x in rects]
      areas.sort()
      minArea = areas[0]
      if len(areas) > 1:
        minArea = areas[len(areas)-1]
      
      rectsOk = [x for x in rects if x[2]*x[3] >= minArea]
      rect = rectsOk[0]
#      rectsOk = self.removeOverlapRects(rectsOk) #remove overlapping rectangles
#      for rect in rectsOk:
#        pt1 = CvPoint()
#        pt1.x = rect[0]
#        pt1.y = rect[1]
#        pt2 = CvPoint()
#        pt2.x = pt1.x + rect[2]
#        pt2.y = pt1.y + rect[3]
#        #(img, pt1, pt2, color, thickness, lineType, shift)
#        cv.Rectangle(self._inputImage, pt1, pt2, CV_RGB(255,255,255), 1)
      
      #center the largest rect
      cRect = (rect[0]+(rect[2]/2), rect[1]+(rect[3]/2))
      return rect
    
#    for pt in cornersA:
#      center = CvPoint()
#      center.x = cvRound(pt.x)
#      center.y = cvRound(pt.y)
#      cv.Circle(self._diffImage, center, 4, CV_RGB(255,255,255), -1)
    return None #none means no motion bounding box detected


  def removeOverlapRects(self, rects):
    """List of 4-item tuples, (x,y,width,height), return same list but having removed
       any rects which are completely contained in any other. """
    if len(rects) is 0:
      return rects
    
    toRemove = []
    for i in xrange(len(rects)):
      for j in xrange(len(rects)):
        if i is not j:
          #is rect(i) contained inside rect(j)
          if self.isRectContained(rects[i], rects[j]):
            toRemove.append(i)
            break
    toRemove.reverse()
    for i in toRemove:
      rects.pop(i)
    return rects

  def isRectContained(self, r1, r2):
    """Is rectangle r1 completely contained inside rectangle r2.  r1 and r2 should be
       tuples with 4 integers for x,y of upper-left corner and the width,height """
    x1 = r1[0]
    y1 = r1[1]
    width1 = r1[2]
    height1 = r1[3]
    x2 = r2[0]
    y2 = r2[1]
    width2 = r2[2]
    height2 = r2[3]
    if x1 >= x2 and y1 >= y2 and x1+width1 <= x2+width2 and y1+height1 <= y2+height2:
      return True
    return False
    

class RegionParamsPanel(wx.Panel):
  """
  wx Panel that displays and allows editing of key parameters used to create an HTM Region.
  """
  
  def __init__(self, parent, id, inputSize):
    """
    Create a new RegionParamsPanel with the standard wx parent and id plus the initial
    size of the input that is to be fed into the HTM Region.
    @param id: the wx panel id, but also used as the numerical id for the Region.
    @param inputSize: tuple (x,y) specifying the size of the input data for the Region.
    """
    super(RegionParamsPanel, self).__init__(parent, id)
    
    self.predictedCols = None
    self.activeCols = None
    self.regionFrame = None
    self.inputSize = inputSize
    self.regionID = id
    self.region = None
    self._nextRegionParams = None
    self._sumAccPred = 0.0
    self._sumAccActive = 0.0
    self._meanCount = 0
    
    pad = 0 #default some region 1 params slightly different from rest
    if id>1:
      pad = 5
    
    #set UI controls
    self.staticBox = wx.StaticBox(self, -1, "Region")
    inputBox = wx.StaticBoxSizer(self.staticBox, orient=wx.VERTICAL)
    
    self.onButton = wx.CheckBox(self, 0, "Region On")
    self.onButton.SetToolTipString("Enable this Region for input processing (Region is created fresh if parameters have changed since last on).")
    self.onButton.Bind(wx.EVT_CHECKBOX, self.regionOnRun)
    
    hSizerLearn = wx.BoxSizer(wx.HORIZONTAL)
    
    self.spatialButton = wx.CheckBox(self, 0, "Spatial Learning")
    self.temporalButton = wx.CheckBox(self, 0, "Temporal Learning")
    
    hSizerLearn.Add(self.spatialButton, 1, \
                    wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM | wx.RIGHT, 5), 
    hSizerLearn.Add(self.temporalButton, 1, \
                    wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM | wx.LEFT, 5)
    
    self.viewButton = wx.Button(self, 0, "Visualize")
    self.viewButton.Bind(wx.EVT_BUTTON, self.regionViewRun)
    self.viewButton.Disable() #disable until the Region is created
    
    hbox = wx.BoxSizer(wx.HORIZONTAL)
    
    panel = wx.Panel(self)
    fgs = wx.FlexGridSizer(7, 4, 5, 5) #rows, cols, vgap, hgap
    
    inputPerColText = wx.StaticText(panel, label="Input per Column (%)")
    minOverlapText = wx.StaticText(panel, label="Min Overlap (%)")
    localityRadText = wx.StaticText(panel, label="Locality Radius")
    desireLocalText = wx.StaticText(panel, label="Local Activity (%)")
    cellsPerColText = wx.StaticText(panel, label="Cells per Column")
    thresholdText = wx.StaticText(panel, label="Segment Threshold")
    newSynText = wx.StaticText(panel, label="New Synapse Count")
    colXText = wx.StaticText(panel, label="# Columns (X Dir)")
    colYText = wx.StaticText(panel, label="# Columns (Y Dir)")
    inhiRadText = wx.StaticText(panel, label="Inhibition Radius")
    predAccText = wx.StaticText(panel, label="Prediction Accuracy")
    activeAccText = wx.StaticText(panel, label="Activation Accuracy")
    predMeanAccText = wx.StaticText(panel, label="Prediction Mean Acc")
    activeMeanAccText = wx.StaticText(panel, label="Activation Mean Acc")
#    statusText = wx.StaticText(panel, label="Region Status")
#    blankText = wx.StaticText(panel, label="")
    
    inputPerColText.SetToolTipString("Percent of input bits within locality radius each Column has potential (proximal) synapses for.")
    minOverlapText.SetToolTipString("Minimum percent of column's proximal synapses that must be active for the column to be considered by the spatial pooler.")
    localityRadText.SetToolTipString("Furthest number of Columns away to allow distal synapse connections (0 means no restriction).")
    desireLocalText.SetToolTipString("Approximate percent of Columns within locality radius to be winners after inhibition.")
    cellsPerColText.SetToolTipString("Number of (temporal context) cells to use for each Column.")
    thresholdText.SetToolTipString("Minimum number of active synapses to activate a segment.")
    newSynText.SetToolTipString("Number of 'new' synapses to add to a segment if none activated during learning.")
    colXText.SetToolTipString("Number of Columns in the X direction (width) in this Region.")
    colYText.SetToolTipString("Number of Columns in the Y direction (height) in this Region.")
    inhiRadText.SetToolTipString("Radius, in Columns, of how far inhibition will take effect per Column (most recent time step).")
    predAccText.SetToolTipString("Correctly predicted active columns out of total sequence-segment predicted columns (most recent time step).")
    activeAccText.SetToolTipString("Correctly predicated active columns out of total active columns (most recent time step).")
    predMeanAccText.SetToolTipString("Correctly predicted active columns out of total sequence-segment predicted columns (running average).")
    activeMeanAccText.SetToolTipString("Correctly predicated active columns out of total active columns (running average).")
#    statusText.SetToolTipString("Current state of the Region.")
    
    self.inputPerColSpin = wx.SpinCtrl(panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.inputPerColSpin.SetValue(15+pad)
    self.minOverlapSpin = wx.SpinCtrl(panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.minOverlapSpin.SetValue(10)
    self.localityRadSpin = wx.SpinCtrl(panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.localityRadSpin.SetValue(5)
    self.desireLocalSpin = wx.SpinCtrl(panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.desireLocalSpin.SetValue(10)
    self.cellsPerColSpin = wx.SpinCtrl(panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.cellsPerColSpin.SetRange(1,4)
    self.cellsPerColSpin.SetValue(1)
    self.thresholdSpin = wx.SpinCtrl(panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.thresholdSpin.SetRange(1, 100)
    self.thresholdSpin.SetValue(3)
    self.newSynSpin = wx.SpinCtrl(panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.newSynSpin.SetRange(1, 100)
    self.newSynSpin.SetValue(5)
    self.colXSpin = wx.SpinCtrl(panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.colXSpin.SetRange(4, inputSize[0])
    self.colXSpin.SetValue(inputSize[0]/2)
    self.colYSpin = wx.SpinCtrl(panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.colYSpin.SetRange(4, inputSize[1])
    self.colYSpin.SetValue(inputSize[1]/2)
    
    self.inhiRadValText = wx.StaticText(panel, label="?")
    self.predAccValText = wx.StaticText(panel, label="0%")
    self.activeAccValText = wx.StaticText(panel, label="0%")
    self.predMeanAccValText = wx.StaticText(panel, label="0%")
    self.activeMeanAccValText = wx.StaticText(panel, label="0%")
    #self.statusValText = wx.StaticText(panel, label="Not Built")
    #blankValText = wx.StaticText(panel, label="")

    fgs.AddMany([(inputPerColText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.inputPerColSpin, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (minOverlapText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.minOverlapSpin, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (localityRadText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.localityRadSpin, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (desireLocalText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.desireLocalSpin, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (thresholdText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.thresholdSpin, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (newSynText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.newSynSpin, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (colXText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.colXSpin, 0, wx.ALIGN_CENTER_VERTICAL),
                 (cellsPerColText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.cellsPerColSpin, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (colYText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.colYSpin, 0, wx.ALIGN_CENTER_VERTICAL),
                 (inhiRadText, 0, wx.ALIGN_CENTER_VERTICAL),
                 (self.inhiRadValText, 0, wx.ALIGN_CENTER_VERTICAL),
                 (predAccText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.predAccValText, 0, wx.ALIGN_CENTER_VERTICAL),
                 (predMeanAccText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.predMeanAccValText, 0, wx.ALIGN_CENTER_VERTICAL),
                 (activeAccText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.activeAccValText, 0, wx.ALIGN_CENTER_VERTICAL),
                 (activeMeanAccText, 0, wx.ALIGN_CENTER_VERTICAL), 
                 (self.activeMeanAccValText, 0, wx.ALIGN_CENTER_VERTICAL)])

    hbox.Add(fgs, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
    panel.SetSizer(hbox)
    
    inputBox.Add(self.onButton, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, border=5)
    inputBox.Add(hSizerLearn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, border=5)
    inputBox.Add(panel, 0)#, wx.ALL, border=5)
    inputBox.Add(self.viewButton, 0, wx.ALIGN_CENTER_HORIZONTAL)
    
    vSizer = wx.BoxSizer(wx.VERTICAL)
    vSizer.Add(inputBox, 0, wx.ALIGN_LEFT | wx.ALL, border=0)
    
    self.__refreshInputSize()
    
    self.SetSizer(vSizer)
    self.SetAutoLayout(1)
  
  def __refreshInputSize(self):
    """ 
    This method should be called when the region input size has changed.
    If it does we need to generate a new label for the main UI grouping box 
    for this panel (which displays input size), as well as reset the boundaries
    for the column dimension spinners (which are bound by input size).
    """
    sizeStr = str(self.inputSize[0])+"x"+str(self.inputSize[1])
    rid = self.regionID
    src = "Region "+str(rid-1)
    if rid==1:
      src = "Video Source"
    self.staticBox.SetLabel("Region "+str(rid)+"  (Input="+sizeStr+" from "+src+")")
    self.colXSpin.SetRange(4, self.inputSize[0])
    self.colYSpin.SetRange(4, self.inputSize[1])
  
  def resetRunningAverages(self):
    """ Reset the running average accuracy values for this Region panel. """
    self._sumAccPred = 0.0
    self._sumAccActive = 0.0
    self._meanCount = 0
    
    if self.region!=None:
      nx = len(self.region.columnGrid)
      ny = len(self.region.columnGrid[0])
      self.predictedCols = numpy.zeros((nx,ny), dtype=numpy.uint8)
      self.activeCols = numpy.zeros((nx,ny), dtype=numpy.uint8)
  
  def setNextRegionParams(self, nextRegionParams):
    """ 
    Assign a reference to the next (higher) hierarchical Region's Parameter
    panel.  This is needed to allow communicating Region states between levels.
    If there is no higher Region, the nextRegionParams may be None. 
    """
    self._nextRegionParams = nextRegionParams
    if not self.onButton.GetValue():
      self._nextRegionParams.onButton.Disable()
  
  def enableNextRegion(self, enable=True):
    """ 
    Tell the next hierarchical region panel to enable or disable its "Region On"
    button. This method is recursive so telling the next region will then tell its
    next region such that changes take effect for all higher-up Regions.
    If any higher Regions were turned on, if enable is False they will first turn
    their Regions off before disabling the on button.
    """
    if self._nextRegionParams:
      if not enable:
        self._nextRegionParams.onButton.SetValue(False)
        self._nextRegionParams.onButton.Disable()
        self._nextRegionParams.regionOnRun()
      else:
        regionOn = self.onButton.GetValue()
        self._nextRegionParams.inputSize = (self.colXSpin.GetValue(), self.colYSpin.GetValue())
        self._nextRegionParams.__refreshInputSize()
        self._nextRegionParams.onButton.Enable(regionOn)
        self._nextRegionParams.enableNextRegion(enable)
  
  def regionOnRun(self, evt=None):
    """ 
    User clicked button to enable/disable Region. If turned on, the Region will
    be created new if this is the first time or if the Region parameters have
    changed since last create.  Otherwise the Region is just re-enabled to run
    without creating fresh.  The UI for parameters is only enabled if the Region
    is off as most parameters cannot change once the Region has been created.
    """
    isOn = self.onButton.GetValue()
    
    #if region previously created, rebuild if params changed
    self.__checkCreateRegion()
    #if not isOn:
    #  self.statusValText.SetLabel("Inactive")
    
    #enable next hierarchical Region's onButton only if this one is on
    self.enableNextRegion(isOn)
    
    self.inputPerColSpin.Enable(not isOn)
    self.minOverlapSpin.Enable(not isOn)
    self.localityRadSpin.Enable(not isOn)
    self.desireLocalSpin.Enable(not isOn)
    self.cellsPerColSpin.Enable(not isOn)
    self.thresholdSpin.Enable(not isOn)
    self.newSynSpin.Enable(not isOn)
    self.colXSpin.Enable(not isOn)
    self.colYSpin.Enable(not isOn)
    self.viewButton.Enable(self.region!=None)
    
  def regionViewRun(self, evt=None):
    """ User clicked button to launch Region Visualization view. """
    if not self.regionFrame:
      self.regionFrame = RegionFrame(self.region)
      self.regionFrame.SetTitle("Visualizer for Region "+str(self.regionID))
      self.regionFrame.Show()
  
  def __checkCreateRegion(self):
    """ 
    Create the Region using the currently set UI parameters. The region
    is only created new if this is first run or if the UI parameters have
    changed since Region was last created. 
    """
    colGridSize = (self.colXSpin.GetValue(), self.colYSpin.GetValue())
    pctInputPerCol = self.inputPerColSpin.GetValue() / 100.0
    pctMinOverlap = self.minOverlapSpin.GetValue() / 100.0
    localityRadius = self.localityRadSpin.GetValue()
    pctLocalActivity = self.desireLocalSpin.GetValue() / 100.0
    cellsPerCol = self.cellsPerColSpin.GetValue()
    segActiveThreshold = self.thresholdSpin.GetValue()
    newSynapseCount = self.newSynSpin.GetValue()
    
    rebuild = False
    if not self.region:
      rebuild = self.onButton.GetValue()
    elif self.region.pctInputPerCol!=pctInputPerCol or \
         self.region.pctMinOverlap!=pctMinOverlap or \
         self.region.localityRadius!=localityRadius or \
         self.region.pctLocalActivity!=pctLocalActivity or \
         self.region.cellsPerCol!=cellsPerCol or \
         self.region.segActiveThreshold!=segActiveThreshold or \
         self.region.newSynapseCount!=newSynapseCount or \
         len(self.region.columnGrid)!=colGridSize[0] or \
         len(self.region.columnGrid[0])!=colGridSize[1] or \
         self.region.inputWidth!=self.inputSize[0] or \
         self.region.inputHeight!=self.inputSize[1]:
      rebuild = True
    
    if rebuild:
      #self.statusValText.SetLabel("Initializing...")
      self.region = Region(self.inputSize, colGridSize, pctInputPerCol, \
                           pctMinOverlap, localityRadius, pctLocalActivity, \
                           cellsPerCol, segActiveThreshold, newSynapseCount)
      #self.statusValText.SetLabel("Active")
      self.resetRunningAverages()
      
      #Recreate the region visualizer if previously open
      if self.regionFrame:
        self.regionFrame.Close()
        self.regionFrame = RegionFrame(self.region)
        self.regionFrame.Show()
    
  
  def runRegionOnce(self, inputData):
    """ 
    If this Region is enabled to run, then run the Region for one time step
    using the last processed video frame (or last processed output from the
    previous Region in the hierarchy).  Set the Region to learn based on
    checkbox enablement in the UI.
    @param inputData: current bit-matrix input to this Region.
    @return the output bit-matrix of the Region (or None if Region disabled).
    """
    if not self.onButton.GetValue(): #Region disabled, return None
      return None
    
    #build new Region if first time Run
    if not self.region:
      self.__checkCreateRegion()
    
    #self.statusValText.SetLabel("Active")
    
    #Update inputs, learning states, and run the Region
    self.region.updateInput(inputData)
    self.region.temporalLearning = self.temporalButton.GetValue()
    self.region.spatialLearning = self.spatialButton.GetValue()
    self.region.runOnce()
    
    self.inhiRadValText.SetLabel(SIGF.format(self.region.inhibitionRadius))
    
    #refresh RegionFrame visualization if open
    if self.regionFrame: 
      self.regionFrame.draw()
    
    nx = len(self.region.columnGrid)
    ny = len(self.region.columnGrid[0])
    if self.activeCols==None or self.activeCols.shape!=(nx,ny):
      self.predictedCols = numpy.zeros((nx,ny), dtype=numpy.uint8)
      self.activeCols = numpy.zeros((nx,ny), dtype=numpy.uint8)
  
    #want to know % active columns that were correctly predicted
    for col in self.region.columns:
      if col.isActive:
        self.activeCols[col.cx][col.cy] = 1
      else:
        self.activeCols[col.cx][col.cy] = 0
    
    #compare active columns now, to predicted columns from t-1
    a = self.activeCols
    p = self.predictedCols
    pctA = 0.0
    pctP = 0.0
    if numpy.sum(p)>0:
      pctP = (1.0*numpy.sum(a*p)) / numpy.sum(p)
    if numpy.sum(a)>0:
      pctA = (1.0*numpy.sum(a*p)) / numpy.sum(a)
    
    self._meanCount += 1
    self._sumAccPred += pctP
    self._sumAccActive += pctA
    
    meanPctP = self._sumAccPred / self._meanCount
    meanPctA = self._sumAccActive / self._meanCount
    
    self.predMeanAccValText.SetLabel(SIGF.format(meanPctP*100.0)+"%")
    self.activeMeanAccValText.SetLabel(SIGF.format(meanPctA*100.0)+"%")
    
    self.predAccValText.SetLabel(SIGF.format(pctP*100.0)+"%")
    self.activeAccValText.SetLabel(SIGF.format(pctA*100.0)+"%")
    
    #save the current prediction to compare to next time step
    for col in self.region.columns:
      self.predictedCols[col.cx][col.cy] = 0
      for cell in col.cells:
        if cell.isPredicting:
          for seg in cell.segments:
            if seg.isActive() and seg.isSequence:
              self.predictedCols[col.cx][col.cy] = 1
              break
    
    return self.region.getOutput()


class ImageCanvas(wx.ScrolledWindow):
  """
  Simple wx canvas to paint a bitmap image on the screen.
  """
  
  def __init__(self, parent, id, width, height):
    wx.ScrolledWindow.__init__(self, parent, id, size=(width,height))
    
    self.bitmap = None
    self.width = width
    self.height = height
    self.SetSize((width,height))
    self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
    
    self.Bind(wx.EVT_PAINT, self.OnPaint)
  
  def setBitmap(self, bitmap):
    """ Assign the bitmap image to display in this canvas. """
    self.bitmap = bitmap
    self.Refresh()
  
  def OnPaint(self, evt):
    """ Fired on wx paint events. """
    dc = wx.PaintDC(self)
    self.PrepareDC(dc)
    
    if self.bitmap and self.bitmap.Ok():
      memDC = wx.MemoryDC()
      memDC.SelectObject(self.bitmap)
      dc.Blit(0, 0,
          self.bitmap.GetWidth(), self.bitmap.GetHeight(),
          memDC, 0, 0, wx.COPY, True)
    else:
      dc.DrawRectangle(0,0, self.width, self.height)

