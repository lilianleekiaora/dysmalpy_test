#!/bin/bash

# Usage: dysmalpy_fit_3d.sh fitting_3D.params

# Setup paths on AFS:
source /afs/mpe.mpg.de/astrosoft/dysmalpy/dysmalpy_setup.sh

# Add fitting_wrappers to path:
export PYTHONPATH="/afs/mpe.mpg.de/astrosoft/dysmalpy/fitting_wrappers/:$PYTHONPATH"

# Run fitting
export DPY_PATH='/afs/mpe.mpg.de/astrosoft/dysmalpy/dysmalpy'

python dysmalpy_fit_single_3D.py $1



