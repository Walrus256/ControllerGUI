import libximc.highlevel as ximc
import sys, traceback, datetime, time
from PyQt6.QtWidgets import (
    QMainWindow, QApplication,
    QLabel, QDoubleSpinBox, QVBoxLayout, 
    QWidget, QHBoxLayout, QGridLayout, QPushButton, QFrame, QSpacerItem, QSizePolicy, 
    QTabWidget, QComboBox, QInputDialog, QDialog, QLineEdit, QMessageBox, 
)
from PyQt6.QtCore import Qt, QRunnable, pyqtSlot, QObject, pyqtSignal, QThreadPool, QSize
from PyQt6.QtGui import QIcon, QDoubleValidator

class WorkerSignals(QObject):       
    result = pyqtSignal(object)
    error = pyqtSignal(tuple)
    finished = pyqtSignal()

# class Worker and Simple_Worker are classes, in which processes on different threads are run, 
# Worker takes in no arguments and returns a result, Simple_Worker takes in *args and has not output
# Signals which Workers emit are defined above
class Worker(QRunnable):
    def __init__(self, function):
        super(Worker, self).__init__()

        self.function = function
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            result = self.function()
            self.signals.result.emit(result)
            self.signals.finished.emit()
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))

class Simple_Worker(QRunnable):
    def __init__(self, function, *args):
        super(Simple_Worker, self).__init__()

        self.function = function
        self.args = args

        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            self.function(*self.args)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))

# subclass of QComboBox, which emits a signal when you click on it and pop-up is shown
#   - done for communications between different tabs when user add new motor
class ComboBox(QComboBox):
    popupAboutToBeShown = pyqtSignal()

    def showPopup(self):
        self.popupAboutToBeShown.emit()
        super(ComboBox, self).showPopup()

# main window of the program
class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Motor Controller")
        self.setStyleSheet("background-color:white")
        # dictionary that assigns serial numbers of controller to a number, which is displayed on 
        # controller's label
        self.controller_dict = {17244:1, 36046:3, 17296:2}
        # tab bar, when double clicked, calls function self.open_new_window()
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.tabBarDoubleClicked.connect(self.open_new_window)
        # setting custom tab
        self.tabs.setStyleSheet("""
        QTabWidget::pane { /* The tab widget frame */
            border-top: 2px solid #C2C7CB;
        }

        QTabWidget::tab-bar {
            left: 5px; /* move to the right by 5px */
        }

        /* Style the tab using the tab sub-control. Note that
            it reads QTabBar _not_ QTabWidget */
        QTabBar::tab {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #E1E1E1, stop: 0.4 #DDDDDD,
                                        stop: 0.5 #D8D8D8, stop: 1.0 #D3D3D3);
            border: 2px solid #C4C4C3;
            border-bottom-color: #C2C7CB; /* same as the pane color */
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            min-width: 8ex;
            padding: 2px;
        }

        QTabBar::tab:selected, QTabBar::tab:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                        stop: 0 #fafafa, stop: 0.4 #f4f4f4,
                                        stop: 0.5 #e7e7e7, stop: 1.0 #fafafa);
        }

        QTabBar::tab:selected {
            border-color: #9B9B9B;
            border-bottom-color: #C2C7CB; /* same as pane color */
        }

        QTabBar::tab:!selected {
            margin-top: 2px; /* make non-selected tabs look smaller */
        }

        /* make use of negative margins for overlapping tabs */
        QTabBar::tab:selected {
            /* expand/overlap to the left and right by 4px */
            margin-left: -4px;
            margin-right: -4px;
        }

        QTabBar::tab:first:selected {
            margin-left: 0; /* the first selected tab has nothing to overlap with on the left */
        }

        QTabBar::tab:last:selected {
            margin-right: 0; /* the last selected tab has nothing to overlap with on the right */
        }

        QTabBar::tab:only-one {
            margin: 0; /* if there is only one tab, we don't want overlapping margins */
        }
        """)
        # this list holds reference to all created tabs (Tab())
        self.tab_list = []
        self.setCentralWidget(self.tabs)

        self.load_controllers()

    # clears any previous tabs and creates new tab
    def load_controllers(self):
        # this loop closes any connected device, so it can be accessed in new tab
        # and any windows left open will close too
        for i in range(len(self.tab_list)):
            self.tab_list[i].axis.close_device()
            self.tab_list[i].close()

        self.tabs.clear()

        self.tab1 = Tab()
        # when "Try Again" button is pressed, function load_controllers() is called
        self.tab1.tryAgainPressed.connect(self.load_controllers)
        self.tabs.addTab(self.tab1, "")
        # if there are more than 1 controllers connected, valueChanged signal is emitted 
        # and function addtabs() is called
        self.tab1.valueChanged.connect(self.addtabs)

    # adds more tabs and gives them proper names, all tabs are stored in self.tab_list
    def addtabs(self):
        devices = self.tab1.devices
        # if the device serial number is not in controller_dict, tab name is just empty space
        self.no_controllers = []
        for i in range(len(devices)):
            try:
                number = self.controller_dict[devices[i]['device_serial']]
            except KeyError:
                number = devices[i]['device_serial']
            
            self.no_controllers.append(number)
        # try:
        #     self.no_controllers = [self.controller_dict[devices[i]['device_serial']] for i in range(len(devices))]
        # except:
        #     self.no_controllers = ["" for i in range(len(devices))]
        self.tab_list = [i for i in range(len(devices))]
        for i in range(len(devices)):
            if i == 0:
                self.tabs.setTabText(0, f"Controller {self.no_controllers[0]}")
                self.tab_list[0] = self.tab1
                continue

            self.tab_list[i] = Tab(devices[i])
            # connects "Try Again" button to function load_controller()
            self.tab_list[i].tryAgainPressed.connect(self.load_controllers)
            self.tabs.addTab(self.tab_list[i], f"Controller {self.no_controllers[i]}")
        
    # when tab is double clicked, it's opened as a separate window
    def open_new_window(self, index):
        if self.tabs.count() == 1:
            return
        # getting index i that corresponds to index of widget in self.tab_list
        i = self.tab_list.index(self.tabs.widget(index))

        self.tabs.removeTab(index)
        self.tab_list[i].setParent(None)
        self.tab_list[i].show()
        self.tab_list[i].widgetClosed.connect(lambda: self.window_closed(i))
    
    # when separate window created from a tab is closed, it goes back as a tab in tab menu
    def window_closed(self, index):
        self.tab_list[index].setParent(self)
        self.tabs.addTab(self.tab_list[index], f"Controller {self.no_controllers[index]}")
    
# Tab class that holds all buttons and controls for one controller
class Tab(QWidget):
    valueChanged = pyqtSignal(object)
    tryAgainPressed = pyqtSignal()
    widgetClosed = pyqtSignal()

    def __init__(self, device=None):

        super(QWidget, self).__init__()
        # setting name of a tab when opened in a separate window
        self.setWindowTitle("Motor Controller")
        self.setStyleSheet("background-color: white;")
        # Default controller to motor connection dictionary
        self.motor_connections = {17244:0, 17296:1, 36046:2}
        # reference to device that is returned from ximc.enumerate_device()
        self.device = device
        self.devices = ""
        # number of connected devices
        self.no_devices = 0
        # uri adress of controller, used for establishing connection with it
        self.uri = ""
        # init variable later used for sending commands to controller
        self.axis = None
        # left and right boundaries of default three motors
        self.right_boundaries = [1221, 10081, 2627]
        self.left_boundaries = [-1050, -4298, -14465]
        self.L, self.R = -1050, 1221
        # motor ranges in mm
        self.ranges = [22, 13, 20]
        # range of this tab's motor
        self.range = 22
        # resolution, steps per mm
        self.resolutions = [102, 1000, 800]
        # resolution of this tab's motor
        self.resolution = 102

        # when calibration is started in self.calibrate(), False value of this 
        # variable is going to stop it
        self.continue_calibrating = True

        # Labels in top left corner of application
        self.finding_devices_label = QLabel("Looking for controller...")
        self.absolute_position_label = QLabel("Absolute position: ")

        # grid in which later controller info is displayed
        self.table = QGridLayout()

        # vertical layout consisting of everything left to the vertical line 
        # splitting the application
        main_vertical_layout = QVBoxLayout()

        # button "Try Again" connected to self.emit_load_signal()
        self.try_again_button = QPushButton("Try Again")
        self.try_again_button.setStyleSheet("""                                                
        QPushButton {
            background-color: rgb(255, 240, 189);
            border: 1px solid black;
            padding:3px;
            border-radius: 8px;
            }

        QPushButton:hover {
            background-color: rgb(230, 217, 173);                                 
            }
        """)
        self.try_again_button.clicked.connect(self.emit_load_signal)
        
        # block in the top left corner of application
        self.searching_layout = QVBoxLayout()
        self.searching_layout.addWidget(self.finding_devices_label)
        self.searching_layout.addWidget(self.try_again_button)

        # top left row (on top of first horizontal line)
        first_row_layout = QHBoxLayout()
        first_row_layout.addLayout(self.searching_layout)

        # lines splitting application into sections
        vline_1 = QFrame(self)
        vline_1.setStyleSheet("color: rgb(0, 0, 0);")
        vline_1.setFrameShape(QFrame.Shape.VLine)
        vline_1.setFrameShadow(QFrame.Shadow.Sunken)

        first_row_layout.addWidget(vline_1)
        first_row_layout.addLayout(self.table)
        main_vertical_layout.addLayout(first_row_layout)

        hline_1 = QFrame(self)
        hline_1.setStyleSheet("color: rgb(0, 0, 0);")
        hline_1.setFrameShape(QFrame.Shape.HLine)
        hline_1.setFrameShadow(QFrame.Shadow.Sunken)
        main_vertical_layout.addWidget(hline_1)
        
        # layout for "Add Motor" and "Calibrate" buttons
        new_motor_layout = QHBoxLayout()
        add_motor_button = QPushButton("Add Motor")
        add_motor_button.setFixedWidth(110)
        add_motor_button.setStyleSheet("""                                                
        QPushButton {
            background-color: rgb(199, 255, 210);
            border: 1px solid black;
            padding:5px;
            border-radius: 8px;
            }

        QPushButton:hover {
            background-color: rgb(143, 255, 166)                                    
            }
        """)
        add_motor_button.clicked.connect(self.add_motor)
        self.calibrate_button = QPushButton("Calibrate")
        self.calibrate_button.setFixedWidth(110)
        self.calibrate_button.setStyleSheet("""                                                
        QPushButton {
            background-color: rgb(255, 130, 130);
            border: 1px solid black;
            padding:5px;
            border-radius: 8px;
            }

        QPushButton:hover {
            background-color: rgb(255, 90, 90)                                    
            }
        """)

        self.calibrate_button.clicked.connect(self.run_calibration)
        self.calibrate_button.setEnabled(False)
        new_motor_layout.addWidget(add_motor_button, alignment=Qt.AlignmentFlag.AlignLeft)
        new_motor_layout.addWidget(self.calibrate_button, alignment=Qt.AlignmentFlag.AlignRight)
        main_vertical_layout.addLayout(new_motor_layout)

        hline_12 = QFrame(self)
        hline_12.setStyleSheet("color: rgb(0, 0, 0);")
        hline_12.setFrameShape(QFrame.Shape.HLine)
        hline_12.setFrameShadow(QFrame.Shadow.Sunken)
        main_vertical_layout.addWidget(hline_12)

        # layout containing Double Spin Boxes for setting position and step increases +, -
        action_layout = QHBoxLayout()
        # grid for spin boxes (float inputs of positions)
        action_grid = QGridLayout()
        step_layout = QVBoxLayout()

        percentage_label = QLabel("%")
        percentage_label2 = QLabel("%")
        mm_label = QLabel("mm")
        mm_label2 = QLabel("mm")
        lower_limit_label = QLabel("Lower Limit")
        upper_limit_label = QLabel("Upper Limit")
        position_label = QLabel("Position")
        step_label = QLabel("Step")

        # double spin box (float input) of lower limit, position and upper limit of motor 
        # in percentages and physical units - mm
        # if one of these boxes are set, corresponding one in mm or percentage changes 
        # accordingly with function lower_limit_changed(), position_value_changed(), upper_limit_changed()
        self.percentage_lower_limit_spinbox = QDoubleSpinBox()
        self.percentage_lower_limit_spinbox.setMinimum(0)
        self.percentage_lower_limit_spinbox.setMaximum(100)
        self.percentage_lower_limit_spinbox.valueChanged.connect(lambda: self.lower_limit_changed(True))
        self.percentage_position_spinbox = QDoubleSpinBox()
        self.percentage_position_spinbox.setMinimum(0)
        self.percentage_position_spinbox.setMaximum(100)
        self.percentage_position_spinbox.valueChanged.connect(lambda: self.position_value_changed(True))
        self.percentage_upper_limit_spinbox = QDoubleSpinBox()
        self.percentage_upper_limit_spinbox.setMinimum(0)
        self.percentage_upper_limit_spinbox.setMaximum(100)
        self.percentage_upper_limit_spinbox.setValue(100)
        self.percentage_upper_limit_spinbox.valueChanged.connect(lambda: self.upper_limit_changed(True))

        
        self.mm_lower_limit_spinbox = QDoubleSpinBox()
        self.mm_lower_limit_spinbox.setMinimum(0)
        self.mm_lower_limit_spinbox.setMaximum(self.range)
        self.mm_lower_limit_spinbox.valueChanged.connect(lambda: self.lower_limit_changed(False))
        self.mm_position_spinbox = QDoubleSpinBox()
        self.mm_position_spinbox.setMinimum(0)
        self.mm_position_spinbox.setMaximum(self.range)
        self.mm_position_spinbox.valueChanged.connect(lambda: self.position_value_changed(False))
        self.mm_upper_limit_spinbox = QDoubleSpinBox()
        self.mm_upper_limit_spinbox.setMinimum(0)
        self.mm_upper_limit_spinbox.setMaximum(self.range)
        self.mm_upper_limit_spinbox.setValue(self.range)
        self.mm_upper_limit_spinbox.valueChanged.connect(lambda: self.upper_limit_changed(False))

        # plus/minus button for increase/decrease in position by defined step size
        self.plus_button = QPushButton("+")
        self.plus_button.setFixedSize(40, 40)
        self.plus_button.clicked.connect(lambda: self.step_movement_handler(0))
        self.plus_button.setEnabled(False)
        self.plus_button.setStyleSheet("""
        QPushButton {
            font-family: "Gill Sans Ultra Bold";
            color: rgb(0, 114, 196);
            font-size: 18px;
            padding:10px;
            border: 1px solid rgb(0, 114, 196);
            border-radius:20px;
        }
        QPushButton:hover {
            background-color:rgba(43, 167, 255, 0.25);                          
        }
        QPushButton:disabled {
            color:rgb(129, 160, 182);                              
        }
        """)
        self.minus_button = QPushButton("-")
        self.minus_button.setFixedSize(40, 40)
        self.minus_button.clicked.connect(lambda: self.step_movement_handler(1))
        self.minus_button.setEnabled(False)
        self.minus_button.setStyleSheet("""
        QPushButton {
            font-family: "Gill Sans Ultra Bold";
            color: rgb(0, 114, 196);
            font-size: 18px;
            padding:10px;
            border: 1px solid rgb(0, 114, 196);
            border-radius:20px;
        }
        QPushButton:hover {
            background-color:rgba(43, 167, 255, 0.25);                          
        }
        QPushButton:disabled {
            color:rgb(129, 160, 182);                              
        }
        """)
        self.percentage_step = QDoubleSpinBox()
        self.percentage_step.valueChanged.connect(lambda: self.step_value_changed(True))
        self.mm_step = QDoubleSpinBox()
        self.mm_step.valueChanged.connect(lambda: self.step_value_changed(False))

        # adding all defined widgets to action_grid
        action_grid.addWidget((lower_limit_label), 0, 0)
        action_grid.addWidget((position_label), 0, 1)
        action_grid.addWidget((upper_limit_label), 0, 2)

        action_grid.addWidget((self.percentage_lower_limit_spinbox), 1, 0)
        action_grid.addWidget((self.percentage_position_spinbox), 1, 1)
        action_grid.addWidget((self.percentage_upper_limit_spinbox), 1, 2)

        action_grid.addWidget((self.mm_lower_limit_spinbox), 2, 0)
        action_grid.addWidget((self.mm_position_spinbox), 2, 1)
        action_grid.addWidget((self.mm_upper_limit_spinbox), 2, 2)

        action_grid.addWidget((percentage_label), 1, 3)
        action_grid.addWidget((mm_label), 2, 3)

        action_grid.addWidget((step_label), 3, 0)
        action_grid.addWidget((self.percentage_step), 3, 1)
        action_grid.addWidget((self.mm_step), 4, 1)
        action_grid.addWidget((percentage_label2), 3, 2)
        action_grid.addWidget((mm_label2), 4, 2)

        # creating enter button, upon pressing moves motor to set position
        self.enter_button = QPushButton(" Enter")
        self.enter_button.setIcon(QIcon("icons/keyboard-enter"))
        self.enter_button.setIconSize(QSize(40,40))
        #self.enter_button.setStyleSheet("background-color: rgba(54, 206, 54, 200);")
        self.enter_button.setStyleSheet("""                                                
        QPushButton {
            background-color: rgba(54, 206, 54, 200);
            border: 1px solid black;
            padding:5px;
            border-radius: 12px;
            }

        QPushButton:hover {
            background-color: rgba(53, 173, 53, 200)                                    
            }
        """)
        
        #self.enter_button.setStyleSheet("background-color: rgb(54, 206, 54);")
        self.enter_button.clicked.connect(self.enter_was_pressed)
        self.enter_button.setEnabled(False)

        action_grid.addWidget((self.enter_button), 3, 3, 2, 1)

        action_layout.addLayout(action_grid)
        action_hline = QFrame(self)
        action_hline.setStyleSheet("color: rgb(0, 0, 0);")
        action_hline.setFrameShape(QFrame.Shape.VLine)
        action_hline.setFrameShadow(QFrame.Shadow.Sunken)
        action_layout.addWidget(action_hline)

        step_layout.addWidget(self.plus_button)
        step_layout.addWidget(self.minus_button)

        action_layout.addLayout(step_layout)
        
        main_vertical_layout.addLayout(action_layout)

        hline_2 = QFrame(self)
        hline_2.setStyleSheet("color: rgb(0, 0, 0);")
        hline_2.setFrameShape(QFrame.Shape.HLine)
        hline_2.setFrameShadow(QFrame.Shadow.Sunken)
        main_vertical_layout.addWidget(hline_2)
    
        # arrow layout at the bottom left side of application
        arrow_layout = QHBoxLayout()
        arrow_layout.addSpacing(20)
        # left arrow - while pressed motor moves to the left (command_left() in ximc library)
        self.arrow_left_button = QPushButton("")
        self.arrow_left_button.setIcon(QIcon("icons/arrow-180.png"))
        self.arrow_left_button.setIconSize(QSize(60,24))
        #self.arrow_left_button.setIconSize(QSize(120,60))
        self.arrow_left_button.pressed.connect(lambda: self.arrows_interaction(True, 'left'))
        self.arrow_left_button.released.connect(lambda: self.arrows_interaction(False))
        self.arrow_left_button.setEnabled(False)
        self.arrow_left_button.setStyleSheet("""                                                
        QPushButton {
            border:1px solid black;
            padding: 3px;
            border-radius: 10px;
            }
        QPushButton:hover {
            background-color: rgba(0, 0, 0, 0.05);                                   
            }
        """)
        arrow_layout.addWidget(self.arrow_left_button)

        # right arrow - while pressed motor moves to the right (command_right() in ximc library)
        self.arrow_right_button = QPushButton("")
        self.arrow_right_button.setIcon(QIcon("icons/arrow.png"))
        self.arrow_right_button.setIconSize(QSize(60,24))
        self.arrow_right_button.pressed.connect(lambda: self.arrows_interaction(True, 'right'))
        self.arrow_right_button.released.connect(lambda: self.arrows_interaction(False))
        self.arrow_right_button.setEnabled(False)
        self.arrow_right_button.setStyleSheet("""                                                
        QPushButton {
            border:1px solid black;
            padding: 3px;
            border-radius: 10px;
            }
        QPushButton:hover {
            background-color: rgba(0, 0, 0, 0.05);                                   
            }
        """)
        arrow_layout.addWidget(self.arrow_right_button)

        # button "Store Poses" next to arrows
        self.store_pose_button = QPushButton("Store Current Pose")
        #self.store_pose_button.setStyleSheet("background-color: rgb(71, 220, 250); padding:5px;")
        self.store_pose_button.setStyleSheet("""                                                
        QPushButton {
            background-color: rgb(71, 220, 250);
            border: 1px solid black;
            padding:8px;
            border-radius: 8px;
            }

        QPushButton:hover {
            background-color: rgb(0, 200, 255)                                    
            }
        """)
        self.store_pose_button.clicked.connect(self.store_pose)
        self.store_pose_button.setEnabled(False)
        arrow_layout.addWidget(self.store_pose_button, alignment=Qt.AlignmentFlag.AlignRight)

        main_vertical_layout.addLayout(arrow_layout)

        # label for displaying messages to the user
        self.status_label = QLabel()
        main_vertical_layout.addWidget(self.status_label)

        main_vertical_layout.addStretch()
 
        main_vertical_layout.setSpacing(10)

        # main layout of the app containing every widget and layout
        self.main_layout = QHBoxLayout()

        # layout for displayed Poses in the right side of the application
        self.poses_layout = QVBoxLayout()

        self.poses_layout.setContentsMargins(0, 0, 8, 2)
        # alternative to .addStretch() that can be deleted and placed elsewhere
        # makes it so window can be resized, but widgets don't scale with it
        self.stretch =QSpacerItem(10,10,QSizePolicy.Policy.Minimum,QSizePolicy.Policy.Expanding)
        self.poses_layout.addItem(self.stretch)

        self.main_layout.addLayout(main_vertical_layout)

        main_vline = QFrame(self)
        main_vline.setStyleSheet("color: rgb(0, 0, 0);")
        main_vline.setFrameShape(QFrame.Shape.VLine)
        main_vline.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(main_vline)

        self.poses_widget = QWidget()
        self.poses_widget.setLayout(self.poses_layout)
        self.main_layout.addWidget(self.poses_widget)

        # alternative to .addStretch() that can be deleted and placed elsewhere
        # makes it so window can be resized, but widgets don't scale with it
        self.main_stretch =QSpacerItem(10,10,QSizePolicy.Policy.MinimumExpanding,QSizePolicy.Policy.MinimumExpanding)
        self.main_layout.addItem(self.main_stretch)

        self.setLayout(self.main_layout)

        # Thread pool for starting and managing threads
        self.threadpool = QThreadPool()

        # for first created tab with no argument it just runs function self.find_devices(), 
        # for other created tabs runs function self.create_table with passed argument from 
        # initialization
        if self.device == None:
            self.find_devices()
        else:
            self.create_table(self.device)


    # getter and setter for variable 't' - sends signal valueChanged if when value of 't' 
    # is changed - more controllers found
    @property
    def t(self):
        return self._t

    @t.setter
    def t(self, value):
        self._t = value
        self.valueChanged.emit(value)

    # finds devices and returns dictionary with info about them - used in self.create_table()
    def return_device_info(self):
        devices = ximc.enumerate_devices(
        ximc.EnumerateFlags.ENUMERATE_ALL_COM |
        ximc.EnumerateFlags.ENUMERATE_PROBE)

        if len(devices) == 0:
            return None
        
        self.t = len(devices)
        self.devices = devices
        
        self.device = devices[0]
        return self.device

    # creates table with info about connected controller
    def create_table(self, device):
        # if no device is passed as argument, displays message and enables to press button "Try Again"
        if device == None:
            self.finding_devices_label.setText("No controller was found.")
            self.try_again_button.setEnabled(True)
        else:
            self.finding_devices_label.setText("Controller was found")
            self.searching_layout.addWidget(QLabel("Set Corresponding Motor:"))
            # list of motors which user can choose from
            self.combobox = ComboBox()
            self.combobox.addItems(["Iris", "Up-Down", "Forwards-Backwards"])
            self.combobox.popupAboutToBeShown.connect(self.update_motor_list)
            # when selection is changed, ranges of boxes in action_layout scale accordingly
            self.combobox.currentIndexChanged.connect(self.motor_changed)
            self.combobox.setStyleSheet("""
            QComboBox {
                border: 1px solid black;
                padding: 3px;
                border-radius:8px;
                }
            
            QComboBox:hover {
                background-color:rgba(0, 0, 0, 0.05)                            
            }
                    
            QListView {
                border: 1px solid black;
                border-radius:
            }
            QComboBox::drop-down
            {
            border: none;
            }
            QComboBox::down-arrow {
                image: url(icons/arrow-270-medium.png);                      
            }
            QComboBox::drop-down:hover {
                background-color: rgba(0, 0, 0, 0.1); 
            }
            """)
            self.searching_layout.addWidget(self.combobox)
            self.status_label.setText("")
            # enable various buttons because connection with controller has been established
            self.arrow_left_button.setEnabled(True)
            self.arrow_right_button.setEnabled(True)
            self.enter_button.setEnabled(True)
            self.plus_button.setEnabled(True)
            self.minus_button.setEnabled(True)
            self.calibrate_button.setEnabled(True)
            self.store_pose_button.setEnabled(True)
            # pass device uri to self.uri variable
            self.uri = device["uri"]
            # connects to a controller with uri and runs function open_device() after which 
            # commands to it can be passed
            self.axis = ximc.Axis(self.uri)
            self.axis.open_device()
            
            # updating selection of motors, current position displayed and poses stored
            self.update_motor_list()
            self.update_position()
            self.update_poses()

            # creation of table with information about controller extracted from 
            # device dictionary
            label00 = QLabel("Controller Name:")
            label10 = QLabel("Manufacturer:")
            label20 = QLabel("Product Description:")
            label30 = QLabel("Serial Number:")
            label01 = QLabel(device["ControllerName"])
            label11 = QLabel(device["Manufacturer"])
            label21 = QLabel(device["ProductDescription"])
            label31 = QLabel(str(device["device_serial"]))

            self.table.addWidget((label00), 0, 0)
            self.table.addWidget((label10), 1, 0)
            self.table.addWidget((label20), 2, 0)
            self.table.addWidget((label30), 3, 0)

            self.table.addWidget((label01), 0, 1)
            self.table.addWidget((label11), 1, 1)
            self.table.addWidget((label21), 2, 1)
            self.table.addWidget((label31), 3, 1)

    # updates displayed position in _position_spinbox based on set left boundary self.L
    # and right boundary self.R
    def update_position(self):
        absolute_position = int(self.axis.get_position().Position)
        position = float("%.2f" % ((absolute_position - self.L) / (self.R - self.L) * 100))
        self.percentage_position_spinbox.setValue(position)
    
    # updates ranges based on currently selected motor
    def update_ranges(self):
        absolute_position = int(self.axis.get_position().Position)
        position = float("%.2f" % ((absolute_position - self.L) / (self.R - self.L) * 100))
        self.percentage_position_spinbox.setValue(position)
        self.mm_lower_limit_spinbox.setMaximum(self.range)
        self.mm_position_spinbox.setMaximum(self.range)
        self.mm_upper_limit_spinbox.setMaximum(self.range)
        self.mm_upper_limit_spinbox.setValue(self.range)

    # starts process of finding device in different thread, the result of self.return_device_info() 
    # is sent to function self.create_table(device)
    def find_devices(self):
        self.finding_devices_label.setText("Looking for controller...")
        worker = Worker(self.return_device_info)
        worker.signals.result.connect(self.create_table)

        self.threadpool.start(worker)

    # function that is ran when enter_button or Enter on keyboard is pressed
    def enter_was_pressed(self):
        # if this function is started by keyboard Enter press, it can only 
        # run if enter_button is enabled
        if not self.enter_button.isEnabled():
            return
        # checking if current position is within limits to be able to move
        position = self.percentage_position_spinbox.value()
        lower_limit = self.percentage_lower_limit_spinbox.value()
        upper_limit = self.percentage_upper_limit_spinbox.value()
        if not (lower_limit <= position <= upper_limit):
            self.status_label.setText("Reached Set Limit")
            self.update_position()
            return
        # calling self.move_to_position in different thread
        simple_worker = Simple_Worker(self.move_to_position, position)
        # error for when controller was disconnected
        simple_worker.signals.error.connect(self.error_handler)

        self.threadpool.start(simple_worker)

    # catches error that occurs when user tries to move with motor when controller was disconnected
    def error_handler(self):
        # displaying info message about current status
        self.status_label.setText("Controller was disconnected")
        self.finding_devices_label.setText("No controller was found.")
        # disabling buttons for moving with controller
        self.try_again_button.setEnabled(True)
        self.arrow_left_button.setEnabled(False)
        self.arrow_right_button.setEnabled(False)
        self.enter_button.setEnabled(False)
        self.plus_button.setEnabled(False)
        self.minus_button.setEnabled(False)
        self.calibrate_button.setEnabled(False)
        self.store_pose_button.setEnabled(False)
        # deleting info about controller in self.table
        for i in reversed(range(self.table.count())): 
            self.table.itemAt(i).widget().setParent(None)

    # moves to set position using functions from ximc library
    def move_to_position(self, position):
        self.status_label.setText("Launching Movement")

        # calculating new position
        k = int((self.R - self.L) * (position/100) + self.L)
        new_position = k if self.R >= k >= self.L else self.L if k < self.R else self.R
        # command for moving with connected motor
        self.axis.command_move(new_position, 0)
        self.axis.command_wait_for_stop(100)
        self.axis.command_stop()
        # displaying status message
        self.status_label.setText("Launching Movement\nStopping Movement")
    
    # function that handles pressing and releasing arrow buttons
    # if arrows are pressed, first argument is True, when released it is False
    # second argument is either 'left' or 'right'
    def arrows_interaction(self, *args):
        if args[0]:
            direction = args[1]
            if direction == 'left':
                self.status_label.setText("Moving Left")
            else:
                self.status_label.setText("Moving Right")
        else:
            self.status_label.setText("Stopping Movement")
        # starts movement in different thread, passes down the same arguments
        simple_worker = Simple_Worker(self.arrow_movement, *args)
        # error handler for when controller is disconnected during movement
        simple_worker.signals.error.connect(self.error_handler)

        self.threadpool.start(simple_worker)

    # if arrows are pressed, first argument is True, when released it is False
    # second argument is either 'left' or 'right'
    def arrow_movement(self, *args):
        if args[0]:
            direction = args[1]
            if direction == 'left':
                self.axis.command_left()
            else:
                self.axis.command_right()
        else:
            self.axis.command_stop()

        # position displayed in _position_spinbox is updated
        self.update_position()

    # handles Enter key press and "a" & "d" key press
    def keyPressEvent(self, qKeyEvent):
        if qKeyEvent.key() == Qt.Key.Key_Return: 
            self.enter_was_pressed()
        elif self.enter_button.isEnabled():
            # moves left when "a" is pressed
            if qKeyEvent.key() == 65:
                self.arrows_interaction(True, 'left')
            # moves right when "d" is pressed
            elif qKeyEvent.key() == 68:
                self.arrows_interaction(True, 'right')
    
    # stops motor movement when "a" or "d" is released
    def keyReleaseEvent(self, qKeyEvent):
        if self.enter_button.isEnabled():
            if qKeyEvent.key() in [65, 68]:
                self.arrows_interaction(False)

    # next couple of functions change value displayed in mm when percentage value is changed 
    # and vice versa
    def position_value_changed(self, bool):
        if bool:
            self.mm_position_spinbox.setValue(self.percentage_position_spinbox.value() * self.range / 100)
        else:
            self.percentage_position_spinbox.setValue(self.mm_position_spinbox.value() * 100 / self.range)

    def step_value_changed(self, bool):
        if bool:
            self.mm_step.setValue(self.percentage_step.value() * self.range / 100)
        else:
            self.percentage_step.setValue(self.mm_step.value() * 100 / self.range)

    # when '+' or '-' button is pressed, this function checks if the new position is within limits 
    # and calculates new position based on set resolution of connected motor and passes it to 
    # function step_movement, argument is for increase/decrease by step
    def step_movement_handler(self, bool):
        # w, h = self.size().width(), self.size().height()
        # print(f"{w}, {h}")
        # only allows movement if enter_button is enabled - controller is connected
        if not self.enter_button.isEnabled():
            return
        # checking if current position is within limits to be able to move
        # '+' button press passes 0 and '-' button press passes 1
        position = self.percentage_position_spinbox.value() + (-1)**(bool) * self.percentage_step.value()
        lower_limit = self.percentage_lower_limit_spinbox.value()
        upper_limit = self.percentage_upper_limit_spinbox.value()
        if not (lower_limit <= position <= upper_limit):
            self.status_label.setText("Reached Set Limit")
            self.update_position()
            return
        
        # calculating new position based on resolution of 
        mm_to_move = self.mm_step.value()
        points_to_move = round((-1)**(bool)*mm_to_move * self.resolution)
        new_position = int(self.axis.get_position().Position) + points_to_move
        # starting step_movement function in a new thread
        simple_worker = Simple_Worker(self.step_movement, new_position)
        simple_worker.signals.error.connect(self.error_handler)
        self.threadpool.start(simple_worker)

    def step_movement(self, new_position):
        # displaying status message
        self.status_label.setText("Launching Movement")
        # commands for moving with connected motor
        self.axis.command_move(new_position, 0)
        self.axis.command_wait_for_stop(100)
        self.axis.command_stop()
        # displaying status message
        self.status_label.setText("Launching Movement\nStopping Movement")
        # updates current position after moving by a set step
        self.update_position()

    # def step_movement(self, bool):
    #     self.percentage_position_spinbox.setValue(self.percentage_position_spinbox.value() + (-1)**(bool) * self.percentage_step.value())
    #     self.enter_was_pressed()
    
    def lower_limit_changed(self, bool):
        if bool:
            self.mm_lower_limit_spinbox.setValue(self.percentage_lower_limit_spinbox.value() * self.range / 100)
        else:
            self.percentage_lower_limit_spinbox.setValue(self.mm_lower_limit_spinbox.value() * 100 / self.range)     
    
    def upper_limit_changed(self, bool):
        if bool:
            self.mm_upper_limit_spinbox.setValue(self.percentage_upper_limit_spinbox.value() * self.range / 100)
        else:
            self.percentage_upper_limit_spinbox.setValue(self.mm_upper_limit_spinbox.value() * 100 / self.range)
    
    # stores current position, limits and set step in a text file
    def store_pose(self):
        # takes current time, limits, position and step
        current_time = datetime.datetime.now().replace(microsecond=0)
        lower_limit = self.percentage_lower_limit_spinbox.value()
        position = self.percentage_position_spinbox.value()
        upper_limit = self.percentage_upper_limit_spinbox.value()
        step = self.percentage_step.value()
        # string which will stored in a text file
        pose = f"Lower_limit: {lower_limit}\tPosition: {position}\tUpper_limit: {upper_limit}\tStep: {step}\tDate_time: {current_time}"
        # default string for a name of stored pose, that will be displayed in the application
        pose_data = f"{lower_limit} < {position} < {upper_limit}, Step: {step}    Date: {current_time}"
        
        # creating dialog window for text input
        name, bool = QInputDialog.getText(self, "Name Dialog", "Enter name of this pose:", text=pose_data)

        # if dialog window is closed, return
        if not bool:
            return

        # storing pose in a text file
        filename = f"stored_poses/{self.combobox.currentText()}_stored_poses.txt"
        with open(filename, 'a') as f:
            f.write(f"{name};{pose}\n")
        
        self.status_label.setText("Pose Stored")
        # loads new pose into app's UI
        self.update_poses()

    # function connected to toggle button that shows and hides "Stored Poses" section 
    def hide_show_poses(self, bool):
        if bool:
            self.poses_widget.hide()
            # creates new button that shows "Stored Poses" section
            show_poses_button = QPushButton("")
            show_poses_button.setIcon(QIcon("icons/eye.png"))
            show_poses_button.setStyleSheet("padding: 6px; border: none")
            show_poses_button.setIconSize(QSize(8, 8))
            show_poses_button.clicked.connect(lambda: self.hide_show_poses(False))

            # putting new button before QSpacerItem
            self.main_layout.removeItem(self.main_stretch)
            self.main_layout.addWidget(show_poses_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.main_layout.addItem(self.main_stretch)

        else:
            # when show_poses_button is pressed, "Stored Poses" section is showed and 
            # show_poses_button is deleted
            self.main_layout.itemAt(self.main_layout.count()-2).widget().setParent(None)
            self.poses_widget.show()

    # deletes current poses displayed in app and loads them again from a text file
    def update_poses(self):
        # deleting current poses
        self.poses_layout.removeItem(self.stretch)
        for i in reversed(range(self.poses_layout.count())):
            self.poses_layout.itemAt(i).widget().setParent(None)

        first_row_container = QWidget()
        first_row_container.setStyleSheet("background-color: rgb(225, 225, 225);")
        poses_first_row = QHBoxLayout()
        poses_first_row.setContentsMargins(0, 0, 0, 0)
        # button for hiding "Stored Poses" section
        self.hide_poses_button = QPushButton("")
        self.hide_poses_button.setIcon(QIcon("icons/eye-close.png"))
        self.hide_poses_button.setIconSize(QSize(8, 8))
        self.hide_poses_button.clicked.connect(lambda: self.hide_show_poses(True))
        self.hide_poses_button.setStyleSheet("background-color: rgb(255, 255, 255); border: none; background-color: rgb(225, 225, 225); padding: 6px;")
        #self.poses_layout.addWidget(self.hide_poses_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        poses_first_row.addWidget(self.hide_poses_button, alignment=Qt.AlignmentFlag.AlignLeft)
        stored_poses_label = QLabel("Stored Poses")
        stored_poses_label.setStyleSheet("background-color: rgb(225, 225, 225); padding-left:70px; text-align: center;")
        stored_poses_label.setFixedWidth(260)
        #self.poses_layout.addWidget(stored_poses_label, alignment=Qt.AlignmentFlag.AlignTop)
        poses_first_row.addWidget(stored_poses_label)
        first_row_container.setLayout(poses_first_row)
        self.poses_layout.addWidget(first_row_container)

        # loads pose based on currently selected motor
        combobox_text = self.combobox.currentText()
        if combobox_text == "":
            return
        filename = f"stored_poses/{combobox_text}_stored_poses.txt"
        with open(filename) as f:
            poses = f.read().split("\n")[::-1]

        if poses == ['']:
            self.stretch = QSpacerItem(10,10,QSizePolicy.Policy.Minimum,QSizePolicy.Policy.Expanding)
            self.poses_layout.addItem(self.stretch)
            return
        
        self.poses_list = {}

        # loads data from text file to variables for each line
        for i in range(len(poses[1:])):
            # loads only last ten stored poses
            if i > 9:
                break
            
            pose = poses[1:][i]
            name = pose.split(";")[0]
            pose = pose.split(";")[1]
            pose = pose.split('\t')
            date = pose[4].split(' ')[1] + ' ' + pose[4].split(' ')[2]
            pose = [x.split(' ')[1] for x in pose[:-1]]

            lower_limit, position, upper_limit, step = pose[0], pose[1], pose[2], pose[3]

            # new pose is stored in the UI as a button that can be selected
            new_pose = QPushButton(name)
            pose_data = f"{lower_limit} < {position} < {upper_limit}, Step: {step}    Date: {date}"
            #new_pose.setStyleSheet("background-color: rgb(245, 245, 245);font-size: 8pt; text-align:center; padding:3px;")
            new_pose.setStyleSheet("""
            QPushButton {
                font-size: 8pt;
                text-align:center;
                padding:3px;
                border: 1px solid black;
                border-radius: 5px;                      
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05)           
            }
            """)
            new_pose.setCheckable(True)
            new_pose.setFixedWidth(290)
            new_pose.setToolTip(name)
            new_pose.pressed.connect(self.checking_pose_buttons)
            new_pose.released.connect(self.set_checked_color)
            # storing every pose in dictionary
            self.poses_list[new_pose] = pose_data

            self.poses_layout.addWidget(new_pose, alignment=Qt.AlignmentFlag.AlignTop)

        # adding load button which sets selected pose
        self.load_poses_button = QPushButton("Load Pose")
        self.load_poses_button.setStyleSheet("""                                                
        QPushButton {
            background-color: rgb(255, 178, 102);
            border: 1px solid black;
            padding:5px;
            border-radius: 8px;
            }

        QPushButton:hover {
            background-color: rgb(250, 150, 50);                                   
            }
        """)
        self.load_poses_button.clicked.connect(self.load_pose)
        self.poses_layout.addWidget(self.load_poses_button, alignment=Qt.AlignmentFlag.AlignRight)
        # QSpacerItem for keeping fixed layout size
        self.stretch = QSpacerItem(10,10,QSizePolicy.Policy.Minimum,QSizePolicy.Policy.Expanding)
        self.poses_layout.addItem(self.stretch)
            
    # when pose is selected, unchecks previously selected pose
    def checking_pose_buttons(self):
        for pose in self.poses_list.keys():
            pose.setChecked(False)

    def set_checked_color(self):
        for pose in self.poses_list.keys():
            if pose.isChecked():
                pose.setStyleSheet("""
                QPushButton {
                    background-color: rgba(193, 193, 193, 0.5);
                    font-size: 8pt;
                    text-align:center;
                    padding:3px;
                    border: 1px solid black;
                    border-radius: 5px;                      
                }
                """)
            else:
                pose.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    font-size: 8pt;
                    text-align:center;
                    padding:3px;
                    border: 1px solid black;
                    border-radius: 5px;                      
                }
                QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05)           
                }
                """)
    # Loads selected pose
    def load_pose(self):
        # loop that finds the checked pose and extracts its data from dictionary self.poses_list
        for pose in self.poses_list.keys():
            if pose.isChecked():
                pose = self.poses_list[pose].split(',')
                values = [float(x) for x in pose[0].split(" < ")]
                lower_limit, position, upper_limit = values[0], values[1], values[2]
                step = float(pose[1].split(": ")[1].split("    ")[0])
                # setting limits, position and step based on acquired data
                self.percentage_lower_limit_spinbox.setValue(lower_limit)
                self.percentage_position_spinbox.setValue(position)
                self.percentage_upper_limit_spinbox.setValue(upper_limit)
                self.percentage_step.setValue(step)

                self.status_label.setText("Pose Loaded")

    # emit a signal to MainWindow when "Try Again" button is clicked
    def emit_load_signal(self):
        self.tryAgainPressed.emit()

    # this function is called when new motor is selected in combobox, set left 
    # and right boundary and updates range and position
    def motor_changed(self, index):
        # if it is not a default motor, IndexError occurs
        try:
            self.R = self.right_boundaries[index]
            self.L = self.left_boundaries[index]
        except IndexError:
            # getting calibration data from a text file
            with open("motors/motor_calibration.txt") as f:
                calibration_data = f.read().split('\n')
            bool = True
            # checking if currently selected motor's calibration data are stored already
            for i in range(len(calibration_data)):
                if calibration_data[i].split(": ")[0] == self.combobox.currentText():
                    bool = False
                    boundaries = calibration_data[i].split(": ")[1].split(';')
                    # setting left and right boundary
                    self.R = float(boundaries[1].split('=')[1])
                    self.L = float(boundaries[0].split('=')[1])

            # if currently selected motor's calibration data was not found, 
            # displays message asking user to calibrate it first
            if bool:
                self.status_label.setText("You Need to Calibrate This Motor")

        # updates ranges and scales positions
        self.range = self.ranges[index]
        self.resolution = self.resolutions[index]
        self.update_ranges()
        # displays poses for currently selected motor
        self.update_poses()

    # displays dialog window, which asks user for data input
    def add_motor(self):
        # creating new dialog window that asks for data about new motor that will be added
        self.add_dialog = QDialog(self)
        self.add_dialog.setWindowTitle("Add New Motor")
        
        dialog_v_layout = QVBoxLayout()

        dialog_grid = QGridLayout()

        # creating grid containing input for name, range and resolution
        name_label = QLabel("Name: ")
        range_label = QLabel("Range in mm: ")
        res_label = QLabel("Resolution, steps per mm: ")
        self.name_input = QLineEdit()
        #self.name_input.setStyleSheet("border: 1px solid black; padding: 3px; border-radius: 8px;")
        self.name_input.setStyleSheet("""
        QLineEdit {
            border: 1px solid black;
            padding: 3px;
            border-radius: 8px;                              
        }
        QLineEdit:focus {
            border-color: rgb(22, 96, 149);
            }
        """)
        self.range_input = QLineEdit()
        self.range_input.setStyleSheet("""
        QLineEdit {
            border: 1px solid black;
            padding: 3px;
            border-radius: 8px;                              
        }
        QLineEdit:focus {
            border-color: rgb(22, 96, 149);
            }
        """)
        self.range_input.setValidator(QDoubleValidator())
        self.res_input = QLineEdit()
        self.res_input.setStyleSheet("""
        QLineEdit {
            border: 1px solid black;
            padding: 3px;
            border-radius: 8px;                              
        }
        QLineEdit:focus {
            border-color: rgb(22, 96, 149);
            }
        """)
        self.res_input.setValidator(QDoubleValidator())
        dialog_grid.addWidget((name_label), 0, 0)
        dialog_grid.addWidget((self.name_input), 0, 1)
        dialog_grid.addWidget((range_label), 1, 0)
        dialog_grid.addWidget((self.range_input), 1, 1)
        dialog_grid.addWidget((res_label), 2, 0)
        dialog_grid.addWidget((self.res_input), 2, 1)

        dialog_v_layout.addLayout(dialog_grid)
        # Add button that calls function self.motor_added()
        add_button = QPushButton("Add")
        add_button.setStyleSheet("""
        QPushButton {
            background-color: rgb(66, 255, 239);
            border: 1px solid black;
            padding: 5px;
            border-radius: 8px;                        
        }
                                
        QPushButton:hover {
            background-color: rgb(63, 216, 203);                      
        }
        """)
        add_button.clicked.connect(self.motor_added)
        dialog_v_layout.addWidget(add_button, alignment=Qt.AlignmentFlag.AlignRight)

        self.add_dialog.setLayout(dialog_v_layout)

        self.add_dialog.exec()

    # stores data about new added motor to a text file
    def motor_added(self):
        name = self.name_input.text()
        range = self.range_input.text()
        res = self.res_input.text()
        # if any of the input fields are left empty, displays message box asking user to 
        # fill out all inputs
        if any([x == "" for x in [name, range, res]]):
            QMessageBox.critical(self.add_dialog, "Oh Dear!", "Please fill out all inputs!")
            return
        
        self.add_dialog.close()
        # storing data in a text file
        with open("motors/motor_list.txt", 'a') as f:
            f.write(f"{name};{range};{res}\n")
        # creates new text file for storing poses for this new added motor
        with open(f"stored_poses/{name}_stored_poses.txt", 'w') as f:
            pass
        # updates list of motors so new motor is displayed
        self.update_motor_list()
    
    # adds motor listed in motor_list.txt
    def update_motor_list(self):
        # loading data from text file and storing it in global variables
        with open("motors/motor_list.txt") as f:
            data = f.read()
        
        data = data.split("\n")[:-1]
        try:
            self.combobox.clear()
        except AttributeError:
            return
        self.combobox.addItems(["Iris", "Up-Down", "Forwards-Backwards"])
        self.ranges = [22, 13, 20]
        self.resolutions = [102, 1000, 800]
        for dat in data:
            dat = dat.split(";")
            self.combobox.addItem(dat[0])
            self.ranges.append(float(dat[1]))
            self.resolutions.append(float(dat[2]))
        # set currently selected motor to default
        try:
            self.combobox.setCurrentIndex(self.motor_connections[self.device["device_serial"]])
        except:
            pass

    # creates worker thread to run calibration in
    def run_calibration(self):
        # display message box, so user can't move with motor during calibration
        self.wait_message_box = QMessageBox(self)
        self.wait_message_box.setIcon(QMessageBox.Icon.Warning)
        self.wait_message_box.setWindowTitle("Calibration in Process")
        self.wait_message_box.setText("Please Wait for Calibration to Finish")
        self.wait_message_box.setStandardButtons(QMessageBox.StandardButton.Abort)
        # calibration can be stopped by clicking on "Abort"
        self.wait_message_box.buttonClicked.connect(self.stop_calibration)
        # calibration only runs if this variable is set to True
        self.continue_calibrating = True
        calibration_worker = Worker(self.calibrate)
        # when finished calibrating signal is send to close warning message box
        calibration_worker.signals.finished.connect(self.close_msg_box)
        self.threadpool.start(calibration_worker)

        self.wait_message_box.exec()

    # stops calibration, called by clicking on "Abort" button in message box
    def stop_calibration(self):
        self.continue_calibrating = False
    
    # closes message box, that is displayed while calibrating a motor
    # calls self.motor_changed so new boundaries are set
    def close_msg_box(self):
        self.wait_message_box.close()
        self.motor_changed(self.combobox.currentIndex())

    # calibrates motor by going to right and left limit and storing those limits
    # in a text file
    def calibrate(self):
        k = 1
        current_position = ["", " "]
        # while loops that check if two previous position are the same - if yes it 
        # means motor has hit one of its limits
        while current_position[k] != current_position[k-1]:
            if not self.continue_calibrating:
                self.axis.command_stop()
                self.status_label.setText("Calibration Stopped")
                return
            self.axis.command_right()
            time.sleep(0.2)
            current_position.append(self.axis.get_position().Position)
            k += 1
        # storing right limit in a variable
        right_limit = current_position[-1]

        k = 1
        current_position = ["", " "]
        while current_position[k] != current_position[k-1]:
            if not self.continue_calibrating:
                self.axis.command_stop()
                self.status_label.setText("Calibration Stopped")
                return
            self.axis.command_left()
            time.sleep(0.2)
            current_position.append(self.axis.get_position().Position)
            k += 1
        # storing left limit in a variable
        left_limit = current_position[-1]

        # storing newly found limits to a text file
        with open("motors/motor_calibration.txt", 'a') as f:
            f.write(f"{self.combobox.currentText()}: Left limit={left_limit};Right limit={right_limit}\n")
        
        # stopping movement and displaying status message
        self.axis.command_stop()
        self.status_label.setText("Motor Has Been Calibrated.")

    # emits signal when this window is closed
    def closeEvent(self, event):
        self.widgetClosed.emit()

# creating an instance of MainWindow and executing the app
app = QApplication([])
window = MainWindow()
window.show()
app.exec()
