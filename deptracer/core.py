# core.py
import os
import sys
import platform
import time
from pathlib import Path

class UI:
    GREEN = "\033[92m"
    RED = "\033[91m"
    BLUE = "\033[34m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @classmethod
    def step(cls, module, text):
        """Prints standard operations: [MODULE] in Blue, text in White."""
        print(f"{cls.BLUE}{cls.BOLD}[{module}]{cls.RESET} {text}")

    @classmethod
    def success(cls, module, text):
        """Prints successful operations entirely in Green."""
        print(f"{cls.GREEN}{cls.BOLD}[{module}] {text}{cls.RESET}")

    @classmethod
    def error(cls, module, text):
        """Prints fatal/error operations entirely in Red."""
        print(f"{cls.RED}{cls.BOLD}[{module}] {text}{cls.RESET}")

from . import tracer
from . import parser
from . import resolver
from . import fixer
from . import compiler
from . import explain as explainer

STATE_LOG = ".akdeptracer_state"

def set_pipeline_state(stage, error, fix):
    with open(STATE_LOG, "w") as f:
        f.write(f"{stage}|{error}|{fix}")

def run_akdeptracer(project_dir, binary_name, spec_name, verbose=False):
    
    if platform.system().lower() != "linux":
        UI.error("CORE", "Non-Linux OS detected.")
        set_pipeline_state("ENVIRONMENT", "Non-Linux OS detected.", "Use Linux.")
        sys.exit(1)

    root_dir = Path(project_dir).resolve()
    target_binary = root_dir / "dist" / binary_name
    spec_file = root_dir / spec_name
    
    if not spec_file.exists():
        UI.error("CORE", f"Setup Error: {spec_file} not found.")
        set_pipeline_state("SETUP", f"Missing {spec_name}", "Run pyinstaller first.")
        sys.exit(1)

    iteration = 1
    unresolved_from_previous = set()
    total_resolved_so_far = 0
    start_time = time.time()
    
    historically_injected = set()
    
    while True:
        print("")
        UI.step("CORE", f"Starting iteration {iteration}")
        
        trace_result = tracer.run_and_trace(str(target_binary), str(project_dir), verbose=verbose)
        if not trace_result or not trace_result[0]:
            UI.error("CORE", "Tracer failed. Pipeline aborted.")
            set_pipeline_state("TRACER", "Failed to trace binary.", "Check binary and permissions.Possible solution: chmod +x on the binary. Also ensure the binary is a valid executable. bwrap and strace must be installed on the host system.")
            break
        else:
            UI.step("TRACER", "Sandbox Created. Successfully Communicated with Kernel ")
            
        log_path, returncode = trace_result
        resolved_patches = []
        iteration_unresolved = set()
        
        missing_from_parser = list(parser.extract_missing_libraries(log_path, verbose=verbose))
        
        #if os.path.exists(log_path):
            #os.remove(log_path)
            
        if not missing_from_parser:
            print("")
            if returncode != 0:
                UI.error("CORE", f"DEPENDENCIES SECURE, BUT APPLICATION CRASHED (Code {returncode})")
                set_pipeline_state("APPLICATION", str(returncode), "Check Python logic.")
            else:
                UI.success("CORE", "EXECUTABLE IS FULLY SAFE FOR PRODUCTION!")
                set_pipeline_state("SUCCESS", "Clean Execution", "None")
            break

        for missing_full_path in missing_from_parser:
            target_filename = os.path.basename(missing_full_path)

            if target_filename in historically_injected:
                print("")
                UI.error("CORE", f"FATAL: Absolute Path / Logic Deadlock on '{target_filename}'!")
                set_pipeline_state("DEADLOCK", "Absolute Path Deadlock", f"Modify your code to check sys._MEIPASS for {target_filename}.Explanation: We already injected this file into PyInstaller, but the app STILL crashed looking for it.This happens if your Python code hardcodes an absolute path (e.g., ctypes.CDLL('/exact/path.so')).PyInstaller puts files in sys._MEIPASS. Your Python code must be updated to look there!")
                sys.exit(1)

            UI.step("PARSER", f" Missing file named {target_filename}")

            found_path = resolver.hunt_missing_library(target_filename, str(project_dir), verbose=verbose)
            if found_path:
                UI.step("RESOLVER", f"Found {target_filename} at {found_path}")
                resolved_patches.append((target_filename, found_path))
                historically_injected.add(target_filename) 
            else:
                iteration_unresolved.add(target_filename)
                
        if iteration_unresolved == unresolved_from_previous and iteration_unresolved:
            print("")
            UI.error("CORE", f"FATAL: Unresolvable dependencies detected:")
            for lib in iteration_unresolved:
                print(f"  • {lib} not found on host system")
            set_pipeline_state("RESOLVER", "Dependencies missing from disk.", "Install system packages.")
            break
            
        unresolved_from_previous = iteration_unresolved
        
        if not fixer.patch_spec_file(str(spec_file), resolved_patches):
            UI.error("CORE", "Fixer failed to patch the .spec file. Pipeline aborted.")
            set_pipeline_state("FIXER", "Script injection failed.", "Check fixer script.")
            break
        else:
            UI.step("FIXER", f"Spec file patched with {len(resolved_patches)} new entries. Ready to recompile.")
            
        if not compiler.build(str(spec_file),iteration = iteration,verbose=verbose):
            UI.error("CORE", "Compiler failed to build the executable. Pipeline aborted.")
            set_pipeline_state("COMPILER", "Compilation crashed.", "Check compilation process.")
            break
        else:
                UI.step("COMPILER", "Build successful. Checking for remaining issues...")
        iteration += 1
