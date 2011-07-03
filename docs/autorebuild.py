"""
Launch this as a shell script to observe this directory and automatically
rebuild you sphinx documentation on changes.
"""



import sys
import os
import fsevents
import subprocess
import datetime
import time



def main():
    os.chdir(os.path.dirname(__file__))

    observer = fsevents.Observer()

    def callback(event):
        if '_build' in event.name:
            return

        if not event.name.endswith('.rst'):
            return

        print "Rebuilding", event

        subprocess.call(['make', 'html'])
        subprocess.call(['touch', 'rebuilt'])

    stream = fsevents.Stream(callback, '.', file_events=True)
    observer.schedule(stream)

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print "Stopping..."

    observer.unschedule(stream)
    observer.stop()
    observer.join()



if __name__ == '__main__':
    sys.exit(main())
