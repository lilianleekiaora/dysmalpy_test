# coding=utf8
# Licensed under a 3-clause BSD style license - see LICENSE.rst
#
# Testing of DYSMALPY model (component) calculations

import os
import shutil

import math

import numpy as np
import astropy.io.fits as fits
import astropy.units as u

from dysmalpy.fitting_wrappers import dysmalpy_make_model
from dysmalpy.fitting_wrappers import utils_io as fw_utils_io

from dysmalpy import galaxy, models, parameters, instrument, config


# TESTING DIRECTORY
path = os.path.abspath(__file__)
_dir_tests = os.path.dirname(path) + '/'
_dir_tests_data = _dir_tests+'test_data/'



class HelperSetups(object):

    def __init__(self):
        self.z = 1.613
        self.name = 'GS4_43501'

    def setup_diskbulge(self):
        # Baryonic Component: Combined Disk+Bulge
        total_mass =    11.0    # M_sun
        bt =            0.3     # Bulge-Total ratio
        r_eff_disk =    5.0     # kpc
        n_disk =        1.0
        invq_disk =     5.0
        r_eff_bulge =   1.0     # kpc
        n_bulge =       4.0
        invq_bulge =    1.0
        noord_flat =    True    # Switch for applying Noordermeer flattening

        # Fix components
        bary_fixed = {'total_mass': False,
                      'r_eff_disk': False,
                      'n_disk': True,
                      'r_eff_bulge': True,
                      'n_bulge': True,
                      'bt': False}

        # Set bounds
        bary_bounds = {'total_mass': (10, 13),
                       'r_eff_disk': (1.0, 30.0),
                       'n_disk': (1, 8),
                       'r_eff_bulge': (1, 5),
                       'n_bulge': (1, 8),
                       'bt': (0, 1)}

        bary = models.DiskBulge(total_mass=total_mass, bt=bt,
                                r_eff_disk=r_eff_disk, n_disk=n_disk,
                                invq_disk=invq_disk,
                                r_eff_bulge=r_eff_bulge, n_bulge=n_bulge,
                                invq_bulge=invq_bulge,
                                noord_flat=noord_flat,
                                name='disk+bulge',
                                fixed=bary_fixed, bounds=bary_bounds)

        bary.r_eff_disk.prior = parameters.BoundedGaussianPrior(center=5.0, stddev=1.0)

        return bary

    def setup_sersic(self, noord_flat=False):
        # Baryonic Component: Combined Disk+Bulge
        total_mass =    11.0    # M_sun
        r_eff =         5.0     # kpc
        n =             1.0
        invq =          5.0

        # Fix components
        sersic_fixed = {'total_mass': False,
                      'r_eff': False,
                      'n': True}

        # Set bounds
        sersic_bounds = {'total_mass': (10, 13),
                       'r_eff': (1.0, 30.0),
                       'n': (1, 8)}

        sersic = models.Sersic(total_mass=total_mass,r_eff=r_eff, n=n,invq=invq,
                                noord_flat=noord_flat,name='sersic',
                                fixed=sersic_fixed, bounds=sersic_bounds)

        sersic.r_eff.prior = parameters.BoundedGaussianPrior(center=5.0, stddev=1.0)

        return sersic

    def setup_NFW(self):
        # NFW Halo component
        mvirial = 12.0
        conc = 5.0
        fdm = 0.5
        halo_fixed = {'mvirial': False,
                      'conc': True,
                      'fdm': False}

        halo_bounds = {'mvirial': (10, 13),
                       'conc': (1, 20),
                       'fdm': (0., 1.)}

        halo = models.NFW(mvirial=mvirial, conc=conc, fdm=fdm,z=self.z,
                          fixed=halo_fixed, bounds=halo_bounds, name='halo')

        halo.fdm.tied = fw_utils_io.tie_fdm
        halo.mvirial.prior = parameters.BoundedGaussianPrior(center=11.5, stddev=0.5)

        return halo

    def setup_TPH(self):
        # TPH Halo component
        mvirial = 12.0
        conc = 5.0
        alpha = 0.
        beta = 3.
        fdm = 0.5

        halo_fixed = {'mvirial': False,
                      'conc': True,
                      'alpha': False,
                      'beta': True,
                      'fdm': False}

        halo_bounds = {'mvirial': (10, 13),
                       'conc': (1, 20),
                       'alpha': (0, 3),
                       'beta': (1,4),
                       'fdm': (0., 1.)}

        halo = models.TwoPowerHalo(mvirial=mvirial, conc=conc,
                            alpha=alpha, beta=beta, fdm=fdm, z=self.z,
                            fixed=halo_fixed, bounds=halo_bounds, name='halo')

        halo.fdm.tied = fw_utils_io.tie_fdm
        halo.fdm.fixed = False

        return halo

    def setup_const_dispprof(self):
        # Dispersion profile
        sigma0 = 39.   # km/s
        disp_fixed = {'sigma0': False}
        disp_bounds = {'sigma0': (10, 200)}

        disp_prof = models.DispersionConst(sigma0=sigma0, fixed=disp_fixed,
                                                  bounds=disp_bounds, name='dispprof')

        return disp_prof

    def setup_zheight_prof(self):
        # z-height profile
        sigmaz = 0.9   # kpc
        zheight_fixed = {'sigmaz': False}

        zheight_prof = models.ZHeightGauss(sigmaz=sigmaz, name='zheightgaus', fixed=zheight_fixed)
        zheight_prof.sigmaz.tied = fw_utils_io.tie_sigz_reff

        return zheight_prof

    def setup_geom(self):
        # Geometry
        inc = 62.     # degrees
        pa = 142.     # degrees, blue-shifted side CCW from north
        xshift = 0    # pixels from center
        yshift = 0    # pixels from center

        geom_fixed = {'inc': False,
                      'pa': True,
                      'xshift': True,
                      'yshift': True}

        geom_bounds = {'inc': (0, 90),
                       'pa': (90, 180),
                       'xshift': (0, 4),
                       'yshift': (-10, -4)}

        geom = models.Geometry(inc=inc, pa=pa, xshift=xshift, yshift=yshift,
                               fixed=geom_fixed, bounds=geom_bounds, name='geom')

        return geom

    def setup_biconical_outflow(self):
        bicone = models.BiconicalOutflow(n=0.5, vmax=300., rturn=0.5, thetain=30, dtheta=20.,
                                         rend=1., norm_flux=0., tau_flux=5., name='bicone')
        bicone_geom = models.Geometry(inc=10., pa=30., xshift=0., yshift=0., name='outflow_geom')
        bicone_disp = models.DispersionConst(sigma0=250., name='outflow_dispprof')
        return bicone, bicone_geom, bicone_disp

    def setup_uniform_inflow(self):
        # Negative vr is inflow
        inflow = models.UniformRadialFlow(vr=-90,  name='inflow')
        return inflow

    def setup_fullmodel(self, adiabatic_contract=False,
                pressure_support=True, pressure_support_type=1):
        # Initialize the Galaxy, Instrument, and Model Set
        gal = galaxy.Galaxy(z=self.z, name=self.name)
        mod_set = models.ModelSet()

        bary = self.setup_diskbulge()
        halo = self.setup_NFW()
        disp_prof = self.setup_const_dispprof()
        zheight_prof = self.setup_zheight_prof()
        geom = self.setup_geom()

        # Add all of the model components to the ModelSet
        mod_set.add_component(bary, light=True)
        mod_set.add_component(halo)
        mod_set.add_component(disp_prof)
        mod_set.add_component(zheight_prof)
        mod_set.add_component(geom)

        ## Set some kinematic options for calculating the velocity profile
        # pressure_support_type: 1 / Exponential, self-grav [Burkert+10]
        #                        2 / Exact nSersic, self-grav
        #                        3 / Pressure gradient
        mod_set.kinematic_options.adiabatic_contract = adiabatic_contract
        mod_set.kinematic_options.pressure_support = pressure_support
        mod_set.kinematic_options.pressure_support_type = pressure_support_type

        # Add the model set and instrument to the Galaxy
        gal.model = mod_set

        return gal

    def setup_fullmodel_biconical(self, adiabatic_contract=False,
                pressure_support=True, pressure_support_type=1):
        # Initialize the Galaxy, Instrument, and Model Set
        gal = galaxy.Galaxy(z=self.z, name=self.name)
        mod_set = models.ModelSet()

        bary = self.setup_diskbulge()
        halo = self.setup_NFW()
        disp_prof = self.setup_const_dispprof()
        zheight_prof = self.setup_zheight_prof()
        geom = self.setup_geom()
        bicone, bicone_geom, bicone_disp = self.setup_biconical_outflow()
        inst = self.setup_instrument()

        # Add all of the model components to the ModelSet
        mod_set.add_component(bary, light=True)
        mod_set.add_component(halo)
        mod_set.add_component(disp_prof)
        mod_set.add_component(zheight_prof)
        mod_set.add_component(geom)
        mod_set.add_component(bicone)
        mod_set.add_component(bicone_geom, geom_type=bicone.name)
        mod_set.add_component(bicone_disp, disp_type=bicone.name)

        ## Set some kinematic options for calculating the velocity profile
        # pressure_support_type: 1 / Exponential, self-grav [Burkert+10]
        #                        2 / Exact nSersic, self-grav
        #                        3 / Pressure gradient
        mod_set.kinematic_options.adiabatic_contract = adiabatic_contract
        mod_set.kinematic_options.pressure_support = pressure_support
        mod_set.kinematic_options.pressure_support_type = pressure_support_type

        # Add the model set and instrument to the Galaxy
        gal.model = mod_set
        gal.instrument = inst

        return gal


    def setup_fullmodel_uniform_inflow(self, adiabatic_contract=False,
                pressure_support=True, pressure_support_type=1):
        # Initialize the Galaxy, Instrument, and Model Set
        gal = galaxy.Galaxy(z=self.z, name=self.name)
        mod_set = models.ModelSet()

        bary = self.setup_diskbulge()
        halo = self.setup_NFW()
        disp_prof = self.setup_const_dispprof()
        zheight_prof = self.setup_zheight_prof()
        geom = self.setup_geom()
        inflow = self.setup_uniform_inflow()
        inst = self.setup_instrument()

        # Add all of the model components to the ModelSet
        mod_set.add_component(bary, light=True)
        mod_set.add_component(halo)
        mod_set.add_component(disp_prof)
        mod_set.add_component(zheight_prof)
        mod_set.add_component(geom)
        mod_set.add_component(inflow)

        ## Set some kinematic options for calculating the velocity profile
        # pressure_support_type: 1 / Exponential, self-grav [Burkert+10]
        #                        2 / Exact nSersic, self-grav
        #                        3 / Pressure gradient
        mod_set.kinematic_options.adiabatic_contract = adiabatic_contract
        mod_set.kinematic_options.pressure_support = pressure_support
        mod_set.kinematic_options.pressure_support_type = pressure_support_type

        # Add the model set and instrument to the Galaxy
        gal.model = mod_set
        gal.instrument = inst


        return gal


    def setup_instrument(self):
        inst = instrument.Instrument()

        # Set up the instrument
        pixscale = 0.125*u.arcsec                # arcsec/pixel
        fov = [33, 33]                           # (nx, ny) pixels
        beamsize = 0.55*u.arcsec                 # FWHM of beam
        spec_type = 'velocity'                   # 'velocity' or 'wavelength'
        spec_start = -1000*u.km/u.s              # Starting value of spectrum
        spec_step = 10*u.km/u.s                  # Spectral step
        nspec = 201                              # Number of spectral pixels
        sig_inst = 45*u.km/u.s                   # Instrumental spectral resolution

        beam = instrument.GaussianBeam(major=beamsize)
        lsf = instrument.LSF(sig_inst)

        inst.beam = beam
        inst.lsf = lsf
        inst.pixscale = pixscale
        inst.fov = fov
        inst.spec_type = spec_type
        inst.spec_step = spec_step
        inst.spec_start = spec_start
        inst.nspec = nspec

        # Set the beam kernel so it doesn't have to be calculated every step
        inst.set_beam_kernel()
        inst.set_lsf_kernel()

        return inst



class TestModels:
    helper = HelperSetups()

    def test_diskbulge(self):
        bary = self.helper.setup_diskbulge()

        ftol = 1.e-9
        rarr = np.array([0.,2.5,5.,7.5,10.])   # kpc
        vcirc = np.array([0., 233.84762112, 231.63051349, 222.14143224, 207.24934609]) #km/s
        menc = np.array([0., 3.17866553e+10, 6.23735490e+10, 8.60516713e+10, 9.98677462e+10]) # Msun

        for i, r in enumerate(rarr):
            # Assert vcirc, menc values are the same
            assert math.isclose(bary.circular_velocity(r), vcirc[i], rel_tol=ftol)
            assert math.isclose(bary.enclosed_mass(r), menc[i], rel_tol=ftol)

        if models._sersic_profile_mass_VC_loaded:
            dlnrho_dlnr = np.array([ 0., -1.4710141147249862, -2.178978908144452,
                        -3.0000815229630002, -3.8338659358932334])
            rho = np.array([3.970102840765826e+17, 399133357.6711784, 117795156.79188688,
                            41725350.996718735, 15703871.592708467]) # msun/kpc^3 ??
            for i, r in enumerate(rarr):
                # Assert density, dlnrho_dlnr values are the same
                assert math.isclose(bary.rho(r), rho[i], rel_tol=ftol)
                assert math.isclose(bary.dlnrho_dlnr(r), dlnrho_dlnr[i], rel_tol=ftol)



    def test_sersic(self):
        sersic = self.helper.setup_sersic(noord_flat=False)

        ftol = 1.e-9
        rarr = np.array([0.,2.5,5.,7.5,10.])   # kpc
        vcirc = np.array([0.0, 187.95808079510437, 207.38652969925448,
                            202.6707348023267, 190.9947720259013]) #km/s
        menc = np.array([0.0, 20535293937.195515, 50000000000.0,
                            71627906617.42969, 84816797558.70425]) # Msun

        for i, r in enumerate(rarr):
            # Assert vcirc, menc values are the same
            assert math.isclose(sersic.circular_velocity(r), vcirc[i], rel_tol=ftol)
            assert math.isclose(sersic.enclosed_mass(r), menc[i], rel_tol=ftol)

        if models._sersic_profile_mass_VC_loaded:
            dlnrho_dlnr = np.array([0.0, -1.6783469900166612, -3.3566939800333224,
                            -5.035040970049984, -6.713387960066645])
            rho = np.array([1793261526.5567722, 774809992.0335385, 334770202.1509947,
                            144643318.23351952, 62495674.272009104]) # msun/kpc^3 ??
            for i, r in enumerate(rarr):
                # Assert density, dlnrho_dlnr values are the same
                assert math.isclose(sersic.rho(r), rho[i], rel_tol=ftol)
                assert math.isclose(sersic.dlnrho_dlnr(r), dlnrho_dlnr[i], rel_tol=ftol)

    def test_sersic_noord_flat(self):
        sersic = self.helper.setup_sersic(noord_flat=True)

        ftol = 1.e-9
        rarr = np.array([0.,2.5,5.,7.5,10.])   # kpc
        vcirc = np.array([0.0, 168.75231977473914, 213.96601851622563,
                            219.70437621918154, 209.92527768889798]) #km/s
        menc = np.array([0.0, 16553065102.83822, 53222898982.82668,
                            84173927151.13939, 102463310604.53976]) # Msun

        for i, r in enumerate(rarr):
            # Assert vcirc, menc values are the same
            assert math.isclose(sersic.circular_velocity(r), vcirc[i], rel_tol=ftol)
            assert math.isclose(sersic.enclosed_mass(r), menc[i], rel_tol=ftol)

        if models._sersic_profile_mass_VC_loaded:
            dlnrho_dlnr = np.array([0.0, -1.2608824256730886, -2.128495149023024,
                                -2.980578859391685, -3.8272560398656132])
            rho = np.array([35133994466.11231, 510439919.6032341, 162957719.18618384,
                                58502355.720370084, 22099112.430362392]) # msun/kpc^3 ??
            for i, r in enumerate(rarr):
                # Assert density, dlnrho_dlnr values are the same
                assert math.isclose(sersic.rho(r), rho[i], rel_tol=ftol)
                assert math.isclose(sersic.dlnrho_dlnr(r), dlnrho_dlnr[i], rel_tol=ftol)

    def test_NFW(self):
        halo = self.helper.setup_NFW()

        ftol = 1.e-9
        # Assert Rvir is the same
        assert math.isclose(halo.calc_rvir(), 113.19184480200144, rel_tol=ftol)

        rarr = np.array([0.,2.5,5.,7.5,10.,50.])   # kpc
        vcirc = np.array([0.0, 97.53274745638375, 129.37952931721014,
                        149.39249515561673, 163.34037609257453, 207.0167394246318]) #km/s
        menc = np.array([0.0, 5529423277.0931425, 19459875132.71848,
                        38918647245.552315, 62033461205.42702, 498218492834.53705]) # Msun

        for i, r in enumerate(rarr):
            # Assert vcirc, menc values are the same
            assert math.isclose(halo.circular_velocity(r), vcirc[i], rel_tol=ftol)
            assert math.isclose(halo.enclosed_mass(r), menc[i], rel_tol=ftol)


    def test_TPH(self):
        halo = self.helper.setup_TPH()

        ftol = 1.e-9
        # Assert Rvir is the same
        assert math.isclose(halo.calc_rvir(), 113.19184480200144, rel_tol=ftol)

        rarr = np.array([0.,2.5,5.,7.5,10.,50.])   # kpc
        vcirc = np.array([0.0, 31.585366510730005, 56.73315065922273,
                            77.10747504831834, 93.85345758098778, 184.0132403616831]) #km/s
        menc = np.array([0.0, 579896865.582416, 3741818525.6905646,
                        10367955836.483051, 20480448580.59536, 393647104816.9644]) # Msun

        for i, r in enumerate(rarr):
            # Assert vcirc, menc values are the same
            assert math.isclose(halo.circular_velocity(r), vcirc[i], rel_tol=ftol)
            assert math.isclose(halo.enclosed_mass(r), menc[i], rel_tol=ftol)

    def test_asymm_drift_selfgrav(self):
        gal = self.helper.setup_fullmodel(pressure_support_type=1)

        ftol = 1.e-9
        rarr = np.array([0.,2.5,5.,7.5,10.])   # kpc
        vrot = np.array([0.0, 248.27820429923966, 255.50185397469704,
                        252.9804212303498, 243.74423052912974]) #km/s

        for i, r in enumerate(rarr):
            # Assert vrot values are the same
            assert math.isclose(gal.model.velocity_profile(r), vrot[i], rel_tol=ftol)

    def test_asymm_drift_exactsersic(self):
        gal = self.helper.setup_fullmodel(pressure_support_type=2)
        gal.model.set_parameter_value('disk+bulge', 'n_disk', 0.5)

        ftol = 1.e-9
        rarr = np.array([0.,2.5,5.,7.5,10.])   # kpc
        vrot = np.array([0.0, 232.03861252444398, 253.47823945210072,
                        261.186198203435, 242.75798891697548]) #km/s

        for i, r in enumerate(rarr):
            # Assert vrot values are the same
            assert math.isclose(gal.model.velocity_profile(r), vrot[i], rel_tol=ftol)

    def test_asymm_drift_pressuregradient(self):
        if models._sersic_profile_mass_VC_loaded:
            gal = self.helper.setup_fullmodel(pressure_support_type=3)

            ftol = 1.e-9
            rarr = np.array([0.,2.5,5.,7.5,10.])   # kpc
            vrot = np.array([0.0, 248.91752501894734, 258.9933019697994,
                            259.0401697217219, 252.5887167466986]) #km/s

            for i, r in enumerate(rarr):
                # Assert vrot values are the same
                assert math.isclose(gal.model.velocity_profile(r), vrot[i], rel_tol=ftol)
        else:
            pass

    def test_composite_model(self):
        gal_noAC = self.helper.setup_fullmodel(adiabatic_contract=False)

        ftol = 1.e-9
        rarr = np.array([0.,2.5,5.,7.5,10.,50.])   # kpc
        vcirc_noAC = np.array([0.0, 253.37195332170248, 265.3144500107512,
                        267.70306969828573, 263.8794609594266, 226.93164583634422]) #km/s
        menc_noAC = np.array([0.0, 37316078582.12215, 81833424086.48811,
                        124970318584.0155, 161901207448.951, 598685915680.8903]) # Msun

        for i, r in enumerate(rarr):
            # Assert vcirc, menc values are the same
            assert math.isclose(gal_noAC.model.circular_velocity(r), vcirc_noAC[i], rel_tol=ftol)
            assert math.isclose(gal_noAC.model.enclosed_mass(r), menc_noAC[i], rel_tol=ftol)


    def test_adiabatic_contraction(self):
        gal_AC = self.helper.setup_fullmodel(adiabatic_contract=True)

        ftol = 1.e-9
        rarr = np.array([0.,2.5,5.,7.5,10.,50.])   # kpc
        vcirc_AC = np.array([45.52585221837478, 270.5127652416235, 283.47161746884086,
                        284.6186917220378, 278.84200286773034, 226.8176250265685]) #km/s
        menc_AC = np.array([0.0, 42535784556.8831, 93417465234.21672,
                        141262539926.01163, 180782046435.46255, 598084452596.9691]) # Msun

        for i, r in enumerate(rarr):
            # Assert vcirc, menc values are the same
            assert math.isclose(gal_AC.model.circular_velocity(r), vcirc_AC[i], rel_tol=ftol)
            assert math.isclose(gal_AC.model.enclosed_mass(r), menc_AC[i], rel_tol=ftol)


    def test_biconical_outflow(self):
        gal_bicone = self.helper.setup_fullmodel_biconical()

        ##################
        # Create cube:
        param_filename = 'make_model_3Dcube.params'
        param_filename_full=_dir_tests_data+param_filename
        params = fw_utils_io.read_fitting_params(fname=param_filename_full)

        config_c_m_data = config.Config_create_model_data(**params)
        config_sim_cube = config.Config_simulate_cube(**params)
        kwargs_galmodel = {**config_c_m_data.dict, **config_sim_cube.dict}

        # Additional settings:
        kwargs_galmodel['from_data'] = False
        kwargs_galmodel['ndim_final'] = 3

        # Make model
        gal_bicone.create_model_data(**kwargs_galmodel)

        # Get cube:
        cube = gal_bicone.model_cube.data.unmasked_data[:].value

        ##################
        # Check some pix points:
        atol = 1.e-9
        # array: ind0,ind1,ind2, value
        ## TO FIX THIS!!!
        arr_pix_values = [[100,18,18, 0.00381117107560445],
                          [0,0,0, -1.1293772630057338e-22],
                          [100,18,0, 3.126830600463532e-07],
                          [50,18,18, 5.320399157467473e-05],
                          [95,10,10, 0.00025114780006119477],
                          [100,5,5, 3.765977728305624e-06],
                          [150,18,18, 5.312417940379806e-05],
                          [100,15,15, 0.0073600622525440765],
                          [100,15,21, 0.0022638772935597885],
                          [90,15,15, 0.010582918504479507],
                          [90,15,21, 0.0005703088570851938]]

        for arr in arr_pix_values:
            # Assert pixel values are the same
            assert math.isclose(cube[arr[0],arr[1],arr[2]], arr[3], abs_tol=atol)


    def test_uniform_inflow(self):
        gal_inflow = self.helper.setup_fullmodel_uniform_inflow()

        ##################
        # Create cube:
        param_filename = 'make_model_3Dcube.params'
        param_filename_full=_dir_tests_data+param_filename
        params = fw_utils_io.read_fitting_params(fname=param_filename_full)

        config_c_m_data = config.Config_create_model_data(**params)
        config_sim_cube = config.Config_simulate_cube(**params)
        kwargs_galmodel = {**config_c_m_data.dict, **config_sim_cube.dict}

        # Additional settings:
        kwargs_galmodel['from_data'] = False
        kwargs_galmodel['ndim_final'] = 3

        # Make model
        gal_inflow.create_model_data(**kwargs_galmodel)

        # Get cube:
        cube = gal_inflow.model_cube.data.unmasked_data[:].value

        ##################
        # Check some pix points:
        atol = 1.e-9
        # array: ind0,ind1,ind2, value
        ## TO FIX THIS!!!
        arr_pix_values = [[100,18,18, 0.003449915379640308],
                          [0,0,0, 2.2587545260114675e-22],
                          [100,18,0, 4.0604749531314176e-08],
                          [50,18,18, 1.742932001716722e-08],
                          [95,10,10, 0.00021499585635224392],
                          [100,5,5, 1.9462550747609577e-06],
                          [150,18,18, 2.4190233367665794e-07],
                          [100,15,15, 0.006070378312299052],
                          [100,15,21, 0.0008699919431378374],
                          [90,15,15, 0.008918484250396356],
                          [90,15,21, 0.0001878819028507639]]

        ## Compare to no-inflow model: from "test_simulate_cube()"
        # arr_pix_values = [[100,18,18, 0.003642043894515958],
        #                   [0,0,0, 8.470329472543004e-23],
        #                   [100,18,0, 3.1268306004623424e-07],
        #                   [50,18,18, 2.440707378333536e-09],
        #                   [95,10,10, 0.0002511288203406142],
        #                   [100,5,5, 3.7659777283049023e-06],
        #                   [150,18,18, 5.6281450732294695e-08],
        #                   [100,15,15, 0.006963221989588695],
        #                   [100,15,21, 0.0022507391576765032],
        #                   [90,15,15, 0.010201219579003603],
        #                   [90,15,21, 0.000557673465544929]]


        for arr in arr_pix_values:
            # Assert pixel values are the same
            assert math.isclose(cube[arr[0],arr[1],arr[2]], arr[3], abs_tol=atol)

    def test_simulate_cube(self):
        gal = self.helper.setup_fullmodel()
        inst = self.helper.setup_instrument()
        gal.instrument = inst

        ##################
        # Create cube:
        param_filename = 'make_model_3Dcube.params'
        param_filename_full=_dir_tests_data+param_filename
        params = fw_utils_io.read_fitting_params(fname=param_filename_full)

        config_c_m_data = config.Config_create_model_data(**params)
        config_sim_cube = config.Config_simulate_cube(**params)
        kwargs_galmodel = {**config_c_m_data.dict, **config_sim_cube.dict}

        # Additional settings:
        kwargs_galmodel['from_data'] = False
        kwargs_galmodel['ndim_final'] = 3

        # Make model
        gal.create_model_data(**kwargs_galmodel)

        # Get cube:
        cube = gal.model_cube.data.unmasked_data[:].value

        ##################
        # Check some pix points:
        atol = 1.e-9
        # array: ind0,ind1,ind2, value
        ## TO FIX THIS!!!
        arr_pix_values = [[100,18,18, 0.003642043894515958],
                          [0,0,0, 8.470329472543004e-23],
                          [100,18,0, 3.1268306004623424e-07],
                          [50,18,18, 2.440707378333536e-09],
                          [95,10,10, 0.0002511288203406142],
                          [100,5,5, 3.7659777283049023e-06],
                          [150,18,18, 5.6281450732294695e-08],
                          [100,15,15, 0.006963221989588695],
                          [100,15,21, 0.0022507391576765032],
                          [90,15,15, 0.010201219579003603],
                          [90,15,21, 0.000557673465544929]]

        for arr in arr_pix_values:
            # Assert pixel values are the same
            assert math.isclose(cube[arr[0],arr[1],arr[2]], arr[3], abs_tol=atol)



class TestModelsFittingWrappers:
    def test_fitting_wrapper_model(self):
        param_filename = 'make_model_3Dcube.params'
        param_filename_full=_dir_tests_data+param_filename

        # Delete existing folder:
        params = fw_utils_io.read_fitting_params(fname=param_filename_full)
        outdir = _dir_tests_data+params['outdir']
        if os.path.isdir(outdir):
            shutil.rmtree(outdir)

        # Make model
        dysmalpy_make_model.dysmalpy_make_model(param_filename=param_filename_full)

        # Load cube:
        f_cube = outdir+'{}_model_cube.fits'.format(params['galID'])
        cube = fits.getdata(f_cube)

        # Check some pix points:
        atol = 1.e-9
        # array: ind0,ind1,ind2, value
        arr_pix_values = [[100,18,18, 0.008900917775023906],
                          [  0, 0, 0, 3.3463030014984708e-22],
                          [100,18, 0, 3.5919506170302206e-07],
                          [ 50,18,18, 7.63640034138618e-08],
                          [ 95,10,10, 0.0002370085470795104],
                          [100, 5, 5, 1.4420204105232684e-05],
                          [150,18,18, 7.636400341471845e-08],
                          [100,15,15, 0.0015740863443549139],
                          [100,15,21, 0.0038719443027728975],
                          [ 90,15,15, 0.006517270586277637],
                          [ 90,15,21, 0.002939684687493484]]

        for arr in arr_pix_values:
            # Assert pixel values are the same
            assert math.isclose(cube[arr[0],arr[1],arr[2]], arr[3], abs_tol=atol)
