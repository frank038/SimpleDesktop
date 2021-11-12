#!/usr/bin/env python3
# Version 0.5.5

from PyQt5.QtCore import (pyqtSlot,QProcess, QCoreApplication, QTimer, QModelIndex,QFileSystemWatcher,QEvent,QObject,QUrl,QFileInfo,QRect,QStorageInfo,QMimeData,QMimeDatabase,QFile,QThread,Qt,pyqtSignal,QSize,QMargins,QDir,QByteArray,QItemSelection,QItemSelectionModel,QPoint)
from PyQt5.QtWidgets import (QStyleFactory,QTreeWidget,QTreeWidgetItem,QLayout,QHeaderView,QTreeView,QSpacerItem,QScrollArea,QTextEdit,QSizePolicy,qApp,QBoxLayout,QLabel,QPushButton,QDesktopWidget,QApplication,QDialog,QGridLayout,QMessageBox,QLineEdit,QTabWidget,QWidget,QGroupBox,QComboBox,QCheckBox,QProgressBar,QListView,QFileSystemModel,QItemDelegate,QStyle,QFileIconProvider,QAbstractItemView,QFormLayout,QAction,QMenu)
from PyQt5.QtGui import (QPainterPath,QDrag,QPixmap,QStaticText,QTextOption,QIcon,QStandardItem,QStandardItemModel,QFontMetrics,QColor,QPalette,QClipboard,QPainter,QFont)
import sys
import os
import stat
from urllib.parse import unquote, quote
import shutil
import time
import datetime
import glob
import importlib
import subprocess
import threading
from xdg.BaseDirectory import *
from xdg.DesktopEntry import *
from cfg_qt5desktop import *
if USE_MEDIA:
    import pyudev
    import dbus


class firstMessage(QWidget):
    
    def __init__(self, *args):
        super().__init__()
        title = args[0]
        message = args[1]
        self.setWindowTitle(title)
        box = QBoxLayout(QBoxLayout.TopToBottom)
        box.setContentsMargins(5,5,5,5)
        self.setLayout(box)
        label = QLabel(message)
        box.addWidget(label)
        button = QPushButton("Close")
        box.addWidget(button)
        button.clicked.connect(self.close)
        self.show()
        self.center()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

#
if not os.path.exists(os.path.join(os.path.expanduser("~") , USER_DESKTOP)):
    app = QApplication(sys.argv)
    fm = firstMessage("Info", "The folder {} doesn't exist.\nCreate one or set a new folder\nin the config file.".format(USER_DESKTOP))
    sys.exit(app.exec_())

isXDGDATAHOME = 1

if OPEN_WITH:
    try:
        import Utility.open_with as OW
    except Exception as E:
        OPEN_WITH = 0

#
# trash module
if USE_TRASH:
    try:
        import trash_module
    except Exception as E:
        app = QApplication(sys.argv)
        fm = firstMessage("Error", "Error while importing the module:\n{}".format(str(E)))
        sys.exit(app.exec_())

#
if USE_THUMB == 1:
    try:
        from pythumb import *
    except Exception as E:
        USE_THUMB = 0

############
# the mimeapps.list used by this program
if USER_MIMEAPPSLIST:
    MIMEAPPSLIST = os.path.expanduser('~')+"/.config/mimeapps.list"
else:
    MIMEAPPSLIST = "mimeapps.list"

# create an empty mimeapps.list if it doesnt exist
if not os.path.exists(MIMEAPPSLIST):
    ff = open(MIMEAPPSLIST, "w")
    ff.write("[Default Applications]\n")
    ff.write("[Added Associations]\n")
    ff.write("[Removed Associations]\n")
    ff.close()

###########
# where to look for desktop files or default locations
if xdg_data_dirs:
    xdgDataDirs = list(set(xdg_data_dirs))
else:
    xdgDataDirs = ['/usr/local/share', '/usr/share', os.path.expanduser('~')+"/.local/share"]
# consistency
if "/usr/share" not in xdgDataDirs:
    xdgDataDirs.append("/usr/share")
if os.path.expanduser('~')+"/.local/share" not in xdgDataDirs:
    xdgDataDirs.append(os.path.expanduser('~')+"/.local/share")

#### custom actions
if not os.path.exists("modules_custom"):
    try:
        os.mkdir("modules_custom")
    except:
        app = QApplication(sys.argv)
        fm = firstMessage("Error", "Cannot create the modules_custom folder. Exiting...")
        sys.exit(app.exec_())

sys.path.append("modules_custom")
mmod_custom = glob.glob("modules_custom/*.py")
list_custom_modules = []
for el in reversed(mmod_custom):
    try:
        # from python 3.4 exec_module instead of import_module
        ee = importlib.import_module(os.path.basename(el)[:-3])
        list_custom_modules.append(ee)
    except ImportError as ioe:
        app = QApplication(sys.argv)
        fm = firstMessage("Error", "Error while importing the plugin:\n{}".format(str(ioe)))
        sys.exit(app.exec_())

####
if not os.path.exists("icons"):
    app = QApplication(sys.argv)
    fm = firstMessage("Error", "The folder icons doesn't exist. Exiting...")
    sys.exit(app.exec_())

#################################

DDIR = os.path.join(os.path.expanduser("~"), USER_DESKTOP)

TRASH_PATH = os.path.join(os.path.expanduser("~"), ".local/share/Trash/files")

stopCD = 0

# desktop size
WINW = 0
WINH = 0

# special entries
special_entries = ["trash", "media", "desktop"]


#
if ICON_SIZE > ITEM_WIDTH:
    ITEM_WIDTH = ICON_SIZE

# margins
LEFT_M = LEFT_M
TOP_M = TOP_M
RIGHT_M = RIGHT_M
BOTTOM_M = BOTTOM_M
# number of columns and rows
ITEM_SPACE = int(ITEM_SPACE/2)*2
ITEM_WIDTH += ITEM_SPACE
ITEM_HEIGHT += ITEM_SPACE
num_col = 0 
num_row = 0
# reserved cells - items cannot be positioned there (type: indexes)
reserved_cells = []
# text height
ST_HEIGHT = 0


# get the folder size
def folder_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for fl in filenames:
            flp = os.path.join(dirpath, fl)
            if os.access(flp, os.R_OK):
                if os.path.islink(flp):
                    continue
                total_size += os.path.getsize(flp)
    return total_size

def convert_size(fsize2):
    if fsize2 == 0 or fsize2 == 1:
        sfsize = str(fsize2)+" byte"
    elif fsize2//1024 == 0:
        sfsize = str(fsize2)+" bytes"
    elif fsize2//1048576 == 0:
        sfsize = str(round(fsize2/1024, 3))+" KB"
    elif fsize2//1073741824 == 0:
        sfsize = str(round(fsize2/1048576, 3))+" MB"
    elif fsize2//1099511627776 == 0:
        sfsize = str(round(fsize2/1073741824, 3))+" GiB"
    else:
        sfsize = str(round(fsize2/1099511627776, 3))+" GiB"
    return sfsize  


ARCHIVE_PASSWORD=""
class MyQlist(QListView):
    def __init__(self):
        super(MyQlist, self).__init__()
        # the list of dragged items
        self.item_idx = []
        self.customMimeType = "application/x-customqt5archiver"
        
    
    def startDrag(self, supportedActions):
        item_list = []
        self.item_idx = []
        for index in self.selectionModel().selectedIndexes():
            if index.data(Qt.UserRole+1) == "file":
                filepath = os.path.join(DDIR, index.data(0))
                #
                # regular files or folders (not fifo, etc.)
                if os.path.islink(filepath) or stat.S_ISREG(os.stat(filepath).st_mode) or stat.S_ISDIR(os.stat(filepath).st_mode):
                    item_list.append(QUrl.fromLocalFile(filepath))
                    self.item_idx.append(index)
                else:
                    continue
                #
            elif index.data(Qt.UserRole+1) == "desktop":
                if len(self.selectionModel().selectedIndexes()) > 1:
                    continue
                dname = index.data(Qt.UserRole+2)[0]
                filepath = os.path.join(DDIR, dname)
                item_list.append(QUrl.fromLocalFile(filepath))
                self.item_idx.append(index)
        # 
        drag = QDrag(self)
        # 
        if len(item_list) > 1:
            if not USE_EXTENDED_DRAG_ICON:
                pixmap = QPixmap("icons/items_multi.png").scaled(ICON_SIZE, ICON_SIZE, Qt.KeepAspectRatio, Qt.FastTransformation)
            else:
                painter = None
                # number of selected items
                num_item = len(self.item_idx)
                poffsetW = X_EXTENDED_DRAG_ICON
                poffsetH = Y_EXTENDED_DRAG_ICON
                psizeW = ICON_SIZE + (min(NUM_OVERLAY, num_item) * poffsetW) - poffsetW
                psizeH = ICON_SIZE + (min(NUM_OVERLAY, num_item) * poffsetH) - poffsetH
                pixmap = QPixmap(psizeW, psizeH)
                pixmap.fill(QColor(253,253,253,0.0))
                incr_offsetW = poffsetW
                incr_offsetH = poffsetH
                items_idx_temp = self.item_idx
                #
                model = self.model()
                for i in reversed(range(min(NUM_OVERLAY, num_item))):
                    index = items_idx_temp[i]
                    # skip special entries
                    if index.data(Qt.UserRole+1) in special_entries:
                        self.item_idx.remove(index)
                        continue
                    if stat.S_ISREG(os.stat(filepath).st_mode) or stat.S_ISDIR(os.stat(filepath).st_mode) or stat.S_ISLNK(os.stat(filepath).st_mode):
                        file_icon = index.data(1)
                        pixmap1 = file_icon.pixmap(QSize(ICON_SIZE, ICON_SIZE))
                        if not painter:
                            painter = QPainter(pixmap)
                            woffset = int((ICON_SIZE - pixmap1.size().width())/2)
                            ioffset = int((ICON_SIZE - pixmap1.size().height())/2)
                            painter.drawPixmap(psizeW-ICON_SIZE+woffset, psizeH-ICON_SIZE+ioffset, pixmap1)
                        else:
                            # limit the number of overlays
                            if i < NUM_OVERLAY:
                                woffset = int((ICON_SIZE - pixmap1.size().width())/2)
                                ioffset = int((ICON_SIZE - pixmap1.size().height())/2)
                                painter.drawPixmap(psizeW-ICON_SIZE-incr_offsetW+woffset, psizeH-ICON_SIZE-incr_offsetH+ioffset, pixmap1)
                                incr_offsetW += poffsetW
                                incr_offsetH += poffsetH
                            else:
                                break
                    else:
                        continue
                if painter:
                    painter.end()
        elif len(item_list) == 1:
            try:
                index = self.item_idx[0]
                if index.data(Qt.UserRole+1) == "file":
                    filepath = os.path.join(DDIR, index.data(0))
                elif index.data(Qt.UserRole+1) == "desktop":
                    dname = index.data(Qt.UserRole+2)[0]
                    filepath = os.path.join(DDIR, dname)
                if stat.S_ISREG(os.stat(filepath).st_mode) or stat.S_ISDIR(os.stat(filepath).st_mode) or stat.S_ISLNK(os.stat(filepath).st_mode):
                    file_icon = index.data(1)
                    pixmap = file_icon.pixmap(QSize(ICON_SIZE, ICON_SIZE))
            except:
                pixmap = QPixmap("icons/empty.svg").scaled(ICON_SIZE, ICON_SIZE, Qt.KeepAspectRatio, Qt.FastTransformation)
        else:
            return
        #
        drag.setPixmap(pixmap)
        data = QMimeData()
        data.setUrls(item_list)
        drag.setMimeData(data)
        drag.setHotSpot(pixmap.rect().topLeft())
        drag.exec_(Qt.CopyAction|Qt.MoveAction|Qt.LinkAction, Qt.CopyAction)
    
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            ## the number of items to be copied must not exced the empty cells available
            # cells taken
            model_entries = self.model().rowCount()
            # total cells
            total_cells = num_col * num_row - len(reserved_cells)
            if model_entries < total_cells:
                if len(event.mimeData().urls()) < (total_cells-model_entries):
                    event.accept()
                else:
                    event.ignore()
        else:
            event.ignore()
    
    
    def dragMoveEvent(self, event):
        event.acceptProposedAction()
    
    # check it the archive is password protected
    def test_archive(self, path):
        szdata = None
        try:
            szdata = subprocess.check_output('{} l -slt -bso0 -- "{}"'.format(COMMAND_EXTRACTOR, path), shell=True)
        except:
            return 0
        #
        if szdata != None:
            szdata_decoded = szdata.decode()
            ddata = szdata_decoded.splitlines()
            if "Encrypted = +" in ddata:
                return 2
            else:
                return 1
    
    def dropEvent(self, event):
        # qt5simplearchiver
        if event.mimeData().hasFormat(self.customMimeType):
            ddata_temp = event.mimeData().data(self.customMimeType)
            ddata = str(ddata_temp, 'utf-8').split("\n")
            archive_name = ddata[0]
            # extraction mode (e or x) - item type (file or folder) - item name (with path)
            items = ddata[1:]
            #
            dest_path = DDIR
            pointedItem = self.indexAt(event.pos())
            if pointedItem.isValid():
                ifp = pointedItem.data(0)
                dest_dir = os.path.join(DDIR, ifp)
                if os.path.isdir(dest_dir):
                    if os.access(dest_dir, os.W_OK):
                        dest_path = dest_dir
                    else:
                        MyDialog("Info", "Not writable:\n{}".format(os.path.basename(ifp)), None)
            #
            if shutil.which(COMMAND_EXTRACTOR):
                try:
                    global ARCHIVE_PASSWORD
                    hasPassWord = self.test_archive(archive_name)
                    if hasPassWord == 2:
                        if not ARCHIVE_PASSWORD:
                            ARCHIVE_PASSWORD = passWord(archive_name, None).arpass
                            if not ARCHIVE_PASSWORD:
                                MyDialog("Info", "Cancelled.", None)
                                return
                    # 
                    for i in range(0, len(items), 3):
                        ttype = items[i]
                        item_type = items[i+1]
                        item_to_extract = items[i+2]
                        if item_type == "file":
                            # -aou rename the file to be copied -aot rename the file at destination - both if an item with the same name already exists
                            ret = os.system("{0} {1} '-i!{2}' {3} -y -aou -p{4} -o{5} 1>/dev/null".format(COMMAND_EXTRACTOR, ttype, item_to_extract, archive_name, ARCHIVE_PASSWORD, dest_path))
                        elif item_type == "folder":
                            ttype = "x"
                            if passWord:
                                ret = os.system("{0} {1} {2} *.* -r '{3}' -y -aou -p{4} -o{5} 1>/dev/null".format(COMMAND_EXTRACTOR, ttype, archive_name, item_to_extract, ARCHIVE_PASSWORD, dest_path))
                            else:
                                ret = os.system("{0} {1} {2} *.* -r '{3}' -y -aou -o{4} 1>/dev/null".format(COMMAND_EXTRACTOR, ttype, archive_name, item_to_extract, dest_path))
                        time.sleep(0.5)
                    ### exit codes
                    # 0 No error
                    # 1 Warning (Non fatal error(s)). For example, one or more files were locked by some other application, so they were not compressed.
                    # 2 Fatal error
                    # 7 Command line error
                    # 8 Not enough memory for operation
                    # 255 User stopped the process
                    if ret == 0:
                        MyDialog("Info", "Extracted.", None)
                    elif ret != -5:
                        MyDialog("Error", "{}".format(ret), None)
                except Exception as E:
                    MyDialog("Error", str(E), None)
            return
        #
        dest_path = DDIR
        curr_dir = QFileInfo(dest_path)
        if not curr_dir.isWritable():
            MyDialog("Info", "The current folder is not writable: "+DDIR, None)
            event.ignore()
        #
        if event.mimeData().hasUrls:
            if isinstance(event.source(), MyQlist):
                pointedItem = self.indexAt(event.pos())
                #
                if pointedItem.isValid():
                    ifp = os.path.join(DDIR, pointedItem.data(0))
                    #
                    if os.path.isdir(ifp):
                        for uurl in event.mimeData().urls():
                            if uurl.toLocalFile() == ifp:
                                event.ignore()
                                break
                        else:
                            event.acceptProposedAction()
                            self.dropEvent2(event)
                    # the recycle bin
                    elif pointedItem.data(Qt.UserRole+1) == "trash":
                        event.acceptProposedAction()
                        self.trashItem(event.mimeData().urls())
                    # the desktop file
                    elif pointedItem.data(Qt.UserRole+1) == "desktop":
                        # some items have been moved around the desktop
                        event.ignore()
                        # one item only
                        if len(self.item_idx) == 1:
                            self.dropEvent3(event)
                    else:
                        event.ignore()
                else:
                    # some items have been moved around the desktop
                    event.ignore()
                    # one item only
                    if len(self.item_idx) == 1:
                        self.dropEvent3(event)
            else:
                event.accept()
                filePathsTemp = []
                # web address list - not used
                webPaths = []
                #
                for uurl in event.mimeData().urls():
                    # check if the element is a local file
                    if uurl.isLocalFile():
                        filePathsTemp.append(str(uurl.toLocalFile()))
                    else:
                        webUrl = uurl.url()
                        if webUrl[0:5] == "http:" or webUrl[0:6] == "https:":
                            webPaths.append(webUrl)
                #
                filePaths = filePathsTemp
                # if not empty
                if filePaths:
                    pointedItem = self.indexAt(event.pos())
                    #
                    if pointedItem.isValid():
                        ifp = os.path.join(DDIR, pointedItem.data(0))
                        if os.path.isdir(ifp):
                            if os.access(ifp, os.W_OK):
                                PastenMerge(ifp, event.proposedAction(), filePaths, None)
                            else:
                                MyDialog("Info", "The following folder in not writable: "+DDIR, None)
                                return
                        else:
                            PastenMerge(dest_path, event.proposedAction(), filePaths, None)
                    else:
                        PastenMerge(dest_path, event.proposedAction(), filePaths, None)
                else:
                    event.ignore()
        else:
            event.ignore()
    
    
    # Delete
    def trashItem(self, urls):
        if urls:
            list_items = []
            for uurl in urls:
                list_items.append(str(uurl.toLocalFile()))
            #
            dialogList = ""
            for item in list_items:
                dialogList += os.path.basename(item)+"\n"
            ret = retDialogBox("Question", "Do you really want to move these items to the trashcan?", "", dialogList, None)
            #
            if ret.getValue():
                TrashModule(list_items, self)
    
    
    # dropEvent - some items have been moved around the desktop
    def dropEvent3(self, event):
        # already occupied cells
        cells_taken = reserved_cells[:]
        desktop_items = []
        cells_taken_temp = []
        #
        with open("items_position", "r") as ff:
            cells_taken_temp = ff.readlines()
        #
        for iitem in cells_taken_temp:
            c,r,n = iitem.split("/")
            cells_taken.append([int(c), int(r)])
            desktop_items.append([int(c), int(r), n.strip("\n")])
        # calculate the cell
        x = int(event.pos().x()/ITEM_WIDTH) * ITEM_WIDTH + LEFT_M
        y = int(event.pos().y()/ITEM_HEIGHT) * ITEM_HEIGHT + TOP_M
        col_x = int((x)/ITEM_WIDTH)
        col_y = int((y)/ITEM_HEIGHT)
        #
        if [col_x, col_y] in cells_taken:
            event.ignore()
            # reset
            cells_taken = []
            desktop_items = []
            cells_taken_temp = []
            self.item_idx = []
            return
        if col_x <= num_col-1 and col_y <= num_row-1:
            self.setPositionForIndex(QPoint(x, y) , self.item_idx[0])
        else:
            cells_taken = []
            desktop_items = []
            cells_taken_temp = []
            self.item_idx = []
            return
        # rebuild the file
        itemIdx = self.item_idx[0]
        custom_data = itemIdx.data(Qt.UserRole+1)
        if custom_data == "file":
            item_name = itemIdx.data(0)
        elif custom_data == "desktop":
            item_name = itemIdx.data(Qt.UserRole+2)[0]
        # 
        with open("items_position", "w") as ff:
            for iitem in desktop_items:
                iname = iitem[2]
                if iname == item_name:
                    x = col_x
                    y = col_y
                else:
                    x = iitem[0]
                    y = iitem[1]
                ditem = "{}/{}/{}\n".format(x, y, iname)
                ff.write(ditem)
        # reset
        cells_taken = []
        desktop_items = []
        cells_taken_temp = []
        self.item_idx = []
        
        
    # dropEvent
    def dropEvent2(self, event):
        dest_path = DDIR
        curr_dir = QFileInfo(dest_path)
        if not curr_dir.isWritable():
            MyDialog("Info", "The current folder is not writable: "+DDIR, None)
            event.ignore()
            return
        if event.mimeData().hasUrls:
            event.accept()
            filePathsTemp = []
            # web address list
            webPaths = []
            #
            for uurl in event.mimeData().urls():
                # check if the element is a local file
                if uurl.isLocalFile():
                    filePathsTemp.append(str(uurl.toLocalFile()))
                else:
                    webUrl = uurl.url()
                    if webUrl[0:5] == "http:" or webUrl[0:6] == "https:":
                        webPaths.append(webUrl)
            # 
            if webPaths:
                MyDialog("Info", "Not supported.", None)
                event.ignore()
            #
            filePaths = filePathsTemp
            #
            # if not empty
            if filePaths:
                #
                pointedItem = self.indexAt(event.pos())
                #
                if pointedItem.isValid():
                    ifp = os.path.join(DDIR, pointedItem.data(0))
                    if os.path.isdir(ifp):
                        if os.access(ifp, os.W_OK):
                            PastenMerge(ifp, event.proposedAction(), filePaths, None)
                        else:
                            MyDialog("Info", "The following folder in not writable: "+os.path.basename(ifp), None)
                            return
                    else:
                        PastenMerge(dest_path, event.proposedAction(), filePaths, None)
                else:
                    PastenMerge(dest_path, event.proposedAction(), filePaths, None)
            else:
                event.ignore()
        else:
            event.ignore()
        

# dialog for asking the archive password
class passWord(QDialog):
    def __init__(self, path, parent):
        super(passWord, self).__init__(parent)
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle("7z extractor")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(DIALOGWIDTH,100)
        #
        self.path = path
        # main box
        mbox = QBoxLayout(QBoxLayout.TopToBottom)
        mbox.setContentsMargins(5,5,5,5)
        # label
        self.label = QLabel("Enter The Password:")
        mbox.addWidget(self.label)
        # checkbox
        self.ckb = QCheckBox("Hide/Show the password")
        self.ckb.setChecked(True)
        self.ckb.toggled.connect(self.on_checked)
        mbox.addWidget(self.ckb)
        # lineedit
        self.le1 = QLineEdit()
        self.le1.setEchoMode(QLineEdit.Password)
        mbox.addWidget(self.le1)
        ##
        button_box = QBoxLayout(QBoxLayout.LeftToRight)
        button_box.setContentsMargins(0,0,0,0)
        mbox.addLayout(button_box)
        #
        button_ok = QPushButton("     Accept     ")
        button_box.addWidget(button_ok)
        #
        button_close = QPushButton("     Cancel     ")
        button_box.addWidget(button_close)
        #
        self.setLayout(mbox)
        button_ok.clicked.connect(self.getpswd)
        button_close.clicked.connect(self.close)
        #
        self.arpass = ""
        #
        self.exec_()
    
    def on_checked(self):
        if self.ckb.isChecked():
            self.le1.setEchoMode(QLineEdit.Password)
        else:
            self.le1.setEchoMode(QLineEdit.Normal)
    
    def getpswd(self):
        passwd = self.le1.text()
        try:
            ptest = subprocess.check_output('{} t -p{} -bso0 -- "{}"'.format(COMMAND_EXTRACTOR, passwd, self.path), shell=True)
            if ptest.decode() == "":
                self.arpass = passwd
                self.close()
        except:
            self.label.setText("Wrong Password:")
            self.le1.setText("")


class itemDelegate(QItemDelegate):

    def __init__(self, parent=None):
        super(itemDelegate, self).__init__(parent)
        self.text_width = ITEM_WIDTH - ITEM_SPACE
    
    def paint(self, painter, option, index):
        itemx = option.rect.x()
        itemy = option.rect.y()
        #
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        iicon = index.data(1)
        ppath = os.path.join(DDIR, index.data(0))
        #
        painter.restore()
        #
        item_icon = index.data(1)
        #
        if not index.data(1).name() and index.data(Qt.UserRole+1) == "file":
            pixmap = item_icon.pixmap(QSize(THUMB_SIZE, THUMB_SIZE))
        else:
            pixmap = item_icon.pixmap(QSize(ICON_SIZE, ICON_SIZE))
        size_pixmap = pixmap.size()
        pw = size_pixmap.width()
        ph = size_pixmap.height()
        # 
        xpad = int((ITEM_WIDTH - pw) / 2)
        ypad = int((ITEM_HEIGHT - ph) / 2)
        painter.drawPixmap(itemx+xpad, itemy+ypad-ST_HEIGHT-int(ITEM_SPACE/4), -1,-1, pixmap,0,0,-1,-1)
        #
        fileInfo = QFileInfo(ppath)
        # skip trashcan and media
        if index.data(Qt.UserRole+1) == "file":
            if not os.path.isdir(ppath):
                if not fileInfo.isReadable() or not fileInfo.isWritable():
                    ppixmap = QPixmap('icons/emblem-readonly.svg').scaled(ICON_SIZE2, ICON_SIZE2, Qt.KeepAspectRatio, Qt.FastTransformation)
                    painter.drawPixmap(itemx+1+int(ITEM_SPACE/2), itemy+ITEM_HEIGHT-ST_HEIGHT*2-ICON_SIZE2-int(ITEM_SPACE/2),-1,-1, ppixmap,0,0,-1,-1)
            else:
                if not fileInfo.isReadable() or not fileInfo.isWritable() or not fileInfo.isExecutable():
                    ppixmap = QPixmap('icons/emblem-readonly.svg').scaled(ICON_SIZE2, ICON_SIZE2, Qt.KeepAspectRatio, Qt.FastTransformation)
                    painter.drawPixmap(itemx+1+int(ITEM_SPACE/2), itemy+ITEM_HEIGHT-ST_HEIGHT*2-ICON_SIZE2-int(ITEM_SPACE/2),-1,-1, ppixmap,0,0,-1,-1)
            #
            if os.path.islink(ppath):
                lpixmap = QPixmap('icons/emblem-symbolic-link.svg').scaled(ICON_SIZE2, ICON_SIZE2, Qt.KeepAspectRatio, Qt.FastTransformation)
                painter.drawPixmap(itemx+ITEM_WIDTH-ICON_SIZE2-1-ITEM_SPACE/2, itemy+ITEM_HEIGHT-ST_HEIGHT*2-ICON_SIZE2-int(ITEM_SPACE/2),-1,-1, lpixmap,0,0,-1,-1)
        #
        painter.save()
        # text background colour
        color = QColor(TRED,TGREEN,TBLUE,TALPHA)
        if option.state & QStyle.State_Selected:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor(CIRCLE_COLOR))
            painter.setPen(QColor(CIRCLE_COLOR))
            painter.drawEllipse(QRect(itemx+1+int(ITEM_SPACE/2),itemy+1,CIRCLE_SIZE,CIRCLE_SIZE))
            # skip trashcan and media
            if index.data(Qt.UserRole+1) == "file":
                # tick symbol
                painter.setPen(QColor(TICK_COLOR))
                text = '<div style="font-size:{}px">{}</div>'.format(TICK_SIZE, TICK_CHAR)
                st = QStaticText(text)
                tx = int(itemx+1+((CIRCLE_SIZE - st.size().width())/2))+int(ITEM_SPACE/2)
                ty = int(itemy+1+((CIRCLE_SIZE - st.size().height())/2))
                painter.drawStaticText(tx, ty, st)
            #
            qstring = index.data(0)
            
            st = QStaticText(qstring)
            st.setTextWidth(self.text_width-4)
            to = QTextOption(Qt.AlignCenter)
            to.setWrapMode(QTextOption.WrapAnywhere)
            st.setTextOption(to)
            # text background
            if TEXT_BACKGROUND:
                painter.setBrush(QColor(color))
                painter.setPen(QColor(color))
                painter.setRenderHint(QPainter.Antialiasing)
                painter.drawRoundedRect(QRect(itemx+ITEM_SPACE/2,itemy+ITEM_HEIGHT-ST_HEIGHT*2-1,ITEM_WIDTH-ITEM_SPACE,st.size().height()), 5.0, 5.0, Qt.AbsoluteSize)
            #
            if TEXT_COLOR:
                painter.setPen(QColor(TEXT_COLOR))
            else:
                painter.setPen(QColor(option.palette.color(QPalette.WindowText)))
            #
            painter.drawStaticText(itemx+ITEM_SPACE/2+2, itemy+ITEM_HEIGHT-ST_HEIGHT*2-1, st)
        elif option.state & QStyle.State_MouseOver:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor(CIRCLE_COLOR))
            painter.setPen(QColor(CIRCLE_COLOR))
            painter.drawEllipse(QRect(itemx+1+int(ITEM_SPACE/2),itemy+1,CIRCLE_SIZE,CIRCLE_SIZE))
            #
            qstring = index.data(0)
            #
            metrics = QFontMetrics(painter.font())
            qstring = metrics.elidedText(qstring, Qt.ElideRight, ITEM_WIDTH-ITEM_SPACE)
            #
            st = QStaticText(qstring)
            st.setTextWidth(self.text_width-4)
            to = QTextOption(Qt.AlignCenter)
            to.setWrapMode(QTextOption.WrapAnywhere)
            st.setTextOption(to)
            # text background
            if TEXT_BACKGROUND:
                painter.setBrush(QColor(color))
                painter.setPen(QColor(color))
                painter.setRenderHint(QPainter.Antialiasing)
                painter.drawRoundedRect(QRect(itemx+ITEM_SPACE/2,itemy+ITEM_HEIGHT-ST_HEIGHT*2-1,ITEM_WIDTH-ITEM_SPACE,st.size().height()), 5.0, 5.0, Qt.AbsoluteSize)
            if TEXT_COLOR:
                painter.setPen(QColor(TEXT_COLOR))
            else:
                painter.setPen(QColor(option.palette.color(QPalette.WindowText)))
            #
            painter.drawStaticText(itemx+ITEM_SPACE/2+2, itemy+ITEM_HEIGHT-ST_HEIGHT*2-1, st)
        else:
            qstring = index.data(0)
            #
            metrics = QFontMetrics(painter.font())
            qstring = metrics.elidedText(qstring, Qt.ElideRight, ITEM_WIDTH-ITEM_SPACE)
            #
            st = QStaticText(qstring)
            st.setTextWidth(self.text_width-4)
            to = QTextOption(Qt.AlignCenter)
            to.setWrapMode(QTextOption.WrapAnywhere)
            st.setTextOption(to)
            # text background
            if TEXT_BACKGROUND:
                painter.setBrush(QColor(color))
                painter.setPen(QColor(color))
                painter.setRenderHint(QPainter.Antialiasing)
                painter.drawRoundedRect(QRect(itemx+ITEM_SPACE/2,itemy+ITEM_HEIGHT-ST_HEIGHT*2-1,ITEM_WIDTH-ITEM_SPACE,st.size().height()), 5.0, 5.0, Qt.AbsoluteSize)
            #
            if TEXT_COLOR:
                painter.setPen(QColor(TEXT_COLOR))
            else:
                painter.setPen(QColor(option.palette.color(QPalette.WindowText)))
            #
            painter.drawStaticText(itemx+ITEM_SPACE/2+2, itemy+ITEM_HEIGHT-ST_HEIGHT*2-1, st)
        #
        painter.restore()
        
    
    def sizeHint(self, option, index):
        return QSize(ITEM_WIDTH, ITEM_HEIGHT)
        

class thumbThread(threading.Thread):
    
    def __init__(self, fpath, listview):
        threading.Thread.__init__(self)
        self.event = threading.Event()
        self.fpath = fpath
        self.listview = listview
    
    def run(self):
        list_dir = os.listdir(self.fpath)
        while not self.event.is_set():
            for iitem in list_dir:
                item_fpath = os.path.join(self.fpath, iitem)
                if os.path.exists(item_fpath):
                    if stat.S_ISREG(os.stat(item_fpath).st_mode):
                        hmd5 = "Null"
                        imime = QMimeDatabase().mimeTypeForFile(iitem, QMimeDatabase.MatchDefault)
                        hmd5 = create_thumbnail(item_fpath, imime.name())
                        self.event.wait(0.05)
            self.event.set()
    

########################### MAIN WINDOW ############################
# 1
class MainWin(QWidget):
    media_signal = pyqtSignal(str,str,str,str)
    def __init__(self, parent=None):
        super(MainWin, self).__init__(parent)
        # 
        global ITEM_WIDTH
        global ITEM_HEIGHT
        global ST_HEIGHT
        global LEFT_M
        global TOP_M
        num_col_rest = int((WINW-LEFT_M-RIGHT_M)%ITEM_WIDTH)
        num_row_rest = int((WINH-TOP_M-BOTTOM_M)%ITEM_HEIGHT)
        LEFT_M += int(num_col_rest/2)
        TOP_M += int(num_row_rest/4)
        # calculate the height of some text
        st = QStaticText("A")
        ST_HEIGHT = st.size().height()
        # calculate the new cell size
        ITEM_WIDTH += ITEM_SPACE
        ITEM_HEIGHT += ST_HEIGHT*2 + ITEM_SPACE
        #
        # number of columns and rows
        global num_col
        num_col = int((WINW-LEFT_M-RIGHT_M)/ITEM_WIDTH)
        global num_row
        num_row = int((WINH-TOP_M-BOTTOM_M)/ITEM_HEIGHT)
        # reserved cells - items cannot be positioned there (type: indexes)
        global reserved_cells
        reserved_cells = [[0, num_row-1]]
        #
        # main box
        self.vbox = QBoxLayout(QBoxLayout.TopToBottom)
        self.vbox.setContentsMargins(QMargins(0,0,0,0))
        self.setLayout(self.vbox)
        # the list of items in the folder at program launch
        self.desktop_items = os.listdir(DDIR)
        # remove the hidden items
        for iitem in self.desktop_items[:]:
            if iitem[0] == ".":
                self.desktop_items.remove(iitem)
        ##################
        self.listview = MyQlist()
        # disable the double clicking renaming
        self.listview.setEditTriggers(QAbstractItemView.NoEditTriggers)
        #
        self.selection = None
        self.vbox.addWidget(self.listview)
        self.listview.hide()
        self.listview.setViewMode(QListView.IconMode)
        self.listview.setFlow(QListView.TopToBottom)
        #
        self.listview.clicked.connect(self.singleClick)
        self.listview.doubleClicked.connect(self.doubleClick)
        # number of columns and rows
        self.num_col = num_col
        self.num_row = num_row
        # reserved cells - items cannot be positioned there
        self.reserved_cells = reserved_cells
        #
        self.listview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.listview.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        #
        self.listview.setSelectionMode(self.listview.ExtendedSelection)
        ### the model
        self.model = QStandardItemModel()
        #
        self.listview.setModel(self.model)
        self.listview.selectionModel().selectionChanged.connect(self.lselectionChanged)
        #
        self.listview.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listview.customContextMenuRequested.connect(self.onRightClick)
        #
        self.listview.viewport().setAttribute(Qt.WA_Hover)
        self.listview.setItemDelegate(itemDelegate())
        # 
        self.listview.viewport().installEventFilter(self)
        #
        # the background color or the wallpaper
        if USE_BACKGROUND_COLOUR == 1 or not os.path.exists("wallpaper.jpg"):
            self.listview.setStyleSheet("background-color: {};".format(BACKGROUND_COLOR))
        else:
            self.listview.setStyleSheet("background-image: url(wallpaper.jpg) 0 0 0 0 stretch stretch;") # max-width:{0}px;min-width:{0}px; max-height:{1}px; min-height:{1}px;".format(WINW, WINH))
        #
        if USE_THUMB == 1:
            thread = thumbThread(DDIR, self.listview)
            thread.start()
        # menu style
        if MENU_H_COLOR:
            csaa = "QMenu { "
            csab = "background: {}".format(QPalette.Window)
            csac = "; margin: 1px; padding: 5px 5px 5px 5px;}"
            csad = " QMenu::item:selected { "
            csae = "background-color: {};".format(MENU_H_COLOR)
            csaf = " padding: 10px;}"
            csag = " QMenu::item:!selected {padding: 2px 15px 2px 10px;}"
            self.csa = csaa+csab+csac+csad+csae+csaf+csag
        # item are added in the selected item list if clicked at its top-left position
        self.static_items = False
        # [[QPos], device]
        self.media_added = []
        # restore the item position from items_position file
        self.listviewRestore()
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self.listviewRestore2)
        timer.start(200)
        #
        ### trash can
        self.trash_standartItem = None
        if USE_TRASH:
            # press the delete key to send to trash the selected items
            self.clickable2(self.listview).connect(self.itemsToTrash)
        #
        # check for changes in the application directories
        fPath = [DDIR]
        if USE_TRASH:
            fPath.append(TRASH_PATH)
        fileSystemWatcher = QFileSystemWatcher(fPath, self)
        fileSystemWatcher.directoryChanged.connect(self.directory_changed)
        #
        if USE_MEDIA:
            self.context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(self.context)
            monitor.filter_by('block')
            self.observer = pyudev.MonitorObserver(monitor, self.mediaEvent)
            self.observer.daemon
            self.observer.start()
            #
            self.bus = dbus.SystemBus()
            #
            self.media_signal.connect(self.signal_media)
            # the devices at program launch
            self.on_media_detected()
        # 
        time.sleep(1)
        self.listview.show()
    
    
    ######################### devices ########################
    # the devices at program launch
    def on_media_detected(self):
        for device in self.context.list_devices(subsystem='block'):
            if 'DEVTYPE' in device.properties:
                if device.get('ID_FS_USAGE') == "filesystem":
                    mountpoint = self.get_device_mountpoint(device.device_node)
                    if mountpoint in ["/", "/boot", "/home"]:
                        continue
                    #
                    if device.get('ID_FS_LABEL'):
                        name = device.get('ID_FS_LABEL')
                    elif device.get('ID_MODEL'):
                        name = device.get('ID_MODEL')
                    else:
                        name = device
                    # disk - etc.
                    if device.get('ID_DRIVE_FLASH_MS') == "1":
                        ttype = "flash-ms"
                    elif device.get('ID_DRIVE_THUMB') == "1":
                        ttype = "thumb"
                    else:
                        ttype = device.get('ID_TYPE')
                    #
                    self.addMedia(device.device_node, name, ttype)
    
    
    #
    def mediaEvent(self, action, device):
        if action == "add":
            if 'DEVTYPE' in device.properties:
                if device.get('ID_FS_USAGE') == "filesystem":
                    ddevice = device.device_node
                    #
                    if device.get('ID_FS_LABEL'):
                        name = device.get('ID_FS_LABEL')
                    elif device.get('ID_MODEL'):
                        name = device.get('ID_MODEL')
                    else:
                        name = ddevice
                    # disk - etc.
                    if device.get('ID_DRIVE_FLASH_MS') == "1":
                        ttype = "flash-ms"
                    elif device.get('ID_DRIVE_THUMB') == "1":
                        ttype = "thumb"
                    else:
                        ttype = device.get('ID_TYPE')
                    #
                    self.media_signal.emit(action, ddevice, name, ttype)
        elif action == "remove":
            ddevice = device.device_node
            self.media_signal.emit(action, ddevice, "", "")
    
    #
    def signal_media(self, action, ddevice, name, ttype):
        if action == "add":
            self.addMedia(ddevice, name, ttype)
        elif action == "remove":
            self.removeMedia(ddevice)
    
    # add the device into the model and view
    def addMedia(self, ddevice, name, ttype):
        time.sleep(2)
        # the first empty cell
        data = self.itemSetPos2()
        #
        if data == [-1,-1]:
            MyDialog("Info", "Cannot add the device {}.".format(name), self)
            return
        #
        if ttype == "flash-ms":
            iicon_type = "icons/media-flash.svg"
        elif ttype == "thumb":
            iicon_type = "icons/drive-thumb.svg"
        elif ttype == "disk":
            iicon_type = "icons/drive-harddisk.svg"
        elif ttype == "cd":
            iicon_type = "icons/media-optical.svg"
        else:
            iicon_type = "icons/drive-harddisk.svg"
        iicon = QIcon(iicon_type)
        iitem = name
        item = QStandardItem(iicon, iitem)
        item.setData("media", Qt.UserRole+1)
        item.setData(ddevice, Qt.UserRole+2)
        item.setData(ttype, Qt.UserRole+3)
        self.model.appendRow(item)
        # set the position
        self.itemSetPos(item)
        # restore the positions
        self.listviewRestore2()
        # desktop notification
        if USE_MEDIA and USE_MEDIA_NOTIFICATION == 2:
            if shutil.which("notify-send"):
                icon_path = os.path.join(os.getcwd(), iicon_type)
                # 
                command = ["notify-send", "-i", icon_path, "-t", "3000", "-u", "normal", iitem, "Inserted"]
                subprocess.Popen(command)
    
    
    # remove the device from the model and view
    def removeMedia(self, ddevice):
        time.sleep(1)
        for row in range(self.model.rowCount()):
            iitem = self.model.item(row)
            if iitem.data(Qt.UserRole+1) == "media":
                if iitem.data(Qt.UserRole+2) == ddevice:
                    item_idx = None
                    item_display_name = iitem.data(Qt.DisplayRole)
                    item_icon_type = iitem.data(Qt.UserRole+3)
                    for mm in range(len(self.media_added)):
                        if self.media_added[mm][1].data(Qt.UserRole+2) == ddevice:
                            iitem_idx = mm
                    ret = self.model.removeRow(row)
                    # True if removed
                    if ret:
                        # remove the device from the list
                        del self.media_added[mm]
                        # restore the positions
                        self.listviewRestore2()
                        # desktop notification
                        if USE_MEDIA and USE_MEDIA_NOTIFICATION:
                            if shutil.which("notify-send"):
                                icon_path = os.path.join(os.getcwd(), "icons/drive-harddisk.svg")
                                if item_icon_type:
                                    if item_icon_type == "flash-ms":
                                        item_icon = "icons/media-flash.svg"
                                    elif item_icon_type == "thumb":
                                        item_icon = "icons/drive-thumb.svg"
                                    elif item_icon_type == "disk":
                                        item_icon = "icons/drive-harddisk.svg"
                                    elif item_icon_type == "cd":
                                        item_icon = "icons/media-optical.svg"
                                    else:
                                        item_icon = "icons/drive-harddisk.svg"
                                    icon_path = os.path.join(os.getcwd(), item_icon)
                                # 
                                command = ["notify-send", "-i", icon_path, "-t", "3000", "-u", "normal", item_display_name, "Ejected"]
                                subprocess.Popen(command)
    
    
    # get the device mount point
    def get_device_mountpoint(self, ddevice):
        ddev = ddevice.split("/")[-1]
        mount_point = self.on_get_mounted(ddev)
        return mount_point
        
    # get the mount point or return N
    def on_get_mounted(self, ddev):
        path = os.path.join('/org/freedesktop/UDisks2/block_devices/', ddev)
        bd = self.bus.get_object('org.freedesktop.UDisks2', path)
        try:
            mountpoint = bd.Get('org.freedesktop.UDisks2.Filesystem', 'MountPoints', dbus_interface='org.freedesktop.DBus.Properties')
            if mountpoint:
                mountpoint = bytearray(mountpoint[0]).replace(b'\x00', b'').decode('utf-8')
                return mountpoint
            else:
                return "N"
        except:
            return "N"
    
    
    # mount - unmount the device
    def mount_device(self, mountpoint, ddevice):
        if mountpoint == "N":
            ret = self.on_mount_device(ddevice, 'Mount')
            if ret == -1:
                MyDialog("Info", "The device cannot be mounted.", self)
                return 
        else:
            ret = self.on_mount_device(ddevice, 'Unmount')
            if ret == -1:
                MyDialog("Info", "The device cannot be unmounted.", self)
                return
        #
        return ret
    
    # self.mount_device
    def on_mount_device(self, ddevice, operation):
        ddev = ddevice.split("/")[-1]
        progname = 'org.freedesktop.UDisks2'
        objpath = os.path.join('/org/freedesktop/UDisks2/block_devices', ddev)
        intfname = 'org.freedesktop.UDisks2.Filesystem'
        try:
            obj  = self.bus.get_object(progname, objpath)
            intf = dbus.Interface(obj, intfname)
            # return the mount point or None if unmount
            ret = intf.get_dbus_method(operation, dbus_interface='org.freedesktop.UDisks2.Filesystem')([])
            return ret
        except:
            return -1


    # eject the media
    def eject_media(self, index):
        ddevice = index.data(Qt.UserRole+2)
        mountpoint = self.get_device_mountpoint(ddevice)
        self.eject_media1(mountpoint, ddevice, index)
    
    # self.eject_media
    def eject_media1(self, mountpoint, ddevice, index):
        # first unmount if the case
        if mountpoint != "N":
            ret = self.mount_device(mountpoint, ddevice)
            if ret == -1:
                MyDialog("Info", "Device busy.", self)
                return
        # 
        k = "/org/freedesktop/UDisks2/block_devices/"+ddevice.split("/")[-1]
        bd = self.bus.get_object('org.freedesktop.UDisks2', k)
        ddrive = bd.Get('org.freedesktop.UDisks2.Block', 'Drive', dbus_interface='org.freedesktop.DBus.Properties')
        bd2 = self.bus.get_object('org.freedesktop.UDisks2', ddrive)
        can_poweroff = bd2.Get('org.freedesktop.UDisks2.Drive', 'CanPowerOff', dbus_interface='org.freedesktop.DBus.Properties')
        #
        ret = self.on_eject(ddrive)
        if ret == -1:
            MyDialog("Info", "The device cannot be ejected.", self)
            return
        #
        if can_poweroff:
            try:
                ret = self.on_poweroff(ddrive)
                # if ret == -1:
                    # MyDialog("Info", "The device cannot be turned off.", self)
                    # return
            except:
                pass

        
    # self.eject_media1
    def on_eject(self, ddrive):
        progname = 'org.freedesktop.UDisks2'
        objpath  = ddrive
        intfname = 'org.freedesktop.UDisks2.Drive'
        try:
            methname = 'Eject'
            obj  = self.bus.get_object(progname, objpath)
            intf = dbus.Interface(obj, intfname)
            ret = intf.get_dbus_method(methname, dbus_interface='org.freedesktop.UDisks2.Drive')([])
            return ret
        except:
            return -1
    
    
    # self.eject_media1
    def on_poweroff(self, ddrive):
        progname = 'org.freedesktop.UDisks2'
        objpath  = ddrive
        intfname = 'org.freedesktop.UDisks2.Drive'
        try:
            methname = 'PowerOff'
            obj  = self.bus.get_object(progname, objpath)
            intf = dbus.Interface(obj, intfname)
            ret = intf.get_dbus_method(methname, dbus_interface='org.freedesktop.UDisks2.Drive')([])
            return ret
        except:
            return -1
    
    
    ####################### devices end #######################
    
    # get the items in the desktop directory
    def desktopItems(self):
        new_desktop_list = os.listdir(DDIR)
        for iitem in new_desktop_list[:]:
            if iitem[0] == ".":
                new_desktop_list.remove(iitem)
        return new_desktop_list
    
    
    # send to trash the selected items
    def clickable2(self, widget):
        class Filter(QObject):
            clicked = pyqtSignal()
            def eventFilter(self, obj, event):
                if obj == widget:
                    if event.type() == QEvent.KeyRelease:
                        if event.key() == Qt.Key_Delete:
                            self.clicked.emit()
                return False
        #
        filter = Filter(widget)
        widget.installEventFilter(filter)
        return filter.clicked
    
    
    #  send to trash or delete the selected items - function
    def itemsToTrash(self):
        if self.selection:
            self.ftrashAction()
    
    #
    def singleClick(self, index):
        time.sleep(0.1)
        path = os.path.join(DDIR, index.data(0))
        file_info = QFileInfo(path)
        #
        self.listview.viewport().update()
    
    #
    def doubleClick(self, index):
        ### the special entries
        # the recycle bin
        if index.data(Qt.UserRole+1) == "trash":
            try:
                subprocess.Popen(["./trash_command.sh"])
            except Exception as E:
                MyDialog("Error", str(E), self)
            return
        # the media devices
        elif index.data(Qt.UserRole+1) == "media":
            self.fopenMediaAction(index)
            return
        # desktop file
        elif index.data(Qt.UserRole+1) == "desktop":
            self.flaunchDesktop(index)
            return
        #
        path = os.path.join(DDIR, index.data(0))
        #
        if not os.path.exists(path):
            MyDialog("Info", "It doesn't exist.", self)
            return
        #
        if os.path.isdir(path):
            if os.access(path, os.R_OK):
                try:
                    defApp = getDefaultApp(path, self).defaultApplication()
                    if defApp != "None":
                        subprocess.Popen([defApp, path])
                    else:
                        MyDialog("Info", "No programs found.", self)
                except Exception as E:
                    MyDialog("Error", str(E), self)
            else:
                MyDialog("Error", path+"\n\n   Not readable", self)
        #
        elif os.path.isfile(path):
            perms = QFileInfo(path).permissions()
            if perms & QFile.ExeOwner:
                imime = QMimeDatabase().mimeTypeForFile(path, QMimeDatabase.MatchDefault).name()
                if imime == "application/x-sharedlib":
                    ret = execfileDialog(path, 1, self).getValue()
                else:
                    ret = execfileDialog(path, 0, self).getValue()
                #
                if ret == 2:
                    try:
                        subprocess.Popen(path, shell=True)
                    except Exception as E:
                        MyDialog("Error", str(E), self)
                    finally:
                        return
                elif ret == -1:
                    return
            #
            defApp = getDefaultApp(path, self).defaultApplication()
            if defApp != "None":
                try:
                    subprocess.Popen([defApp, path])
                except Exception as E:
                    MyDialog("Error", str(E), self)
            else:
                MyDialog("Info", "No programs found.", self)
        
    
    # some applications have been added or removed
    def directory_changed(self, edir):
        if edir == TRASH_PATH:
            tmp = os.listdir(TRASH_PATH)
            for row in range(self.model.rowCount()):
                item_model = self.model.item(row)
                if item_model.data(Qt.UserRole+1) == "trash":
                    tmp = os.listdir(TRASH_PATH)
                    if tmp:
                        iicon = QIcon.fromTheme("user-trash-full")
                        item_model.setData(iicon, 1)
                    else:
                        iicon = QIcon.fromTheme("user-trash")
                        item_model.setData(iicon, 1)
                    return
        #
        new_desktop_list = self.desktopItems()
        # items added
        if len(new_desktop_list) > len(self.desktop_items):
            self.addItem(new_desktop_list)
        # items removed
        elif len(new_desktop_list) < len(self.desktop_items):
            self.removeItem(new_desktop_list)
        # all the other cases supported: renaming, properties, ecc.
        else:
            self.changedItem(new_desktop_list)
        # update the list
        self.desktop_items = new_desktop_list
        #
        self.listview.viewport().update()
    
    #
    def lselectionChanged(self):
        self.selection = self.listview.selectionModel().selectedIndexes()
        self.listview.viewport().update()
    
    
    # add item
    def addItem(self, new_desktop_list):
        for itd in new_desktop_list:
            if itd not in self.desktop_items:
                time.sleep(0.5)
                ireal_path = os.path.join(DDIR, itd)
                imime = QMimeDatabase().mimeTypeForFile(ireal_path, QMimeDatabase.MatchDefault)
                if imime.name() == "application/x-desktop":
                    # program name - icon - exec/URL - type (Application/Directory/Link)
                    ddata = self.getDesktopData(ireal_path)
                    if ddata:
                        dname = ddata[0]
                        # 
                        if ddata[1]:
                            if ddata[3] == "Application":
                                iicon = QIcon.fromTheme(ddata[1])
                                if iicon.isNull():
                                    iicon = QIcon(ddata[1])
                                    if iicon.isNull():
                                        iicon = QIcon("icons/unknown.svg")
                            elif ddata[3] == "Directory":
                                iicon = QIcon.fromTheme(ddata[1])
                                if iicon.isNull():
                                    iicon = QIcon(ddata[1])
                                    if iicon.isNull():
                                        iicon = QIcon("icons/unknown.svg")
                            elif ddata[3] == "Link":
                                iicon = QIcon(ddata[1])
                                if iicon.isNull():
                                    iicon = QIcon("icons/unknown.svg")
                        else:
                            if ddata[3] == "Link":
                                imime = QMimeDatabase().mimeTypeForFile(ddata[2][7:], QMimeDatabase.MatchDefault)
                                imime_name = imime.iconName()
                                iicon = QIcon.fromTheme(imime_name, QIcon("icons/unknown.svg"))
                            elif ddata[3] == "Directory":
                                iicon = QIcon("icons/unknown.svg")
                        # 
                        dexec = ddata[2]
                        item = QStandardItem(iicon, dname)
                        item.setData("desktop", Qt.UserRole + 1)
                        item.setData([itd, ddata[1], ddata[2], ddata[3]], Qt.UserRole + 2)
                        # if ddata[3] == "Directory" or ddata[3] == "Link":
                            # item.setData(ddata[2][7:], Qt.ToolTipRole)
                        self.model.appendRow(item)
                        #
                        self.itemSetPos(item)
                    # set the desktop file as normal file
                    else:
                        iicon = self.setIcons(os.path.join(DDIR, itd))
                        item = QStandardItem(iicon, itd)
                        item.setData("file", Qt.UserRole + 1)
                        # Add the item to the model
                        self.model.appendRow(item)
                        #
                        self.itemSetPos(item)
                else:
                    iicon = self.setIcons(os.path.join(DDIR, itd))
                    item = QStandardItem(iicon, itd)
                    item.setData("file", Qt.UserRole + 1)
                    # Add the item to the model
                    self.model.appendRow(item)
                    #
                    self.itemSetPos(item)
        # restore the position
        self.listviewRestore2()
    
    
    # get the data from a desktop file
    def getDesktopData(self, dpath):
        try:
            entry = DesktopEntry(dpath)
            dtype = entry.getType() # type: Application, Directory, Link
            if dtype == "Application":
                dname = entry.getName() # program name
                dicon = entry.getIcon() # icon
                dexec = entry.getExec() # executable
                if dname and dexec:
                    return [dname, dicon, dexec, dtype]
            elif dtype == "Directory" or dtype == "Link":
                dname = entry.getName() # directory name
                dicon = entry.getIcon() # icon
                durl = entry.getURL() # url
                if dname and durl:
                    return [dname, dicon, durl, dtype]
        except:
            return None
        
        
    # remove item
    def removeItem(self, new_desktop_list):
        item_name_removed = []
        for itd in self.desktop_items:
            if itd not in new_desktop_list:
                for row in range(self.model.rowCount()):
                    item = self.model.item(row)
                    if item:
                        custom_data = item.data(Qt.UserRole + 1)
                        if custom_data != "desktop" and custom_data in special_entries:
                            continue
                        #
                        if custom_data == "file":
                            item_name = item.data(0)
                        elif custom_data == "desktop":
                            item_name = item.data(Qt.UserRole + 2)[0]
                        if item_name == itd:
                            self.model.removeRow(row)
                            item_name_removed.append(item_name)
        items_position = []
        with open("items_position", "r") as ff:
            items_position = ff.readlines()
        for iitem in items_position[:]:
            if iitem.split("/")[-1].strip("\n") in item_name_removed:
                items_position.remove(iitem)
        # update the file
        with open("items_position", "w") as ff:
            for iitem in items_position:
                ff.write(iitem)
        # restore the position
        self.listviewRestore2()
    
    
    #
    def changedItem(self, new_desktop_list):
        old_item = None
        for itd in self.desktop_items:
            if itd not in new_desktop_list:
                old_item = itd
        new_item = None
        for itd in new_desktop_list:
            if itd not in self.desktop_items:
                new_item = itd
        # update the model
        for row in range(self.model.rowCount()):
            item_model = self.model.item(row)
            if item_model.data(0) == old_item:
                #  DisplayRole, DecorationRole
                item_model.setData(new_item, Qt.DisplayRole)
        # update the file
        items_position = []
        x = 0
        y = 0
        with open("items_position", "r") as ff:
            items_position = ff.readlines()
        for iitem in items_position[:]:
            if iitem.split("/")[-1].strip("\n") == old_item:
                items_position.remove(iitem)
                x,y,n = iitem.split("/")
                items_position.append("{}/{}/{}\n".format(x, y, new_item))
                break
        # 
        with open("items_position", "w") as ff:
            for iitem in items_position:
                ff.write(iitem)
        #
        self.listview.viewport().update()
    
    
    # service function for self.listview.setPositionForIndex
    def fSetPositionForIndex(self, data, itemIdx):
        x = data[0]*ITEM_WIDTH+LEFT_M
        y = data[1]*ITEM_HEIGHT+TOP_M
        self.listview.setPositionForIndex(QPoint(x, y), itemIdx)
        
    
    # item positioning in the listview
    def itemSetPos(self, item):
        data = self.itemSetPos2()
        self.fSetPositionForIndex((data[0], data[1]), item.index())
        # update the file - skip the special entries except desktop
        custom_data = item.data(Qt.UserRole+1)
        if custom_data != "desktop" and custom_data in special_entries:
            # udpate the media list
            if item.data(Qt.UserRole+1) == "media":
                self.media_added.append([data, item])
            return
        #
        with open("items_position", "a") as ff:
            if custom_data == "file":
                iitem = "{}/{}/{}\n".format(data[0], data[1], item.data(0))
            elif custom_data == "desktop":
                dname = item.data(Qt.UserRole+2)[0]
                iitem = "{}/{}/{}\n".format(data[0], data[1], dname)
            ff.write(iitem)
    
    
    # itemSetPos - return the first empty cell in the listview
    def itemSetPos2(self):
        items_position = []
        with open("items_position", "r") as ff:
            items_position = ff.readlines()
        #
        rr1 = 0
        cc1 = 0
        #
        list_pos = []
        for iitem in items_position:
            iitem_data = iitem.split("/")
            list_pos.append([int(iitem_data[0]), int(iitem_data[1])])
        # 
        for cc in reversed(range(self.num_col)):
            for rr in range(self.num_row):
                if [cc, rr] not in list_pos:
                    if [cc, rr] in self.reserved_cells:
                        continue
                    #
                    cc1 = cc
                    rr1 = rr
                    #
                    if self.media_added:
                        for mmedia in self.media_added:
                            if [cc1, rr1] == mmedia[0]:
                                break
                            else:
                                return [int(cc1), int(rr1)]
                    else:
                        return [int(cc1), int(rr1)]
                    continue
        # no empty cells
        return [-1,-1]
    
    
    # update the file
    def fitems_desktop(self):
        with open("items_position", "w") as ff:
            for row in range(self.model.rowCount()):
                item_model = self.model.item(row)
                # skip the special entries
                if item_model.data(Qt.UserRole+1) in special_entries:
                    continue
                item_name = item_model.data(0)
                item_rect = self.listview.visualRect(item_model.index())
                x = int((item_rect.x()-LEFT_M)/ITEM_WIDTH)
                y = int((item_rect.y()-TOP_M)/ITEM_HEIGHT)
                # 
                if item_model:
                    iitem = "{}/{}/{}\n".format(x, y, item_name)
                    ff.write(iitem)
    
    
    # populate the model at program launch
    def listviewRestore(self):
        # the items in the file
        items_position = []
        if os.path.exists("items_position"):
            if os.path.getsize("items_position") != 0:
                with open("items_position", "r") as ff:
                    items_position = ff.readlines()
        # if the file need to be rebuilt at the end
        file_is_changed = 0
        # only item name
        item_names = []
        # empty cell counter
        empty_cell_counter = 0
        # max slots to be used
        num_slot = self.num_col * self.num_row - len(self.reserved_cells)
        # some items cannot be added in the view
        items_skipped = 0
        for iitem in items_position[:]:
            if iitem == "\n":
                continue
            # reached the number of empty cells available
            if empty_cell_counter == num_slot:
                items_skipped = 1
                # remove excedent items
                file_is_changed = 1
                items_position.remove(iitem)
                continue
            x, y, item_name_temp = iitem.split("/")
            item_name = item_name_temp.strip("\n")
            # 
            if os.path.exists(os.path.join(DDIR, item_name)) or os.path.islink(os.path.join(DDIR, item_name)):
                # fill the model
                ireal_path = os.path.join(DDIR, item_name)
                imime = QMimeDatabase().mimeTypeForFile(ireal_path, QMimeDatabase.MatchDefault)
                if imime.name() == "application/x-desktop":
                    # name - icon - exec/URL - type (Application/Directory/Link)
                    ddata = self.getDesktopData(ireal_path)
                    if ddata:
                        dname = ddata[0]
                        if ddata[1]:
                            if ddata[3] == "Application":
                                iicon = QIcon.fromTheme(ddata[1])
                                if iicon.isNull():
                                    iicon = QIcon(ddata[1])
                                    if iicon.isNull():
                                        iicon = QIcon("icons/unknown.svg")
                            elif ddata[3] == "Directory":
                                iicon = QIcon.fromTheme(ddata[1])
                                if iicon.isNull():
                                    iicon = QIcon(ddata[1])
                                    if iicon.isNull():
                                        iicon = QIcon("icons/unknown.svg")
                            elif ddata[3] == "Link":
                                iicon = QIcon(ddata[1])
                                if iicon.isNull():
                                    iicon = QIcon("icons/unknown.svg")
                        else:
                            if ddata[3] == "Link":
                                imime = QMimeDatabase().mimeTypeForFile(ddata[2][7:], QMimeDatabase.MatchDefault)
                                imime_name = imime.iconName()
                                iicon = QIcon.fromTheme(imime_name, QIcon("icons/unknown.svg"))
                            elif ddata[3] == "Directory":
                                iicon = QIcon("icons/unknown.svg")
                        # 
                        dexec = ddata[2]
                        item = QStandardItem(iicon, dname)
                        item.setData("desktop", Qt.UserRole + 1)
                        item.setData([item_name, ddata[1], ddata[2], ddata[3]], Qt.UserRole + 2)
                        # if ddata[3] == "Directory" or ddata[3] == "Link":
                            # item.setData(ddata[2][7:], Qt.ToolTipRole)
                        self.model.appendRow(item)
                        item_names.append(item_name)
                    # set the desktop file as normal file
                    else:
                        iicon = self.setIcons(os.path.join(DDIR, item_name))
                        item = QStandardItem(iicon, item_name)
                        # custom data
                        item.setData("file", Qt.UserRole + 1)
                        # add the item to the model
                        self.model.appendRow(item)
                        item_names.append(item_name)
                else:
                    iicon = self.setIcons(os.path.join(DDIR, item_name))
                    item = QStandardItem(iicon, item_name)
                    # custom data
                    item.setData("file", Qt.UserRole + 1)
                    # add the item to the model
                    self.model.appendRow(item)
                    item_names.append(item_name)
                #
                empty_cell_counter += 1
            else:
                # remove no more existent items
                file_is_changed = 1
                items_position.remove(iitem)
        ### add the trashcan
        tmp = os.listdir(TRASH_PATH)
        if tmp:
            iicon = QIcon.fromTheme("user-trash-full")
        else:
            iicon = QIcon.fromTheme("user-trash")
        iitem = TRASH_NAME
        item = QStandardItem(iicon, iitem)
        item.setData("trash", Qt.UserRole + 1)
        self.model.appendRow(item)
        self.trash_standartItem = item
        ### add new items
        if not items_skipped:
            for item_name in self.desktop_items:
                # reached the number of empty cells available
                if empty_cell_counter == num_slot:
                    items_skipped = 1
                    break
                if item_name not in item_names:
                    if os.path.exists(os.path.join(DDIR, item_name)):
                        # the first empty cell
                        data = self.itemSetPos2()
                        # no more empty cells
                        if data == [-1,-1]:
                            items_skipped = 1
                            break
                        file_is_changed = 1
                        items_position.append("{}/{}/{}\n".format(data[0], data[1], item_name))
                        ## add the item to the model
                        # custom data
                        ireal_path = os.path.join(DDIR, item_name)
                        imime = QMimeDatabase().mimeTypeForFile(ireal_path, QMimeDatabase.MatchDefault)
                        if imime.name() == "application/x-desktop":
                            # name - icon - exec/URL - type
                            ddata = self.getDesktopData(ireal_path)
                            if ddata:
                                dname = ddata[0]
                                # 
                                if ddata[3] == "Application":
                                    iicon = QIcon.fromTheme(ddata[1])
                                    if iicon.isNull():
                                        iicon = QIcon(ddata[1])
                                        if iicon.isNull():
                                            iicon = QIcon("icons/unknown.svg")
                                elif ddata[1]:
                                    if ddata[3] == "Directory":
                                        iicon = QIcon.fromTheme(ddata[1])
                                        if iicon.isNull():
                                            iicon = QIcon(ddata[1])
                                            if iicon.isNull():
                                                iicon = QIcon("icons/unknown.svg")
                                    elif ddata[3] == "Link":
                                        iicon = QIcon(ddata[1])
                                        if iicon.isNull():
                                            iicon = QIcon("icons/unknown.svg")
                                else:
                                    if ddata[3] == "Link":
                                        imime = QMimeDatabase().mimeTypeForFile(ddata[2][7:], QMimeDatabase.MatchDefault)
                                        imime_name = imime.iconName()
                                        iicon = QIcon.fromTheme(imime_name, QIcon("icons/unknown.svg"))
                                    elif ddata[3] == "Directory":
                                        iicon = QIcon("icons/unknown.svg")
                                # 
                                dexec = ddata[2]
                                item = QStandardItem(iicon, dname)
                                item.setData("desktop", Qt.UserRole + 1)
                                item.setData([item_name, ddata[1], ddata[2], ddata[3]], Qt.UserRole + 2)
                            else:
                                iicon = self.setIcons(os.path.join(DDIR, item_name))
                                item = QStandardItem(iicon, item_name)
                                item.setData("file", Qt.UserRole + 1)
                        else:
                            iicon = self.setIcons(os.path.join(DDIR, item_name))
                            item = QStandardItem(iicon, item_name)
                            item.setData("file", Qt.UserRole + 1)
                        # add the item to the model
                        self.model.appendRow(item)
                        #
                        item_names.append(item_name)
                        #
                        empty_cell_counter += 1
                        #
                        # rebuild the file
                        if file_is_changed:
                            with open("items_position", "w") as ff:
                                for iitem in items_position:
                                    ff.write(iitem)
                            file_is_changed = 0
        # message
        if items_skipped:
            MyDialog("Info", "Too many items in the desktop folder to be all placed.", self)
        #
        # self.listview.viewport().update()
    
    
    # restore the item position from the items_position file
    def listviewRestore2(self):
        items_position = []
        with open("items_position", "r") as ff:
            items_position = ff.readlines()
        # some items has been repositioned
        items_changed = 0
        #
        for row in range(self.model.rowCount()):
            item_model = self.model.item(row)
            item_name = item_model.data(0)
            #
            if item_model:
                # the trashcan
                if item_model.data(Qt.UserRole+1) == "trash":
                    x = reserved_cells[0][0]
                    y = reserved_cells[0][1]
                    self.fSetPositionForIndex((x, y), item_model.index())
                # the media devices
                elif item_model.data(Qt.UserRole+1) == "media":
                    for mmedia in self.media_added:
                        if mmedia[1].data(0) == item_model.data(0):
                            x = mmedia[0][0]
                            y = mmedia[0][1]
                            self.fSetPositionForIndex((x, y), item_model.index())
                #
                # normal items and desktop files
                for iitem in items_position:
                    x, y, i_name = iitem.split("/")
                    # repositioning if excede the screen limits
                    max_width = (num_col-1)*ITEM_WIDTH
                    max_height = (num_row-1)*ITEM_HEIGHT
                    # 
                    if int(x)*ITEM_WIDTH > max_width or int(y)*ITEM_HEIGHT > max_height:
                        data = self.itemSetPos2()
                        items_changed = 1
                        x = data[0]
                        y = data[1]
                    #
                    if item_model.data(Qt.UserRole+1) == "file":
                        if i_name.strip("\n") == item_name:
                            self.fSetPositionForIndex((int(x), int(y)), item_model.index())
                    # desktop files
                    elif item_model.data(Qt.UserRole+1) == "desktop":
                        ddata = item_model.data(Qt.UserRole+2)
                        item_model_real_name = ddata[0]
                        #
                        if i_name.strip("\n") == item_model_real_name: 
                            self.fSetPositionForIndex((int(x), int(y)), item_model.index())
        #
        # rebuild the file
        if items_changed:
            self.fitems_desktop()
        #
        self.listview.viewport().update()


    #
    def eventFilter(self, obj, event):
        # select items continuosly without deselecting the others
        if event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                itemIdx = self.listview.indexAt(event.pos())
                item_rect = self.listview.visualRect(itemIdx)
                # item selected at top-left
                topLeft = QRect(item_rect.x()+int(ITEM_SPACE/2), item_rect.y(), CIRCLE_SIZE, CIRCLE_SIZE)
                if event.pos() in topLeft:
                    self.static_items = True
                    self.listview.setSelectionMode(QAbstractItemView.MultiSelection)
                else:
                    if self.static_items == True:
                        self.static_items = False
                        self.listview.setSelectionMode(QAbstractItemView.ExtendedSelection)
        #
        return QObject.event(obj, event)
    
    
    # find an icon to the item
    def setIcons(self, ppath):
        # info = fileInfo
        fileInfo = QFileInfo(ppath)
        ireal_path = ppath
        if fileInfo.exists():
            if fileInfo.isFile():
                imime = QMimeDatabase().mimeTypeForFile(ireal_path, QMimeDatabase.MatchDefault)
                #
                if imime:
                    try:
                        if USE_THUMB == 1:
                            file_icon = self.evaluate_pixbuf(ireal_path, imime.name())
                            #
                            if file_icon != "Null":
                                return file_icon
                            else:
                                file_icon = QIcon.fromTheme(imime.iconName())
                                if file_icon:
                                    return file_icon
                        else:
                            file_icon = QIcon.fromTheme(imime.iconName())
                            if file_icon:
                                return file_icon
                    except:
                        pass
            #
            elif fileInfo.isDir():
                # use custom icons
                if USE_FOL_CI:
                    if fileInfo.exists():
                        # exists the file .directory in the dir - set the custom icon
                        dir_path = os.path.join(ireal_path, ".directory")
                        icon_name = None
                        # only for home dir
                        if os.path.exists(dir_path) and dir_path[0:6] == "/home/":
                            try:
                                with open(dir_path,"r") as f:
                                    dcontent = f.readlines()
                                for el in dcontent:
                                    if "Icon=" in el:
                                        icon_name = el.split("=")[1].strip("\n")
                                        break
                            except:
                                icon_name = None
                        #
                        if icon_name:
                            icon_name_path = os.path.join(ireal_path, icon_name)
                            if os.path.exists(icon_name_path):
                                return QIcon(icon_name_path)
                            else:
                                return QIcon.fromTheme("folder")
                else:
                    return QIcon.fromTheme("folder")
        else:
            return QIcon.fromTheme("text-plain")
    
    
    # self.setIcons
    def evaluate_pixbuf(self, ifull_path, imime):
        hmd5 = "Null"
        hmd5 = create_thumbnail(ifull_path, imime)
        #
        file_icon = "Null"
        if hmd5 != "Null":
            file_icon = QIcon(QPixmap(XDG_CACHE_LARGE+"/"+str(hmd5)+".png"))
        #
        return file_icon
        
    
    # mouse right click on the pointed item
    def onRightClick(self, position):
        time.sleep(0.2)
        pointedItem = self.listview.indexAt(position)
        # the special entries
        if pointedItem.data(Qt.UserRole+1) == "trash":
            self.trashSelected(position)
            return
        elif pointedItem.data(Qt.UserRole+1) == "media":
            self.mediaSelected(position)
            return
        elif pointedItem.data(Qt.UserRole+1) == "desktop":
            self.desktopSelected(position)
            return
        vr = self.listview.visualRect(pointedItem)
        pointedItem2 = self.listview.indexAt(QPoint(vr.x(),vr.y()))
        # in case of sticky selection
        if self.static_items == True:
            self.static_items = False
            self.listview.setSelectionMode(QAbstractItemView.ExtendedSelection)
            if not pointedItem2 in self.selection:
                # deselect all
                self.listview.clearSelection()
                self.selection = [pointedItem2]
                # select the item
                self.listview.setCurrentIndex(pointedItem2)
        # the items
        if vr:
            # the data of the selected item at the bottom
            self.singleClick(pointedItem)
            #
            itemName = pointedItem.data(0)
            menu = QMenu("Menu", self.listview)
            if MENU_H_COLOR:
                menu.setStyleSheet(self.csa)
            #
            ipath = os.path.join(DDIR, itemName)
            #
            if not os.path.exists(ipath) and not os.path.islink(ipath):
                MyDialog("Info", "It doesn't exist.", self)
                return
            #
            if self.selection != None:
                if len(self.selection) == 1:
                    if os.path.isfile(ipath):
                        subm_openwithAction= menu.addMenu("Open with...")
                        listPrograms = getAppsByMime(ipath).appByMime()
                        #
                        ii = 0
                        defApp = getDefaultApp(ipath, self).defaultApplication()
                        progActionList = []
                        if listPrograms:
                            for iprog in listPrograms[::2]:
                                if iprog == defApp:
                                    progActionList.insert(0, QAction("{} - {} (Default)".format(os.path.basename(iprog), listPrograms[ii+1]), self))
                                    progActionList.insert(1, iprog)
                                else:
                                    progActionList.append(QAction("{} - {}".format(os.path.basename(iprog), listPrograms[ii+1]), self))
                                    progActionList.append(iprog)
                                ii += 2
                            ii = 0
                            for paction in progActionList[::2]:
                                paction.triggered.connect(lambda checked, index=ii:self.fprogAction(progActionList[index+1], ipath))
                                subm_openwithAction.addAction(paction)
                                ii += 2
                        subm_openwithAction.addSeparator()
                        otherAction = QAction("Other Program")
                        otherAction.triggered.connect(lambda:self.fotherAction(ipath))
                        subm_openwithAction.addAction(otherAction)
                        #
                        menu.addSeparator()
                    elif os.path.isdir(ipath):
                        newtabAction = QAction("Open")
                        if os.access(ipath, os.R_OK):
                            defApp = getDefaultApp(ipath, self).defaultApplication()
                            if defApp != "None":
                                newtabAction.triggered.connect(lambda:subprocess.Popen([defApp, ipath]))
                                menu.addAction(newtabAction)
                                menu.addSeparator()
            #
            copyAction = QAction("Copy", self)
            copyAction.triggered.connect(lambda:self.fcopycutAction("copy"))
            menu.addAction(copyAction)
            #
            copyAction = QAction("Cut", self)
            copyAction.triggered.connect(lambda:self.fcopycutAction("cut"))
            menu.addAction(copyAction)
            # can paste into the hovered directory
            if os.path.isdir(ipath):
                pasteNmergeAction = QAction("Paste", self)
                pasteNmergeAction.triggered.connect(lambda d:PastenMerge(ipath, -3, "", self))
                menu.addAction(pasteNmergeAction)
            #
            if USE_TRASH:
                # only items in the desktop
                if isXDGDATAHOME:
                    trashAction = QAction("Trash", self)
                    trashAction.triggered.connect(self.ftrashAction)
                    menu.addAction(trashAction)
            # delete function
            if USE_DELETE:
                deleteAction = QAction("Delete", self)
                deleteAction.triggered.connect(self.fdeleteAction)
                menu.addAction(deleteAction)
            if self.selection and len(self.selection) == 1:
                menu.addSeparator()
                renameAction = QAction("Rename", self)
                renameAction.triggered.connect(lambda:self.frenameAction(ipath))
                menu.addAction(renameAction)
            #
            menu.addSeparator()
            #
            subm_customAction = menu.addMenu("Actions")
            #
            if len(list_custom_modules) > 0:
                listActions = []
                for el in list_custom_modules:
                    if el.mmodule_type(self.listview) == 1 and self.selection and len(self.selection) == 1:
                        icustomAction = QAction(el.mmodule_name(), self)
                        listActions.append(icustomAction)
                        listActions.append(el)
                        listActions.append(1)
                    elif el.mmodule_type(self.listview) == 2 and self.selection and len(self.selection) > 1:
                        icustomAction = QAction(el.mmodule_name(), self)
                        listActions.append(icustomAction)
                        listActions.append(el)
                        listActions.append(2)
                    elif el.mmodule_type(self.listview) == 3 and self.selection and len(self.selection) > 0:
                        icustomAction = QAction(el.mmodule_name(), self)
                        listActions.append(icustomAction)
                        listActions.append(el)
                        listActions.append(3)
                    elif el.mmodule_type(self.listview) == 5:
                        icustomAction = QAction(el.mmodule_name(), self)
                        listActions.append(icustomAction)
                        listActions.append(el)
                        listActions.append(5)
                ii = 0
                for paction in listActions[::3]:
                    paction.triggered.connect(lambda checked, index=ii:self.ficustomAction(listActions[index+1], listActions[index+2]))
                    subm_customAction.addAction(paction)
                    ii += 3
            #
            menu.addSeparator()
            if self.selection and len(self.selection) == 1:
                propertyAction = QAction("Property", self)
                propertyAction.triggered.connect(lambda:self.fpropertyAction(ipath))
                menu.addAction(propertyAction)
            #
            elif self.selection and len(self.selection) > 1:
                propertyAction = QAction("Property", self)
                propertyAction.triggered.connect(self.fpropertyActionMulti)
                menu.addAction(propertyAction)
            #
            menu.exec_(self.listview.mapToGlobal(position))
        ## background
        else:
            #
            if not os.path.exists(DDIR):
                MyDialog("Info", "It doesn't exist.", self)
                return
            #
            self.listview.clearSelection()
            menu = QMenu("Menu", self.listview)
            if MENU_H_COLOR:
                menu.setStyleSheet(self.csa)
            #
            newFolderAction = QAction("New Folder", self)
            newFolderAction.triggered.connect(self.fnewFolderAction)
            menu.addAction(newFolderAction)
            newFileAction = QAction("New File", self)
            newFileAction.triggered.connect(self.fnewFileAction)
            menu.addAction(newFileAction)
            #
            if shutil.which("xdg-user-dir"):
                templateDir = subprocess.check_output(["xdg-user-dir", "TEMPLATES"], universal_newlines=False).decode().strip()
                if not os.path.exists(templateDir):
                    optTemplateDir = os.path.join(os.path.expanduser("~"), "Templates")
                    if os.path.exists(optTemplateDir):
                       templateDir = optTemplateDir
                    else:
                        templateDir = None
                #
                if templateDir:
                    if os.path.exists(templateDir):
                        menu.addSeparator()
                        subm_templatesAction= menu.addMenu("Templates")
                        listTemplate = os.listdir(templateDir)
                        #
                        progActionListT = []
                        for ifile in listTemplate:
                            progActionListT.append(QAction(ifile))
                            progActionListT.append(ifile)
                        ii = 0
                        for paction in progActionListT[::2]:
                            paction.triggered.connect(lambda checked, index=ii:self.ftemplateAction(progActionListT[index+1]))
                            subm_templatesAction.addAction(paction)
                            ii += 2
            #
            pasteNmergeAction = QAction("Paste", self)
            pasteNmergeAction.triggered.connect(lambda d:self.validatePastenMerge(DDIR, -3))
            menu.addAction(pasteNmergeAction)
            #
            menu.addSeparator()
            subm_customAction = menu.addMenu("Actions")
            #
            if len(list_custom_modules) > 0:
                listActions = []
                for el in list_custom_modules:
                    if el.mmodule_type(self.listview) == 4 or el.mmodule_type(self.listview) == 5:
                        bcustomAction = QAction(el.mmodule_name(), self)
                        listActions.append(bcustomAction)
                        listActions.append(el)
                #
                ii = 0
                for paction in listActions[::2]:
                    paction.triggered.connect(lambda checked, index=ii:self.fbcustomAction(listActions[index+1]))
                    subm_customAction.addAction(paction)
                    ii += 2
            #
            if SHOW_EXIT:
                menu.addSeparator()
                reloadAction = QAction("Reload", self)
                reloadAction.triggered.connect(self.restart)
                menu.addAction(reloadAction)
                exitAction = QAction("Exit", self)
                exitAction.triggered.connect(self.winClose)
                menu.addAction(exitAction)
            #
            menu.exec_(self.listview.mapToGlobal(position))
    
    
    # validate the pasteNMerge action upon the number of empty cells
    def validatePastenMerge(self, DDIR, ttype):
        # cells taken
        model_entries = self.model.rowCount()
        # total cells
        total_cells = num_col * num_row - len(reserved_cells)
        if model_entries < total_cells:
            PastenMerge(DDIR, ttype, total_cells - model_entries, self)
        else:
            MyDialog("Info", "Too many items to be placed.", self)
            
    
    # right click on the Recycle Bin
    def trashSelected(self, position):
        menu = QMenu("Menu", self.listview)
        if MENU_H_COLOR:
            menu.setStyleSheet(self.csa)
        #
        openAction = QAction("Open", self)
        openAction.triggered.connect(self.fopenTrashAction)
        menu.addAction(openAction)
        menu.addSeparator()
        emptyAction = QAction("Empty", self)
        emptyAction.triggered.connect(self.femptyTrashAction)
        menu.addAction(emptyAction)
        #
        menu.exec_(self.listview.mapToGlobal(position))
    
    # self.trashSelected
    def fopenTrashAction(self):
        try:
            subprocess.Popen(["./trash_command.sh"])
        except Exception as E:
            MyDialog("Error", str(E), self)
    
    # self.trashSelected
    def femptyTrashAction(self):
        # empty the recycle bin
        ret2 = retDialogBox("Question", "Do you really want to empty the recycle bin?", "", [], self)
        #
        if ret2.getValue():
            ret = trash_module.emptyTrash("HOME").tempty()
            if ret == -2:
                MyDialog("Error", "The Recycle Bin cannot be empty.\nDo it manually.", self)
                return
            if ret == -1:
                MyDialog("Error", "Error with some files in the Recycle Bin.\nTry to remove them manually.", self)
    
    
    # media devices menu
    def mediaSelected(self, position):
        pointedItem = self.listview.indexAt(position)
        menu = QMenu("Menu", self.listview)
        if MENU_H_COLOR:
            menu.setStyleSheet(self.csa)
        #
        openAction = QAction("Open", self)
        openAction.triggered.connect(lambda:self.fopenMediaAction(pointedItem))
        menu.addAction(openAction)
        ejectAction = QAction("Eject", self)
        ejectAction.triggered.connect(lambda:self.fejectMediaAction(pointedItem))
        menu.addAction(ejectAction)
        #
        menu.exec_(self.listview.mapToGlobal(position))
    
    # self.mediaSelected - double click
    def fopenMediaAction(self, pointedItem):
        ddevice = pointedItem.data(Qt.UserRole+2)
        mountpoint = self.get_device_mountpoint(ddevice)
        ret = self.mount_device(mountpoint, ddevice)
        # ret is the mount point
        if ret:
            self.openMedia(ret)
    
    # self.fopenMediaAction
    def openMedia(self, path):
        if os.access(path, os.R_OK):
            try:
                defApp = getDefaultApp(path, self).defaultApplication()
                if defApp != "None":
                    subprocess.Popen([defApp, path])
                else:
                    MyDialog("Info", "No programs found.", self)
            except Exception as E:
                MyDialog("Error", str(E), self)
        else:
            MyDialog("Error", path+"\n\n   Not readable", self)
    
    # self.mediaSelected
    def fejectMediaAction(self, index):
        self.eject_media(index)
    
    
    # menu for desktop file
    def desktopSelected(self, position):
        pointedItem = self.listview.indexAt(position)
        menu = QMenu("Menu", self.listview)
        if MENU_H_COLOR:
            menu.setStyleSheet(self.csa)
        #
        # name - icon - exec - type
        ddata = pointedItem.data(Qt.UserRole+2)
        if ddata[3] == "Application":
            openAction = QAction("Launch", self)
        elif ddata[3] in ["Directory", "Link"]:
            openAction = QAction("Open", self)
        openAction.triggered.connect(lambda:self.flaunchDesktop(pointedItem))
        menu.addAction(openAction)
        menu.addSeparator()
        deleteAction = QAction("Delete", self)
        deleteAction.triggered.connect(lambda:self.fdeleteDesktopAction(pointedItem))
        menu.addAction(deleteAction)
        if ddata[3] in ["Directory", "Link"]:
            menu.addSeparator()
            pathAction = QAction("Path", self)
            pathAction.triggered.connect(lambda:MyDialog("Info", ddata[2][7:] , self))
            menu.addAction(pathAction)
        #
        menu.exec_(self.listview.mapToGlobal(position))
    
    # self.desktopSelected
    def fdeleteDesktopAction(self, pointedItem):
        dname = pointedItem.data(Qt.UserRole+2)[0]
        dpath = os.path.join(DDIR, dname)
        try:
            os.remove(dpath)
        except Exception as E:
            MyDialog("Error", str(E), self)
    
    
    # launch a program from its desktop file
    def flaunchDesktop(self, index):
        # name - icon - exec - type
        ddata = index.data(Qt.UserRole+2)
        if ddata[3] == "Application":
            dexec = ddata[2]
            if shutil.which(dexec):
                try:
                    subprocess.Popen([dexec])
                except Exception as E:
                    MyDialog("Error", str(E), self)
            else:
                MyDialog("Info", "The program {} cannot be found.".format(dexec), self)
        elif ddata[3] == "Directory" or ddata[3] == "Link":
            try:
                dirpath = unquote(ddata[2])[7:]
                if not os.path.exists(dirpath):
                    MyDialog("Info", "The folder {} cannot be found.".format(os.path.basename(dirpath)), self)
                    return
                defApp = getDefaultApp(dirpath, self).defaultApplication()
                if defApp != "None":
                    subprocess.Popen([defApp, dirpath])
                else:
                    MyDialog("Info", "No programs found.", self)
            except Exception as E:
                MyDialog("Error", str(E), self)
    
    # 
    def ficustomAction(self, el, menuType):
        if menuType == 1:
            items_list = []
            items_list.append(os.path.join(DDIR, self.selection[0].data(0)))
            el.ModuleCustom(self.listview)
        elif menuType == 2:
            items_list = []
            for iitem in self.selection:
                items_list.append(os.path.join(DDIR, iitem.data(0)))
            el.ModuleCustom(self.listview)
        elif menuType == 3:
            items_list = []
            for iitem in self.selection:
                items_list.append(os.path.join(DDIR, iitem.data(0)))
            el.ModuleCustom(self.listview)
        elif menuType == 5:
            items_list = []
            for iitem in self.selection:
                items_list.append(os.path.join(DDIR, iitem.data(0)))
            el.ModuleCustom(self.listview)
    
    
    def fbcustomAction(self, el):
        el.ModuleCustom(self.listview)
    
    
    # launch the application choosen
    def fprogAction(self, iprog, path):
        try:
            subprocess.Popen([iprog, path])
        except Exception as E:
            MyDialog("Error", str(E), self)
    
    
    # show a menu with all the installed applications
    def fotherAction(self, itemPath):
        if OPEN_WITH:
            self.cw = OW.listMenu(itemPath)
            self.cw.show()
        else:
            ret = otherApp(itemPath, self).getValues()
            if ret == -1:
                return
            if shutil.which(ret):
                try:
                    subprocess.Popen([ret, itemPath])
                except Exception as E:
                    MyDialog("Error", str(E), self)
            else:
                MyDialog("Info", "The program\n"+ret+"\ncannot be found", self)
    
    
    #
    def fcopycutAction(self, action):
        if action == "copy":
            item_list = "copy\n"
        elif action == "cut":
            item_list = "cut\n"
        #
        for iindex in self.selection:
            iname = iindex.data(0)
            iname_fp = os.path.join(DDIR, iname)
            # readable or broken link
            if os.access(iname_fp,os.R_OK) or os.path.islink(iname_fp):
                iname_quoted = quote(iname, safe='/:?=&')
                if iindex != self.selection[-1]:
                    iname_final = "file://{}\n".format(os.path.join(DDIR, iname_quoted))
                    item_list += iname_final
                else:
                    iname_final = "file://{}".format(os.path.join(DDIR, iname_quoted))
                    item_list += iname_final
        #
        if item_list == "copy\n":
            clipboard = QApplication.clipboard()
            clipboard.clear()
            return
        #
        clipboard = QApplication.clipboard()
        data = QByteArray()
        data.append(bytes(item_list, encoding="utf-8"))
        qmimdat = QMimeData()
        qmimdat.setData("x-special/gnome-copied-files", data)
        clipboard.setMimeData(qmimdat, QClipboard.Clipboard)
    
    
    # send to trash the selected items
    def ftrashAction(self):
        if self.selection:
            list_items = []
            for item in self.selection:
                # skip special entries
                if item.data(Qt.UserRole+1) in special_entries:
                    continue
                list_items.append(os.path.join(DDIR, item.data(0)))
            #
            if not list_items:
                return
            dialogList = ""
            for item in list_items:
                dialogList += os.path.basename(item)+"\n"
            ret = retDialogBox("Question", "Do you really want to move these items to the trashcan?", "", dialogList, self)
            #
            if ret.getValue():
                TrashModule(list_items, self)
                self.listview.viewport().update()
    
    
    # bypass the trashcan
    def fdeleteAction(self):
        if self.selection:
            list_items = []
            for item in self.selection:
                list_items.append(os.path.join(DDIR, item.data(0)))
            #
            dialogList = ""
            for item in list_items:
                dialogList += os.path.basename(item)+"\n"
            ret = retDialogBox("Question", "Do you really want to delete these items?", "", dialogList, self)
            #
            if ret.getValue():
                self.fdeleteItems(list_items)
                self.listview.viewport().update()
    
    # related to self.fdeleteAction
    def fdeleteItems(self, listItems):
        # something happened with some items
        items_skipped = ""
        #
        for item in listItems:
            time.sleep(0.1)
            if os.path.islink(item):
                try:
                    os.remove(item)
                except Exception as E:
                    items_skipped += os.path.basename(item)+"\n"+str(E)+"\n\n"
            elif os.path.isfile(item):
                try:
                    os.remove(item)
                except Exception as E:
                    items_skipped += os.path.basename(item)+"\n"+str(E)+"\n\n"
            elif os.path.isdir(item):
                try:
                    shutil.rmtree(item)
                except Exception as E:
                    items_skipped += os.path.basename(item)+"\n"+str(E)+"\n\n"
            # not regular files or folders 
            else:
                items_skipped += os.path.basename(item)+"\n"+"Only files and folders can be deleted."+"\n\n"
        #
        if items_skipped != "":
            MyMessageBox("Info", "Items not deleted:", "", items_skipped, self)
    
    
    # from contextual menu
    def frenameAction(self, ipath):
        ibasename = os.path.basename(ipath)
        idirname = os.path.dirname(ipath)
        inew_name = self.wrename2(ibasename, idirname)
        #
        if inew_name != -1:
            try:
                shutil.move(ipath, inew_name)
            except Exception as E:
                MyDialog("Error", str(E), self)
    
    # from contextual menu
    def wrename2(self, ditem, dest_path):
        ret = ditem
        ret = MyDialogRename2(ditem, dest_path, self).getValues()
        if ret == -1:
                return ret
        elif not ret:
            return -1
        else:
            return os.path.join(dest_path, ret)
            
    
    def fpropertyAction(self, ipath):
        propertyDialog(ipath, self)
    
    
    def fpropertyActionMulti(self):
        # size of all the selected items
        iSize = 0
        # number of the selected items
        iNum = len(self.selection)
        for iitem in self.selection:
            if iitem.data(Qt.UserRole+1) in special_entries:
                iNum -= 1
                continue
            try:
                item = os.path.join(DDIR, item.data(0))
                #
                if os.path.islink(item):
                    iSize += 512
                elif os.path.isfile(item):
                    iSize += QFileInfo(item).size()
                elif os.path.isdir(item):
                    iSize += folder_size(item)
                else:
                    QFileInfo(item).size()
            except:
                iSize += 0
        #
        propertyDialogMulti(convert_size(iSize), iNum, self)
        
    
    # create a new folder
    def fnewFolderAction(self):
        if os.access(DDIR, os.W_OK): 
            ret = self.wrename3("New Folder", DDIR)
            if ret != -1 or not ret:
                destPath = os.path.join(DDIR, ret)
                if not os.path.exists(destPath):
                    try:
                        os.mkdir(destPath)
                    except Exception as E:
                        MyDialog("Error", str(E), self)
    
    # crate a text file
    def fnewFileAction(self):
        if os.access(DDIR, os.W_OK): 
            ret = self.wrename3("Text file.txt", DDIR)
            if ret != -1 or not ret:
                destPath = os.path.join(DDIR, ret)
                if not os.path.exists(destPath):
                    try:
                        iitem = open(destPath,'w')
                        iitem.close()
                    except Exception as E:
                        MyDialog("Error", str(E), self)
    
    
    # copy the template choosen - the rename dialog appears
    def ftemplateAction(self, templateName):
        templateDir = None
        if shutil.which("xdg-user-dir"):
            templateDir = subprocess.check_output(["xdg-user-dir", "TEMPLATES"], universal_newlines=False).decode().strip()
            if not os.path.exists(templateDir):
                optTemplateDir = os.path.join(os.path.expanduser("~"), "Templates")
                if os.path.exists(optTemplateDir):
                   templateDir = optTemplateDir
        #
        if os.access(DDIR, os.W_OK): 
            ret = self.wrename3(templateName, DDIR)
            if ret != -1 or not ret:
                destPath = os.path.join(DDIR, ret)
                if not os.path.exists(destPath):
                    try:
                        shutil.copy(os.path.join(templateDir, templateName), destPath)
                    except Exception as E:
                        MyDialog("Error", str(E), self)
    
    # new file or folder
    def wrename3(self, ditem, dest_path):
        ret = MyDialogRename3(ditem, DDIR, self).getValues()
        if ret == -1:
                return ret
        elif not ret:
            return -1
        else:
            return ret
    

    def winClose(self):
        global stopCD
        stopCD = 1
        time.sleep(1)
        qApp.quit()

    def restart(self):
        QCoreApplication.quit()
        status = QProcess.startDetached(sys.executable, sys.argv)

################

    

# dialog - for file with the execution bit
class execfileDialog(QDialog):
    def __init__(self, itemPath, flag, parent):
        super(execfileDialog, self).__init__(parent)
        self.itemPath = itemPath
        self.flag = flag
        #
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle("Info")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(DIALOGWIDTH, 100)
        #
        vbox = QBoxLayout(QBoxLayout.TopToBottom)
        vbox.setContentsMargins(5,5,5,5)
        self.setLayout(vbox)
        #
        label1 = QLabel("This is an executable file.\nWhat do you want to do?")
        vbox.addWidget(label1)
        hbox = QBoxLayout(QBoxLayout.LeftToRight)
        vbox.addLayout(hbox)
        #
        if self.flag == 0 or self.flag == 3:
            button1 = QPushButton("Open")
            hbox.addWidget(button1)
            button1.clicked.connect(self.fopen)
        if self.flag != 3:
            button2 = QPushButton("Execute")
            hbox.addWidget(button2)
            button2.clicked.connect(self.fexecute)
        button3 = QPushButton("Cancel")
        hbox.addWidget(button3)
        button3.clicked.connect(self.fcancel)
        self.Value = 0
        self.exec_()

    def getValue(self):
        return self.Value

    def fopen(self):
        self.Value = 1
        self.close()
    
    def fexecute(self):
        self.Value = 2
        self.close()
    
    def fcancel(self):
        self.Value = -1
        self.close()

# find the default application for a given mimetype if any
# using xdg-mime
class getDefaultApp():
    
    def __init__(self, path, window):
        self.path = path
        self.window = window
        
    def defaultApplication(self):
        ret = shutil.which("xdg-mime")
        if ret:
            imime = QMimeDatabase().mimeTypeForFile(self.path, QMimeDatabase.MatchDefault).name()
            #
            if imime in ["application/x-zerosize", "application/x-trash"]:
                mimetype = "text/plain"
            else:
                mimetype = imime
            #
            associatedDesktopProgram = None
            #
            if USER_MIMEAPPSLIST:
                #
                try:
                    associatedDesktopProgram = subprocess.check_output([ret, "query", "default", mimetype], universal_newlines=False).decode()
                except:
                    return "None"
            else:
                associatedDesktopProgram = self.defaultApplication2(mimetype)
            #
            if associatedDesktopProgram:
                for ddir in xdgDataDirs:
                    if ddir[-1] == "/":
                        ddir = ddir[:-1]
                    desktopPath = os.path.join(ddir+"/applications", associatedDesktopProgram.strip())
                    #
                    if os.path.exists(desktopPath):
                        applicationName2 = DesktopEntry(desktopPath).getExec()
                        if applicationName2:
                            applicationName = applicationName2.split()[0]
                        else:
                            return "None"
                        applicationPath = shutil.which(applicationName)
                        if applicationPath:
                            if os.path.exists(applicationPath):
                                return applicationPath
                            else:
                                MyDialog("Error", "{} cannot be found".format(applicationPath), self.window)
                        else:
                            return "None"
                #
                # no apps found
                return "None"
            else:
                return "None"
        #
        else:
            MyDialog("Error", "xdg-mime cannot be found", self.window)
        
    # function that found the default program for the given mimetype
    def defaultApplication2(self, mimetype):
        # lists of mimetypes added or removed
        lista = []
        # all the file in lista: one row one item added to lista
        with open(MIMEAPPSLIST, "r") as f:
            lista = f.readlines()
        # marker
        x = ""
        for el in lista:
            if el == "[Added Associations]\n":
                x = "A"
            elif el == "[Removed Associations]\n":
                x = "R"
            elif el == "[Default Applications]\n":
                x = "D"
            #
            if x == "D":
                if el:
                    if el == "\n":
                        continue
                    if el[0:len(mimetype)+1] == mimetype+"=":
                        desktop_file = el.split("=")[1].strip("\n").strip(";")
                        return desktop_file
        # nothing found
        return "None"
        

# find the applications installed for a given mimetype
class getAppsByMime():
    def __init__(self, path):
        self.path = path
        # three list from mimeapps.list: association added and removed and default applications
        self.lA = []
        self.lR = []
        self.lD = []
        # path of the mimeapps.list
        self.MIMEAPPSLIST = MIMEAPPSLIST

    
    def appByMime(self):
        listPrograms = []
        imimetype = QMimeDatabase().mimeTypeForFile(self.path, QMimeDatabase.MatchDefault).name()
        if imimetype != "application/x-zerosize":
            mimetype = imimetype
        else:
            mimetype = "text/plain"
        # the action for the mimetype also depends on the file mimeapps.list in the home folder 
        #lAdded,lRemoved,lDefault = self.addMime(mimetype)
        lAdded,lRemoved = self.addMime(mimetype)
        #
        for ddir in xdgDataDirs:
            applicationsPath = os.path.join(ddir, "applications")
            if os.path.exists(applicationsPath):
                desktopFiles = os.listdir(applicationsPath)
                for idesktop in desktopFiles:
                    if idesktop.endswith(".desktop"):
                        # skip the removed associations
                        if idesktop in lRemoved:
                            continue
                        desktopPath = os.path.join(ddir+"/applications", idesktop)
                        # consinstency - do not crash if the desktop file is malformed
                        try:
                            if mimetype in DesktopEntry(desktopPath).getMimeTypes():
                                mimeProg2 = DesktopEntry(desktopPath).getExec()
                                # replace $HOME with home path
                                if mimeProg2[0:5].upper() == "$HOME":
                                    mimeProg2 = os.path.expanduser("~")+"/"+mimeProg2[5:]
                                # replace ~ with home path
                                elif mimeProg2[0:1] == "~":
                                    mimeProg2 = os.path.expanduser("~")+"/"+mimeProg2[1:]
                                #
                                if mimeProg2:
                                    mimeProg = mimeProg2.split()[0]
                                else:
                                    # return
                                    continue
                                retw = shutil.which(mimeProg)
                                #
                                if retw is not None:
                                    if os.path.exists(retw):
                                        listPrograms.append(retw)
                                        try:
                                            progName = DesktopEntry(desktopPath).getName()
                                            if progName != "":
                                                listPrograms.append(progName)
                                            else:
                                                listPrograms.append("None")
                                        except:
                                            listPrograms.append("None")
                        except Exception as E:
                            MyDialog("Error", str(E), self.window)
        # 
        # from the lAdded list
        for idesktop in lAdded:
            # skip the removed associations
            if idesktop in lRemoved:
                continue
            desktopPath = ""
            #
            # check if the idesktop is in xdgDataDirs - use it if any
            for ddir in xdgDataDirs:
                applicationsPath = os.path.join(ddir, "applications")
                if os.path.exists(applicationsPath):
                    if idesktop in os.listdir(applicationsPath):
                        desktopPath = os.path.join(applicationsPath, idesktop)
            #
            mimeProg2 = DesktopEntry(desktopPath).getExec()
            #
            if mimeProg2:
                mimeProg = mimeProg2.split()[0]
            else:
                continue
            retw = shutil.which(mimeProg)
            if retw is not None:
                if os.path.exists(retw):
                    # skip the existent applications
                    if retw in listPrograms:
                        continue
                    listPrograms.append(retw)
                    try:
                        progName = DesktopEntry(desktopPath).getName()
                        if progName != "":
                            listPrograms.append(progName)
                        else:
                            listPrograms.append("None")
                    except:
                         listPrograms.append("None")
        #
        return listPrograms


    # function that return mimetypes added and removed (and default applications) in the mimeappss.list
    def addMime(self, mimetype):
        # call the function
        self.fillL123()
        #
        lAdded = []
        lRemoved = []
        lDefault = []
        #
        for el in self.lA:
            if mimetype in el:
                # item is type list
                item = el.replace(mimetype+"=","").strip("\n").split(";")
                lAdded = self.delNull(item)
        #
        for el in self.lR:
            if mimetype in el:
                item = el.replace(mimetype+"=","").strip("\n").split(";")
                lRemoved = self.delNull(item)
        #
        for el in self.lD:
            if mimetype in el:
                item = el.replace(mimetype+"=","").strip("\n").split(";")
                lDefault = self.delNull(item)
        #
        #return lAdded,lRemoved,lDefault
        return lAdded,lRemoved

    # function that return mimetypes added, removed in the mimeappss.list
    def fillL123(self):
        # mimeapps.list can have up to three not mandatory sectors
        # lists of mimetypes added or removed - reset
        lAdded = []
        lRemoved = []
        lDefault = []
        lista = []
        #
        # reset
        lA1 = []
        lR1 = []
        lD1 = []
        #
        if not os.path.exists(self.MIMEAPPSLIST):
            return
        #
        # all the file in lista: one row one item added to lista
        with open(self.MIMEAPPSLIST, "r") as f:
            lista = f.readlines()
        #
        # marker
        x = ""
        for el in lista:
            if el == "[Added Associations]\n":
                x = "A"
            elif el == "[Removed Associations]\n":
                x = "R"
            elif el == "[Default Applications]\n":
                x = "D"
            #
            if el:
                if x == "A":
                    lA1.append(el)
                elif x == "R":
                    lR1.append(el)
                elif x == "D":
                    lD1.append(el) 
        #
        # attributions
        self.lA = lA1
        self.lR = lR1
        self.lD = lD1


    # remove the null elements in the list
    def delNull(self,e):
        return [i for i in e if i != ""]


# dialog - open a file with another program
class otherApp(QDialog):

    def __init__(self, itemPath, parent):
        super(otherApp, self).__init__(parent)
        #
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle("Other application")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(DIALOGWIDTH,100)
        #
        grid = QGridLayout()
        grid.setContentsMargins(5,5,5,5)
        #
        label1 = QLabel("\nChoose the application:")
        grid.addWidget(label1, 0, 0, Qt.AlignCenter)
        #
        self.lineedit = QLineEdit()
        grid.addWidget(self.lineedit, 1, 0)
        #
        button_box = QBoxLayout(QBoxLayout.LeftToRight)
        grid.addLayout(button_box, 2, 0)
        #
        button1 = QPushButton("OK")
        button_box.addWidget(button1)
        button1.clicked.connect(self.faccept)
        #
        button3 = QPushButton("Cancel")
        button_box.addWidget(button3)
        button3.clicked.connect(self.fcancel)
        #
        self.setLayout(grid)
        self.Value = -1
        self.exec_()
        
    def getValues(self):
        return self.Value
    
    def faccept(self):
        if self.lineedit.text() != "":
            self.Value = self.lineedit.text()
            self.close()
    
    def fcancel(self):
        self.Value = -1
        self.close()
        

# renaming dialog - from listview contextual menu - Paste and Merge
class MyDialogRename2(QDialog):
    def __init__(self, *args):
        super(MyDialogRename2, self).__init__(args[-1])
        self.item_name = args[0]
        self.dest_path = args[1]
        self.itemPath = os.path.join(self.dest_path, self.item_name)
        #
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle("Rename")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(DIALOGWIDTH,300)
        #
        mbox = QBoxLayout(QBoxLayout.TopToBottom)
        mbox.setContentsMargins(5,5,5,5)
        self.setLayout(mbox)
        #
        label1 = QLabel("Old name:")
        mbox.addWidget(label1)
        #
        label2 = clabel2()
        label2.setText(self.item_name, self.size().width()-12)
        mbox.addWidget(label2)
        #
        label3 = QLabel("New name:")
        mbox.addWidget(label3)
        #
        self.lineedit = QLineEdit()
        self.lineedit.setText(self.item_name)
        self.lineedit.setCursorPosition(0)
        args_basename = QFileInfo(self.item_name).baseName()
        len_args_basename = len(args_basename)
        self.lineedit.setSelection(0 , len_args_basename)
        mbox.addWidget(self.lineedit)
        #
        box = QBoxLayout(QBoxLayout.LeftToRight)
        mbox.addLayout(box)
        #
        button1 = QPushButton("OK")
        box.addWidget(button1)
        button1.clicked.connect(lambda:self.faccept(self.item_name))
        #
        button3 = QPushButton("Cancel")
        box.addWidget(button3)
        button3.clicked.connect(self.fcancel)
        #
        self.Value = ""
        self.exec_()
    
    def getValues(self):
        return self.Value
    
    def faccept(self, item_name):
        newName = self.lineedit.text()
        if newName != "":
            if newName != item_name:
                if not os.path.exists(os.path.join(self.dest_path, newName)):
                    self.Value = self.lineedit.text()
                    self.close()
    
    def fcancel(self):
        self.Value = -1
        self.close()


# renaming dialog - when a new file is been created
class MyDialogRename3(QDialog):
    def __init__(self, *args):
        super(MyDialogRename3, self).__init__(args[-1])
        #
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle("Set a new name")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(DIALOGWIDTH,300)
        #
        mbox = QBoxLayout(QBoxLayout.TopToBottom)
        mbox.setContentsMargins(5,5,5,5)
        self.setLayout(mbox)
        #
        label1 = QLabel("Choose a new name:")
        mbox.addWidget(label1)
        #
        self.lineedit = QLineEdit()
        self.lineedit.setText(args[0])
        self.lineedit.setCursorPosition(0)
        args_basename = QFileInfo(args[0]).baseName()
        len_args_basename = len(args_basename)
        self.lineedit.setSelection(0 , len_args_basename)
        mbox.addWidget(self.lineedit)
        #
        box = QBoxLayout(QBoxLayout.LeftToRight)
        mbox.addLayout(box)
        #
        button1 = QPushButton("OK")
        box.addWidget(button1)
        button1.clicked.connect(lambda:self.faccept(args[0], args[1]))
        #
        button3 = QPushButton("Cancel")
        box.addWidget(button3)
        button3.clicked.connect(self.fcancel)
        #
        self.Value = ""
        self.exec_()

    def getValues(self):
        return self.Value
    
    def faccept(self, item_name, destDir):
        if self.lineedit.text() != "":
            if not os.path.exists(os.path.join(destDir, self.lineedit.text())):
                self.Value = self.lineedit.text()
                self.close()
    
    def fcancel(self):
        self.Value = -1
        self.close()
        

###############

# property dialog for one item
class propertyDialog(QDialog):
    def __init__(self, itemPath, parent):
        super(propertyDialog, self).__init__(parent)
        self.itemPath = itemPath
        self.window = parent
        #
        self.imime = ""
        self.imime = QMimeDatabase().mimeTypeForFile(self.itemPath, QMimeDatabase.MatchDefault)
        # the external program pkexec is used
        self.CAN_CHANGE_OWNER = 0
        if shutil.which("pkexec"):
            self.CAN_CHANGE_OWNER = 1
        #
        storageInfo = QStorageInfo(self.itemPath)
        storageInfoIsReadOnly = storageInfo.isReadOnly()
        #
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle("Property")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(DIALOGWIDTH, 100)
        #
        vbox = QBoxLayout(QBoxLayout.TopToBottom)
        vbox.setContentsMargins(5,5,5,5)
        self.setLayout(vbox)
        #
        self.gtab = QTabWidget()
        self.gtab.setContentsMargins(5,5,5,5)
        self.gtab.setMovable(False)
        self.gtab.setElideMode(Qt.ElideRight)
        self.gtab.setTabsClosable(False)
        vbox.addWidget(self.gtab)
        #
        page1 = QWidget()
        self.gtab.addTab(page1, "General")
        self.grid1 = QGridLayout()
        page1.setLayout(self.grid1)
        #
        labelName = QLabel("<i>Name</i>")
        self.grid1.addWidget(labelName, 0, 0, 1, 1, Qt.AlignRight)
        self.labelName2 = clabel2()
        self.labelName2.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.grid1.addWidget(self.labelName2, 0, 1, 1, 4, Qt.AlignLeft)
        #
        labelMime = QLabel("<i>MimeType</i>")
        self.grid1.addWidget(labelMime, 2, 0, 1, 1, Qt.AlignRight)
        self.labelMime2 = QLabel()
        self.grid1.addWidget(self.labelMime2, 2, 1, 1, 4, Qt.AlignLeft)
        #
        if os.path.isfile(itemPath) or os.path.isdir(itemPath):
            labelOpenWith = QLabel("<i>Open With...</i>")
            self.grid1.addWidget(labelOpenWith, 3, 0, 1, 1, Qt.AlignRight)
            self.btnOpenWith = QPushButton("----------")
            self.btnOpenWith.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            self.btnOpenWith.clicked.connect(self.fbtnOpenWith)
            self.grid1.addWidget(self.btnOpenWith, 3, 1, 1, 4, Qt.AlignLeft)
            self.btnOpenWithPopulate()
        #
        labelSize = QLabel("<i>Size</i>")
        self.grid1.addWidget(labelSize, 4, 0, 1, 1, Qt.AlignRight)
        self.labelSize2 = QLabel()
        self.grid1.addWidget(self.labelSize2, 4, 1, 1, 4, Qt.AlignLeft)
        #
        if not os.path.exists(self.itemPath):
            if os.path.islink(self.itemPath):
                self.labelName2.setText(os.path.basename(self.itemPath), self.size().width()-12)
                self.labelMime2.setText("Broken link")
                labelSize.hide()
                self.labelSize2.hide()
                label_real_link = QLabel("<i>To Path</i>")
                self.grid1.addWidget(label_real_link, 5, 0, 1, 1, Qt.AlignRight)
                label_real_link2 = clabel2()
                label_real_link2.setText(os.path.realpath(self.itemPath), self.size().width()-12)
                self.grid1.addWidget(label_real_link2, 5, 1, 1, 4, Qt.AlignLeft)
                self.adjustSize()
                self.exec_()
        elif os.path.exists(self.itemPath):
            if os.path.islink(self.itemPath):
                label_real_link = QLabel("<i>To Path</i>")
                self.grid1.addWidget(label_real_link, 5, 0, 1, 1, Qt.AlignRight)
                label_real_link2 = clabel2()
                label_real_link2.setText(os.path.realpath(self.itemPath), self.size().width()-12)
                self.grid1.addWidget(label_real_link2, 5, 1, 1, 4, Qt.AlignLeft)
            #
            labelCreation = QLabel("<i>Creation</i>")
            self.grid1.addWidget(labelCreation, 6, 0, 1, 1, Qt.AlignRight)
            self.labelCreation2 = QLabel()
            self.grid1.addWidget(self.labelCreation2, 6, 1, 1, 4, Qt.AlignLeft)
            #
            labelModification = QLabel("<i>Modification</i>")
            self.grid1.addWidget(labelModification, 7, 0, 1, 1, Qt.AlignRight)
            self.labelModification2 = QLabel()
            self.grid1.addWidget(self.labelModification2, 7, 1, 1, 4, Qt.AlignLeft)
            #
            labelAccess = QLabel("<i>Access</i>")
            self.grid1.addWidget(labelAccess, 8, 0, 1, 1, Qt.AlignRight)
            self.labelAccess2 = QLabel()
            self.grid1.addWidget(self.labelAccess2, 8, 1, 1, 4, Qt.AlignLeft)
            ###### tab 2
            page2 = QWidget()
            self.gtab.addTab(page2, "Permissions")
            vboxp2 = QBoxLayout(QBoxLayout.TopToBottom)
            page2.setLayout(vboxp2)
            #
            gBox1 = QGroupBox("Ownership")
            vboxp2.addWidget(gBox1)
            self.grid2 = QGridLayout()
            gBox1.setLayout(self.grid2)
            #
            labelgb11 = QLabel("<i>Owner</i>")
            self.grid2.addWidget(labelgb11, 0, 0, 1, 1, Qt.AlignRight)
            self.labelgb12 = QLabel()
            self.grid2.addWidget(self.labelgb12, 0, 1, 1, 5, Qt.AlignLeft)
            #
            labelgb21 = QLabel("<i>Group</i>")
            self.grid2.addWidget(labelgb21, 1, 0, 1, 1, Qt.AlignRight)
            self.labelgb22 = QLabel()
            self.grid2.addWidget(self.labelgb22, 1, 1, 1, 5, Qt.AlignLeft)
            #
            gBox2 = QGroupBox("Permissions")
            vboxp2.addWidget(gBox2)
            self.grid3 = QGridLayout()
            gBox2.setLayout(self.grid3)
            if storageInfoIsReadOnly:
                gBox2.setEnabled(False)
            #
            labelOwnerPerm = QLabel("<i>Owner</i>")
            self.grid3.addWidget(labelOwnerPerm, 0, 0, 1, 1, Qt.AlignRight)
            self.combo1 = QComboBox()
            self.combo1.addItems(["Read and Write", "Read", "Forbidden"])
            self.grid3.addWidget(self.combo1, 0, 1, 1, 5, Qt.AlignLeft)
            #
            labelGroupPerm = QLabel("<i>Group</i>")
            self.grid3.addWidget(labelGroupPerm, 1, 0, 1, 1, Qt.AlignRight)
            self.combo2 = QComboBox()
            self.combo2.addItems(["Read and Write", "Read", "Forbidden"])
            self.grid3.addWidget(self.combo2, 1, 1, 1, 5, Qt.AlignLeft)
            #
            labelOtherPerm = QLabel("<i>Others</i>")
            self.grid3.addWidget(labelOtherPerm, 2, 0, 1, 1, Qt.AlignRight)
            self.combo3 = QComboBox()
            self.combo3.addItems(["Read and Write", "Read", "Forbidden"])
            self.grid3.addWidget(self.combo3, 2, 1, 1, 5, Qt.AlignLeft)
            #
            self.combo1.activated.connect(self.fcombo1)
            self.combo2.activated.connect(self.fcombo2)
            self.combo3.activated.connect(self.fcombo3)
            #
            # change owner button
            self.own_btn = QPushButton("Change")
            if self.CAN_CHANGE_OWNER:
                self.own_btn.clicked.connect(lambda:self.on_change_owner(me = os.path.basename(os.getenv("HOME"))))
            self.grid2.addWidget(self.own_btn, 0, 6, 1, 1, Qt.AlignLeft)
            # change group button
            self.grp_btn = QPushButton("Change")
            if self.CAN_CHANGE_OWNER:
                self.grp_btn.clicked.connect(lambda:self.on_change_grp(me = os.path.basename(os.getenv("HOME"))))
            self.grid2.addWidget(self.grp_btn, 1, 6, 1, 1, Qt.AlignLeft)
            # folder access - file executable
            self.cb1 = QCheckBox()
            ## set the initial state
            fileInfo = QFileInfo(self.itemPath)
            perms = fileInfo.permissions()
            # folder access - file execution
            if perms & QFile.ExeOwner:
                self.cb1.setChecked(True)
            #
            self.cb1.stateChanged.connect(self.fcb1)
            self.grid3.addWidget(self.cb1, 4, 0, 1, 5, Qt.AlignLeft)
            # immutable file button
            self.ibtn = QPushButton()
            self.ibtn.clicked.connect(self.ibtn_pkexec)
            self.grid3.addWidget(self.ibtn, 4, 6, 1, 1, Qt.AlignLeft)
            #
            button1 = QPushButton("OK")
            button1.clicked.connect(self.faccept)
            #
            hbox = QBoxLayout(QBoxLayout.LeftToRight)
            vbox.addLayout(hbox)
            hbox.addWidget(button1)
            # populate all
            self.tab()
            self.adjustSize()
            self.exec_()
    
    #
    # def comboOpenWithPopulate(self):
    def btnOpenWithPopulate(self):
        self.defApp = getDefaultApp(self.itemPath, self).defaultApplication()
        listPrograms_temp = getAppsByMime(self.itemPath).appByMime()
        self.listPrograms = []
        for i in range(0, len(listPrograms_temp), 2):
            self.listPrograms.append([listPrograms_temp[i], listPrograms_temp[i+1]])
        if self.listPrograms:
            for i in range(len(self.listPrograms)):
                if self.listPrograms[i][0] == self.defApp:
                    self.btnOpenWith.setText(self.listPrograms[i][1])
        else:
            self.btnOpenWith.setText("----------")

    
    # see comboOpenWithPopulate
    def fbtnOpenWith(self):
        if self.imime or not self.imime.isNull():
            from Utility import assmimeL as AL
            self.AW = AL.MainWin(self.imime.name(), self)
            if self.AW.exec_() == QDialog.Accepted:
                ret = self.AW.getValue()
                if ret:
                    self.btnOpenWithPopulate()
        
        
    # set or unset the immutable flag
    def ibtn_pkexec(self):
        # unset
        if "i" in subprocess.check_output(['lsattr', self.itemPath]).decode()[:19]:
            ret = None
            try:
                ret = subprocess.run(["pkexec", "chattr", "-i", self.itemPath])
            except:
                pass
            # if success
            if ret:
                if ret.returncode == 0:
                    try:
                        if "i" not in subprocess.check_output(['lsattr', self.itemPath]).decode()[:19]:
                            self.ibtn.setText("Not Immutable")
                    except:
                        pass
        # set
        else:
            ret = None
            try:
                ret = subprocess.run(["pkexec", "chattr", "+i", self.itemPath])
            except:
                pass
            # if success
            if ret:
                if ret.returncode == 0:
                    try:
                        if "i" in subprocess.check_output(['lsattr', self.itemPath]).decode()[:19]:
                            self.ibtn.setText("Immutable")
                    except:
                        pass
        # repopulate
        self.tab()
        
    
    # populate the property dialog
    def tab(self):
        # folder access - file executable
        if os.path.isdir(self.itemPath):
            self.cb1.setText('folder access')
        elif os.path.isfile(self.itemPath):
            self.cb1.setText('Executable')
        else:
            self.cb1.setText('Executable')
        #
        # set or unset the immutable flag
        if self.CAN_CHANGE_OWNER:
            if os.access(self.itemPath, os.R_OK):
                if os.path.isfile(self.itemPath) and not os.path.islink(self.itemPath):
                    try:
                        if "i" in subprocess.check_output(['lsattr', self.itemPath]).decode()[:19]:
                            self.ibtn.setText("Immutable")
                        else:
                            self.ibtn.setText("Not Immutable")
                    except:
                        self.ibtn.setEnabled(False)
                        self.ibtn.hide()
                else:
                    self.ibtn.setEnabled(False)
                    self.ibtn.hide()
            else:
                self.ibtn.setEnabled(False)
                self.ibtn.hide()
        else:
            self.ibtn.setEnabled(False)
            self.ibtn.hide()
        #
        fileInfo = QFileInfo(self.itemPath)
        self.labelName2.setText(fileInfo.fileName(), self.size().width()-12)
        self.labelMime2.setText(self.imime.name())
        #
        if not os.path.exists(self.itemPath):
            if os.path.islink(self.itemPath):
                self.labelSize2.setText("(Broken Link)")
            else:
                self.labelSize2.setText("Unrecognizable")
        if os.path.isfile(self.itemPath):
            if os.access(self.itemPath, os.R_OK):
                self.labelSize2.setText(convert_size(QFileInfo(self.itemPath).size()))
            else:
                self.labelSize2.setText("(Not readable)")
        elif os.path.isdir(self.itemPath):
            if os.access(self.itemPath, os.R_OK):
                self.labelSize2.setText(str(convert_size(folder_size(self.itemPath))))
            else:
                self.labelSize2.setText("(Not readable)")
        else:
            self.labelSize2.setText("0")
        #
        if os.path.exists(self.itemPath):
            if DATE_TIME == 0:
                mctime = datetime.datetime.fromtimestamp(os.stat(self.itemPath).st_ctime).strftime('%c')
            elif DATE_TIME == 1:
                try:
                    mctime1 = subprocess.check_output(["stat", "-c", "%W", self.itemPath], universal_newlines=False).decode()
                    mctime2 = subprocess.check_output(["date", "-d", "@{}".format(mctime1)], universal_newlines=False).decode()
                    mctime = mctime2.strip("\n")
                except:
                    mctime = datetime.datetime.fromtimestamp(os.stat(self.itemPath).st_ctime).strftime('%c')
            #
            mmtime = datetime.datetime.fromtimestamp(os.stat(self.itemPath).st_mtime).strftime('%c')
            matime = datetime.datetime.fromtimestamp(os.stat(self.itemPath).st_atime).strftime('%c')
            #
            self.labelCreation2.setText(str(mctime))
            self.labelModification2.setText(str(mmtime))
            self.labelAccess2.setText(str(matime))
            #
            self.labelgb12.setText(fileInfo.owner())
            self.labelgb22.setText(fileInfo.group())
            # file owner
            if self.CAN_CHANGE_OWNER:
                me = os.path.basename(os.getenv("HOME"))
                if me != fileInfo.owner():
                    self.own_btn.setEnabled(True)
                else:
                    self.own_btn.setEnabled(False)
            else:
                self.own_btn.setEnabled(False)
            # file group
            if self.CAN_CHANGE_OWNER:
                me = os.path.basename(os.getenv("HOME"))
                if me != fileInfo.group():
                    self.grp_btn.setEnabled(True)
                else:
                    self.grp_btn.setEnabled(False)
            else:
                self.grp_btn.setEnabled(False)
            #####
            perms = fileInfo.permissions()
            # folder access - file execution
            if perms & QFile.ExeOwner:
                if not self.cb1.checkState():
                    self.cb1.setChecked(True)
            #
            nperm = self.fgetPermissions()
            #
            if nperm[0] + nperm[1] + nperm[2] in [6, 7]:
                self.combo1.setCurrentIndex(0)
            elif nperm[0] + nperm[1] + nperm[2] in [4, 5]:
                self.combo1.setCurrentIndex(1)
            else:
                self.combo1.setCurrentIndex(2)
            #
            if nperm[3] + nperm[4] + nperm[5] in [6, 7]:
                self.combo2.setCurrentIndex(0)
            elif nperm[3] + nperm[4] + nperm[5] in [4, 5]:
                self.combo2.setCurrentIndex(1)
            else:
                self.combo2.setCurrentIndex(2)
            #
            if nperm[6] + nperm[7] + nperm[8] in [6, 7]:
                self.combo3.setCurrentIndex(0)
            elif nperm[6] + nperm[7] + nperm[8] in [4, 5]:
                self.combo3.setCurrentIndex(1)
            else:
                self.combo3.setCurrentIndex(2)
    
    
    # change the owner to me
    def on_change_owner(self, me):
        ret = None
        try:
            ret = subprocess.run(["pkexec", "chown", me, self.itemPath])
        except:
            pass
        # if success
        if ret:
            if ret.returncode == 0:
                self.tab()
    
    # 
    # change the group to mine
    def on_change_grp(self, me):
        ret = None
        try:
            ret = subprocess.run(["pkexec", "chgrp", me, self.itemPath])
        except:
            pass
        # if success
        if ret:
            if ret.returncode == 0:
                self.tab()
    
    def tperms(self, perms):
        tperm = ""
        tperm = str(perms[0] + perms[1] + perms[2])+str(perms[3] + perms[4] + perms[5])+str(perms[6] + perms[7] + perms[8])
        return tperm
    
    # folder access - file executable
    def fcb1(self, state):
        perms = self.fgetPermissions()
        #
        if state == 2:
            perms[2] = 1
            perms[5] = 1
            perms[8] = 1
            tperm =self.tperms(perms)
            try:
                os.chmod(self.itemPath, int("{}".format(int(tperm)), 8))
            except Exception as E:
                MyDialog("Error", str(E), self.window)
        else:
            perms[2] = 0
            perms[5] = 0
            perms[8] = 0
            tperm =self.tperms(perms)
            try:
                os.chmod(self.itemPath, int("{}".format(int(tperm)), 8))
            except Exception as E:
                MyDialog("Error", str(E), self.window)
        # repopulate
        self.tab()
    
    # 
    def fcombo1(self, index):
        perms = self.fgetPermissions()
        if index == 0:
            perms[0] = 4
            perms[1] = 2
        elif index == 1: 
            perms[0] = 4
            perms[1] = 0
        elif index == 2:
            perms[0] = 0
            perms[1] = 0
        #
        tperm = self.tperms(perms)
        try:
            os.chmod(self.itemPath, int("{}".format(tperm), 8))
        except Exception as E:
            MyDialog("Error", str(E), self.window)
        # repopulate
        self.tab()
    
    def fcombo2(self, index):
        perms = self.fgetPermissions()
        if index == 0:
            perms[3] = 4
            perms[4] = 2
        elif index == 1: 
            perms[3] = 4
            perms[4] = 0
        elif index == 2:
            perms[3] = 0
            perms[4] = 0

        tperm = self.tperms(perms)
        try:
            os.chmod(self.itemPath, int("{}".format(tperm), 8))
        except Exception as E:
            MyDialog("Error", str(E), self.window)
        # repopulate
        self.tab()
    
    def fcombo3(self, index):
        perms = self.fgetPermissions()
        if index == 0:
            perms[6] = 4
            perms[7] = 2
        elif index == 1: 
            perms[6] = 4
            perms[7] = 0
        elif index == 2:
            perms[6] = 0
            perms[7] = 0

        tperm = self.tperms(perms)
        try:
            os.chmod(self.itemPath, int("{}".format(tperm), 8))
        except Exception as E:
            MyDialog("Error", str(E), self.window)
        # repopulate
        self.tab()


    def fgetPermissions(self):
        perms = QFile(self.itemPath).permissions()
        # 
        permissions = []
        #
        if perms & QFile.ReadOwner:
            permissions.append(4)
        else:
            permissions.append(0)
        if perms & QFile.WriteOwner:
            permissions.append(2)
        else:
            permissions.append(0)
        if perms & QFile.ExeOwner:
            permissions.append(1)
        else:
            permissions.append(0)
        #
        if perms & QFile.ReadGroup:
            permissions.append(4)
        else:
            permissions.append(0)
        if perms & QFile.WriteGroup:
            permissions.append(2)
        else:
            permissions.append(0)
        if perms & QFile.ExeGroup:
            permissions.append(1)
        else:
            permissions.append(0)
        #
        if perms & QFile.ReadOther:
            permissions.append(4)
        else:
            permissions.append(0)
        if perms & QFile.WriteOther:
            permissions.append(2)
        else:
            permissions.append(0)
        if perms & QFile.ExeOther:
            permissions.append(1)
        else:
            permissions.append(0)
        #
        return permissions
    
    def faccept(self):
        self.close()


# property dialog for more than one item
class propertyDialogMulti(QDialog):
    def __init__(self, itemSize, itemNum, parent):
        super(propertyDialogMulti, self).__init__(parent)
        #
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle("Property")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(DIALOGWIDTH, 100)
        #
        vbox = QBoxLayout(QBoxLayout.TopToBottom)
        self.setLayout(vbox)
        #
        label1 = QLabel("<i>Number of items&nbsp;&nbsp;&nbsp;</i> {}".format(itemNum))
        vbox.addWidget(label1)
        label2 = QLabel("<i>Total size of the items&nbsp;&nbsp;&nbsp;</i> {}".format(itemSize))
        vbox.addWidget(label2)
        #
        button1 = QPushButton("Close")
        vbox.addWidget(button1)
        button1.clicked.connect(self.close)
        #
        self.exec_()

###################

# Paste and Merge function - utility
class PastenMerge():
    
    def __init__(self, lvDir, action, dlist, window):
        self.lvDir = lvDir
        # -3 if not DnD - or 1 or 2
        self.action = action
        self.dlist = dlist
        self.window = window
        self.fpasteNmergeAction()
    
    # make the list of all the item to be copied - find the action
    def fmakelist(self):
        filePaths = []
        #
        clipboard = QApplication.clipboard()
        mimeData = clipboard.mimeData(QClipboard.Clipboard)
        #
        got_quoted_data = []
        for f in mimeData.formats():
            #
            if f == "x-special/gnome-copied-files":
                data = mimeData.data(f)
                got_quoted_data = data.data().decode().split("\n")
                got_action = got_quoted_data[0]
                if got_action == "copy":
                    self.action = 1
                elif got_action == "cut":
                    self.action = 2
                filePaths = [unquote(x)[7:] for x in got_quoted_data[1:]]
        #
        return filePaths
    
    # paste and merge function
    def fpasteNmergeAction(self):
        # copy/paste
        if self.action == -3:
            # make the list of the items
            filePaths = self.fmakelist()
            if filePaths:
                if isinstance(self.dlist, int):
                    if len(filePaths) > self.dlist:
                        MyDialog("Info", "Too many items.", None)
                        return
                # execute the copying copy/cut operations
                # self.action: 1 copy - 2 cut - 4 make link
                copyItems2(self.action, filePaths, -4, self.lvDir, self.window)
        # DnD - 1 copy - 2 cut - 4 link (not supported)
        elif self.action == 1 or self.action == 2:
            if self.dlist:
                # execute the copying copy/cut operations
                # self.action: 1 copy - 2 cut - 4 make link
                copyItems2(self.action, self.dlist, -4, self.lvDir, self.window)


        
# Paste and Merge function
class copyItems2():
    def __init__(self, action, newList, atype, pathdest, window):
        self.action = action
        self.newList = newList
        self.atype = atype
        self.pathdest = pathdest
        self.window = window
        #
        self.newDtype = ""
        self.newAtype = ""
        self.myDialog()

    def myDialog(self):
        self.mydialog = QDialog(parent = self.window)
        self.mydialog.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.mydialog.setWindowTitle("Copying...")
        self.mydialog.setWindowModality(Qt.ApplicationModal)
        self.mydialog.resize(DIALOGWIDTH,300)
        # 
        grid = QGridLayout()
        grid.setContentsMargins(5,5,5,5)
        #
        self.label1 = clabel2()
        self.label1.setText("Processing...", self.mydialog.size().width()-12)
        grid.addWidget(self.label1, 0, 0, 1, 4, Qt.AlignCenter)
        #
        self.label2 = QLabel("")
        grid.addWidget(self.label2, 1, 0, 1, 4, Qt.AlignCenter)
        #
        self.pb = QProgressBar()
        self.pb.setMinimum(0)
        self.pb.setMaximum(100)
        self.pb.setValue(0)
        grid.addWidget(self.pb, 3, 0, 1, 4, Qt.AlignCenter)
        #
        self.button1 = QPushButton("Close")
        self.button1.clicked.connect(self.fbutton1)
        grid.addWidget(self.button1, 4, 0, 1, 2, Qt.AlignCenter)
        #
        self.button1.setEnabled(False)
        #
        self.button2 = QPushButton("Abort")
        self.button2.clicked.connect(self.fbutton2)
        grid.addWidget(self.button2, 4, 2, 1, 2, Qt.AlignCenter)
        #
        # number of items in the list
        self.numItemList = len(self.newList)
        # number of items processed
        self.numItemProc = 0
        #
        self.mydialog.setLayout(grid)
        self.mythread = copyThread2(self.action, self.newList, self.atype, self.pathdest)
        self.mythread.sig.connect(self.threadslot)
        self.mythread.start()
        #
        self.mydialog.exec()
   
    
    def threadslot(self, aa):
        # from directories
        if aa[0] == "ReqNewDtype":
            # 1 skip - 2 overwrite - 4 automatic - 5 backup
            sNewDtype = pasteNmergeDialog(self.window, aa[1], aa[2], "folder").getValue()
            self.mythread.sig.emit(["SendNewDtype", sNewDtype])
            self.newDtype = sNewDtype
        # from any files
        elif aa[0] == "ReqNewAtype":
            # 1 skip - 2 overwrite - 4 automatic - 5 backup
            sNewAtype = pasteNmergeDialog(self.window, aa[1], aa[2], "file").getValue()
            self.mythread.sig.emit(["SendNewAtype", sNewAtype])
            self.newAtype = sNewAtype
        # copying process
        elif aa[0] == "mSending":
            self.label1.setText(aa[1], self.mydialog.size().width()-12)
            self.numItemProc += 1
            self.label2.setText("Items: {}/{}".format(self.numItemProc,self.numItemList))
            self.pb.setValue(int(self.numItemProc/self.numItemList*100))
        # the copying process ends
        elif aa[0] == "mDone":
            self.label1.setText("Done", self.mydialog.size().width()-12)
            if self.numItemProc == self.numItemList:
                self.pb.setValue(100)
            # change the button state
            self.button1.setEnabled(True)
            self.button2.setEnabled(False)
            # something happened with some items
            if len(aa) == 4 and aa[3] != "":
                MyMessageBox("Info", "Something happened with some items", "", aa[3], self.window)
        # operation interrupted by the user
        elif aa[0] == "Cancelled":
            self.label1.setText("Cancelled.", self.mydialog.size().width()-12)
            self.label2.setText("Items: {}/{}".format(self.numItemProc,self.numItemList))
            self.pb.setValue(int(self.numItemProc/self.numItemList*100))
            # change the button state
            self.button1.setEnabled(True)
            self.button2.setEnabled(False)
            # something happened with some items
            if len(aa) == 4 and aa[3] != "":
                MyMessageBox("Info", "Something happened with some items", "", aa[3], self.window)
    
    def fbutton1(self):
        self.mydialog.close()

    def fbutton2(self):
        self.mythread.requestInterruption()


# for item copying - Paste and Merge function
class copyThread2(QThread):
    
    sig = pyqtSignal(list)
    
    def __init__(self, action, newList, atype, pathdest, parent=None):
        super(copyThread2, self).__init__(parent)
        # action: 1 copy - 2 cut
        self.action = action
        # the list of the items
        self.newList = newList
        # 1 skip - 2 overwrite - 4 automatic suffix - 5 backup the existent items
        self.atype = atype
        # for folders
        self.atypeDir = atype
        # destination path
        self.pathdest = pathdest
        #
        # ask for a new name from a dialog
        self.sig.connect(self.getdatasygnal)
        # used for main program-thread communication
        self.reqNewNm = ""
    
    def getdatasygnal(self, l=None):
        if l[0] == "SendNewAtype" or l[0] == "SendNewDtype":
            self.reqNewNm = l[1]

    def run(self):
        time.sleep(1)
        self.item_op()

    
    # calculate the folder size 
    def folder_size(self, path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for fl in filenames:
                flp = os.path.join(dirpath, fl)
                if os.access(flp, os.R_OK):
                    if os.path.islink(flp):
                        continue
                    total_size += os.path.getsize(flp)
        return total_size

    
    # total size of the list
    def listTotSize(self):
        total_size = 0
        skipped = ""
        for sitem in newList:
            try:
                if os.path.islink(sitem):
                    # just a number
                    total_size += 512
                elif os.path.isfile(sitem):
                    item_size = QFileInfo(sitem).size()
                    total_size += max(item_size, 512)
                elif os.path.isdir(sitem):
                    item_size = self.folder_size(sitem)
                    total_size += max(item_size, 512)
            except:
                skipped += sitem+"\n"
        #
        return total_size

    ## self.atype 4 or 5
    # add a suffix to the filename if the file exists at destination
    def faddSuffix(self, dest):
        # it exists or it is a broken link
        if os.path.exists(dest) or os.path.islink(dest):
            i = 1
            dir_name = os.path.dirname(dest)
            bname = os.path.basename(dest)
            dest = ""
            while i:
                nn = bname+"_("+str(i)+")"
                if os.path.exists(os.path.join(dir_name, nn)):
                    i += 1
                else:
                    dest = os.path.join(dir_name, nn)
                    i = 0
            #
            return dest
    
    # add the suffix to the name
    def faddSuffix2(self, dts, dest):
        new_name = os.path.basename(dest)+dts
        dest = os.path.join(os.path.dirname(dest), new_name)
        return dest
        
    # the work on each item
    # self.atype: 1 skip - 2 overwrite - 3 rename - 4 automatic suffix - 5 backup the existent items
    def item_op(self):
        items_skipped = ""
        # action: copy 1 - cut 2
        action = self.action
        newList = self.newList
        total_size = 1
        incr_size = 1
        # common suffix if date - the same date for all items
        commSfx = ""
        if USE_DATE:
            z = datetime.datetime.now()
            #dY, dM, dD, dH, dm, ds, dms
            commSfx = "_{}.{}.{}_{}.{}.{}".format(z.year, z.month, z.day, z.hour, z.minute, z.second)
        
        self.sig.emit(["Starting...", 0, total_size])
        #
        # the default action for all files in the dir to be copied...
        # ... if an item with the same name already exist at destination
        dirfile_dcode = 0
        # for the items in the dir: 1 skip - 2 replace - 4 automatic - 5 backup
        for dfile in newList:
            # the user can interrupt the operation for the next items
            if self.isInterruptionRequested():
                self.sig.emit(["Cancelled", 1, 1, items_skipped])
                return
            time.sleep(0.1)
            #
            # one signal for each element in the list
            self.sig.emit(["mSending", os.path.basename(dfile)])
            #
            # item is dir and not link to dir
            if os.path.isdir(dfile) and not os.path.islink(dfile):
                tdest = os.path.join(self.pathdest, os.path.basename(dfile))
                # recursive copying
                len_dfile = len(dfile)
                if tdest[0:len_dfile] == dfile and not tdest == dfile:
                    items_skipped += "Recursive copying:\n{}".format(os.path.basename(dfile))
                    continue
                # it isnt the exactly same item
                elif dfile != tdest:
                    #
                    # the dir doesnt exist at destination or it is a broken link
                    if not os.path.exists(tdest):
                        try:
                            # check broken link
                            if os.path.islink(tdest):
                                ret = ""
                                if USE_DATE:
                                    ret = self.faddSuffix2(commSfx, tdest)
                                else:
                                    ret = self.faddSuffix(tdest)
                                shutil.move(tdest, ret)
                                items_skipped += "{}:\nRenamed (broken link).\n------------\n".format(tdest)
                            #
                            if action == 1:
                                shutil.copytree(dfile, tdest, symlinks=True, ignore=None, copy_function=shutil.copy2, ignore_dangling_symlinks=False)
                            elif action == 2:
                                shutil.move(dfile, tdest)
                        except Exception as E:
                            items_skipped += "{}:\n{}\n------------\n".format(tdest, str(E))
                            # reset
                            self.reqNewNm = ""
                    #
                    # exists at destination a folder with the same name
                    elif os.path.exists(tdest):
                        # get the default choise (one choise for all folders to copy in the main dir)
                        if self.atypeDir == -4:
                            self.sig.emit(["ReqNewDtype", tdest, os.path.basename(tdest)])
                            while self.reqNewNm == "":
                                time.sleep(1)
                            else:
                                # 
                                self.atypeDir = self.reqNewNm
                                # reset
                                self.reqNewNm = ""
                        #
                        # -1 abort if cancelled
                        if self.atypeDir == -1:
                            items_skipped += "Operation aborted by the user.\n"
                            break
                        # 1 skip
                        elif self.atypeDir == 1:
                            # items_skipped += "{}:\n{}\n------------\n".format(dfile, "Folder skipped by the user.")
                            continue
                        #
                        # new dir name if an item exists at destination with the same name
                        newDestDir = ""
                        #
                        # 4 automatic - rename the item to copy
                        if self.atypeDir == 4:
                            if USE_DATE:
                                newDestDir = self.faddSuffix2(commSfx, tdest)
                            else:
                                newDestDir = self.faddSuffix(tdest)
                            # first create the dir
                            try:
                                os.makedirs(newDestDir)
                            except Exception as E:
                                items_skipped += "{}:\n{}\n------------\n".format(newDestDir, str(E))
                                continue
                            # copy or move
                            try:
                                for sdir,ddir,ffile in os.walk(dfile):
                                    if action == 1:
                                        for dr in ddir:
                                            shutil.copytree(os.path.join(sdir, dr), os.path.join(newDestDir, dr), symlinks=True, ignore=None, copy_function=shutil.copy2, ignore_dangling_symlinks=False)
                                        for ff in ffile:
                                            shutil.copy2(os.path.join(sdir, ff), newDestDir, follow_symlinks=False)
                                    elif action == 2:
                                        for dr in ddir:
                                            shutil.move(os.path.join(sdir, dr), newDestDir)
                                        for ff in ffile:
                                            shutil.move(os.path.join(sdir, ff), newDestDir)
                            except Exception as E:
                                items_skipped += "{}:\n{}\n------------\n".format(newDestDir, str(E))
                                continue
                            try:
                                shutil.rmtree(dfile)
                            except Exception as E:
                                items_skipped += "{}:\n{}\n------------\n".format(newDestDir, str(E))
                                continue
                        # 5 backup - rename the item at destination and copy
                        elif self.atypeDir == 5:
                            # rename the dir
                            try:
                                ret = ""
                                if USE_DATE:
                                    ret = self.faddSuffix2(commSfx, tdest)
                                else:
                                    ret = self.faddSuffix(tdest)
                                os.rename(tdest, os.path.join(os.path.dirname(tdest),ret))
                            except Exception as E:
                                items_skipped += "{}:\n{}\n------------\n".format(tdest, str(E))
                                continue
                            # copy or move
                            try:
                                if action == 1:
                                    shutil.copytree(dfile, tdest, symlinks=True, ignore=None, copy_function=shutil.copy2, ignore_dangling_symlinks=False)
                                elif action == 2:
                                    shutil.move(dfile, tdest)
                            except Exception as E:
                                items_skipped += "{}:\n{}\n------------\n".format(dfile, str(E))
                                continue
                        #
                        # 2 merge - broken link or not folder
                        if self.atypeDir == 2:
                            try:
                                if os.path.islink(tdest):
                                    os.unlink(tdest)
                                elif not os.path.isdir(tdest):
                                    os.remove(tdest)
                            except Exception as E:
                                items_skipped += "{}:\n{}\n------------\n".format(tdest, str(E))
                                continue
                            #
                            todest = tdest
                            # 
                            # sdir has full path
                            for sdir,ddir,ffile in os.walk(dfile):
                                # temp_dir = sdir[len(dfile)+1:]
                                temp_dir = os.path.relpath(sdir, dfile)
                                # 1 - create the subdirs if the case
                                for dr in ddir:
                                    todest2 = os.path.join(todest, temp_dir, dr)
                                    if not os.path.exists(todest2):
                                        # require python >= 3.3
                                        os.makedirs(todest2, exist_ok=True)
                                #
                                # 2 - copy the files
                                for item_file in ffile:
                                    # the item at destination
                                    dest_item = os.path.join(todest, temp_dir, item_file)
                                    #
                                    # at destination exists or is a broken link
                                    if os.path.exists(dest_item) or os.path.islink(dest_item):
                                        # eventually the source file - it could not exist
                                        source_item = os.path.join(dfile, sdir, item_file)
                                        source_item_skipped = os.path.join(os.path.basename(dfile), sdir, item_file)
                                        # atype choosing dialog if dirfile_dcode is 0 (no choises previously made)
                                        if dirfile_dcode == 0:
                                            self.sig.emit(["ReqNewAtype", tdest, os.path.basename(dest_item)])
                                            while self.reqNewNm == "":
                                                time.sleep(1)
                                            else:
                                                # dcode
                                                dirfile_dcode = self.reqNewNm
                                                # also for files outside this folder
                                                self.atype = dirfile_dcode
                                                # reset
                                                self.reqNewNm = ""
                                        #
                                        # -1 means cancelled from the rename dialog
                                        if dirfile_dcode == -1:
                                            items_skipped += "Operation cancelled by the user\n------------\n"
                                            break
                                        # 1 skip
                                        elif dirfile_dcode == 1:
                                            # items_skipped += "{}:\n{}\n------------\n".format(fpsitem, "Skipped.")
                                            continue
                                        # 2 overwrite
                                        elif dirfile_dcode == 2:
                                            try:
                                                # link
                                                if os.path.islink(dest_item):
                                                    os.unlink(dest_item)
                                                # dir
                                                elif os.path.isdir(dest_item):
                                                    shutil.rmtree(dest_item)
                                                # copy or overwrite
                                                if action == 1:
                                                    shutil.copy2(source_item, dest_item, follow_symlinks=False)
                                                elif action == 2:
                                                    shutil.move(source_item, dest_item)
                                            except Exception as E:
                                                items_skipped += "{}:\n{}\n------------\n".format(source_item_skipped, str(E))
                                        # 4 automatic
                                        elif dirfile_dcode == 4:
                                            try:
                                                ret = ""
                                                if USE_DATE:
                                                    ret = self.faddSuffix2(commSfx, dest_item)
                                                else:
                                                    ret = self.faddSuffix(dest_item)
                                                iNewName = os.path.join(os.path.dirname(dest_item),ret)
                                                if action == 1:
                                                    shutil.copy2(source_item, iNewName, follow_symlinks=False)
                                                elif action == 2:
                                                    shutil.move(source_item, iNewName)
                                            except Exception as E:
                                                items_skipped += "{}:\n{}\n------------\n".format(source_item_skipped, str(E))
                                        # 5 backup the existent file
                                        elif dirfile_dcode == 5:
                                            try:
                                                ret = ""
                                                if USE_DATE:
                                                    ret = self.faddSuffix2(commSfx, dest_item)
                                                else:
                                                    ret = self.faddSuffix(dest_item)
                                                shutil.move(dest_item, ret)
                                                if action == 1:
                                                    shutil.copy2(source_item, dest_item, follow_symlinks=False)
                                                elif action == 2:
                                                    shutil.move(source_item, dest_item)
                                            except Exception as E:
                                                items_skipped += "{}:\n{}\n------------\n".format(source_item_skipped, str(E))
                                    # doesnt exist at destination
                                    else:
                                        try:
                                            if action == 1:
                                                shutil.copy2(os.path.join(sdir,item_file), dest_item, follow_symlinks=False)
                                            elif action == 2:
                                                shutil.move(os.path.join(sdir,item_file), dest_item)
                                        except Exception as E:
                                            items_skipped += "{}:\n{}\n------------\n".format(os.path.join(sdir,item_file), str(E))
                        #
                        #############
                # origin and destination are the exactly same directory
                else:
                    if action == 1:
                        try:
                            ret = ""
                            if USE_DATE:
                                ret = self.faddSuffix2(commSfx, dfile)
                            else:
                                ret = self.faddSuffix(dfile)
                            shutil.copytree(dfile, ret, symlinks=True, ignore=None, copy_function=shutil.copy2, ignore_dangling_symlinks=False)
                            # items_skipped += "{}:\nCopied and Renamed:\n{}\n------------\n".format(os.path.basename(tdest), os.path.basename(ret))
                        except Exception as E:
                            items_skipped += "{}:\n{}\n------------\n".format(os.path.basename(dfile), str(E))
                    # elif action == 2:
                        # pass
            # item is file or link/broken link or else
            else:
                # check for an item with the same name at destination
                tdest = os.path.join(self.pathdest, os.path.basename(dfile))
                # if not the exactly same item
                if dfile != tdest:
                    if os.path.exists(tdest):
                        if self.atype == -4:
                            self.sig.emit(["ReqNewAtype", tdest, os.path.basename(tdest)])
                            while self.reqNewNm == "":
                                time.sleep(1)
                            else:
                                # 
                                self.atype = self.reqNewNm
                                # also for files isside folders
                                dirfile_dcode = self.atype
                                # reset
                                self.reqNewNm = ""
                        # -1 cancel
                        if self.atype == -1:
                            items_skipped += "Operation aborted by the user.\n"
                            break
                        # 1 skip
                        elif self.atype == 1:
                            # items_skipped += "{}:\n{}\n------------\n".format(dfile, "Skipped.")
                            continue
                        # 2 overwrite
                        elif self.atype == 2:
                            try:
                                if action == 1:
                                    shutil.copy2(dfile, tdest, follow_symlinks=False)
                                elif action == 2:
                                    shutil.move(dfile, tdest)
                            except Exception as E:
                                items_skipped += "{}:\n{}\n------------\n".format(dfile, str(E))
                        # 4 automatic
                        elif self.atype == 4:
                            try:
                                ret = ""
                                if USE_DATE:
                                    ret = self.faddSuffix2(commSfx, tdest)
                                else:
                                    ret = self.faddSuffix(tdest)
                                #
                                if action == 1:
                                    shutil.copy2(dfile, ret, follow_symlinks=False)
                                elif action == 2:
                                    shutil.move(dfile, ret)
                            except Exception as E:
                                items_skipped += "{}:\n{}\n------------\n".format(dfile, str(E))
                        # 5 backup the existent files
                        elif self.atype == 5:
                            try:
                                ret = ""
                                if USE_DATE:
                                    ret = self.faddSuffix2(commSfx, tdest)
                                else:
                                    ret = self.faddSuffix(tdest)
                                shutil.move(tdest, ret)
                                if action == 1:
                                    shutil.copy2(dfile, tdest, follow_symlinks=False)
                                elif action == 2:
                                    shutil.move(dfile, tdest)
                            except Exception as E:
                                items_skipped += "{}:\n{}\n------------\n".format(dfile, str(E))
                    # it doesnt exist at destination
                    else:
                        # if broken link rename
                        if os.path.islink(tdest):
                            try:
                                ret = ""
                                if USE_DATE:
                                    ret = self.faddSuffix2(commSfx, tdest)
                                else:
                                    ret = self.faddSuffix(tdest)
                                shutil.move(tdest, ret)
                                items_skipped += "{}:\nRenamed (broken link)\n------------\n".format(tdest)
                            except Exception as E:
                                items_skipped += "{}:\n{}\n------------\n".format(dfile, str(E))
                        #
                        try:
                            if action == 1:
                                shutil.copy2(dfile, tdest, follow_symlinks=False)
                            elif action == 2:
                                shutil.move(dfile, tdest)
                        except Exception as E:
                            items_skipped += "{}:\n{}\n------------\n".format(dfile, str(E))
                # if it is the exactly same item
                else:
                    if action == 1:
                        try:
                            ret = ""
                            if USE_DATE:
                                ret = self.faddSuffix2(commSfx, tdest)
                            else:
                                ret = self.faddSuffix(tdest)
                            shutil.copy2(dfile, ret, follow_symlinks=False)
                            # items_skipped += "{}:\nCopied and Renamed:\n{}\n------------\n".format(tdest, ret)
                        except Exception as E:
                            items_skipped += "{}:\n{}\n------------\n".format(tdest, str(E))
                    elif action == 2:
                        items_skipped += "{}:\n{}\n------------\n".format(dfile, "Exactly the same item.")
        #
        # DONE
        self.sig.emit(["mDone", 1, 1, items_skipped])
    

# dialog - Paste-n-Merge - choose the default action
# if an item at destination has the same name
# as the item to be copied
class pasteNmergeDialog(QDialog):
    
    def __init__(self, parent, destination, ltitle, item_type):
        super(pasteNmergeDialog, self).__init__(parent)
        # 
        self.destination = destination
        self.ltitle = ltitle
        self.item_type = item_type
        #
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle("Paste and Merge")
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(DIALOGWIDTH, 100)
        #
        vbox = QBoxLayout(QBoxLayout.TopToBottom)
        vbox.setContentsMargins(5,5,5,5)
        self.setLayout(vbox)
        #
        if self.item_type == "folder":
            label1 = QLabel("The folder\n"+self.ltitle+"\nexists in\n{}.".format(os.path.dirname(self.destination))+"\nPlease choose the default action for all folders.\nThis choise cannot be changed afterwards.\n")
        elif self.item_type == "file":
            label1 = QLabel("The file\n"+self.ltitle+"\nexists in\n{}.".format(os.path.dirname(self.destination))+"\nPlease choose the default action for all files.\nThis choise cannot be changed afterwards.\n")
        vbox.addWidget(label1)
        #
        hbox = QBoxLayout(QBoxLayout.LeftToRight)
        vbox.addLayout(hbox)
        # skip all the items
        skipButton = QPushButton("Skip")
        skipButton.setToolTip("File and folders with the same name will be skipped.")
        hbox.addWidget(skipButton)
        skipButton.clicked.connect(lambda:self.fsetValue(1))
        # merge or overwrite all the items
        if self.item_type == "folder":
            overwriteButton = QPushButton("Merge")
            overwriteButton.setToolTip("All the folders will be merged.")
        elif self.item_type == "file":
            overwriteButton = QPushButton("Overwrite")
            overwriteButton.setToolTip("All the files will be overwritten.")
        hbox.addWidget(overwriteButton)
        overwriteButton.clicked.connect(lambda:self.fsetValue(2))
        # add an preformatted extension to the items
        automaticButton = QPushButton("Automatic")
        automaticButton.setToolTip("A suffix will be added to files an folders.")
        hbox.addWidget(automaticButton)
        automaticButton.clicked.connect(lambda:self.fsetValue(4))
        # backup the existen item(s)
        backupButton = QPushButton("Backup")
        backupButton.setToolTip("The original file or folder will be backed up.")
        hbox.addWidget(backupButton)
        backupButton.clicked.connect(lambda:self.fsetValue(5))
        # abort the operation
        cancelButton = QPushButton("Cancel")
        cancelButton.setToolTip("Abort.")
        hbox.addWidget(cancelButton)
        cancelButton.clicked.connect(self.fcancel)
        #
        self.Value = 0
        self.exec_()
    
    def getValue(self):
        return self.Value
    
    def fsetValue(self, n):
        self.Value = n
        self.close()
    
    def fcancel(self):
        self.Value = -1
        self.close()


# dialog - with optional item list and return of the choise
class retDialogBox(QMessageBox):
    def __init__(self, *args):
        super(retDialogBox, self).__init__(args[-1])
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle(args[0])
        if args[0] == "Info":
            self.setIcon(QMessageBox.Information)
        elif args[0] == "Error":
            self.setIcon(QMessageBox.Critical)
        elif args[0] == "Question":
            self.setIcon(QMessageBox.Question)
        self.resize(DIALOGWIDTH, 100)
        self.setText(args[1])
        self.setInformativeText(args[2])
        if args[3]:
            self.setDetailedText("The details are as follows:\n\n"+args[3])
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        #
        self.Value = None
        retval = self.exec_()
        #
        if retval == QMessageBox.Yes:
            self.Value = 1
        elif retval == QMessageBox.Cancel:
            self.Value = 0
    
    def getValue(self):
        return self.Value
    
    def event(self, e):
        result = QMessageBox.event(self, e)
        #
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #
        textEdit = self.findChild(QTextEdit)
        if textEdit != None :
            textEdit.setMinimumHeight(0)
            textEdit.setMaximumHeight(16777215)
            textEdit.setMinimumWidth(0)
            textEdit.setMaximumWidth(16777215)
            textEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #
        return result


class clabel2(QLabel):
    def __init__(self, parent=None):
        super(clabel2, self).__init__(parent)
    
    def setText(self, text, wWidth):
        boxWidth = wWidth*QApplication.instance().devicePixelRatio()
        font = self.font()
        metric = QFontMetrics(font)
        string = text
        ctemp = ""
        ctempT = ""
        for cchar in string:
            ctemp += str(cchar)
            width = metric.width(ctemp)
            if width < boxWidth:
                ctempT += str(cchar)
                continue
            else:
                ctempT += str(cchar)
                ctempT += "\n"
                ctemp = str(cchar)
        ntext = ctempT
        super(clabel2, self).setText(ntext)


# dialog message with info list
class MyMessageBox(QMessageBox):
    def __init__(self, *args):
        super(MyMessageBox, self).__init__(args[-1])
        self.setIcon(QMessageBox.Information)
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle(args[0])
        self.resize(DIALOGWIDTH,300)
        self.setText(args[1])
        self.setInformativeText(args[2])
        self.setDetailedText("The details are as follows:\n\n"+args[3])
        self.setStandardButtons(QMessageBox.Ok)
        retval = self.exec_()
    
    def event(self, e):
        result = QMessageBox.event(self, e)
        #
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #
        textEdit = self.findChild(QTextEdit)
        if textEdit != None :
            textEdit.setMinimumHeight(0)
            textEdit.setMaximumHeight(16777215)
            textEdit.setMinimumWidth(0)
            textEdit.setMaximumWidth(16777215)
            textEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #
        return result


# simple dialog message
# type - message - parent
class MyDialog(QMessageBox):
    def __init__(self, *args):
        super(MyDialog, self).__init__(args[-1])
        if args[0] == "Info":
            self.setIcon(QMessageBox.Information)
        elif args[0] == "Error":
            self.setIcon(QMessageBox.Critical)
        elif args[0] == "Question":
            self.setIcon(QMessageBox.Question)
        self.setWindowIcon(QIcon("icons/file-manager-red.svg"))
        self.setWindowTitle(args[0])
        self.resize(DIALOGWIDTH,300)
        self.setText(args[1])
        self.setStandardButtons(QMessageBox.Ok)
        retval = self.exec_()
    
    def event(self, e):
        result = QMessageBox.event(self, e)
        #
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # 
        return result


###################

class TrashModule():
    
    def __init__(self, list_items, window):
        self.list_items = list_items
        self.window = window
        self.trash_path = self.find_trash_path(self.list_items[0])
        self.Tfiles = os.path.join(self.trash_path, "files")
        self.Tinfo = os.path.join(self.trash_path, "info")
        self.can_trash = 0
        self.Ttrash_can_trash()
        #
        if self.can_trash:
            self.Tcan_trash(self.list_items)

    def find_trash_path(self, path):
        mount_point = ""
        while not os.path.ismount(path):
            path = os.path.dirname(path)
        mount_point = path
        #
        if mount_point == "/home" or mount_point == "/":
            trash_path = os.path.join(os.path.expanduser("~"), ".local/share/Trash")
        else:
            user_id = os.getuid()
            trash_path = os.path.join(mount_point, ".Trash-"+str(user_id))
        return trash_path

    def Ttrash_can_trash(self):
        if not os.path.exists(self.trash_path):
            if os.access(os.path.dirname(self.trash_path), os.W_OK):
                try:
                    os.mkdir(self.trash_path, 0o700)
                    os.mkdir(self.Tfiles, 0o700)
                    os.mkdir(self.Tinfo, 0o700)
                    self.can_trash = 1
                except Exception as E:
                    MyDialog("Error", str(E), self.window)
                    return
                finally:
                    return
            else:
                MyDialog("Error", "Cannot create the Trash folder.", self.window)
                return
        #
        if not os.access(self.Tfiles, os.W_OK):
            MyDialog("Error", "Cannot create the files folder.", self.window)
            return
        if not os.access(self.Tinfo, os.W_OK):
            MyDialog("Error", "Cannot create the info folder.", self.window)
            return
        #
        if os.access(self.trash_path, os.W_OK):
            if not os.path.exists(self.Tfiles):
                try:
                    os.mkdir(self.Tfiles, 0o700)
                except Exception as E:
                    MyDialog("Error", str(E), self.window)
                    return
            #
            if not os.path.exists(self.Tinfo):
                try:
                    os.mkdir(self.Tinfo, 0o700)
                except Exception as E:
                    MyDialog("Error", str(E), self.window)
                    return
            #
            self.can_trash = 1
            return
        #
        else:
            MyDialog("Error", "The Trash folder has wrong permissions.", self.window)
            return
        
    def Tcan_trash(self, list_items):
        for item_path in list_items:
            item = os.path.basename(item_path)
            tnow = datetime.datetime.now()
            del_time = tnow.strftime("%Y-%m-%dT%H:%M:%S")
            item_uri = quote("file://{}".format(item_path), safe='/:?=&')[7:]
            if os.path.exists(os.path.join(self.Tinfo, item+".trashinfo")):
                basename, suffix = os.path.splitext(item)
                i = 2
                aa = basename+"."+str(i)+suffix+".trashinfo"
                #
                while os.path.exists(os.path.join(self.Tinfo, basename+"."+str(i)+suffix+".trashinfo")):
                    i += 1
                else:
                    item = basename+"."+str(i)+suffix
            #
            try:
                shutil.move(item_path, os.path.join(self.Tfiles, item))
            except Exception as E:
                MyDialog("Error", str(E), self.window)
                continue
            ifile = open(os.path.join(self.Tinfo, "{}.trashinfo".format(item)),"w")
            ifile.write("[Trash Info]\n")
            ifile.write("Path={}\n".format(item_uri))
            ifile.write("DeletionDate={}\n".format(del_time))
            ifile.close()

###################### END TRASHCAN #####################

###################

if __name__ == '__main__':

    app = QApplication(sys.argv)
    #
    screen = app.primaryScreen()
    size = screen.size()
    # WINW = 1200
    WINW = size.width()+2
    # WINH = 800
    WINH = size.height()+2
    #
    window = MainWin()
    window.setAttribute(Qt.WA_X11NetWmWindowTypeDesktop)
    window.setWindowFlags(window.windowFlags() | Qt.FramelessWindowHint)
    window.setGeometry(-1, -1, WINW, WINH)
    window.show()
    #########
    # from Xlib.display import Display
    # from Xlib import X
    # windowID = int(window.winId())
    # _display = Display()
    # this_window = _display.create_resource_object('window', windowID)
    ####
    # L = 0
    # R = 0
    # T = 0
    # B = 0
    # # this_window.change_property(_display.intern_atom('_NET_WM_STRUT'),
                                # # _display.intern_atom('CARDINAL'),
                                # # 32, [L, R, T, B])
    # # x = 0
    # # y = x+WINW-1
    # # this_window.change_property(_display.intern_atom('_NET_WM_STRUT_PARTIAL'),
                           # # _display.intern_atom('CARDINAL'), 32,
                           # # [L, R, T, B, 0, 0, 0, 0, x, y, T, B],
                           # # X.PropModeReplace)
    # _display.sync()
    ####
    # from ewmh import EWMH
    # ewmh = EWMH()
    # wins = ewmh.getClientList()
    # for this_window in wins:
        # if ewmh.getWmName(this_window).decode() == "qt5desktop.py":
            # ewmh.setWmState(this_window, 1, '_NET_WM_STATE_SKIP_TASKBAR')
            # ewmh.setWmState(this_window, 1, '_NET_WM_STATE_SKIP_PAGER')
    # ewmh.display.flush()
    # ewmh.display.sync()
    #########
    ############
    # set new style globally
    if THEME_STYLE:
        s = QStyleFactory.create(THEME_STYLE)
        app.setStyle(s)
    # set the icon style globally
    if ICON_THEME:
        QIcon.setThemeName(ICON_THEME)
    ################
    ret = app.exec_()
    stopCD = 1
    sys.exit(ret)

####################
