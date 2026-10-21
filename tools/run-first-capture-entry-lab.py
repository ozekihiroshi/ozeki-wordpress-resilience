#!/usr/bin/env python3
"""Generated isolated WP/MariaDB verification of mandatory first capture admission."""
import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('capture_lab',Path(__file__).with_name('run-first-site-capture-lab.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
if __name__=='__main__':m.main('first-capture-entry-cases.py')
