#!/usr/bin/env python3
import os
import shutil
if os.name == "posix":
    os.system("pyinstaller --clean flo.spec")
    home_path = os.path.expanduser('~')
    bin_dir = os.path.join( home_path, "bin", "flo-compiler")
    os.makedirs(bin_dir, exist_ok=True)
    shutil.copy("./dist/flo", bin_dir)
    print("creating symlink to bin path")
    os.system("sudo ln -s "+os.path.join(bin_dir, "flo")+" /usr/bin/flo")
    print("Cleaning up...")
    shutil.rmtree("./build")
    shutil.rmtree("./dist")
    print("Flo is now installed!!")
elif os.name == 'nt':
    print("windows not supported yet.")