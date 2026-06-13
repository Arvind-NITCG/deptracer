# linux_core/tracer.py
import subprocess
import os

def run_and_trace(executable_path, project_dir=".", log_name=None):
    if log_name is None:
        log_name = os.path.abspath(f"trace_{os.getpid()}.log")

    abs_executable = os.path.abspath(executable_path)
    abs_project = os.path.abspath(project_dir)

    bwrap_jail = [
        "bwrap",
        "--dev-bind", "/", "/",                     
        "--tmpfs", "/home",                         
        "--ro-bind", abs_project, abs_project,      
        "--bind", abs_executable, abs_executable,   
        "--chdir", abs_project,                     
        "--unshare-all",                            
        abs_executable                              
    ]

    command = [
        "strace", 
        "-f", 
        "-s", "2048",  
        "-o", log_name, 
        "-e", "trace=file"
    ] + bwrap_jail

    try:
        process = subprocess.Popen(
            command, 
            cwd=project_dir,
            stdin = subprocess.DEVNULL,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        process.communicate()
        rc = process.returncode
        
        
        if os.path.exists(log_name):
            return log_name, rc
        else:
            return None, rc
            
    except Exception as e:
        return None, -1