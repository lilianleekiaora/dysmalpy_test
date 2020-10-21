# Script to plot kin

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os, sys
from contextlib import contextmanager

import copy

import datetime

import numpy as np
import pandas as pd
import astropy.units as u

from dysmalpy import data_classes
from dysmalpy import parameters
from dysmalpy import fitting
from dysmalpy import galaxy
from dysmalpy import models
from dysmalpy import plotting
from dysmalpy import utils as dysmalpy_utils

from dysmalpy import aperture_classes
from dysmalpy import instrument

import scipy.optimize as scp_opt

from astropy.table import Table

import astropy.io.fits as fits

try:
    import utils_io
    import dysmalpy_fit_single_1D
    import dysmalpy_fit_single_2D
except:
    from . import utils_io
    from . import dysmalpy_fit_single_1D
    from . import dysmalpy_fit_single_2D



#
def plot_curve_components_overview(fname_gal=None, fname_results=None, param_filename=None, 
        overwrite = False, 
        overwrite_curve_files=False, 
        outpath=None):
    
    # Reload the galaxy:
    gal = galaxy.load_galaxy_object(filename=fname_gal)
    
    params = utils_io.read_fitting_params(fname=param_filename)
    
    if 'aperture_radius' not in params.keys():
        params['aperture_radius'] = -99.
    
    if ('moment_calc' in params.keys()):
        moment_calc = params['moment_calc']
    else:
        moment_calc = False
        
    #
    if ('partial_weight' in params.keys()):
        partial_weight = params['partial_weight']
    else:
        # Preserve previous default behavior
        partial_weight = False
    
    
    plotting.plot_rotcurve_components(gal=gal, 
                overwrite=overwrite, overwrite_curve_files=overwrite_curve_files, 
                outpath = outpath,
                profile1d_type = params['profile1d_type'], 
                oversample=params['oversample'], oversize=params['oversize'], 
                aperture_radius=params['aperture_radius'],
                moment=moment_calc,
                partial_weight=partial_weight)
                
                
    return None


#
def plot_results_multid(param_filename=None, data=None, fit_ndim=None,
    remove_shift=True,
    show_1d_apers=False,
    plot_type='pdf'):
    
    # Read in the parameters from param_filename:
    params = utils_io.read_fitting_params(fname=param_filename)
    
    # Setup some paths:
    outdir = utils_io.ensure_path_trailing_slash(params['outdir'])
    params['outdir'] = outdir
    
    if 'plot_type' not in params.keys():
        params['plot_type'] = plot_type
    
    if fit_ndim == 2:
        gal, fit_dict = dysmalpy_fit_single_2D.setup_single_object_2D(params=params, data=data)
    elif fit_ndim == 1:
        gal, fit_dict = dysmalpy_fit_single_1D.setup_single_object_1D(params=params, data=data)
    
    
    # Reload the best-fit:
    if fit_dict['fit_method'] == 'mcmc':
        gal, results = fitting.reload_all_fitting(filename_galmodel=fit_dict['f_model'], 
                    filename_mcmc_results=fit_dict['f_mcmc_results'])
    elif fit_dict['fit_method'] == 'mpfit':
        gal, results = fitting.reload_all_fitting_mpfit(filename_galmodel=fit_dict['f_model'], 
                    filename_results=fit_dict['f_results'])
                    
                    
    print("results.bestfit_parameters={}".format(results.bestfit_parameters))
    plot_results_multid_general(param_filename=param_filename, data=data, 
        fit_ndim=fit_ndim,
        remove_shift=remove_shift,
        show_1d_apers=show_1d_apers,
        theta = results.bestfit_parameters,
        fileout=fit_dict['f_plot_bestfit_multid'])
    
    return None
    
#
def plot_results_multid_general(param_filename=None, 
    data=None, 
    fit_ndim=None,
    remove_shift=True,
    show_1d_apers=False,
    theta = None,
    fileout=None):
    
    
    gal, fit_dict = load_setup_multid_multifit_data(param_filename=param_filename, 
                        data=data, fit_ndim=fit_ndim)
    
    if theta is None:
        theta=results.bestfit_parameters
    if fileout is None:
        raise ValueError
        
    
    # Plot:
    plotting.plot_model_multid(gal, theta=theta, 
            fitdispersion=fit_dict['fitdispersion'], 
            oversample=fit_dict['oversample'],fileout=fileout,
            show_1d_apers=show_1d_apers, remove_shift=remove_shift)
            
    
    return None
    
#


#
############################################################################


def load_setup_multid_multifit_data(param_filename=None, data=None, fit_ndim=None):
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Read in the parameters from param_filename:
    params = utils_io.read_fitting_params(fname=param_filename)
    
    # Setup some paths:
    outdir = utils_io.ensure_path_trailing_slash(params['outdir'])
    params['outdir'] = outdir
    
    # Setup datadir, if set. If not set (so datadir=None), fdata must be the full path.
    if 'datadir' in params.keys():
        datadir = params['datadir']
    else:
        datadir = None
    if datadir is None:
        datadir = ''
    ####
    if 'datadir1d' in params.keys():
        datadir1d = params['datadir1d']
    else:
        datadir1d = None
    if datadir1d is None:
        datadir1d = datadir
    #
    ####
    if 'datadir2d' in params.keys():
        datadir2d = params['datadir2d']
    else:
        datadir2d = None
    if datadir2d is None:
        datadir2d = datadir
    ####
    
    
    if fit_ndim == 2:
        gal, fit_dict = dysmalpy_fit_single_2D.setup_single_object_2D(params=params, data=data)
    elif fit_ndim == 1:
        gal, fit_dict = dysmalpy_fit_single_1D.setup_single_object_1D(params=params, data=data)
        
        
    # Reload the best-fit:
    if fit_dict['fit_method'] == 'mcmc':
        gal, results = fitting.reload_all_fitting(filename_galmodel=fit_dict['f_model'], 
                    filename_mcmc_results=fit_dict['f_mcmc_results'])
    elif fit_dict['fit_method'] == 'mpfit':
        gal, results = fitting.reload_all_fitting_mpfit(filename_galmodel=fit_dict['f_model'], 
                    filename_results=fit_dict['f_results'])
                    
    # Load the other data:
    if fit_ndim == 2:
        if 'fdata_1d_mask' in params.keys():
            fdata_mask = datadir1d+params['fdata_1d_mask']
        else:
            fdata_mask = None
        
        #### 
        # Setup params1d
        params1d = copy.deepcopy(params)
    
        test_keys = ['data_inst_corr', 'pixscale', 'psf_type', 'psf_fwhm', 
                    'psf_fwhm1', 'psf_fwhm2', 'psf_beta', 'psf_scale1', 'psf_scale2',
                    'use_lsf', 'sig_inst_res',
                    'fov', 'spec_type', 'spec_step', 'spec_start', 'nspec']
        for tkey in test_keys:
            if '{}_1d'.format(tkey) in params1d.keys():
                params1d['{}'.format(tkey)] = params1d['{}_1d'.format(tkey)]
    
    
        #####
        # Setup instrument:
        try:
            if params1d['psf_type'].lower().strip() == 'gaussian':
                beamsize = params1d['psf_fwhm']*u.arcsec              # FWHM of beam, Gaussian
                beam = instrument.GaussianBeam(major=beamsize)
            elif params1d['psf_type'].lower().strip() == 'moffat':
                beamsize = params1d['psf_fwhm']*u.arcsec              # FWHM of beam, Moffat
                beta = params1d['psf_beta']
                beam = instrument.Moffat(major_fwhm=beamsize, beta=beta)
            elif params1d['psf_type'].lower().strip() == 'doublegaussian':
                # Kernel of both components multipled by: self._scaleN / np.sum(kernelN.array)
                #    -- eg, scaleN controls the relative amount of flux in each component.

                beamsize1 = params1d['psf_fwhm1']*u.arcsec              # FWHM of beam, Gaussian
                beamsize2 = params1d['psf_fwhm2']*u.arcsec              # FWHM of beam, Gaussian

                try:
                    scale1 = params1d['psf_scale1']                     # Flux scaling of component 1
                except:
                    scale1 = 1.                                       # If ommitted, assume scale2 is rel to scale1=1.
                scale2 = params1d['psf_scale2']                         # Flux scaling of component 2

                beam = instrument.DoubleBeam(major1=beamsize1, major2=beamsize2, 
                                scale1=scale1, scale2=scale2)

            else:
                raise ValueError("PSF type {} not recognized!".format(params['psf_type']))
            
            #
            inst = instrument.Instrument()
            if params1d['use_lsf']:
                sig_inst = params1d['sig_inst_res'] * u.km / u.s  # Instrumental spectral resolution  [km/s]
                lsf = instrument.LSF(sig_inst)
                inst.lsf = lsf
                inst.set_lsf_kernel()

            inst.beam = beam
            inst.pixscale = params1d['pixscale'] * u.arcsec
        
            # Just set the same
            inst.fov = [params1d['fov_npix'], params1d['fov_npix']] 
            inst.spec_type = params1d['spec_type']
            inst.spec_step = params1d['spec_step'] * u.km / u.s
            inst.spec_start = params1d['spec_start'] * u.km / u.s
            inst.nspec = params1d['nspec']

            # Set the beam kernel so it doesn't have to be calculated every step
            inst.set_beam_kernel(support_scaling=12.)   # ORIGINAL: support_scaling=8.

            # Add the model set and instrument to the Galaxy
            gal.instrument1d = inst
        except:
            gal.instrument1d = None
        
        #### 
        # Setup data1d
    
        data1d = utils_io.load_single_object_1D_data(fdata=params1d['fdata_1d'], fdata_mask=fdata_mask, params=params1d, datadir=datadir1d)
        data1d.filename_velocity = datadir1d+params1d['fdata_1d']
    
        if (params1d['profile1d_type'] != 'circ_ap_pv') & (params1d['profile1d_type'] != 'single_pix_pv'):
            data_orig = copy.deepcopy(gal.data)
            inst_orig = copy.deepcopy(gal.instrument)
            gal.data = data1d
            gal.instrument = gal.instrument1d
            data1d.apertures = utils_io.setup_basic_aperture_types(gal=gal, params=params1d)
            data1d.profile1d_type = params1d['profile1d_type']
            # Reset:
            gal.data = data_orig
            gal.instrument = inst_orig
    
        gal.data1d = data1d
    
    
    elif fit_ndim == 1:
        data2d = utils_io.load_single_object_2D_data(params=params, skip_crop=True, datadir=datadir2d)
        gal.data2d = data2d
    
    
        #### 
        # Setup params2d
        params2d = copy.deepcopy(params)
    
        test_keys = ['data_inst_corr', 'pixscale', 'psf_type', 'psf_fwhm', 
                    'psf_fwhm1', 'psf_fwhm2', 'psf_beta', 'psf_scale1', 'psf_scale2',
                    'use_lsf', 'sig_inst_res',
                    'fov', 'spec_type', 'spec_step', 'spec_start', 'nspec']
        for tkey in test_keys:
            if '{}_2d'.format(tkey) in params2d.keys():
                params2d['{}'.format(tkey)] = params2d['{}_2d'.format(tkey)]
    
    
        #####
        # Setup instrument:
        try:
            if params2d['psf_type'].lower().strip() == 'gaussian':
                beamsize = params2d['psf_fwhm']*u.arcsec              # FWHM of beam, Gaussian
                beam = instrument.GaussianBeam(major=beamsize)
            elif params2d['psf_type'].lower().strip() == 'moffat':
                beamsize = params2d['psf_fwhm']*u.arcsec              # FWHM of beam, Moffat
                beta = params2d['psf_beta']
                beam = instrument.Moffat(major_fwhm=beamsize, beta=beta)
            elif params2d['psf_type'].lower().strip() == 'doublegaussian':
                # Kernel of both components multipled by: self._scaleN / np.sum(kernelN.array)
                #    -- eg, scaleN controls the relative amount of flux in each component.
            
                beamsize1 = params2d['psf_fwhm1']*u.arcsec              # FWHM of beam, Gaussian
                beamsize2 = params2d['psf_fwhm2']*u.arcsec              # FWHM of beam, Gaussian
            
                try:
                    scale1 = params2d['psf_scale1']                     # Flux scaling of component 1
                except:
                    scale1 = 1.                                         # If omitted, assume scale2 is rel to scale1=1.
                scale2 = params2d['psf_scale2']                         # Flux scaling of component 2

                beam = instrument.DoubleBeam(major1=beamsize1, major2=beamsize2, 
                                scale1=scale1, scale2=scale2)

            else:
                raise ValueError("PSF type {} not recognized!".format(params['psf_type']))
            
            #
            inst = instrument.Instrument()
            if params2d['use_lsf']:
                sig_inst = params2d['sig_inst_res'] * u.km / u.s  # Instrumental spectral resolution  [km/s]
                lsf = instrument.LSF(sig_inst)
                inst.lsf = lsf
                inst.set_lsf_kernel()

            inst.beam = beam
            inst.pixscale = params2d['pixscale'] * u.arcsec
        
            # Just set the same
            inst.fov = [params2d['fov_npix'], params2d['fov_npix']] 
            inst.spec_type = params2d['spec_type']
            inst.spec_step = params2d['spec_step'] * u.km / u.s
            inst.spec_start = params2d['spec_start'] * u.km / u.s
            inst.nspec = params2d['nspec']

            # Set the beam kernel so it doesn't have to be calculated every step
            inst.set_beam_kernel(support_scaling=12.)   # ORIGINAL: support_scaling=8.

            # Add the model set and instrument to the Galaxy
            gal.instrument2d = inst
        except:
            gal.instrument2d = None
        
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    return gal, fit_dict




