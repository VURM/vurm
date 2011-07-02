"""
Collection of scripts to be installed as executables on the target system

The following restrictions/conventions apply to command definitions:

 * The first letter of the executable name is the letter 'v' (all SLURM
   commands start with the letter 's');

 * The command definition has to be contained in a single module called the
   same as the command itself;

 * Each module defines a function called 'main' which takes no arguments and is
   responsible for the command line parsing and the command dispatching;

 * The entry point is called when invoking the script from the command line by
   including the following snipper::

       if __name__ == '__main__':
           sys.exit(main())

 * After having defined the command, add it to the 'entry-points.ini' file at
   the root of the package directory, using the following format::

       <command-name> = vurm.bin.<command-name>:main

   This directive has to be placed in the 'console_scripts' section.

"""
