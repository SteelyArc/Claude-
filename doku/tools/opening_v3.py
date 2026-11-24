"""Opening sequence in the broadcast-documentary style (same timing as opening.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import pro_style
import opening
import visual_test

pro_style.patch(opening, visual_test)

if __name__ == "__main__":
    opening.main()
