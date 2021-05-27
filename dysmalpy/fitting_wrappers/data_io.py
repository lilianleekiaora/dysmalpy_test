# Methods for loading data for fitting wrappers

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os, sys
import platform
import shutil

# import tkinter as tk
# from tkinter import filedialog

import datetime

import numpy as np
import pandas as pd
import astropy.units as u
import astropy.constants as apy_con

try:
    import tkinter_io
except ImportError:
    from . import tkinter_io

from dysmalpy import data_classes
from dysmalpy import utils as dysmalpy_utils
from dysmalpy import config

import astropy.io.fits as fits

from dysmalpy.fitting_wrappers.utils_calcs import auto_gen_3D_mask, _auto_truncate_crop_cube
from dysmalpy.fitting_wrappers.setup_gal_models import setup_data_weighting_method

def read_fitting_params_input(fname=None):
    params = {}

    columns = ['keys', 'values']
    df = pd.read_csv(fname, sep=',', comment='#', names=columns, skipinitialspace=True).copy()

    for j, key in enumerate(df['keys'].values):
        if key is np.NaN:
            pass
        else:
            valset = False
            try:
                tmpval = df['values'][j].split('#')[0].strip()
            except:
                try:
                    tmpval = df['values'][j].strip()
                except:
                    print("param key: {}".format(key))
                    print("param line: {}".format(df['values'][j]))
                    raise ValueError
            try:
                tmparr = tmpval.split(' ')
                tmparrnew = []
                if len(tmparr) > 1:
                    tmparrnew = []
                    for ta in tmparr:
                        if len(ta) > 0:
                            tv = ta.strip()
                            try:
                                tvn = np.float(tv)
                            except:
                                tvn = tv
                            tmparrnew.append(tvn)
                    tmpval = tmparrnew
                    valset = True

            except:
                pass

            if not valset:
                strtmpval = str(tmpval).strip()
                if strtmpval == 'True':
                    tmpval = True
                elif strtmpval == 'False':
                    tmpval = False
                elif strtmpval == 'None':
                    tmpval = None
                elif strtmpval.lower() == 'inf':
                    tmpval = np.inf
                else:
                    try:
                        fltval = np.float(tmpval)
                        if (fltval % 1) == 0.:
                            tmpval = np.int(fltval)
                        else:
                            tmpval = fltval
                    except:
                        tmpval = strtmpval.strip()

            params[key] = tmpval

    return params
    #

def read_fitting_params(fname=None):
    if fname is None:
        raise ValueError("parameter filename {} not found!".format(fname))

    # READ FILE HERE!
    param_input = read_fitting_params_input(fname=fname)

    # Set some defaults if not otherwise specified
    params_wrapper_specific = {'oversample': 1,
                               'include_halo': False,
                               'halo_profile_type': 'NFW',
                               'weighting_method': None}
    if 'fit_method' in list(param_input.keys()):
        fit_method = param_input['fit_method'].strip().lower()
        if param_input['fit_method'].strip().lower() == 'mcmc':
            params = config.Config_fit_mcmc().dict
        elif param_input['fit_method'].strip().lower() == 'mpfit':
            params = config.Config_fit_mpfit().dict
    else:
        fit_method = None
        params = {'outdir': None, 'overwrite': False}

    params.update(params_wrapper_specific)

    # param_filename
    fname_split = fname.split('/')
    params['param_filename'] = fname_split[-1]

    for key in param_input.keys():
        params[key] = param_input[key]

    # Catch depreciated case:
    if 'halo_inner_slope_fit' in params.keys():
        if params['halo_inner_slope_fit']:
            if params['halo_profile_type'].upper() == 'NFW':
                print("using depreciated param setting 'halo_inner_slope_fit=True'.")
                print("Assuming 'halo_profile_type=TwoPowerHalo' halo form.")
                params['halo_profile_type'] = 'TwoPowerHalo'

    # Catch other cases:
    if 'components_list' in params.keys():
        if 'halo' in params['components_list']:
            params['include_halo'] = True

    if params['include_halo']:
        if (fit_method is not None):
            if params['blob_name'] is None:
                if 'fdm_fixed' in params.keys():
                    if not params['fdm_fixed']:
                        # fdm is free
                        if params['halo_profile_type'].upper() == 'NFW':
                            params['blob_name'] = 'mvirial'
                        elif params['halo_profile_type'].lower() == 'twopowerhalo':
                            params['blob_name'] = ['alpha', 'mvirial']
                        elif params['halo_profile_type'].lower() == 'burkert':
                            params['blob_name'] = ['rb', 'mvirial']
                    else:
                        if params['halo_profile_type'].upper() == 'NFW':
                            if params['halo_conc_fixed'] is False:
                                params['blob_name'] = ['fdm', 'mvirial']
                            else:
                                params['blob_name'] = 'fdm'
                        else:
                            params['blob_name'] = ['fdm', 'mvirial']

            # ONLY SET THESE IF FITTING, FOR NOW
            if ('fdm_fixed' not in params.keys()) | ('fdm' not in params.keys()):
                if params['mvirial_fixed'] is True:
                    params['fdm'] = 0.5
                    params['fdm_fixed'] = False
                    params['fdm_bounds'] = [0, 1]
                    params['blob_name'] = 'mvirial'
                else:
                    params['fdm'] = -99.9
                    params['fdm_fixed'] = True
                    params['fdm_bounds'] = [0, 1]
                    params['blob_name'] = 'fdm'

            # Put a default, if missing
            if ('mvirial_tied' not in params.keys()):
                if params['halo_profile_type'].upper() == 'NFW':
                    params['mvirial_tied'] = False
                #elif ((params['halo_profile_type'].lower() == 'twopowerhalo') | \
                #            (params['halo_profile_type'].lower() == 'burkert')):
                else:
                    # Default to the "old" behavior
                    params['mvirial_tied'] = True

        # Put a default, if missing:
        if ('mhalo_relation' not in params.keys()):
            # Default to MISSING
            params['mhalo_relation'] = None

        if ('truncate_lmstar_halo' not in params.keys()):
            # Default to MISSING
            params['truncate_lmstar_halo'] = None

    return params


def save_results_ascii_files(fit_results=None, gal=None, params=None, overwrite=False):
    filename_extra = ''
    if 'filename_extra' in params.keys():
        if params['filename_extra'] is not None:
            filename_extra =  params['filename_extra']
    f_ascii_pretty = params['outdir']+'{}{}_{}_best_fit_results_report.info'.format(params['galID'],
                            filename_extra, params['fit_method'])
    f_ascii_machine = params['outdir']+'{}{}_{}_best_fit_results.dat'.format(params['galID'],
                            filename_extra, params['fit_method'])

    fit_results.results_report(gal=gal, filename=f_ascii_pretty, params=params,
                    report_type='pretty', overwrite=overwrite)
    fit_results.results_report(gal=gal, filename=f_ascii_machine, params=params,
                        report_type='machine', overwrite=overwrite)

    return None


def save_results_ascii_files_mcmc(fit_results=None, gal=None, params=None, outdir=None, galID=None):
    # Backwards compatibility:
    # Depreciated:
    wrn_msg = "Method save_results_ascii_files_mcmc() depreciated.\n"
    wrn_msg += "Use save_results_ascii_files() in the future."
    raise FutureWarning(wrn_msg)
    save_results_ascii_files(fit_results=fit_results, gal=gal, params=params, overwrite=True)
    return None

def save_results_ascii_files_mpfit(fit_results=None, gal=None, params=None, outdir=None, galID=None):
    # Backwards compatibility:
    # Depreciated:
    wrn_msg = "Method save_results_ascii_files_mpfit() depreciated.\n"
    wrn_msg += "Use save_results_ascii_files() in the future."
    raise FutureWarning(wrn_msg)
    save_results_ascii_files(fit_results=fit_results, gal=gal, params=params, overwrite=True)
    return None



def read_results_ascii_file(fname=None):


    names = ['component', 'param_name', 'fixed', 'best_value', 'l68_err', 'u68_err']

    data = pd.read_csv(fname, sep=' ', comment='#', names=names, skipinitialspace=True,
                    index_col=False)


    return data




def make_catalog_row_entry(ascii_data=None, galID=None):

    params = ['total_mass', 'r_eff_disk', 'bt', 'mvirial', 'conc', 'sigma0']
    extra_params = ['f_DM_RE']

    data = pd.DataFrame({'galID': galID},
                         index=[0])

    for par in params:
        whrow = np.where((ascii_data['param_name'].str.strip()==par))[0][0]
        data[par] = ascii_data['best_value'].iloc[whrow]
        data[par+"_u68_err"] = ascii_data['u68_err'].iloc[whrow]
        data[par+"_l68_err"] = ascii_data['l68_err'].iloc[whrow]

    for par in extra_params:
        whrow = np.where((ascii_data['component'].str.strip()==par))[0][0]
        data[par] = ascii_data['best_value'].iloc[whrow]
        data[par+"_u68_err"] = ascii_data['u68_err'].iloc[whrow]
        data[par+"_l68_err"] = ascii_data['l68_err'].iloc[whrow]


    return data


def load_single_object_1D_data(fdata=None, fdata_mask=None, params=None, datadir=None):

    # Setup datadir, if set. If not set (so datadir=None), fdata must be the full path.
    if datadir is None:
        # If datadir not passed directly, look for entry in params file:
        if 'datadir' in params.keys():
            datadir = params['datadir']
        # If not passed directly as kwarg, and missing from params file, set to empty -- filenames must be full path.
        if datadir is None:
            datadir = ''

    # Load the data set to be fit
    dat_arr =   np.loadtxt(datadir+fdata)
    gal_r =     dat_arr[:,0]
    gal_vel =   dat_arr[:,1]
    gal_disp =  dat_arr[:,3]
    err_vel =   dat_arr[:,2]
    err_disp =  dat_arr[:,4]

    try:
        gal_flux = dat_arr[:,5]
        err_flux = dat_arr[:,6]
    except:
        gal_flux = None
        err_flux = None


    if fdata_mask is not None:
        if os.path.isfile(datadir+fdata_mask):
            msk_arr =   np.loadtxt(datadir+fdata_mask)
            msk_r =     msk_arr[:,0]
            msk_vel =   msk_arr[:,1]
            msk_disp =  msk_arr[:,2]
        else:
            msk_vel = None
            msk_disp = None
    else:
        msk_vel = None
        msk_disp = None
    #####
    # Apply symmetrization if wanted:
    try:
        if params['symmetrize_data']:
            gal_r_new, gal_vel, err_vel = dysmalpy_utils.symmetrize_1D_profile(gal_r, gal_vel, err_vel, sym=1)
            gal_r, gal_disp, err_disp = dysmalpy_utils.symmetrize_1D_profile(gal_r, gal_disp, err_disp, sym=2)
            if gal_flux is not None:
                gal_r, gal_flux, err_flux = dysmalpy_utils.symmetrize_1D_profile(gal_r, gal_flux, err_flux, sym=2)
    except:
        pass


    if 'weighting_method' in params.keys():
        gal_weight = setup_data_weighting_method(method=params['weighting_method'], r=gal_r)
    else:
        gal_weight = None
    #
    if ('xcenter' in params.keys()):
        xcenter = params['xcenter']
    else:
        xcenter = None
    #
    if ('ycenter' in params.keys()):
        ycenter = params['ycenter']
    else:
        ycenter = None

    data1d = data_classes.Data1D(r=gal_r, velocity=gal_vel,vel_disp=gal_disp,
                                vel_err=err_vel, vel_disp_err=err_disp,
                                flux=gal_flux, flux_err=err_flux,
                                weight=gal_weight,
                                mask_velocity=msk_vel, mask_vel_disp=msk_disp,
                                slit_width=params['slit_width'],
                                slit_pa=params['slit_pa'], inst_corr=params['data_inst_corr'],
                                xcenter=xcenter, ycenter=ycenter)

    return data1d

def load_single_object_2D_data(params=None, adjust_error=False,
            automask=True, vmax=500., dispmax=600.,
            skip_crop=False, datadir=None):

    # +++++++++++++++++++++++++++++++++++++++++++
    # Upload the data set to be fit


    # Setup datadir, if set. If not set (so datadir=None), fdata must be the full path.
    if datadir is None:
        # If datadir not passed directly, look for entry in params file:
        if 'datadir' in params.keys():
            datadir = params['datadir']
        # If not passed directly as kwarg, and missing from params file, set to empty -- filenames must be full path.
        if datadir is None:
            datadir = ''


    gal_vel = fits.getdata(datadir+params['fdata_vel'])
    err_vel = fits.getdata(datadir+params['fdata_verr'])
    if params['fitdispersion']:
        gal_disp = fits.getdata(datadir+params['fdata_disp'])
        err_disp = fits.getdata(datadir+params['fdata_derr'])
    if params['fitflux']:
        gal_flux = fits.getdata(datadir+params['fdata_flux'])
        err_flux = fits.getdata(datadir+params['fdata_ferr'])

    mask = fits.getdata(datadir+params['fdata_mask'])


    # Mask NaNs:
    mask[~np.isfinite(gal_vel)] = 0
    gal_vel[~np.isfinite(gal_vel)] = 0.

    mask[~np.isfinite(err_vel)] = 0
    err_vel[~np.isfinite(err_vel)] = 0.

    if params['fitdispersion']:
        mask[~np.isfinite(gal_disp)] = 0
        gal_disp[~np.isfinite(gal_disp)] = 0.

        mask[~np.isfinite(err_disp)] = 0
        err_disp[~np.isfinite(err_disp)] = 0.
    if params['fitflux']:
        mask[~np.isfinite(gal_flux)] = 0
        gal_flux[~np.isfinite(gal_flux)] = 0.

        mask[~np.isfinite(err_disp)] = 0
        err_flux[~np.isfinite(err_flux)] = 0.

    # Auto mask som bad data
    if automask:
        indtmp = (gal_disp > dispmax) | (np.abs(gal_vel) > vmax)
        mask[indtmp] = 0



    if adjust_error:
        # Mask > 1sig lower error outliers:
        errv_l68 = np.percentile(err_vel, 15.865)
        indv = (err_vel < errv_l68)
        err_vel[indv] = errv_l68
        if params['fitdispersion']:
            errd_l68 = np.percentile(err_disp, 15.865)
            indd = (err_disp < errd_l68)
            err_disp[indd] = errd_l68
        if params['fitflux']:
            errf_l68 = np.percentile(err_flux, 15.865)
            indf = (err_flux < errf_l68)
            err_flux[indf] = errf_l68


    # Mask pixels with zero error for vel/disp:
    mask[(err_vel == 0)] = 0
    if params['fitdispersion']:
        mask[(err_disp == 0)] = 0
    if params['fitflux']:
        mask[(err_flux == 0)] = 0

    #####
    # Apply symmetrization if wanted:
    try:
        if params['symmetrize_data']:
            ybin, xbin = np.indices(gal_vel.shape, dtype=np.float64)
            ybin = ybin.flatten()
            xbin = xbin.flatten()
            xbin -= (gal_vel.shape[1]-1.)/2.
            ybin -= (gal_vel.shape[0]-1.)/2.
            xbin -= params['xshift']
            ybin -= params['yshift']

            bool_mask = np.array(mask.copy(), dtype=bool)
            bool_mask_flat = np.array(mask.copy(), dtype=bool).flatten()

            gal_vel_flat_in = gal_vel.flatten()
            err_vel_flat_in = err_vel.flatten()
            gal_vel_flat_in[~bool_mask_flat] = np.NaN
            err_vel_flat_in[~bool_mask_flat] = np.NaN

            gal_vel_flat, err_vel_flat = dysmalpy_utils.symmetrize_velfield(xbin, ybin,
                                gal_vel_flat_in, err_vel_flat_in,
                                sym=1, pa=params['pa'])

            gal_vel[bool_mask] = gal_vel_flat[bool_mask_flat]
            err_vel[bool_mask] = err_vel_flat[bool_mask_flat]

            if params['fitdispersion']:
                gal_disp_flat_in = gal_disp.flatten()
                err_disp_flat_in = err_disp.flatten()
                gal_disp_flat_in[~bool_mask_flat] = np.NaN
                err_disp_flat_in[~bool_mask_flat] = np.NaN
                gal_disp_flat, err_disp_flat = dysmalpy_utils.symmetrize_velfield(xbin, ybin,
                                    gal_disp_flat_in, err_disp_flat_in,
                                    sym=2, pa=params['pa'])

                gal_disp[bool_mask] = gal_disp_flat[bool_mask_flat]
                err_disp[bool_mask] = err_disp_flat[bool_mask_flat]
            if params['fitflux']:
                gal_flus_flat_in = gal_flux.flatten()
                err_flux_flat_in = err_flux.flatten()
                gal_flux_flat_in[~bool_mask_flat] = np.NaN
                err_flux_flat_in[~bool_mask_flat] = np.NaN
                gal_flux_flat, err_flux_flat = dysmalpy_utils.symmetrize_velfield(xbin, ybin,
                                    gal_flux_flat_in, err_flux_flat_in,
                                    sym=2, pa=params['pa'])

                gal_flux[bool_mask] = gal_flux_flat[bool_mask_flat]
                err_flux[bool_mask] = err_flux_flat[bool_mask_flat]

    except:
        pass

    #
    if 'weighting_method' in params.keys():
        gal_weight = setup_data_weighting_method(method=params['weighting_method'], r=None)
    else:
        gal_weight = None

    #
    if ('moment_calc' in params.keys()):
        moment_calc = params['moment_calc']
    else:
        moment_calc = False
    if ('xcenter' in params.keys()):
        xcenter = params['xcenter']
    else:
        xcenter = None
    if ('ycenter' in params.keys()):
        ycenter = params['ycenter']
    else:
        ycenter = None

    if params['fitdispersion']:
        file_disp = datadir+params['fdata_disp']
    else:
        file_disp = None
        gal_disp = None
        err_disp = None
    if params['fitflux']:
        try:
            file_flux = datadir+params['fdata_flux']
        except:
            file_flux = None
    else:
        file_flux = None
        gal_flux = None
        err_flux = None


    # Crop, if desired
    if not skip_crop:
        if 'cropbox' in params.keys():
            if params['cropbox'] is not None:
                crp = params['cropbox']
                # cropbox: l r b t
                mask = mask[crp[2]:crp[3], crp[0]:crp[1]]
                gal_vel = gal_vel[crp[2]:crp[3], crp[0]:crp[1]]
                err_vel = err_vel[crp[2]:crp[3], crp[0]:crp[1]]
                if params['fitdispersion']:
                    gal_disp = gal_disp[crp[2]:crp[3], crp[0]:crp[1]]
                    err_disp = err_disp[crp[2]:crp[3], crp[0]:crp[1]]
                if params['fitflux']:
                    gal_flux = gal_flux[crp[2]:crp[3], crp[0]:crp[1]]
                    err_flux = err_flux[crp[2]:crp[3], crp[0]:crp[1]]
                if gal_weight is not None:
                    gal_weight = gal_weight[crp[2]:crp[3], crp[0]:crp[1]]
                if xcenter is not None:
                    xcenter -= crp[0]
                    ycenter -= crp[2]
        elif params['fov_npix'] < min(gal_vel.shape):
            crp_x = np.int64(np.round((gal_vel.shape[1] - params['fov_npix'])/2.))
            crp_y = np.int64(np.round((gal_vel.shape[0] - params['fov_npix'])/2.))
            gal_vel = gal_vel[crp_y:params['fov_npix']+crp_y, crp_x:params['fov_npix']+crp_x]
            err_vel = err_vel[crp_y:params['fov_npix']+crp_y, crp_x:params['fov_npix']+crp_x]
            if params['fitdispersion']:
                gal_disp = gal_disp[crp_y:params['fov_npix']+crp_y, crp_x:params['fov_npix']+crp_x]
                err_disp = err_disp[crp_y:params['fov_npix']+crp_y, crp_x:params['fov_npix']+crp_x]
            if params['fitflux']:
                gal_flux = gal_flux[crp_y:params['fov_npix']+crp_y, crp_x:params['fov_npix']+crp_x]
                err_flux = err_flux[crp_y:params['fov_npix']+crp_y, crp_x:params['fov_npix']+crp_x]

            mask = mask[crp_y:params['fov_npix']+crp_y, crp_x:params['fov_npix']+crp_x]
            if gal_weight is not None:
                gal_weight = gal_weight[crp_y:params['fov_npix']+crp_y, crp_x:params['fov_npix']+crp_x]


    data2d = data_classes.Data2D(pixscale=params['pixscale'], velocity=gal_vel,
                                      vel_disp=gal_disp, vel_err=err_vel,
                                      vel_disp_err=err_disp,
                                      flux=gal_flux, flux_err=err_flux,
                                      mask=mask,
                                      weight=gal_weight,
                                      filename_velocity=datadir+params['fdata_vel'],
                                      filename_dispersion=file_disp,
                                      filename_flux=file_flux,
                                      smoothing_type=params['smoothing_type'],
                                      smoothing_npix=params['smoothing_npix'],
                                      inst_corr=params['data_inst_corr'],
                                      moment=moment_calc,
                                      xcenter=xcenter, ycenter=ycenter)


    return data2d

#
def load_single_object_3D_data(params=None, datadir=None):


    # +++++++++++++++++++++++++++++++++++++++++++
    # Upload the data set to be fit

    # Setup datadir, if set. If not set (so datadir=None), fdata must be the full path.
    if datadir is None:
        # If datadir not passed directly, look for entry in params file:
        if 'datadir' in params.keys():
            datadir = params['datadir']
        # If not passed directly as kwarg, and missing from params file, set to empty -- filenames must be full path.
        if datadir is None:
            datadir = ''


    cube = fits.getdata(datadir+params['fdata_cube'])
    err_cube = fits.getdata(datadir+params['fdata_err'])
    header = fits.getheader(datadir+params['fdata_cube'])

    mask = None
    if 'fdata_mask' in params.keys():
        if params['fdata_mask'] is not None:
            mask = fits.getdata(datadir+params['fdata_mask'])

    #
    mask_sky=None
    if 'fdata_mask_sky' in params.keys():
        if params['fdata_mask_sky'] is not None:
            mask_sky = fits.getdata(datadir+params['fdata_mask_sky'])
    #
    mask_spec=None
    if 'fdata_mask_spec' in params.keys():
        if params['fdata_mask_spec'] is not None:
            mask_spec = fits.getdata(datadir+params['fdata_mask_spec'])


    if 'weighting_method' in params.keys():
        gal_weight = setup_data_weighting_method(method=params['weighting_method'], r=None)
    else:
        gal_weight = None

    if ('xcenter' in params.keys()):
        xcenter = params['xcenter']
    else:
        xcenter = None
    #
    if ('ycenter' in params.keys()):
        ycenter = params['ycenter']
    else:
        ycenter = None



    ####################################
    # Convert spectrum:
    if 'spec_orig_type' in params.keys():
        spec_arr_orig = (np.arange(cube.shape[0])+1 - header['CRPIX3'])*header['CDELT3'] + header['CRVAL3']
        spec_line = params['spec_line_rest'] * (1.+params['z'])
        if params['spec_orig_type'].strip().upper() == 'WAVE':
            if params['spec_line_rest_unit'].strip().upper() == 'ANGSTROM':
                l0 = spec_line * u.angstrom
            elif (params['spec_line_rest_unit'].strip().upper() == 'MICRON') | (params['spec_line_rest_unit'].strip().upper() == 'UM'):
                l0 = spec_line * u.micrometer
            #
            if (header['CUNIT3'].strip().upper() == 'MICRON') | (header['CUNIT3'].strip().upper() == 'UM'):
                spec_arr_unit = u.micrometer
            elif (header['CUNIT3'].strip().upper() == 'ANGSTROM'):
                spec_arr_unit = u.angstrom
            elif (header['CUNIT3'].strip().upper() == 'M'):
                spec_arr_unit = u.meter
            elif (header['CUNIT3'].strip().upper() == 'CM'):
                spec_arr_unit = u.centimeter

            spec_arr_wave = spec_arr_orig * spec_arr_unit

            c_kms = apy_con.c.cgs.to(u.km/u.s)

            spec_arr_tmp = (spec_arr_wave - l0.to(spec_arr_unit))/l0.to(spec_arr_unit) * c_kms
            spec_arr = spec_arr_tmp.value
            spec_unit = u.km/u.s


        elif params['spec_orig_type'].strip().upper() == 'VELOCITY':
            spec_arr = spec_arr_orig
            spec_unit = u.km/u.s

            if header['CUNIT3'].strip().upper() == 'M/S':
                spec_arr /= 1000.


    else:
        # ASSUME IN KM/S
        spec_arr = (np.arange(cube.shape[0])+1 - header['CRPIX3'])*header['CDELT3'] + header['CRVAL3']
        spec_unit = u.km/u.s

        if header['CUNIT3'].strip().upper() == 'M/S':
            spec_arr /= 1000.
        elif header['CUNIT3'].strip().upper() == 'MICRON':
            raise ValueError('Assumed unit was km/s -- but does not match the cube header! CUNIT3={}'.format(header['CUNIT3']))




    pscale = np.abs(header['CDELT1']) * 3600.    # convert from deg CDELT1 to arcsec

    ####################################


    cube, err_cube, mask, mask_sky, mask_spec, gal_weight, spec_arr, xcenter, ycenter = _auto_truncate_crop_cube(cube,
                                            params=params,
                                            pixscale=pscale,
                                            spec_type='velocity', spec_arr=spec_arr,
                                            err_cube=err_cube, mask_cube=mask,
                                            mask_sky=mask_sky, mask_spec=mask_spec,
                                            spec_unit=spec_unit,weight=gal_weight,
                                            xcenter=xcenter, ycenter=ycenter)


    ####################################
    if (mask is None) & ('auto_gen_3D_mask' in params.keys()):
        if params['auto_gen_3D_mask']:
            if 'auto_gen_mask_snr_thresh_1' not in params.keys():
                params['auto_gen_mask_snr_thresh_1'] = params['auto_gen_mask_snr_thresh']
            if 'auto_gen_mask_sky_var_thresh' not in params.keys():
                params['auto_gen_mask_sky_var_thresh'] = 3.
            #mask = _auto_gen_3D_mask_simple(cube=cube, err=err_cube, snr_thresh=params['auto_gen_mask_snr_thresh'],
            #        npix_min=params['auto_gen_mask_npix_min'])
            mask = auto_gen_3D_mask(cube=cube, err=err_cube,
                    sig_thresh=params['auto_gen_mask_sig_thresh'],
                    #snr_thresh=params['auto_gen_mask_snr_thresh'],
                    #snr_thresh_1 = params['auto_gen_mask_snr_thresh_1'],
                    npix_min=params['auto_gen_mask_npix_min'],
                    sky_var_thresh=params['auto_gen_mask_sky_var_thresh'])

        else:
            mask = np.ones(cube.shape)

    ####################################
    # Mask NaNs:
    mask[~np.isfinite(cube)] = 0
    cube[~np.isfinite(cube)] = -99.

    mask[~np.isfinite(cube)] = 0
    err_cube[~np.isfinite(err_cube)] = -99.

    # # Clean up 0s in error, if it's masked
    # err_cube[mask == 0] = 99.

    ####################################
    if 'smoothing_type' in params.keys():
        smoothing_type=params['smoothing_type']
    else:
        smoothing_type = None
    if 'smoothing_npix' in params.keys():
        smoothing_npix=params['smoothing_npix']
    else:
        smoothing_npix = 1

    data3d = data_classes.Data3D(cube, pixscale=pscale, spec_type='velocity', spec_arr=spec_arr,
                                      err_cube=err_cube, mask_cube=mask,
                                      mask_sky=mask_sky, mask_spec=mask_spec,
                                      spec_unit=u.km/u.s,
                                      weight=gal_weight,
                                      smoothing_type=smoothing_type,
                                      smoothing_npix=smoothing_npix,
                                      xcenter=xcenter, ycenter=ycenter)

    return data3d




def ensure_path_trailing_slash(path):
    if (path[-1] != '/'):
        path += '/'
    return path

####
def get_ndim_fit_from_paramfile(param_filename=None):
    params = read_fitting_params(fname=param_filename)

    ndim_fit = None

    if 'fdata' in params.keys():
        ndim_fit = 1
    elif 'fdata_vel' in params.keys():
        ndim_fit = 2
    elif 'fdata_cube' in params.keys():
        ndim_fit = 3

    if ndim_fit is None:
        # Try a final thing:
        if 'ndim' in params.keys():
            ndim_fit = params['ndim']

    if ndim_fit is None:
        msg = "Could not determine fit dimension from data filenames!\n"
        msg += "  1D: params['fdata']\n"
        msg += "  2D: params['fdata_vel']\n"
        msg += "  1D: params['fdata_cube']\n"
        msg += "   OR SET params['ndim']"
        raise ValueError(msg)

    return ndim_fit

def stub_paramfile_dir(param_filename):
    try:
        delim = '/'
        # Strip dir from param_filename
        pf_arr = param_filename.split(delim)
        if len(pf_arr) > 1:
            param_dir = delim.join(pf_arr[:-1]) + delim
        else:
            param_dir = os.getcwd() + delim
    except:
        raise ValueError("Problem getting directory of paramfile={}".format(param_filename))

    return param_dir

def check_outdir_specified(params, outdir, param_filename=None):
    try:
        try:
            if os.path.isabs(outdir):
                stub_paramfilepath = False
            else:
                stub_paramfilepath = True
        except:
            print("Performing string splitting")
            delim = '/'
            od_arr = outdir.split(delim)
            od_arr_nonempt = []
            for od_d in od_arr:
                if len(od_d) > 0:
                    od_arr_nonempt.append(od_d)

            # If only a SINGLE relative path specified, prepend the param directory
            if len(od_arr_nonempt) == 1:
                stub_paramfilepath = True
            else:
                stub_paramfilepath = False

        if stub_paramfilepath:
            # Strip dir from param_filename
            param_dir = stub_paramfile_dir(param_filename)
            outdir = param_dir+outdir
            params['outdir'] = outdir
    except:
        raise ValueError("Directory {} not found! Couldn't get outdir.".format(outdir))

    return outdir, params

def check_datadir_specified(params, datadir, ndim=None, param_filename=None):
    if ndim is None:
        raise ValueError("Must specify 'ndim'!")
    if ndim == 1:
        fdata_orig = params['fdata']
    elif ndim == 2:
        fdata_orig = params['fdata_vel']
    elif ndim == 3:
        fdata_orig = params['fdata_cube']

    if datadir is not None:
        fdata = "{}{}".format(datadir, fdata_orig)
    else:
        # Try case of absolute path for filenames
        fdata = fdata_orig
        datadir = None

    if not os.path.isfile(fdata):
        # Try relative WRT current dir
        delim = '/'
        datadir = os.getcwd() + delim
        fdata = "{}{}".format(datadir, fdata_orig)

    if not os.path.isfile(fdata):
        # Strip dir from param_filename
        datadir = stub_paramfile_dir(param_filename)
        fdata = "{}{}".format(datadir, fdata_orig)

        if os.path.isfile(fdata):
            params['datadir'] = datadir
        else:
            try:
                datadir = tkinter_io.get_datadir_tkinter(ndim=ndim)
                params['datadir'] = datadir
            except:
                raise ValueError("Data file {} not found! Couldn't get datadir from dialog window.".format(fdata))

    return datadir, params


def preserve_param_file(param_filename, params=None, datadir=None, outdir=None):
    # Copy paramfile that is OS independent
    delim = '/'
    param_filename_nopath = param_filename.split(delim)[-1]
    galID_strp = "".join(params['galID'].strip().split("_"))
    galID_strp = "".join(galID_strp.split("-"))
    galID_strp = "".join(galID_strp.split(" "))
    paramfile_strp = "".join(param_filename_nopath.strip().split("_"))
    paramfile_strp = "".join(paramfile_strp.split("-"))
    paramfile_strp = "".join(paramfile_strp.split(" "))


    if galID_strp.strip().lower() in paramfile_strp.strip().lower():
        # Already has galID in param filename:
        fout_name = outdir+param_filename_nopath
    else:
        # Copy, prepending galID
        fout_name = outdir+"{}_{}".format(params['galID'], param_filename_nopath)


    # Check if file already exists in output directory:
    if not os.path.isfile(fout_name):
        # Replace datadir, outdir:
        with open(param_filename, 'r') as f:
            lines = f.readlines()

        for i,l in enumerate(lines):
            #if 'datadir' in l:
            ll = l.split('#')[0]
            if 'datadir' in ll:
                larr = ll.split(',')
                lines[i] = l.replace(larr[1].strip(), "{}".format(datadir))
            if 'outdir' in ll:
                larr = ll.split(',')
                lines[i] = l.replace(larr[1].strip(), "{}".format(outdir))

        with open(fout_name, 'w') as fnew:
            fnew.writelines(lines)


def ensure_dir(dir):
    """ Short function to ensure dir is a directory; if not, make the directory."""
    if not os.path.exists(dir):
        print( "Making path="+dir)
        os.makedirs(dir)
    return None
