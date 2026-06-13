# linux_core/fixer.py
import os
import re
import tempfile

STATE_LOG = ".akdeptracer_state"

def set_pipeline_state(stage, error, fix):
    with open(STATE_LOG, "w") as f:
        f.write(f"{stage}|{error}|{fix}")

def get_data_dest(absolute_path):
    """Intelligently determines the internal bundle destination for data files."""
    if 'site-packages' in absolute_path:
        parts = absolute_path.split('site-packages' + os.sep)
        if len(parts) > 1:
            rel_path = parts[1] 
            dest_folder = os.path.dirname(rel_path) 
            return dest_folder if dest_folder else '.'
            
    parent_folder = os.path.basename(os.path.dirname(absolute_path))
    return parent_folder if parent_folder else '.'

def patch_spec_file(spec_path, resolved_patches):
    
    if not os.path.exists(spec_path) or not os.access(spec_path, os.W_OK):
        set_pipeline_state("FIXER", f"Spec file '{spec_path}' is not writable.", "Check file permissions.")
        return False

    with open(spec_path, 'r') as file:
        lines = file.readlines()

    binary_injections = ""
    data_injections = ""

    for missing_name, absolute_path in resolved_patches:
        if not os.path.exists(absolute_path):
            continue
            
        if absolute_path.endswith(('.so', '.dll', '.dylib', '.pyd')):
            binary_injections += f"\n    ('{absolute_path}', '.'), # Added by deptracer\n"
        else:

            dest_folder = get_data_dest(absolute_path)
            data_injections += f"\n    ('{absolute_path}', '{dest_folder}'), # Added by deptracer\n"

    bin_idx = next((i for i, l in enumerate(lines) if re.search(r'binaries\s*=\s*\[', l) and 'a.binaries' not in l), None)
    if bin_idx is not None and binary_injections:
        lines[bin_idx] = lines[bin_idx].replace('[', f'[{binary_injections}', 1)
        
    dat_idx = next((i for i, l in enumerate(lines) if re.search(r'datas\s*=\s*\[', l) and 'a.datas' not in l), None)
    if dat_idx is not None and data_injections:
        lines[dat_idx] = lines[dat_idx].replace('[', f'[{data_injections}', 1)

    try:
        target_dir = os.path.dirname(spec_path) or '.'
        with tempfile.NamedTemporaryFile(mode='w', dir=target_dir, delete=False) as tmp:
            tmp.writelines(lines)
            tmp_path = tmp.name
        
        os.replace(tmp_path, spec_path)
        return True
    except Exception as e:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        set_pipeline_state("FIXER", f"File write error: {str(e)}", "Check file permissions and disk space.")
        
        return False