#!/usr/bin/env python3
"""
open xterm in the current directory
"""

import subprocess
import shutil
import os

# action name: this appears in the menu
def mmodule_name():
    return "Open xterm here"

# 1 : one item selected - 2 : more than one item selected - 3 : one or more items selected- 4 on background - 5 always
# action type
def mmodule_type(listview):
    if shutil.which("xterm"):
        return 4
    else:
        return 0


class ModuleCustom():
    
    def __init__(self, listview):
        
        try:
            path = os.path.join(os.path.expanduser("~"), "Desktop")
            comm = "cd '{}' && /bin/bash".format(path)
            FONT_SIZE = '14'
            command = ['xterm', '-fa', 'Monospace', '-fs', FONT_SIZE, '-fg', 'white', '-bg', 'black', '-geometry', '70x18', '-e', comm]
            subprocess.Popen(command)
        except:
            pass
