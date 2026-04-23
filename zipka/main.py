#!/usr/bin/env python3
"""
Claster Forensic Toolkit - Main entry point.
Usage:
    python -m claster gui     # Launch GUI
    python -m claster cli     # Launch CLI
"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Claster Forensic Toolkit")
    parser.add_argument("mode", nargs="?", choices=["gui", "cli"], default="gui",
                        help="Launch mode: gui or cli")
    args = parser.parse_args()

    if args.mode == "gui":
        from claster.gui.__init__ import run_gui
        run_gui()

if __name__ == "__main__":
    main()