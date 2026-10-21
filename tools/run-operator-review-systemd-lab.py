"""Reuse generated SSH/systemd/three-VM harness with operator confirmation reports."""
import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('lab',Path(__file__).with_name('run-generated-systemd-lab.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
if __name__=='__main__':m.main(review_mode=True)
