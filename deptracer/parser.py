# linux_core/parser.py
import re
import os
import subprocess

class TraceParser:
  
    _SYSTEM_CACHE = set()
    
    SYSCALL_ANY = re.compile(
        r'(?:openat|newfstatat|stat|access)\((?:AT_FDCWD,\s*)?' 
        r'"([^"\\]*(?:\\.[^"\\]*)*)"' 
        r'[^)]*\)\s*=\s*(-1\s+\w+|\d+)'
    )
    
    TRACKED_EXTENSIONS = {
    '.so', '.dll', '.dylib', '.pyd',
    '.pt', '.pth', '.onnx', '.pb', '.h5', '.joblib',
    '.npy', '.npz', '.pickle', '.pkl', '.json', '.yaml', '.yml', '.toml', '.csv',
    '.wav', '.mp3', '.flac', '.jpg', '.png', '.gif',
    '.txt', '.md', '.db', '.sqlite', '.dat'
    }
    RELEVANT_ERRORS = {'ENOENT', 'EACCES', 'EPERM', 'ENOEXEC'}

    STATE_LOG = ".akdeptracer_state"

    @staticmethod
    def set_pipeline_state(stage, error, fix):
      with open(STATE_LOG, "w") as f:
        f.write(f"{stage}|{error}|{fix}")

    @classmethod
    def load_system_cache(cls):
        if cls._SYSTEM_CACHE: return
        try:
            result = subprocess.run(["ldconfig", "-p"], stdout=subprocess.PIPE, text=True)
            for line in result.stdout.splitlines():
                if "=>" in line:
                    lib_name = line.split("=>")[0].strip().split()[0]
                    cls._SYSTEM_CACHE.add(lib_name)
        except Exception as e:
            print(f" [PARSER] Warning: Could not load ldconfig cache. {e}")
            cls.set_pipeline_state("PARSER", "Failed to load system cache.", "Check ldconfig availability and permissions.")

    @classmethod
    def is_system_noise(cls, file_path):
        file_name = os.path.basename(file_path)
        if file_name.startswith('_') or file_name.startswith('libpython'): 
            return True
        base_lib_name = re.sub(r'\.so(\.\d+)*$', '.so', file_name)
        if base_lib_name in cls._SYSTEM_CACHE or file_name in cls._SYSTEM_CACHE: 
            return True
        if 'glibc-hwcaps' in file_path: 
            return True
        if 'lib-dynload' in file_path and '.cpython-' in file_name: 
            return True
        return False

    @staticmethod
    def _is_binary_file(path: str) -> bool:
        for ext in TraceParser.TRACKED_EXTENSIONS:
            if ext in path:
                idx = path.rfind(ext)
                after_ext = path[idx + len(ext):]
                if after_ext == '' or re.match(r'^(\.\d+)*$', after_ext):
                    return True
        return False

    @classmethod
    def stream_missing_libraries(cls, log_file_path, verbose=False):
        cls.load_system_cache()
        
        library_status = {}  
        path_mapping = {}    
        seen_warnings = set()

        with open(log_file_path, "r") as file:
            for line_num, line in enumerate(file, 1):
                match = cls.SYSCALL_ANY.search(line)
                if not match: continue

                path = match.group(1)
                result_value = match.group(2)

                if not cls._is_binary_file(path): 
                    continue

                filename = os.path.basename(path)

                if not result_value.startswith("-1"): 
                    if "/tmp/_MEI" in path or path.startswith("/lib") or path.startswith("/usr/lib"):
                        library_status[filename] = "FOUND"
                    continue

                parts = result_value.split()
                if len(parts) < 2: continue
                errno = parts[1]

                if errno not in cls.RELEVANT_ERRORS: 
                    continue

                if '...' in path:
                    if path not in seen_warnings:
                        print(f"[WARNING] Line {line_num}: Path truncated by strace: {path}")
                        cls.set_pipeline_state("PARSER", "Path truncated in strace log.", "Check strace configuration and ensure paths are fully captured.")
                        seen_warnings.add(path)
                    continue

                if errno in {'EACCES', 'EPERM'}:
                    if path not in seen_warnings:
                        print(f"[WARNING] Line {line_num}: File locked/unreadable ({errno}): {path}")
                        cls.set_pipeline_state("PARSER", "File locked/unreadable in strace log.", "Check file permissions and accessibility.")
                        seen_warnings.add(path)
                    continue

                if errno == 'ENOENT':
                    if not cls.is_system_noise(path):
                        if library_status.get(filename) != "FOUND":
                            library_status[filename] = "MISSING"
                            path_mapping[filename] = path
                    else:
                        if verbose:
                            print(f"    \033[90m[PARSER-VERBOSE] Filtered system cache hit: {path}\033[0m")

        for filename, status in library_status.items():
            if status == "MISSING":
                yield path_mapping[filename]

def extract_missing_libraries(log_file_path, verbose=False):
    yield from TraceParser.stream_missing_libraries(log_file_path, verbose=verbose)
    