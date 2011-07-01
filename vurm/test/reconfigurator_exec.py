#!/usr/bin/env python

"""
Simple test script to be invoked as replacement for the scontrol binary.
"""

import sys

if __name__ == '__main__':
    if len(sys.argv) < 1:
        sys.exit(1)
    
    if sys.argv[1] == 'succeed':
        sys.exit(0)
    
    if sys.argv[1] == 'fail':
        sys.exit(1)
    
    if sys.argv[1] == 'callback':
        with open(sys.argv[2], 'w') as fh:
            fh.write('called')
        
        sys.exit(0)
    
    sys.exit(1)