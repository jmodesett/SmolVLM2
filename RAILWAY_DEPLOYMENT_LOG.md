# Railway Deployment Failure Log - SmolVLM2 Backend

## Summary of Deployment Attempts

**Repository**: SmolVLM2 Dojo Backend Video Analysis System  
**Target Platform**: Railway (Linux/Ubuntu + Python 3.12)  
**Goal**: Deploy turnkey video analysis system with minimal changes

---

## Failure #1 - MLX Dependencies (2025-09-23 18:35)

### Error:
```
error: pathspec 'smolvlm' did not match any file(s) known to git
× git checkout -q smolvlm did not run successfully.
```

### Root Cause:
- `requirements.txt` contained MLX-specific dependencies
- `git+https://github.com/huggingface/transformers@smolvlm` - branch doesn't exist
- `git+https://github.com/Blaizzy/mlx-vlm@smolvlm` - MLX is Apple Silicon only, won't work on Linux

### Resolution Applied:
- Removed MLX dependencies
- Created `railway_video_generator.py` using transformers directly
- Updated `app.py` to use Railway-compatible generator

---

## Failure #2 - PyTorch Version (2025-09-23 18:44)

### Error:
```
ERROR: Could not find a version that satisfies the requirement torch==2.1.1
ERROR: No matching distribution found for torch==2.1.1
```

### Root Cause:
- PyTorch 2.1.1 is no longer available on PyPI
- Available versions: 2.2.0, 2.2.1, 2.2.2, 2.3.0, 2.3.1, 2.4.0, 2.4.1, 2.5.0+

### Resolution Applied:
- Updated `torch==2.1.1` → `torch==2.4.1`
- Updated `opencv-python-headless==4.8.1.78` → `opencv-python-headless==4.10.0.84`
- Updated `transformers==4.45.0` → `transformers==4.44.0`

---

## Failure #3 - Python 3.12 Compatibility (2025-09-23 18:47)

### Error:
```
ModuleNotFoundError: No module named 'distutils'
```

### Root Cause:
- Railway uses Python 3.12 
- `distutils` was removed in Python 3.12 (PEP 632)
- `numpy==1.24.3` is trying to build from source and requires distutils
- Old numpy versions don't have pre-built wheels for Python 3.12

### Technical Details:
- Python 3.12 removed distutils module entirely
- numpy 1.24.3 (March 2023) predates Python 3.12 (October 2023)
- Need numpy >= 1.26.0 for Python 3.12 compatibility with pre-built wheels

---

## Pattern Analysis:

### Core Issue: 
The turnkey system was built for **Apple Silicon + MLX** but Railway uses **Linux + Python 3.12**

### Dependency Conflicts:
1. **MLX Framework**: Apple-only, doesn't exist on Linux
2. **Old Package Versions**: Predate Python 3.12, lack compatibility
3. **Build Dependencies**: Missing system libraries for source compilation

### Required Approach:
- **Minimal Code Changes**: Preserve existing functionality 
- **Compatible Dependencies**: Use versions with pre-built wheels for Python 3.12
- **Linux Compatibility**: Replace Apple-specific components

---

## Next Actions:

### Immediate Fix Required:
1. Update numpy to Python 3.12 compatible version (>= 1.26.0)
2. Verify all dependencies have pre-built wheels 
3. Test with Python 3.12 environment

### Dependencies Status:
- ✅ `fastapi==0.104.1` - Compatible
- ✅ `torch==2.4.1` - Compatible with Python 3.12
- ❌ `numpy==1.24.3` - **FAILS** on Python 3.12
- ⚠️  Other deps may need verification

### Preservation Goals:
- ✅ Keep all API endpoints identical
- ✅ Maintain video analysis functionality  
- ✅ Preserve Dojo app integration
- ✅ No architectural changes to core system