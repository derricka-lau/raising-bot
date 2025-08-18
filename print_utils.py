# print_utils.py
from datetime import datetime
import builtins

def print_with_ts(*args, **kwargs):
    ts = datetime.now().strftime('[TS:%Y-%m-%d %H:%M:%S]')
    builtins._original_print(ts, *args, **kwargs)

# Patch builtins.print only once
if not hasattr(builtins, '_original_print'):
    builtins._original_print = builtins.print
    builtins.print = print_with_ts
