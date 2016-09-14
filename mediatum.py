#! /usr/bin/env nix-shell
#! nix-shell -i python

import sys


if __name__ == '__main__':
    from bin.mediatum import main
    try:
        main()
    except KeyboardInterrupt:
        print(" - Mediatum stopped by KeyboardInterrupt.")
        sys.exit(1)
