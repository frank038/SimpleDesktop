# the folder to set as desktop in the home directory
USER_DESKTOP="Desktop"
## viewport margins
# left margin
M_LEFT=0
# top margin
M_TOP=0
# right margin
M_RIGHT=0
# bottom margin
M_BOTTOM=0
## other kind of margins
# item left margin - normally not to be used
LEFT_M=0
# item top margin - normally not to be used
TOP_M=0
# item right margin - normally not to be used
RIGHT_M=0
# item bottom margin - to use to reduce the number of rows from bottom
BOTTOM_M=0
##
# multi items drag picture: 0 use simple icon - 1 enable extended icon
USE_EXTENDED_DRAG_ICON=1
# x offset of each icon if USE_EXTENDED_DRAG_ICON is enabled
X_EXTENDED_DRAG_ICON=40
# y offset of each icon if USE_EXTENDED_DRAG_ICON is enabled
Y_EXTENDED_DRAG_ICON=20
# limit the number of icon overlays if USE_EXTENDED_DRAG_ICON is enabled
NUM_OVERLAY=20
# thumbnailers: 0 no - 1 yes
USE_THUMB=0
# use custom icons for folders: 0 no - 1 yes
USE_FOL_CI=0
# space between items
ITEM_SPACE=10
# icon cell width - greater than ICON_SIZE
ITEM_WIDTH=160
# icon cell height
ITEM_HEIGHT=160
# icon size
ICON_SIZE=120
# thumb size: greater than ICON_SIZE - same size of ICON_SIZE to disable bigger thumbnailers
THUMB_SIZE=160
# item text shrinking - in the case the item text takes three lines when not selected increase this value
TEXT_SHRINK=0
# other icons size: link and permissions
ICON_SIZE2=36
# text colour in the form #AARRGGBB - "" to use default
TEXT_COLOR=""
# draw the shadow back the text: 0 no - 1 yes
TEXT_SHADOW=1
TEXT_SHADOW_SHIFT=2
# text shadow colour in the form #AARRGGBB
TEXT_SHADOW_COLOR="#FF999999"
# draw a rouded rectangle back the text: 0 no - 1 yes
TEXT_BACKGROUND=
# text background colors
TRED=233
TGREEN=94
TBLUE=11
TALPHA=185
# menu highlight color: "" to use the default style
MENU_H_COLOR="#DF5E0B"
# the size of the circle at top-left of each item
CIRCLE_SIZE=30
# the circle color in the form #AARRGGBB
CIRCLE_COLOR="#88DF5E0B"
# tick symbol
TICK_CHAR="✓"
# tick size in pixels
TICK_SIZE=30
# tick symbol color
TICK_COLOR="white"
# Open with... dialog: 0 simple - 1 list installed applications
OPEN_WITH=1
# show delete context menu entry that bypass the trashcan: 0 no - 1 yes
USE_DELETE=1
# load the trash module: 0 no - 1 yes
USE_TRASH=1
# recycle bin name
TRASH_NAME="Recycle Bin"
# load the media: 0 no - 1 yes
USE_MEDIA=0
# use desktop notification throu notify-send after a media has been ejected: 0 not - 1 yes - 2 also after inserted
USE_MEDIA_NOTIFICATION=0
# media to skip, comma separated values in the form "/dev/xxx" - not reccomanded for removable ones
MEDIA_SKIP=[]
# Paste and Merge, how to backup the new files: 0 add progressive number
# in the form _(#) - 1 add date and time (without checking eventually
# existing file at destination with same date and time suffix) 
# in the form _yy.mm.dd_hh.mm.ss
USE_DATE=1
# creation data and time of the item in the property dialog: 0 use os.stat - 1 use functions from bash (should be precise)
DATE_TIME=1
# dialog windows width
DIALOGWIDTH=600
# can use: 1 - the user mimeapps.list (in $HOME/.config/mimeapps.list) or 0 - that in the program
USER_MIMEAPPSLIST=1
# icon theme name - if the qt5ct program overrides this use ""
ICON_THEME=""
# theme style: "" to use the default theme
THEME_STYLE=""
# use background colour in the listview widgets: 0 no - 1 yes
USE_BACKGROUND_COLOUR=0
BACKGROUND_COLOR="#878787"
# show the exit button: 0 no - 1 yes
SHOW_EXIT=1
# track screen resolution changes: 0 no - 1 yes
SCRN_RES = 1
### needed for qt5archiver
# usually 7z - or 7za
COMMAND_EXTRACTOR="7z"
### needed by pythumb
# use thumbnailer in the home dir only: 0 no - 1 yes
USE_THUMB_HOME_ONLY=1
# use borders: 0 no - 1 yes
USE_BORDERS=1
# 
BORDER_WIDTH=2
# border color of the thumbnails
BORDER_COLOR_R = 0
BORDER_COLOR_G = 0
BORDER_COLOR_B = 0
# thumbnail images cache
XDG_CACHE_LARGE = "sh_thumbnails/large/"
