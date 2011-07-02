"""
Simple test script to be invoked as replacement for the slurmd binary.
"""

import sys
import time

if __name__ == '__main__':
    if len(sys.argv) != 6:
        sys.exit(1)

    if sys.argv[1] == 'succeed':
        sys.exit(0)

    if sys.argv[1] == 'sleep':
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            pass
        
        sys.exit(0)

    if sys.argv[1] == 'print':
        sys.stdout.write('writing on stdout\n')
        sys.stdout.flush()
        sys.stderr.write('writing on stderr\n')
        sys.stderr.flush()
        
        sys.exit(0)

    if sys.argv[1] == 'callback':
        fh = open(sys.argv[2], 'w')
        fh.write('|'.join(sys.argv[3:]))
        fh.close()

        sys.exit(0)

    sys.exit(1)