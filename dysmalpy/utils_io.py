# coding=utf8
# Licensed under a 3-clause BSD style license - see LICENSE.rst
#
# Module containing some useful utility functions

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

# Standard library

# Third party imports
import numpy as np
from scipy import interpolate

import copy

from astropy.io import fits

import datetime

try:
    import aperture_classes
    import data_classes
except:
    from . import aperture_classes
    from . import data_classes

#
# Class for intrinsic rot curve
class RotCurveInt(object):
    def __init__(self, r=None, vcirc_tot=None, vcirc_bar=None, vcirc_dm=None):

        self.rarr = r

        data = {'vcirc_tot': vcirc_tot,
                'vcirc_bar': vcirc_bar,
                'vcirc_dm': vcirc_dm}


        self.data = data


def read_model_intrinsic_profile(filename=None):
    # Load the data set to be fit
    dat_arr =   np.loadtxt(filename) #datadir+'{}.obs_prof.txt'.format(galID))
    gal_r      = dat_arr[:,0]
    vcirc_tot  = dat_arr[:,1]
    vcirc_bar  = dat_arr[:,2]
    vcirc_dm   = dat_arr[:,3]

    model_int = RotCurveInt(r=gal_r, vcirc_tot=vcirc_tot, vcirc_bar=vcirc_bar, vcirc_dm=vcirc_dm)

    return model_int

def read_bestfit_1d_obs_file(filename=None):
    """
    Short function to save load space 1D obs profile for a galaxy (eg, for plotting, etc)
    Follows form of H.Ü. example.
    """

    # Load the model file
    dat_arr =   np.loadtxt(filename)
    gal_r =     dat_arr[:,0]
    gal_flux =  dat_arr[:,1]
    gal_vel =   dat_arr[:,2]
    gal_disp =  dat_arr[:,3]

    slit_width = None
    slit_pa = None


    #
    model_data = data_classes.Data1D(r=gal_r, velocity=gal_vel,
                             vel_disp=gal_disp, flux=gal_flux,
                             slit_width=slit_width,
                             slit_pa=slit_pa)
    model_data.apertures = None

    return model_data

def write_bestfit_obs_file(gal=None, fname=None, ndim=None, overwrite=False):
    if ndim == 1:
        write_bestfit_1d_obs_file(gal=gal, fname=fname, overwrite=overwrite)
    elif ndim == 2:
        write_bestfit_2d_obs_file(gal=gal, fname=fname, overwrite=overwrite)
    elif ndim == 3:
        write_bestfit_3d_obs_file(gal=gal, fname=fname, overwrite=overwrite)
    elif ndim == 0:
        write_bestfit_0d_obs_file(gal=gal, fname=fname, overwrite=overwrite)
    else:
        raise ValueError("ndim={} not recognized!".format(ndim))


def write_bestfit_1d_obs_file(gal=None, fname=None, overwrite=False):
    """
    Short function to save *observed* space 1D model profile for a galaxy (eg, for plotting, etc)
    Follows form of H.Ü. example.
    """
    if (not overwrite) and (fname is not None):
        if os.path.isfile(fname):
            logger.warning("overwrite={} & File already exists! Will not save file. \n {}".format(overwrite, fname))
            return None

    model_r = gal.model_data.rarr
    model_flux = gal.model_data.data['flux']
    model_vel = gal.model_data.data['velocity']
    model_disp = gal.model_data.data['dispersion']

    # Write 1D profiles to text file
    np.savetxt(fname, np.transpose([model_r, model_flux, model_vel, model_disp]),
               fmt='%2.4f\t%2.4f\t%5.4f\t%5.4f',
               header='r [arcsec], flux [...], vel [km/s], disp [km/s]')

    return None


def write_bestfit_2d_obs_file(gal=None, fname=None, overwrite=False):
    """
    Method to save the model 2D maps for a galaxy.
    """

    flux_mod = gal.model_data.data['flux']
    vel_mod =  gal.model_data.data['velocity']
    disp_mod = gal.model_data.data['dispersion']

    # Correct model for instrument dispersion if the data is instrument corrected:
    if 'inst_corr' in gal.data.data.keys():
        if gal.data.data['inst_corr']:
            disp_mod = np.sqrt(disp_mod**2 -
                               gal.instrument.lsf.dispersion.to(u.km/u.s).value**2)
            disp_mod[~np.isfinite(disp_mod)] = 0   # Set the dispersion to zero when its below
                                                   # below the instrumental dispersion

    try:
        spec_unit = gal.instrument.spec_start.unit
    except:
        spec_unit = 'km/s'  # Assume default

    hdr = fits.Header()

    hdr['NAXIS'] = (2, '2D map')
    hdr['NAXIS1'] = (flux_mod.shape[0], 'x size')
    hdr['NAXIS2'] = (flux_mod.shape[1], 'y size')

    hdr['PIXSCALE'] = gal.data.pixscale

    hdr['CUNIT1'] = ('ARCSEC', 'x unit')
    hdr['CUNIT2'] = ('ARCSEC', 'y unit')
    hdr['CDELT1'] = hdr['CDELT2'] = (hdr['PIXSCALE'], 'pixel scale')
    hdr['CRVAL1'] = (0., 'Reference position x')
    hdr['CRVAL2'] = (0., 'Reference position y')
    try:
        hdr['CRPIX1'] = (gal.data.xcenter - gal.model.geometry.xshift + 1, 'Reference pixel x')
        hdr['CRPIX2'] = (gal.data.ycenter - gal.model.geometry.yshift + 1, 'Reference pixel y')
    except:
        hdr['CRPIX1'] = ((vel_mod.shape[0]-1)/2. + 1, 'Reference pixel x')
        hdr['CRPIX2'] = ((vel_mod.shape[1]-1)/2. + 1, 'Reference pixel y')

    hdr['BUNIT'] = (spec_unit, 'Spectral unit')

    hdu_flux = fits.ImageHDU(data=flux_mod, header=hdr, name='flux')
    hdu_vel =  fits.ImageHDU(data=vel_mod,  header=hdr, name='velocity')
    hdu_disp = fits.ImageHDU(data=disp_mod, header=hdr, name='dispersion')

    hdul = fits.HDUList()
    hdul.append(hdu_flux)
    hdul.append(hdu_vel)
    hdul.append(hdu_disp)

    new_hdul.writeto(fname, overwrite=overwrite)

    return None

def write_bestfit_3d_obs_file(gal=None, fname=None, overwrite=False):

    gal.model_data.data.write(f_cube+'.scaled.fits', overwrite=overwrite)

    return None

def write_bestfit_0d_obs_file(gal=None, fname=None, overwrite=False, spec_type=None):
    if (not overwrite) and (fname is not None):
        if os.path.isfile(fname):
            logger.warning("overwrite={} & File already exists! Will not save file. \n {}".format(overwrite, fname))
            return None

    #
    if spec_type is None:
        spec_type = gal.instrument.spec_orig_type

    try:
        spec_unit = gal.instrument.spec_start.unit
    except:
        spec_unit = '??'

    x = gal.model_data.x
    mod = gal.model_data.data

    if spec_type.lower() == 'velocity':
        hdr = 'vel [{}], flux [...]'.format(spec_unit)

    elif spec_type.lower() == 'wavelength':
        hdr = 'wavelength [{}], flux [...]'.format(spec_unit)

    # Write 0D integrated spectrum to text file
    np.savetxt(fname, np.transpose([x, mod]),
               fmt='%2.4f\t%5.4f',
               header=hdr)


    return None

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

class Report(object):
    def __init__(self, report_type='short', fit_method=None):

        self.report_type = report_type
        self.fit_method = fit_method

        self._report = ''

    @property
    def report(self):
        return self._report

    def add_line(self, line):
        self._report += line + '\n'

    def add_string(self, string):
        self._report += string


    def create_results_report_short(self, gal, results, params=None):

        # --------------------------------------------
        if results.blob_name is not None:
            if isinstance(results.blob_name, str):
                blob_names = [results.blob_name]
            else:
                blob_names = results.blob_name[:]
        else:
            blob_names = None

        # --------------------------------------------

        self.add_line( '###############################' )
        self.add_line( ' Fitting for {}'.format(gal.name) )
        self.add_line( '' )

        self.add_line( "Date: {}".format(datetime.datetime.now()) )
        self.add_line( '' )


        if hasattr(gal.data, 'filename_velocity') & hasattr(gal.data, 'filename_dispersion'):
            if (gal.data.filename_velocity is not None) & (gal.data.filename_dispersion is not None):
                self.add_line( 'Datafiles:' )
                self.add_line( ' vel:  {}'.format(gal.data.filename_velocity) )
                self.add_line( ' disp: {}'.format(gal.data.filename_dispersion) )
            elif (gal.data.filename_velocity is not None):
                self.add_line( 'Datafile: {}'.format(gal.data.filename_velocity) )
        elif hasattr(gal.data, 'filename_velocity'):
            if (gal.data.filename_velocity is not None):
                self.add_line( 'Datafile: {}'.format(gal.data.filename_velocity) )
        else:
            if params is not None:
                try:
                    self.add_line( 'Datafiles:' )
                    self.add_line( ' vel:  {}'.format(params['fdata_vel']) )
                    self.add_line( ' verr: {}'.format(params['fdata_verr']) )
                    self.add_line( ' disp: {}'.format(params['fdata_disp']) )
                    self.add_line( ' derr: {}'.format(params['fdata_derr']) )
                    try:
                        self.add_line( ' mask: {}'.format(params['fdata_mask']) )
                    except:
                        pass
                except:
                    pass

        if params is not None:
            self.add_line( 'Paramfile: {}'.format(params['param_filename']) )

        self.add_line( '' )
        self.add_line( 'Fitting method: {}'.format(results.fit_method.upper()))
        self.add_line( '' )
        if params is not None:
            if 'fit_module' in params.keys():
                self.add_line( '   fit_module: {}'.format(params['fit_module']))
                #self.add_line( '' )
        #self.add_line( '' )
        # --------------------------------------
        if 'profile1d_type' in gal.data.__dict__.keys():
            self.add_line( 'profile1d_type: {}'.format(gal.data.profile1d_type) )
            #self.add_line( '' )
        if params is not None:
            if 'weighting_method' in params.keys():
                if params['weighting_method'] is not None:
                    self.add_line( 'weighting_method: {}'.format(params['weighting_method']))
                    #self.add_line( '' )
            if 'moment_calc' in params.keys():
                self.add_line( 'moment_calc: {}'.format(params['moment_calc']))
                #self.add_line( '' )
            if 'partial_weight' in params.keys():
                self.add_line( 'partial_weight: {}'.format(params['partial_weight']))
                #self.add_line( '' )
        else:
            if 'apertures' in gal.data.__dict__.keys():
                if gal.data.apertures is not None:
                    self.add_line( 'moment_calc: {}'.format(gal.data.apertures.apertures[0].moment))
                    #self.add_line( '' )
                    ####
                    self.add_line( 'partial_weight: {}'.format(gal.data.apertures.apertures[0].partial_weight))
                    #self.add_line( '' )

        # INFO on pressure support type:
        self.add_line( 'pressure_support_type: {}'.format(gal.model.kinematic_options.pressure_support_type))
        #self.add_line( '' )
        # --------------------------------------
        self.add_line( '' )
        self.add_line( '###############################' )
        self.add_line( ' Fitting results' )

        for cmp_n in gal.model.param_names.keys():
            self.add_line( '-----------' )
            self.add_line( ' {}'.format(cmp_n) )

            nfixedtied = 0
            nfree = 0

            for param_n in gal.model.param_names[cmp_n]:

                if '{}:{}'.format(cmp_n,param_n) in results.chain_param_names:
                    nfree += 1
                    whparam = np.where(results.chain_param_names == '{}:{}'.format(cmp_n, param_n))[0][0]
                    best = results.bestfit_parameters[whparam]

                    # MCMC
                    if self.fit_method.upper() == 'MCMC':
                        l68 = results.bestfit_parameters_l68_err[whparam]
                        u68 = results.bestfit_parameters_u68_err[whparam]
                        datstr = '    {: <11}    {:9.4f}  -{:9.4f} +{:9.4f}'.format(param_n, best, l68, u68)

                    # MPFIT
                    elif self.fit_method.upper() == 'MPFIT':
                        err = results.bestfit_parameters_err[whparam]
                        datstr = '    {: <11}    {:9.4f}  +/-{:9.4f}'.format(param_n, best, err)

                    self.add_line( datstr )
                else:
                    nfixedtied += 1
            #
            if (nfree > 0) & (nfixedtied > 0):
                self.add_line( '' )

            for param_n in gal.model.param_names[cmp_n]:

                if '{}:{}'.format(cmp_n,param_n) not in results.chain_param_names:
                    best = getattr(gal.model.components[cmp_n], param_n).value

                    if not getattr(gal.model.components[cmp_n], param_n).tied:
                        if getattr(gal.model.components[cmp_n], param_n).fixed:
                            fix_tie = '[FIXED]'
                        else:
                            fix_tie = '[UNKNOWN]'
                    else:
                        fix_tie = '[TIED]'

                    datstr = '    {: <11}    {:9.4f}  {}'.format(param_n, best, fix_tie)

                    self.add_line( datstr )


        ####
        if blob_names is not None:
            # MCMC
            if self.fit_method.upper() == 'MCMC':
                self.add_line( '' )
                self.add_line( '-----------' )
                for blobn in blob_names:
                    blob_best = results.__dict__['bestfit_{}'.format(blobn)]
                    l68_blob = results.__dict__['bestfit_{}_l68_err'.format(blobn)]
                    u68_blob = results.__dict__['bestfit_{}_u68_err'.format(blobn)]
                    datstr = '    {: <11}    {:9.4f}  -{:9.4f} +{:9.4f}'.format(blobn, blob_best, l68_blob, u68_blob)
                    self.add_line( datstr )


        ####
        self.add_line( '' )
        self.add_line( '-----------' )
        datstr = 'Adiabatic contraction: {}'.format(gal.model.kinematic_options.adiabatic_contract)
        self.add_line( datstr )

        self.add_line( '' )
        self.add_line( '-----------' )
        if results.bestfit_redchisq is not None:
            datstr = 'Red. chisq: {:0.4f}'.format(results.bestfit_redchisq)
        else:
            datstr = 'Red. chisq: {}'.format(results.bestfit_redchisq)
        self.add_line( datstr )

        try:
            Routmax2D = _calc_Rout_max_2D(gal=gal, results=results)
            self.add_line( '' )
            self.add_line( '-----------' )
            datstr = 'Rout,max,2D: {:0.4f}'.format(Routmax2D)
            self.add_line( datstr )
        except:
            pass

        self.add_line( '' )



    def create_results_report_long(self, gal, results, params=None):

        # --------------------------------------------
        if results.blob_name is not None:
            if isinstance(results.blob_name, str):
                blob_names = [results.blob_name]
            else:
                blob_names = results.blob_name[:]
        else:
            blob_names = None

        # --------------------------------------------

        namestr = '# component    param_name    fixed    best_value   l68_err   u68_err'
        self.add_line( namestr )

        for cmp_n in gal.model.param_names.keys():
            for param_n in gal.model.param_names[cmp_n]:

                if '{}:{}'.format(cmp_n,param_n) in results.chain_param_names:
                    whparam = np.where(results.chain_param_names == '{}:{}'.format(cmp_n, param_n))[0][0]
                    best = results.bestfit_parameters[whparam]
                    l68 = results.bestfit_parameters_l68_err[whparam]
                    u68 = results.bestfit_parameters_u68_err[whparam]
                else:
                    best = getattr(gal.model.components[cmp_n], param_n).value
                    l68 = -99.
                    u68 = -99.

                datstr = '{: <12}   {: <11}   {: <5}   {:9.4f}   {:9.4f}   {:9.4f}'.format(cmp_n, param_n,
                            "{}".format(gal.model.fixed[cmp_n][param_n]), best, l68, u68)
                self.add_line( datstr )

        ###

        if 'blob_name' in params.keys():
            for blobn in blob_names:
                blob_best = results.__dict__['bestfit_{}'.format(blobn)]
                l68_blob = results.__dict__['bestfit_{}_l68_err'.format(blobn)]
                u68_blob = results.__dict__['bestfit_{}_u68_err'.format(blobn)]
                datstr = '{: <12}   {: <11}   {: <5}   {:9.4f}   {:9.4f}   {:9.4f}'.format(blobn, '-----',
                            '-----', blob_best, l68_blob, u68_blob)
                self.add_line( datstr )


        ###
        datstr = '{: <12}   {: <11}   {: <5}   {}   {:9.4f}   {:9.4f}'.format('adiab_contr', '-----',
                    '-----', gal.model.kinematic_options.adiabatic_contract, -99, -99)
        self.add_line( datstr )

        if results.bestfit_redchisq is not None:
            datstr = '{: <12}   {: <11}   {: <5}   {:9.4f}   {:9.4f}   {:9.4f}'.format('redchisq', '-----',
                    '-----', results.bestfit_redchisq, -99, -99)
        else:
            datstr = '{: <12}   {: <11}   {: <5}   {}   {:9.4f}   {:9.4f}'.format('redchisq', '-----',
                    '-----', results.bestfit_redchisq, -99, -99)
        self.add_line( datstr )


        if 'profile1d_type' in gal.data.__dict__.keys():
            datstr = '{: <12}   {: <11}   {: <5}   {: <20}   {:9.4f}   {:9.4f}'.format('profile1d_type', '-----',
                        '-----', gal.data.profile1d_type, -99, -99)
            self.add_line( datstr )

        #
        if params is not None:
            if 'weighting_method' in params.keys():
                if params['weighting_method'] is not None:
                    datstr = '{: <12}   {: <11}   {: <5}   {: <20}   {:9.4f}   {:9.4f}'.format('weighting_method', '-----',
                                '-----', params['weighting_method'], -99, -99)
                    self.add_line( datstr )
            if 'moment_calc' in params.keys():
                datstr = '{: <12}   {: <11}   {: <5}   {: <20}   {:9.4f}   {:9.4f}'.format('moment_calc', '-----',
                            '-----', params['moment_calc'], -99, -99)
                self.add_line( datstr )
            if 'partial_weight' in params.keys():
                datstr = '{: <12}   {: <11}   {: <5}   {: <20}   {:9.4f}   {:9.4f}'.format('partial_weight', '-----',
                            '-----', params['partial_weight'], -99, -99)
                self.add_line( datstr )
        #
        else:
            if 'apertures' in gal.data.__dict__.keys():
                if gal.data.apertures is not None:
                    datstr = '{: <12}   {: <11}   {: <5}   {: <20}   {:9.4f}   {:9.4f}'.format('moment_calc', '-----',
                                '-----', gal.data.apertures.apertures[0].moment, -99, -99)
                    self.add_line( datstr )
                    ####
                    datstr = '{: <12}   {: <11}   {: <5}   {: <20}   {:9.4f}   {:9.4f}'.format('partial_weight', '-----',
                                '-----', gal.data.apertures.apertures[0].partial_weight, -99, -99)
                    self.add_line( datstr )


        #
        # INFO on pressure support type:
        datstr = '{: <12}   {: <11}   {: <5}   {: <20}   {:9.4f}   {:9.4f}'.format('pressure_support_type', '-----',
                    '-----', gal.model.kinematic_options.pressure_support_type, -99, -99)
        self.add_line( datstr )






def create_results_report(gal, results, params=None, report_type='short'):

    if results.fit_method is None:
        return None

    report = Report(report_type=report_type, fit_method=results.fit_method)

    if report_type == 'short':
        report.create_results_report_short(gal, results, params=params)
    elif report_type == 'long':
        report.create_results_report_long(gal, results, params=params)


    return report.report




#########################

def _calc_Rout_max_2D(gal=None, results=None):
    gal.model.update_parameters(results.bestfit_parameters)
    inc_gal = gal.model.geometry.inc.value



    ###############
    # Get grid of data coords:
    nx_sky = gal.data.data['velocity'].shape[1]
    ny_sky = gal.data.data['velocity'].shape[0]
    nz_sky = 1 #np.int(np.max([nx_sky, ny_sky]))
    rstep = gal.data.pixscale


    xcenter = gal.data.xcenter
    ycenter = gal.data.ycenter


    if xcenter is None:
        xcenter = (nx_sky - 1) / 2.
    if ycenter is None:
        ycenter = (ny_sky - 1) / 2.


    #
    sh = (nz_sky, ny_sky, nx_sky)
    zsky, ysky, xsky = np.indices(sh)
    zsky = zsky - (nz_sky - 1) / 2.
    ysky = ysky - ycenter
    xsky = xsky - xcenter

    # Apply the geometric transformation to get galactic coordinates
    xgal, ygal, zgal = gal.model.geometry(xsky, ysky, zsky)

    # Get the 4 corners sets:
    gal.model.geometry.inc = 0
    xskyp_ur, yskyp_ur, zskyp_ur = gal.model.geometry(xsky+0.5, ysky+0.5, zsky)
    xskyp_ll, yskyp_ll, zskyp_ll = gal.model.geometry(xsky-0.5, ysky-0.5, zsky)
    xskyp_lr, yskyp_lr, zskyp_lr = gal.model.geometry(xsky+0.5, ysky-0.5, zsky)
    xskyp_ul, yskyp_ul, zskyp_ul = gal.model.geometry(xsky-0.5, ysky+0.5, zsky)

    #Reset:
    gal.model.geometry.inc = inc_gal


    yskyp_ur_flat = yskyp_ur[0,:,:]
    yskyp_ll_flat = yskyp_ll[0,:,:]
    yskyp_lr_flat = yskyp_lr[0,:,:]
    yskyp_ul_flat = yskyp_ul[0,:,:]

    val_sgns = np.zeros(yskyp_ur_flat.shape)
    val_sgns += np.sign(yskyp_ur_flat)
    val_sgns += np.sign(yskyp_ll_flat)
    val_sgns += np.sign(yskyp_lr_flat)
    val_sgns += np.sign(yskyp_ul_flat)

    whgood = np.where( ( np.abs(val_sgns) < 4. ) & (gal.data.mask) )

    xgal_flat = xgal[0,:,:]
    ygal_flat = ygal[0,:,:]
    xgal_list = xgal_flat[whgood]
    ygal_list = ygal_flat[whgood]


    # The circular velocity at each position only depends on the radius
    # Convert to kpc
    rgal = np.sqrt(xgal_list ** 2 + ygal_list ** 2) * rstep / gal.dscale

    Routmax2D = np.max(rgal.flatten())


    return Routmax2D


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def create_vel_profile_files(gal=None, outpath=None, oversample=3, oversize=1,
            profile1d_type=None, aperture_radius=None,
            moment=False,
            partial_weight=False,
            fname_model_matchdata=None,
            fname_finer=None,
            fname_intrinsic=None,
            fname_intrinsic_m = None):
    #
    if outpath is None:
        raise ValueError

    if fname_model_matchdata is None:
        #fname_model_matchdata = outpath + '{}_out-1dplots_{}.txt'.format(gal.name, monthday)
        fname_model_matchdata = "{}{}_out-1dplots.txt".format(outpath, gal.name)
    if fname_finer is None:
        #fname_finer = outpath + '{}_out-1dplots_{}_finer_sampling.txt'.format(gal.name, monthday)
        fname_finer = "{}{}_out-1dplots_finer_sampling.txt".format(outpath, gal.name)

    if fname_intrinsic is None:
        fname_intrinsic = '{}{}_vcirc_tot_bary_dm.dat'.format(outpath, gal.name)
    if fname_intrinsic_m is None:
        fname_intrinsic_m = '{}{}_menc_tot_bary_dm.dat'.format(outpath, gal.name)

    ###
    galin = copy.deepcopy(gal)

    # ---------------------------------------------------------------------------
    gal.create_model_data(oversample=oversample, oversize=oversize,
                          line_center=gal.model.line_center,
                          profile1d_type=profile1d_type)

    # -------------------
    # Save Bary/DM vcirc:
    write_vcirc_tot_bar_dm(gal=gal, fname=fname_intrinsic, fname_m=fname_intrinsic_m)

    # --------------------------------------------------------------------------
    write_bestfit_1d_obs_file(gal=gal, fname=fname_model_matchdata)


    # Reload galaxy object: reset things
    gal = copy.deepcopy(galin)

    # Try finer scale:

    write_1d_obs_finer_scale(gal=gal, fname=fname_finer, oversample=oversample, oversize=oversize,
                profile1d_type=profile1d_type, aperture_radius=aperture_radius, moment=moment,
                partial_weight=partial_weight)


    return None

#
def write_1d_obs_finer_scale(gal=None, fname=None,
            profile1d_type=None, aperture_radius=None,
            oversample=3, oversize=1,
            partial_weight=False,
            moment=False):
    # Try finer scale:
    rmax_abs = np.max([2.5, np.max(np.abs(gal.model_data.rarr))])
    r_step = 0.025 #0.05
    if rmax_abs > 4.:
        r_step = 0.05
    aper_centers_interp = np.arange(0, rmax_abs+r_step, r_step)

    if profile1d_type == 'rect_ap_cube':
        f_par = interpolate.interp1d(gal.data.rarr, gal.data.apertures.pix_parallel,
                        kind='slinear', fill_value='extrapolate')
        f_perp = interpolate.interp1d(gal.data.rarr, gal.data.apertures.pix_perp,
                        kind='slinear', fill_value='extrapolate')

        pix_parallel_interp = f_par(aper_centers_interp)
        pix_perp_interp = f_perp(aper_centers_interp)

        gal.data.apertures = aperture_classes.setup_aperture_types(gal=gal,
                    profile1d_type=profile1d_type,
                    aperture_radius=1.,
                    slit_width=gal.data.slit_width,
                    aper_centers = aper_centers_interp,
                    slit_pa = gal.data.slit_pa,
                    partial_weight=partial_weight,
                    pix_perp=pix_perp_interp, pix_parallel=pix_parallel_interp,
                    pix_length=None, from_data=False,
                    moment=moment)
    elif profile1d_type == 'circ_ap_cube':
        gal.data.apertures = aperture_classes.setup_aperture_types(gal=gal,
                    profile1d_type=profile1d_type,
                    aperture_radius=aperture_radius,
                    slit_width=gal.data.slit_width,
                    aper_centers = aper_centers_interp,
                    slit_pa = gal.data.slit_pa,
                    partial_weight=partial_weight,
                    pix_perp=None, pix_parallel=None,
                    pix_length=None, from_data=False,
                    moment=moment)

    if (profile1d_type == 'circ_ap_cube') | ( profile1d_type == 'rect_ap_cube'):
        gal.create_model_data(oversample=oversample, oversize=oversize,
                              line_center=gal.model.line_center,
                              profile1d_type=profile1d_type)
    else:
        gal.instrument.slit_width = gal.data.slit_width
        gal.create_model_data(from_data=False, from_instrument=True,
                              ndim_final=1,
                              aper_centers=aper_centers_interp,
                              slit_width=gal.data.slit_width, slit_pa=gal.data.slit_pa,
                              profile1d_type=profile1d_type,
                              oversample=oversample, oversize=oversize,
                              aperture_radius=aperture_radius)


    write_bestfit_1d_obs_file(gal=gal, fname=fname)

    return None

def write_vcirc_tot_bar_dm(gal=None, fname=None, fname_m=None):
    # -------------------
    # Save Bary/DM vcirc:

    rstep = 0.1
    rmax = 40.   #17.2   # kpc
    rarr = np.arange(0, rmax+rstep, rstep)

    vcirc_bar = gal.model.components['disk+bulge'].circular_velocity(rarr)
    vcirc_dm  = gal.model.components['halo'].circular_velocity(rarr)
    vcirc_tot = gal.model.circular_velocity(rarr)

    menc_tot, menc_bar, menc_dm = gal.model.enclosed_mass(rarr)

    vcirc_bar[~np.isfinite(vcirc_bar)] = 0.
    vcirc_dm[~np.isfinite(vcirc_dm)] = 0.

    vcirc_tot[~np.isfinite(vcirc_tot)] = 0.

    profiles = np.zeros((len(rarr), 4))
    profiles[:,0] = rarr
    profiles[:,1] = vcirc_tot
    profiles[:,2] = vcirc_bar
    profiles[:,3] = vcirc_dm

    profiles_m = np.zeros((len(rarr), 4))
    profiles_m[:,0] = rarr
    profiles_m[:,1] = np.log10(menc_tot)
    profiles_m[:,2] = np.log10(menc_bar)
    profiles_m[:,3] = np.log10(menc_dm)
    profiles_m[~np.isfinite(profiles_m)] = 0.

    save_vcirc_tot_bar_dm_files(gal=gal, fname=fname, fname_m=fname_m,
                    profiles=profiles, profiles_m=profiles_m)

    return None


#
def save_vcirc_tot_bar_dm_files(gal=None, fname=None, fname_m=None, profiles=None, profiles_m=None):
    with open(fname, 'w') as f:
        namestr = '#   r   vcirc_tot vcirc_bar   vcirc_dm'
        f.write(namestr+'\n')
        unitstr = '#   [kpc]   [km/s]   [km/s]   [km/s]'
        f.write(unitstr+'\n')
        for i in range(profiles.shape[0]):
            datstr = '    '.join(["{0:0.3f}".format(p) for p in profiles[i,:]])
            f.write(datstr+'\n')

    with open(fname_m, 'w') as f:
        namestr = '#   r   lmenc_tot   lmenc_bar   lmenc_dm'
        f.write(namestr+'\n')
        unitstr = '#   [kpc]   [log10Msun]   [log10Msun]   [log10Msun]'
        f.write(unitstr+'\n')
        for i in range(profiles.shape[0]):
            datstr = '    '.join(["{0:0.3f}".format(p) for p in profiles_m[i,:]])
            f.write(datstr+'\n')

    return None
