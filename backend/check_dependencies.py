
import subprocess
import sys
import shutil
import ctypes
from pathlib import Path

def check_command(cmd):
    """Check if a command exists in PATH"""
    return shutil.which(cmd) is not None

def check_compiler():
    """Check for C compilers"""
    print("Checking for C compilers...")
    
    compilers = {
        "gcc": "GCC (GNU Compiler Collection)",
        "clang": "Clang",
        "cl": "MSVC (Microsoft Visual C++)"
    }
    
    found = []
    for cmd, name in compilers.items():
        if check_command(cmd):
            print(f"✅ Found {name} ({cmd})")
            found.append(cmd)
        else:
            print(f"❌ {name} not found")
            
    if not found:
        print("\n⚠️ No C compiler found. The C optimization engine cannot be built.")
        print("   The system will fallback to the Python implementation (slower but functional).")
        print("   To enable full performance, install MinGW-w64 or Visual Studio Build Tools.")
        return False
        
    print(f"\n✅ Ready to build C engine using: {found[0]}")
    return True

def check_engine():
    """Check if the shared library exists and can be loaded"""
    print("\nChecking C Engine status...")
    
    engine_dir = Path(__file__).parent.parent / "engine"
    
    # Determine ext
    if sys.platform == "win32":
        ext = ".dll"
    else:
        ext = ".so"
        
    lib_path = engine_dir / f"scheduler_engine{ext}"
    
    if not lib_path.exists():
        print(f"⚠️ Engine library not found at: {lib_path}")
        return False
        
    try:
        ctypes.CDLL(str(lib_path))
        print(f"✅ Engine library loaded successfully: {lib_path.name}")
        return True
    except Exception as e:
        print(f"❌ Failed to load engine library: {e}")
        return False

if __name__ == "__main__":
    print("AI Engineering Study Assistant - Dependency Check")
    print("===============================================")
    
    has_compiler = check_compiler()
    has_engine = check_engine()
    
    print("\nSummary")
    print("-------")
    status = "READY" if has_engine else "FALLBACK"
    if has_compiler and not has_engine:
        status = "BUILDABLE"
        
    print(f"System Status: {status}")
    
    if status == "FALLBACK":
        print("-> Using Python fallback for optimization tasks.")
    elif status == "BUILDABLE":
        print("-> C engine dependencies met. Run 'make shared' (or 'gcc...') in /engine to build.")
    elif status == "READY":
        print("-> High-performance C engine is active.")
