#!/usr/bin/env python3
"""Explicit real experimental S3 + SSH onboarding acceptance with generated data only."""
import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('capture_lab',Path(__file__).with_name('run-first-site-capture-lab.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
if __name__=='__main__':m.main('onboarding-ssh-s3-cases.py')
