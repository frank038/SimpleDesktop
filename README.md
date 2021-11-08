# SimpleDesktop
A simple and lite desktop manager.

Version 0.5.2 (testing)

Create the empty file "items_position" in the program folder or use the tar packed version.

This program shows the content of the folder "Desktop". The name can be changed in the config file.

To open the recycle bin, the command have to be written in the file trash_command.sh. Make sure to make this file executable. Must be executable also the files qt5desktop.py and qt5desktop.sh. Both can be used to launch this program. qt5desktop.sh is raccomanded.

Personalizations in the config file.

The trashcan change its icon to reflect its state, empty or not empty. The Recycle Bin space is reserved and exclusive. To use a wallpaper, just put an image named wallpaper.jpg at the exactly screen sizes in the program folder.

Can handle desktop files (programs, directories and files as link). Using desktop files for folders and files don't let user manage directly them. Moreover, more files and folders with the same name can coexist at the same time. Actually they can be created with my program SimpleFM. Accept files from my Qt5archiver program.

Limitations: only one item at time can change its position on the desktop. The desktop file cannot be copied, they can only created and deleted.

Needed:
- python3
- pyqt5
- python3-xdg

For media devices (option):
- dbus
- pyudev

For custom actions (option):
- 7z
- tar
- zip
- md5sum - sha256sum
- xterm

For thumbnailers (option):
- pdftocairo
- ffmpegthumbnailer

![My image](https://github.com/frank038/SimpleDesktop/blob/main/screenshot1.jpg)
