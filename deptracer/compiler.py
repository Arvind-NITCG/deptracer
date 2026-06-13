# linux_core/compiler.py
import subprocess
import os
import sys
import time
import threading

def custom_progress_bar(stop_event):
    """Animates a pure-Python progress bar on a loop without external packages."""
    animation_chars = ["■", "■", "■", "■", "■", "■", "■", "■", "■", "■"]
    i = 0
    while not stop_event.is_set():
        fill_level = (i % 10) + 1
        bar = "█" * fill_level + "░" * (10 - fill_level)
        sys.stdout.write(f"\r\033[93m[COMPILER] Building via PyInstaller [{bar}] Compiling system blocks...\033[0m")
        sys.stdout.flush()
        time.sleep(0.25)
        i += 1
        
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()

def build(spec_path,iteration = 1):
    if not os.path.exists(spec_path):
        return False

    # 🎯 THE CWD FIX: Extract the project directory to force PyInstaller to run there!
    project_dir = os.path.dirname(os.path.abspath(spec_path))
    spec_filename = os.path.basename(spec_path)
    
    if iteration == 1:
        command = [sys.executable, "-m", "PyInstaller", "--clean", "-y", spec_filename]
    else:
        command = [sys.executable, "-m", "PyInstaller", "-y", spec_filename]

    stop_compiler_animation = threading.Event()
    progress_thread = threading.Thread(target=custom_progress_bar, args=(stop_compiler_animation,))

    try:
        progress_thread.start()

        process = subprocess.run(
            command,
            cwd=project_dir, # 🎯 THE MAGIC FIX: Compile in the target directory!
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        stop_compiler_animation.set()
        progress_thread.join()
        
        print("\033[92m [COMPILER] Build Successful! New clean binary deployed to dist/ folder.\033[0m")
        return True

    except subprocess.CalledProcessError as e:
        stop_compiler_animation.set()
        progress_thread.join()
        print("\n\033[91m\033[1m [COMPILER] PyInstaller Compilation Fatal Crash!\033[0m")
        print(e.stderr.decode().strip())
        return False
    except Exception as e:
        stop_compiler_animation.set()
        progress_thread.join()
        print(f"\n\033[91m [COMPILER] Unexpected engine failure: {e}\033[0m")
        return False