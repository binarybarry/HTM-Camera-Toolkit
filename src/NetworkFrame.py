"""
Created on May 11, 2011

@author: Barry Maturkanich

The NetworkFrame contains all the top-level UI to allow users to
define HMAX Networks and then visualize the states of each of its
layers to understand what the Network is coming up with and why.

The HMAX Network is trained using static images however the UI is
set up to allow playing video files and presenting each individual
video frame to the network.

Once you click to create an HMAX Network the first step is to perform
learning for the S2 level.  This level is interested in learned small
4x4 "patches" of cells within its layers.  By the time data gets to S2
it has been approximated as lines of various orientations.  S2 then
learns a set of these line-orientation patches.  Layer S2 will try
to then later describe entire images in terms of these learned patches.

Once S2 is trained, we then need to train C2 which ultimately is an SVM
(Support Vector Machine).  C2 looks at how closely all parts of the 
input image match each of the learned S2 patches.  It then passes these
results to its SVM along with a class label (which is toggled in the UI 
during training).

Once C2 is trained, we can perform inference on new images.  C2 will use
its trained SVM to estimate which class of image the input image is
most closely associated with.
"""

import wx
import cv
import numpy
import os
from time import clock
from PIL import Image, ImageOps, ImageDraw
from Util import convertToWxImage
import Util
from HMAX.Layer import Layer
from HMAX.Network import Network
from HMAX.GRBFFilter import GRBFFilter

SIGF0 = "{0:.0f}" #0 significant digits float string format code
SIGF2 = "{0:.2f}" #2 significant digits float string format code

class NetworkFrame(wx.Frame):
  """
  The main HMAX Toolkit wxFrame window.  We include the main menu bar and 
  attach the NetworkWindow panel which contains all the real UI.
  """

  def __init__(self, parent=None):
    """
    Constructor to build the NetworkFrame top-level window frame.
    """
    super(NetworkFrame, self).__init__(parent, title="HMAX Camera Toolkit",
          size=(950,720), 
          style=wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE)
    
    #Create the top-level application menu bar
    menubar = wx.MenuBar()
    
    file = wx.Menu()
    file.Append(wx.ID_EXIT, 'Exit', 'Exit application')
    self.Bind(wx.EVT_MENU, self.onExit, id=wx.ID_EXIT)
    
    options = wx.Menu()
    self.miDetect = wx.MenuItem(options, wx.ID_DEFAULT, 'Perform Motion Detection', \
                                 'Perform Motion Detection', wx.ITEM_CHECK)
    options.AppendItem(self.miDetect)
    self.Bind(wx.EVT_MENU, self.onMotionDetect, id=wx.ID_DEFAULT)
    
    help = wx.Menu()
    help.Append(wx.ID_HELP, 'About HMAX Camera Toolkit', 'Help actions')
    self.Bind(wx.EVT_MENU, self.onHelp, id=wx.ID_HELP)
    
    menubar.Append(file, "&File")
    menubar.Append(options, "&Options")
    menubar.Append(help, "&Help")
    self.SetMenuBar(menubar)
    
    self.networkWin = NetworkWindow(self)
    size = self.networkWin.GetBestSize().Get()
    self.SetSize((size[0]+20,size[1]+60))

  def onExit(self, evt=None):
    """ Top-level menu exit command was issued by user. """
    exit()
  
  def onMotionDetect(self, evt=None):
    """ Top-level menu Perform Motion Detection was toggled """
    self.networkWin._motionDetect = self.miDetect.IsChecked()
  
  def onHelp(self, evt=None):
    """ Top-level menu help about command was issued by user. """
    text = "HMAX Camera Toolkit v1.0 (Aug-14-11) by Barry Maturkanich " + \
          "(binarybarry@gmail.com).\n\n" + \
           "The HMAX (Hierarchical Model and X) Network learning algorithm "+ \
           "is a computer vision algorithm inspired by research of the ventral "+ \
           "'what' pathway of the neocortex in the mammalian brain.  All "+ \
           "code used in this application is my personal implementation of the HMAX "+ \
           "network algorithm based on published techniques from several recent "+ \
           "academic research papers.\n\nMost notably cited is the paper by Jim Mutch "+ \
           "and David G. Lowe \"Object class recognition and localization using "+ \
           "sparse features with limited receptive fields\" 2008."+ \
           "\n\nThe toolkit also uses code from several other open-source projects "+ \
           "including the Python Imaging Library, Numpy, wxPython, OpenCV, and LIBSVM."
    msg = wx.MessageDialog(self, text, "About HMAX Camera Toolkit", wx.OK | wx.ICON_INFORMATION)
    msg.ShowModal()
    
class NetworkWindow(wx.Panel):
  """
  Visualize HMAX network state.
  """
  
  def __init__(self, parent):
    super(NetworkWindow, self).__init__(parent)
    
    self.network = None
    
    self._isPlaying = False
    self._isPaused = False
    self._isLooping = False
    self._capture = None
    self._frameOut = None
    self._videoWriter = None
    self._videoDir = os.getcwd()+os.sep+"video"+os.sep
    self._lastFrameTime = clock()
    self._secPerFrame = 1.0 / 15.0
    self._networkSize = (80,60)
    self._lastImageClick = None
    self._motionDetect = False
    
    self._prevImage = None
    self._normalImage = None
    
    canvasSize = Layer.canvasSize
    self._inputImageNet = cv.CreateImage(self._networkSize, cv.IPL_DEPTH_8U, 1 )
    self._inputImage = cv.CreateImage(canvasSize, cv.IPL_DEPTH_8U, 1 )
    self._diffImage = cv.CreateImage(canvasSize, cv.IPL_DEPTH_8U, 1)
    self._prevIplImage = cv.CreateImage(canvasSize, cv.IPL_DEPTH_8U, 1)
    self._threshImage = cv.CreateImage(canvasSize, cv.IPL_DEPTH_8U, 1)
    self._motionImage = Image.new('L', canvasSize)
    
    self._historyImage = cv.CreateImage(canvasSize, cv.IPL_DEPTH_32F, 1 )
    self._segMaskImage = cv.CreateImage(canvasSize, cv.IPL_DEPTH_32F, 1 )
    self._memStorage = cv.CreateMemStorage()
    
    self._frameImage = None
    self._fileImage = None
    
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
    inputBox.SetMinSize((canvasSize[0]+14, -1))
    
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
    
    #Parameters for network creation and visualization
    createBox = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Define HMAX Network"), \
                                  orient=wx.VERTICAL)
    
    self.onButton = wx.CheckBox(self, 0, "Network On")
    self.onButton.SetToolTipString("Enable this Network for input processing (Network is created fresh if parameters have changed since last on).")
    self.onButton.Bind(wx.EVT_CHECKBOX, self.networkOnRun)
    
    createPanel = wx.Panel(self)
    fgsCreate = wx.FlexGridSizer(2, 2, 5, 5) #rows, cols, vgap, hgap
    
    numScalesText = wx.StaticText(createPanel, label="# Scales")
    numThetasText = wx.StaticText(createPanel, label="# Thetas")
    numScalesText.SetToolTipString("Number of image resolution scales to generate.")
    numThetasText.SetToolTipString("Number of gabor line detection angles to use.")
    
    self.numScalesSpin = wx.SpinCtrl(createPanel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.numScalesSpin.SetRange(2, 12)
    self.numScalesSpin.SetValue(2)
    self.numScalesSpin.SetToolTipString("(Fixed at 2 scales until future release)")
    self.numScalesSpin.Disable()
    self.numThetasSpin = wx.SpinCtrl(createPanel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.numThetasSpin.SetRange(1, 12)
    self.numThetasSpin.SetValue(8)
    
    fgsCreate.AddMany([(numScalesText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.numScalesSpin, 0, wx.ALIGN_CENTER_VERTICAL),
                     (numThetasText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.numThetasSpin, 0, wx.ALIGN_CENTER_VERTICAL)])
    createPanel.SetSizer(fgsCreate)
    
    createBox.Add(self.onButton, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, border=5)
    createBox.Add(createPanel, 0, flag=wx.ALL|wx.EXPAND, border=5)
    
    #network results visualization options
    paramBox = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Results display options"), \
                                 orient=wx.VERTICAL)
    
    scaleText = wx.StaticText(self, label="Scale")
    thetaText = wx.StaticText(self, label="Theta")
    c1TypeText = wx.StaticText(self, label="Render")
    c2TypeText = wx.StaticText(self, label="Results")
    
    scaleText.SetToolTipString("Select image scales to view below.\n(Fixed at 2 scales until future release)")
    thetaText.SetToolTipString("Select gabor theta angle to view below.")
    c1TypeText.SetToolTipString("Render all C1 orientations or only those representing last clicked S2 cell.")
    c2TypeText.SetToolTipString("In the last canvas render either S2 results or C2 results.")
    
    self.scaleCombo = wx.ComboBox(self, -1, size=(110,-1), style=wx.CB_READONLY)
    self.thetaCombo = wx.ComboBox(self, -1, size=(110,-1), style=wx.CB_READONLY)
    self.scaleCombo.Bind(wx.EVT_COMBOBOX, self.displayComboRun)
    self.thetaCombo.Bind(wx.EVT_COMBOBOX, self.displayComboRun)
    self.scaleCombo.Disable() #disable until first network is created
    self.thetaCombo.Disable()
    
    self.c1TypeCombo = wx.ComboBox(self, -1, size=(110,-1), style=wx.CB_READONLY)
    self.c1TypeCombo.Bind(wx.EVT_COMBOBOX, self.displayComboRun)
    self.c1TypeCombo.SetItems(["S2 Selection", "C1 Composite"])
    self.c1TypeCombo.Select(1)
    self.c1TypeCombo.Disable()
    
    self.c2TypeCombo = wx.ComboBox(self, -1, size=(110,-1), style=wx.CB_READONLY)
    self.c2TypeCombo.Bind(wx.EVT_COMBOBOX, self.displayComboRun)
    self.c2TypeCombo.SetItems(["S2 Results", "C2 Results"])
    self.c2TypeCombo.Select(0)
    self.c2TypeCombo.Disable()
    
    fgsParam = wx.FlexGridSizer(3, 2, 5, 5)
    fgsParam.AddMany([(scaleText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.scaleCombo, 0, wx.ALIGN_CENTER_VERTICAL),
                     (thetaText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.thetaCombo, 0, wx.ALIGN_CENTER_VERTICAL),
                     (c1TypeText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.c1TypeCombo, 0, wx.ALIGN_CENTER_VERTICAL),
                     (c2TypeText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.c2TypeCombo, 0, wx.ALIGN_CENTER_VERTICAL)])
    paramBox.Add(fgsParam, 0, flag=wx.ALL|wx.EXPAND, border=5)
    
    #S2 learning parameters options
    learnS2Box = wx.StaticBoxSizer(wx.StaticBox(self, -1, "S2 Learning"), \
                                   orient=wx.VERTICAL)
    learnS2Panel = wx.Panel(self)
    fgsS2Panel = wx.FlexGridSizer(2, 2, 5, 5) #rows, cols, vgap, hgap
    
    self.resetS2Button = wx.Button(learnS2Panel, 0, "Reset")
    self.resetS2Button.SetToolTipString("Reset all learning for S2 (and C2).")
    self.resetS2Button.Bind(wx.EVT_BUTTON, self.resetS2Run)
    
    self.learnS2Button = wx.CheckBox(learnS2Panel, 0, "Learning")
    self.learnS2Button.SetToolTipString("Enable Learning for S2.")
    self.learnS2Button.Bind(wx.EVT_CHECKBOX, self.learnS2Run)
    self.learnS2Button.Disable()
    
    maxPatchText = wx.StaticText(learnS2Panel, label="Max Patches")
    maxPatchText.SetToolTipString("Maximum number of S2 spatial patches to learn. Must decide before creating network.")
    self.maxPatchSpin = wx.SpinCtrl(learnS2Panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.maxPatchSpin.SetRange(1, 200)
    self.maxPatchSpin.SetValue(50)
    
    similarText = wx.StaticText(learnS2Panel, label="Max Similarity")
    similarText.SetToolTipString("If patches are more than this % similar they are considered equivalent during learning.")
    self.similarSpin = wx.SpinCtrl(learnS2Panel, size=(70,-1), style=wx.SP_ARROW_KEYS)
    self.similarSpin.SetRange(1, 100)
    self.similarSpin.SetValue(90)
    
    patchesText = wx.StaticText(learnS2Panel, label="# Patches")
    patchesText.SetToolTipString("Number of S2 patches learned so far.")
    self.numPatchText = wx.StaticText(learnS2Panel, label="0")
    
    fgsS2Panel.AddMany([(self.learnS2Button, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.resetS2Button, 0, wx.ALIGN_CENTER_VERTICAL),
                     (maxPatchText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.maxPatchSpin, 0, wx.ALIGN_CENTER_VERTICAL),
                     (similarText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.similarSpin, 0, wx.ALIGN_CENTER_VERTICAL),
                     (patchesText, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.numPatchText, 0, wx.ALIGN_CENTER_VERTICAL)])
    learnS2Panel.SetSizer(fgsS2Panel)
    
    learnS2Box.Add(learnS2Panel, 0, flag=wx.ALL|wx.EXPAND, border=5)

    #C2 learning parameters options
    learnC2Box = wx.StaticBoxSizer(wx.StaticBox(self, -1, "C2 SVM Learning"), \
                                   orient=wx.VERTICAL)
    c2Panel = wx.Panel(self)
    fgsC2 = wx.FlexGridSizer(1, 2, 5, 5) #rows, cols, vgap, hgap
    
    self.learnC2Button = wx.CheckBox(c2Panel, 0, "Learning: class")
    self.learnC2Button.SetToolTipString("Learn a class for C2.")
    self.learnC2Button.Bind(wx.EVT_CHECKBOX, self.learnC2Run)
    self.learnC2Button.Disable()
    
    self.learnC2Spin = wx.SpinCtrl(c2Panel, size=(55,-1), style=wx.SP_ARROW_KEYS)
    self.learnC2Spin.SetRange(1, 10)
    self.learnC2Spin.SetValue(1)
    
    fgsC2.AddMany([(self.learnC2Button, 0, wx.ALIGN_CENTER_VERTICAL), 
                     (self.learnC2Spin, 0, wx.ALIGN_CENTER_VERTICAL)])
    c2Panel.SetSizer(fgsC2)
    
    self.classLabel = wx.StaticText(self, label="0 learned for class 1")
    self.allClassLabel = wx.StaticText(self, label="0 learned across 0 classes")
    self.classLabel.SetToolTipString("Number of examples learned for SVM classes.")
    
    self.finishC2Button = wx.Button(self, 0, "Finish Learning")
    self.finishC2Button.SetToolTipString("Finalize Learning for C2.")
    self.finishC2Button.Bind(wx.EVT_BUTTON, self.finishC2Run)
    self.finishC2Button.Disable()
    
    learnC2Box.Add(c2Panel, 0, flag=wx.ALL|wx.EXPAND, border=5)
    learnC2Box.Add(self.classLabel, 0, wx.EXPAND | wx.LEFT|wx.BOTTOM, border=5)
    learnC2Box.Add(self.allClassLabel, 0, wx.EXPAND | wx.LEFT|wx.BOTTOM, border=5)
    learnC2Box.Add(self.finishC2Button, 0, wx.EXPAND | wx.LEFT|wx.BOTTOM, border=5)
    
    
    #Add the image canvases for the HMAX network results
    self.siBoxA = wx.StaticBox(self, -1, "SI a")
    canvasBoxSIa = wx.StaticBoxSizer(self.siBoxA, orient=wx.VERTICAL)
    canvasSIa = ImageCanvas(self, -1, canvasSize, 0,0, self.runImageClicked)
    canvasBoxSIa.Add(canvasSIa, 0, wx.BOTTOM | wx.LEFT| wx.RIGHT, border=2)
    
    self.siBoxB = wx.StaticBox(self, -1, "SI b")
    canvasBoxSIb = wx.StaticBoxSizer(self.siBoxB, orient=wx.VERTICAL)
    canvasSIb = ImageCanvas(self, -1, canvasSize, 0,1, self.runImageClicked)
    canvasBoxSIb.Add(canvasSIb, 0, wx.BOTTOM | wx.LEFT| wx.RIGHT, border=2)
    
    self.s1BoxA = wx.StaticBox(self, -1, "S1a")
    canvasBoxS1a = wx.StaticBoxSizer(self.s1BoxA, orient=wx.VERTICAL)
    canvasS1a = ImageCanvas(self, -1, canvasSize, 1,0, self.runImageClicked)
    canvasBoxS1a.Add(canvasS1a, 0, wx.BOTTOM | wx.LEFT| wx.RIGHT, border=2)
    
    self.s1BoxB = wx.StaticBox(self, -1, "S1b")
    canvasBoxS1b = wx.StaticBoxSizer(self.s1BoxB, orient=wx.VERTICAL)
    canvasS1b = ImageCanvas(self, -1, canvasSize, 1,1, self.runImageClicked)
    canvasBoxS1b.Add(canvasS1b, 0, wx.BOTTOM | wx.LEFT| wx.RIGHT, border=2)
    
    self.c1Box = wx.StaticBox(self, -1, "C1")
    canvasBoxC1 = wx.StaticBoxSizer(self.c1Box, orient=wx.VERTICAL)
    canvasC1 = ImageCanvas(self, -1, canvasSize, 2,0, self.runImageClicked)
    canvasBoxC1.Add(canvasC1, 0, wx.BOTTOM | wx.LEFT| wx.RIGHT, border=2)
    
    self.s2Box = wx.StaticBox(self, -1, "S2")
    canvasBoxS2 = wx.StaticBoxSizer(self.s2Box, orient=wx.VERTICAL)
    canvasS2 = ImageCanvas(self, -1, canvasSize, 3,0, self.runImageClicked)
    canvasBoxS2.Add(canvasS2, 0, wx.BOTTOM | wx.LEFT| wx.RIGHT, border=2)
    
    #canvases[levelID][relativeLayerID]
    self.canvases = []
    self.canvases.append([canvasSIa, canvasSIb])
    self.canvases.append([canvasS1a, canvasS1b])
    self.canvases.append([canvasC1])
    self.canvases.append([canvasS2])
    
    self._fgsMain = wx.FlexGridSizer(2, 3, 5, 5)
    self._fgsMain.AddMany([(canvasBoxSIa, 0, wx.EXPAND),
                    (canvasBoxS1a, 0, wx.EXPAND),
                    (canvasBoxC1, 0, wx.EXPAND),
                    (canvasBoxSIb, 0, wx.EXPAND),
                    (canvasBoxS1b, 0, wx.EXPAND),
                    (canvasBoxS2, 0, wx.EXPAND)])
    
    hSizerTop = wx.BoxSizer(wx.HORIZONTAL)
    hSizerTop.Add(inputBox, 0, wx.ALIGN_TOP | wx.RIGHT, border=5)
    hSizerTop.Add(createBox, 0, wx.EXPAND)
    hSizerTop.Add(paramBox, 0, wx.EXPAND)
    hSizerTop.Add(learnS2Box, 0, wx.EXPAND)
    hSizerTop.Add(learnC2Box, 0, wx.EXPAND)

    vSizerMain = wx.BoxSizer(wx.VERTICAL)
    vSizerMain.Add(hSizerTop, 0, wx.ALIGN_TOP | wx.BOTTOM | wx.LEFT, border=5)
    vSizerMain.Add(self._fgsMain, 0, wx.EXPAND | wx.LEFT, border=5)
    
    self.SetSizer(vSizerMain)
    self.SetAutoLayout(1)
    
  def resetS2Run(self, evt=None, confirm=True):
    """ The user clicked the Reset Learning button to clear S2/C2 learning. """
    if self.network.C2.hasBuiltSVM():
      if confirm:
        text = "This will reset all the C2 SVM learning as well. Continue?"
        msg = wx.MessageDialog(self, text, "Reset Learning", \
                               wx.OK | wx.CANCEL | wx.ICON_EXCLAMATION)
        if msg.ShowModal()==wx.ID_CANCEL:
          return
      self.network.C2.resetLearning()
      self.finishC2Button.Disable()
      self.learnC2Spin.Enable()
      self.c2TypeCombo.Select(0)
      self.displayComboRun()
      self.classLabel.SetLabel("0 learned for class 1")
      self.allClassLabel.SetLabel("0 learned across 0 classes")
    
    if self.onButton.GetValue():
      self.learnS2Button.SetValue(True)
    self.learnC2Button.Disable()
    self.network.S2.clearLearnedPatches()
    self.numPatchText.SetLabel("0")
    self.similarSpin.Enable()
  
  def learnS2Run(self, evt=None):
    """ 
    The user clicked the Learning S2 checkbox to enable or disable learning 
    of S2 patches.
    """
    if self.network!=None:
      GRBFFilter.SPATIAL_POOL_DIST = self.similarSpin.GetValue() / 100.0
      isLearning = self.learnS2Button.GetValue()
      self.network.S2.isLearning = isLearning
      
      #disable learn button on uncheck; dim spinners during learning
      #self.learnS2Button.Enable(isLearning)
      self.similarSpin.Disable()
      
  def learnC2Run(self, evt=None):
    """ 
    The user clicked the Learning C2 checkbox to enable or disable learning 
    of C2 classes.
    """
    if self.network!=None:
      self.network.C2.isLearning = self.learnC2Button.GetValue()
      self.network.C2.learningClass = self.learnC2Spin.GetValue()
  
  def finishC2Run(self, evt=None):
    """ 
    The user clicked the Finish Learning C2 checkbox to finialize learning 
    of C2 classes by training the final SVM model.
    """
    if self.network!=None:
      self.network.C2.finishLearning()
      self.learnC2Button.SetValue(False)
      self.learnC2Button.Disable()
      self.learnC2Spin.Disable()
      self.finishC2Button.Disable()
      self.c2TypeCombo.Select(1)
      self.displayComboRun()
  
  def runImageClicked(self, mousePos, levelID, scaleID):
    """ 
    Result image was clicked, so draw bound boxes of clicked cell and
    around all cells representing previous layer inputs to the clicked cell.
    @param mousePos: (x,y) pixel location mouse was lasted clicked.
    @param levelID: integer id of the network level that was clicked in.
    @param scaleID: integer id of the layer (scale) that was clicked in.
    """
    self._lastImageClick = (mousePos, levelID, scaleID)
    self.renderNetwork()
  
  def runNetworkOnce(self):
    """ 
    If the Network is enabled to run, then run the Network for one time step
    using the last processed video frame.  The Network parameters are set
    in their respective UI panels.  After run is finished, render the state
    of the network layers onto their respective canvases.
    """
    if self._frameOut:
      if self.network!=None and self.onButton.GetValue():
        self.learnS2Run() #ensure learning states are up-to-date
        self.learnC2Run()
        
        self.network.inference(self._frameOut)
        
        #if learning S2/C2, update labels and chec
        if self.learnS2Button.GetValue():
          numPatches = len(self.network.S2.learned)
          self.numPatchText.SetLabel(str(numPatches))
          if numPatches >= GRBFFilter.MAX_PATCHES:
            self.learnC2Button.Enable()
            self.learnS2Button.SetValue(False)
            self.learnS2Run()
            self.stopRun()
        if self.learnC2Button.GetValue():
          classID = self.learnC2Spin.GetValue()
          ccount = self.network.C2.getCount(classID)
          acount = self.network.C2.getCount()
          aclass = self.network.C2.numClasses
          
          self.classLabel.SetLabel("%d learned for class %d" % (ccount, classID))
          self.allClassLabel.SetLabel("%d learned across %d classes" % (acount, aclass))
          self.finishC2Button.Enable()
        
        self.renderNetwork()
      else: #if playout enabled, but no network, just render the playback frame
        frameOut = self._frameOut.resize(Layer.canvasSize)
        imageOut = Util.convertToWxImage(frameOut)
        self.canvases[0][0].setBitmap(wx.BitmapFromImage(imageOut))
  
  def renderNetwork(self):
    """ 
    Render the last processed state of the network using the current
    UI visualization settings to choose which scales/angle to view. 
    """
    li = self.scaleCombo.GetSelection()
    ti = self.thetaCombo.GetSelection()
    norm = [False, True, True, True]
    fa = [0, ti, ti, 0]
    maxGabor = self.network.levels[1].getMaxLayerValue()
    maxLevel3 = self.network.levels[3].getMaxLayerValue()
    
    levels = self.network.levels
    for i in xrange(len(levels)-1):
      for ci in xrange(len(self.canvases[i])):
        layer = levels[i].layers[li+ci]
        if i==3:
          if self.c2TypeCombo.GetValue()=="C2 Results":
            layer = levels[i+1].layers[li+ci]
          layer.renderLayer(self.canvases[i][ci], fa[i], norm[i], maxLevel3)
        else:
          layer.renderLayer(self.canvases[i][ci], fa[i], norm[i], maxGabor)
    
    self.renderSelection() #render user selection information
    #s1aArr = levels[1].layers[li].getLayerData(f=ti)
    #print numpy.max(s1aArr), numpy.min(s1aArr), numpy.mean(s1aArr)
  
  def renderSelection(self):
    """
    If a cell in the network was selected (clicked) by the user, render
    bounding boxes around the selected cell and also boxes around all
    cells from input layers used as input that contributed to the ultimate
    value of the clicked cell.
    """
    if self._lastImageClick==None:
      mousePos, levelID, scaleID = (0,0), 0, 0
    else:
      mousePos, levelID, scaleID = self._lastImageClick
    
    #if we are learning S2 patches, display last learned patch
    isDisplay = True
    if self.learnS2Button.GetValue():
      ll = self.network.S2.lastLearned
      if ll!=None:
        mousePos, levelID, scaleID = (ll[0],ll[1]), 3, 0
        bbox = (mousePos[0]*1.0,mousePos[1]*1.0,0.0,0.0)
        isDisplay = False
    
    #self._mouseCallback(event.GetPositionTuple(), self.layerID, self.scaleID)
    #input: layer type, feature index (i.e. si[1], s1[2][theta=45], etc)
    #1) map pixel position to layer cell position that was clicked
    #2) use layer type filter to getInputBoundBox for input layer(s)
    #3)   traverse down hierarchy until all bound boxes found
    #4) draw bound boxes on layer canvases
    ti = self.thetaCombo.GetSelection() #TODO more specific per layer
    li = self.scaleCombo.GetSelection()
    layerIn = self.network.levels[levelID].layers[li+scaleID]
    if isDisplay:
      bbox = layerIn.getBBoxDisplayToLayer(mousePos)
    
    boxMap = layerIn.getBoundBoxHierarchy(bbox)
    
    #Draw red bounding boxes to represent input to the clicked mouse position
    for canvasList in self.canvases:
      for canvas in canvasList:
        canvas.setBBoxSelection(None)
    for layer in boxMap.keys():
      dbbox = boxMap[layer]
      self.canvases[layer.level.index][layer.index].setBBoxSelection(dbbox)
    
    #Draw C1 as a composite of all winning orientations
    c1Type = self.c1TypeCombo.GetValue()
    if c1Type=="S2 Selection" and levelID!=3:
      self.canvases[2][0].setOverlayBitmaps(None)
    else: #"C1 Composite"
      layerS2 = self.network.levels[3].layers[li]
      overlays = layerS2.generateS2InputBitmap(mousePos, c1Type)
      self.canvases[2][0].setOverlayBitmaps(overlays)
  
  def networkOnRun(self, evt=None):
    """ 
    User clicked button to enable/disable Network. If turned on, the Network will
    be created new if this is the first time or if the Network parameters have
    changed since last create.  Otherwise the Network is just re-enabled to run
    without creating fresh.  The UI for parameters is only enabled if the Network
    is off as most parameters cannot change once the Network has been created.
    """
    isOn = self.onButton.GetValue()
    
    #if region previously created, rebuild if params changed
    self.__checkCreateNetwork()
    
    #self.numScalesSpin.Enable(not isOn)
    self.numThetasSpin.Enable(not isOn)
    #self.scaleCombo.Enable(isOn)
    self.thetaCombo.Enable(isOn)
    self.c1TypeCombo.Enable(isOn)
    self.c2TypeCombo.Enable(isOn)
    self.maxPatchSpin.Enable(not isOn)
  
  def __checkCreateNetwork(self):
    """ 
    Create the Network using the currently set UI parameters. The network
    is only created new if this is first run or if the UI parameters have
    changed since Network was last created. 
    """
    numScales = self.numScalesSpin.GetValue()
    numThetas = self.numThetasSpin.GetValue()
    maxPatches = self.maxPatchSpin.GetValue()
    
    rebuild = False
    if not self.network:
      rebuild = self.onButton.GetValue()
    elif maxPatches!=GRBFFilter.MAX_PATCHES or \
         len(self.network.thetas)!=numThetas or \
         len(self.network.levels[0].layers)!=numScales:
      rebuild = True
      self.resetS2Run(confirm=False)
    
    if rebuild:
      GRBFFilter.MAX_PATCHES = maxPatches
      
      self.network = Network(self._networkSize, numScales, numThetas)
      
      #Update the group labels on the layer canvases
      #TODO need to handle correctly when viewing different scales
      self.siBoxA.SetLabel(self.network.levels[0].layers[0].label)
      self.siBoxB.SetLabel(self.network.levels[0].layers[1].label)
      self.s1BoxA.SetLabel(self.network.levels[1].layers[0].label)
      self.s1BoxB.SetLabel(self.network.levels[1].layers[1].label)
      self.c1Box.SetLabel(self.network.levels[2].layers[0].label)
      self.s2Box.SetLabel(self.network.levels[3].layers[0].label)
      
      #force S2 learning to be enabled on network creation
      self.learnS2Button.SetValue(True)
      self.learnS2Run()
      
      #Re-populate the visualizer options
      thetaItems = []
      for theta in self.network.thetas:
        thetaItems.append(SIGF0.format(numpy.degrees(theta))+" degrees")
        
        siLayers = self.network.levels[0].layers
        si0x = siLayers[0].xSize
        prevSize = "100%"
        scaleItems = []
        for si in siLayers[1:]:
          size = SIGF0.format((1.0*si.xSize/si0x)*100.0)+"%"
          scaleItems.append(prevSize+",  "+size)
          prevSize = size
        
        self.scaleCombo.SetItems(scaleItems)
        self.scaleCombo.SetSelection(0)
        self.thetaCombo.SetItems(thetaItems)
        self.thetaCombo.SetSelection(0)
  
  def displayComboRun(self, evt=None):
    """ A combo box toggling result visualization options has been selected. """
    if self.c2TypeCombo.GetValue()=="C2 Results":
      self.s2Box.SetLabel(self.network.levels[4].layers[0].label)
    else:
      self.s2Box.SetLabel(self.network.levels[3].layers[0].label)
    self.renderNetwork()
    
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
    
    #test if we can get frames from the input; error dialog if not
    try:
      frame = cv.QueryFrame(self._capture)
      frame.width #if frame is invalid, asking for width will fail
      
      #if reading from file, re-init the capture on success to ensure
      #we do not throw away the very first frame on a test
      if self.fileButton.GetValue():
        fileName = self._videoDir+self.fileCombo.GetValue()
        self._capture = cv.CaptureFromFile(fileName)
      
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
      self.canvases[0][0].setBitmap(wx.NullBitmap)
      self.canvases[0][1].setBitmap(wx.NullBitmap)
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
                                               15, self._networkSize, 0)
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
      #update last processed frame, and process Network if enabled
      self._frameOut = frameOut
      self.runNetworkOnce()
    
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
      else:
        self.stopRun()
      return
    
    return self.__processVideoFrame(frame)
  
  def captureFromCamera(self):
    """ 
    Capture a live frame from the camera and perform motion processing
    on the acquired image.  If recording is enabled, also write the processed
    frame to an output video file. 
    """
    frame = cv.QueryFrame(self._capture) # Grab the frame from the capture
    if not frame:
      self.stopRun()
      return None
    
    frameOut = self.__processVideoFrame(frame)
    
    # Mirror if using camera, this is more intuitive for webcams
    frameOut = ImageOps.mirror(frameOut)
  
    if self._videoWriter: #if recording enabled, write out to the video file
      cvImage = Util.convertPILToCV(frameOut)
      cv.WriteFrame(self._videoWriter, cvImage)
    
    return frameOut
    
  def __processVideoFrame(self, frame):
    """ 
    Process the most recently read video frame (either from the live 
    camera or a video file) to prepare for passing into the network.
    First we ensure the image size matches the size that the network
    is expecting (we resize the image if needed).  Then if motion
    detection is enabled we compare the current video frame to the
    previous frame and only keep those pixels where changes have occurred.
    If the live camera is used we perform a mirror operation for a more
    intuitive look when using a front-facing webcam.
    @param frame: the most recently acquired OpenCV video frame image.
    """
    #if frame exactly matches network and motionDetect is off, then
    #just return a gray-scale version of the image to avoid extra resizes
    if frame.width==self._networkSize[0] and frame.height==self._networkSize[1]:
      if not self._motionDetect:
        cv.CvtColor(frame, self._inputImageNet, cv.CV_RGB2GRAY)
        return Image.fromstring('L', self._networkSize, 
                                self._inputImageNet.tostring(), 'raw','L',0,1)
    
    #if camera's frame size is incorrect, resize to what we need
    canvasSize = Layer.canvasSize
    if frame.width!=canvasSize[0] or frame.height!=canvasSize[1]:
      if self._frameImage==None:
        self._frameImage = cv.CreateImage(canvasSize, cv.IPL_DEPTH_8U, 3)
      cv.Resize(frame, self._frameImage)
    else: #size is already correct, use frame as-is
      self._frameImage = frame
    
    #convert camera image to gray-scale to perform motion analysis
    cv.CvtColor(self._frameImage, self._inputImage, cv.CV_RGB2GRAY)
    
    # perform motion detection and get the processed image frame
    # the new frame will either be None (no motion) or the motion box subset image
    rect = None
    if self._motionDetect:
      rect = self.processMotion()
    
    if rect!=None:
      mask0 = Image.fromstring('L', canvasSize, 
                               self._threshImage.tostring(), 'raw', 'L', 0, 1)
      xy = (rect[0], rect[1], rect[0]+rect[2], rect[1]+rect[3])
      
      #erase motionImage and paste only thresholded motion pixels on top
      draw = ImageDraw.Draw(self._motionImage)
      draw.rectangle((0,0,self._networkSize[0],self._networkSize[1]), fill="black")
      del draw
      
      imgMask = mask0.crop(xy)
      self._motionImage.paste(imgMask, xy)
      frameOut = self._motionImage
    else:
      frameOut = Image.fromstring('L', canvasSize, 
                                  self._inputImage.tostring(), 'raw', 'L', 0, 1)
    
    return frameOut.resize(self._networkSize)
  
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
      
      #center the largest rect
      cRect = (rect[0]+(rect[2]/2), rect[1]+(rect[3]/2))
      return rect
    
    return None #none means no motion bounding box detected


class ImageCanvas(wx.ScrolledWindow):
  """
  Simple wx canvas to paint a bitmap image on the screen.
  """
  
  def __init__(self, parent, id, size, levelID=0, scaleID=0, mouseCallback=None):
    """
    @param size: size of the image to be drawn on this canvas.
    @param layerID: integer HMAX layer ID this image represents.
    @param scaleID: integer relative HMAX scale ID this image represents.
    @param mouseCallback: callback function to be called when the mouse is
    clicked inside the image; the mouse position, layerID, and scaleID will
    be passed as parameters to the callback.
    """
    wx.ScrolledWindow.__init__(self, parent, id, size)
    
    self._bboxSelection = None
    self._overlayList = None
    self._grid = None
    self.bitmap = None
    self.levelID = levelID
    self.scaleID = scaleID
    self._mouseCallback = mouseCallback
    self.width = size[0]
    self.height = size[1]
    self.SetSize(size)
    self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
    
    self.Bind(wx.EVT_PAINT, self.OnPaint)
    self.Bind(wx.EVT_LEFT_DOWN, self.onMouseLeftDown)
  
  def setBitmap(self, bitmap):
    """ Assign the bitmap image to display in this canvas. """
    self.bitmap = bitmap
    self.Refresh()
  
  def onMouseLeftDown(self, event):
    """ Called when left mouse button clicked somewhere in the Canvas """
    if self._mouseCallback!=None:
      self._mouseCallback(event.GetPositionTuple(), self.levelID, self.scaleID)
  
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
      
      if self._overlayList!=None:
        memDC = wx.MemoryDC()
        for overlay,pos in self._overlayList:
          memDC.SelectObject(overlay)
          if pos==None:
            pos = (0,0)
          dc.Blit(pos[0], pos[1], overlay.GetWidth(), overlay.GetHeight(),
            memDC, 0, 0, wx.COPY, True)
    else:
      dc.DrawRectangle(0,0, self.width, self.height)
      
    if self._grid!=None:
      dc.SetPen(wx.Pen('GRAY'))
      size = self.GetSize()
      w = int(1.0*size[0] / self._grid[0])
      h = int(1.0*size[1] / self._grid[1])
      for xi in xrange(self._grid[0]):
        dc.DrawLine(xi*w, 0, xi*w, size[1])
      for yi in xrange(self._grid[1]):
        dc.DrawLine(0, yi*h, size[0], yi*h)
    
    if self._bboxSelection!=None:
      dc.SetPen(wx.Pen('RED'))
      dc.SetBrush(wx.Brush('WHITE', wx.TRANSPARENT))
      dc.DrawRectangleRect(self._bboxSelection)
  
  def setBBoxSelection(self, bbox):
    """ 
    Assign the last selected bounding box for this canvas.
    The bounding box is drawn as a red rectangle on top of
    the primary canvas contents.
    """
    self._bboxSelection = bbox
    self.Refresh()
    
  def setOverlayBitmaps(self, overlayList):
    """ 
    Assign an overlay bitmap to draw on top of the standard 
    canvas contents. This allows effectively overwriting 
    (part of all of) the default canvas contents with more 
    customized results.
    """
    self._overlayList = overlayList
    self.Refresh()
  
  def setDrawGrid(self, size):
    """ Toggle whether to draw the layer cell grid lines. """
    self._grid = size
    self.Refresh()
    
    