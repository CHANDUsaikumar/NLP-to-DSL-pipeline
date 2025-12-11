import sys
from pathlib import Path

# Ensure repository root and package paths are available for imports
REPO_ROOT = Path(__file__).resolve().parents[2]
PKG_SRC = REPO_ROOT / 'nl_dsl_strategy' / 'src'
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
if str(PKG_SRC) not in sys.path:
    sys.path.append(str(PKG_SRC))
