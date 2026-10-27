"""Project-root compatibility entry point for the canonical App parser package."""
from pathlib import Path
import sys
_runtime=Path(__file__).resolve().parents[1]/'App'
if str(_runtime) not in sys.path:
    sys.path.insert(0,str(_runtime))
__path__=[str(_runtime/'pyresparser')]
from .resume_parser import ResumeParser
