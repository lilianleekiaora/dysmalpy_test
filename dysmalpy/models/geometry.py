# coding=utf8
# Licensed under a 3-clause BSD style license - see LICENSE.rst
#
# Geometry models for DysmalPy

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

# Standard library
import logging

# Third party imports
import numpy as np
import scipy.ndimage as scp_ndi

try:
    from dysmalpy.utils import get_cin_cout
except:
    from .utils import get_cin_cout


# Local imports
from .base import _DysmalFittable3DModel
from dysmalpy.parameters import DysmalParameter

__all__ = ['Geometry']


# LOGGER SETTINGS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DysmalPy')

np.warnings.filterwarnings('ignore')



class Geometry(_DysmalFittable3DModel):
    """
    Model component defining the transformation from galaxy to sky coordinates

    Parameters
    ----------
    inc : float
        Inclination of the model in degrees

    pa : float
        Position angle East of North of the blueshifted side of the model in degrees

    xshift : float
        x-coordinate of the center of the model relative to center of data cube in pixels

    yshift : float
        y-coordinate of the center of the model relative to center of data cube in pixels

    vel_shift : float
        Systemic velocity shift that will be applied to the whole cube in km/s

    Methods
    -------
    coord_transform:
        Transform from sky to galaxy coordinates.

    inverse_coord_transform:
        Transform from galaxy to sky coordinates.

    Notes
    -----
    This model component takes as input sky coordinates and converts them
    to galaxy frame coordinates. `vel_shift` instead is used within `ModelSet.simulate_cube` to
    apply the necessary velocity shift.
    """

    inc = DysmalParameter(default=45.0, bounds=(0, 90))
    pa = DysmalParameter(default=0.0, bounds=(-180, 180))
    xshift = DysmalParameter(default=0.0)
    yshift = DysmalParameter(default=0.0)

    vel_shift = DysmalParameter(default=0.0, fixed=True)  # default: none

    _type = 'geometry'
    outputs = ('xp', 'yp', 'zp')

    @staticmethod
    def evaluate(x, y, z, inc, pa, xshift, yshift, vel_shift):
        """Transform sky coordinates to galaxy/model reference frame"""
        inc = np.pi / 180. * inc
        pa = np.pi / 180. * (pa - 90.)

        # Apply the shifts in the sky system
        xsky = x - xshift
        ysky = y - yshift
        zsky = z

        xtmp = xsky * np.cos(pa) + ysky * np.sin(pa)
        ytmp = -xsky * np.sin(pa) + ysky * np.cos(pa)
        ztmp = zsky

        xgal = xtmp
        ygal = ytmp * np.cos(inc) - ztmp * np.sin(inc)
        zgal = ytmp * np.sin(inc) + ztmp * np.cos(inc)

        return xgal, ygal, zgal

    def coord_transform(self, x, y, z, inc=None, pa=None, xshift=None, yshift=None):
        """Transform sky coordinates to galaxy/model reference frame"""
        if inc is None:     inc = self.inc
        if pa is None:      pa = self.pa
        if xshift is None:  xshift = self.xshift
        if yshift is None:  yshift = self.yshift

        return self.evaluate(x, y, z, inc, pa, xshift, yshift, self.vel_shit)


    def inverse_coord_transform(self, xgal, ygal, zgal,
            inc=None, pa=None, xshift=None, yshift=None):
        """Transform galaxy/model reference frame to sky coordinates"""
        if inc is None:     inc = self.inc
        if pa is None:      pa = self.pa
        if xshift is None:  xshift = self.xshift
        if yshift is None:  yshift = self.yshift

        inc = np.pi / 180. * inc
        pa = np.pi / 180. * (pa - 90.)

        # Apply inlincation:
        xtmp =  xgal
        ytmp =  ygal * np.cos(inc) + zgal * np.sin(inc)
        ztmp = -ygal * np.sin(inc) + zgal * np.cos(inc)

        # Apply PA + shifts in sky system:
        xsky = xtmp * np.cos(pa) - ytmp * np.sin(pa) + xshift
        ysky = xtmp * np.sin(pa) + ytmp * np.cos(pa) + yshift
        zsky = ztmp

        return xsky, ysky, zsky


    def transform_cube_affine(self, cube, inc=None, pa=None, xshift=None, yshift=None,
                output_shape=None):
        """Incline and transform a cube from galaxy/model reference frame to sky frame.
            Use scipy.ndimage.affine_transform"""
        if inc is None:     inc = self.inc
        if pa is None:      pa = self.pa
        if xshift is None:  xshift = self.xshift
        if yshift is None:  yshift = self.yshift

        inc = np.pi / 180. * inc
        pa = np.pi / 180. * (pa - 90.)

        c_in =  get_cin_cout(cube.shape)
        if output_shape is not None:
            c_out = get_cin_cout(output_shape)
        else:
            c_out = get_cin_cout(cube.shape)

        # # CUBE: z, y, x
        minc = np.array([[np.cos(inc), np.sin(inc),  0.],
                         [-np.sin(inc), np.cos(inc), 0.],
                         [0., 0., 1.]])

        mpa = np.array([[1., 0., 0.],
                        [0., np.cos(pa), -np.sin(pa)],
                        [0., np.sin(pa), np.cos(pa)]])

        transf_matrix = np.matmul(minc, mpa)
        offset_arr = np.array([0., yshift.value, xshift.value])
        offset_transf = c_in-np.matmul(transf_matrix,c_out+offset_arr)

        cube_sky = scp_ndi.interpolation.affine_transform(cube, transf_matrix,
                    offset=offset_transf, order=3, output_shape=output_shape)

        return cube_sky



    def zsky_direction_emitframe(self, x, y, z, inc=None):
        r"""
        Method to return the zsky direction in terms of the emission frame.
        This just accounts for the inclination.

        Parameters
        ----------
        x, y, z : float or array
            xyz position in the radial flow reference frame.

        Returns
        -------
        zsky_unit_vector : 3-element array
            Direction of the zsky vector in (xyz).

            This corrects for the inclination, so returns [0, -sin(i), cos(i)]
        """
        if inc is None:     inc = self.inc
        inc = np.pi / 180. * inc
        zsky_unit_vector = [ x*0., y*0. - np.sin(inc), z*0. + np.cos(inc) ]
        return zsky_unit_vector

    def project_velocity_along_LOS(self, model, vel, x, y, z, inc=None):
        r"""
        Method to project velocities in models' emission frame along the LOS (zsky direction).

        Parameters
        ----------
        model : `~dysmalpy.models._DysmalModel`
            Model component from which the velocity was calculated.

        vel : float or array or tuple of arrays
            Amplitude of the velocity.
            If model._multicoord_velocity is True, must pass a tuple of velocity components
                for each coordinate in the model's native geometry.

        x, y, z : float or array
            xyz position in the radial flow reference frame.

        inc : float, optional
            Specify a separate inclination. Default: uses self.inc

        Returns
        -------
        v_LOS : float or array
            Projection of velocity 'vel' along the LOS.
        """

        zsky_hat = self.zsky_direction_emitframe(x, y, z, inc=inc)

        # Dot product of vel_hat, zsky_unit_vector
        if model._multicoord_velocity:
            # Matrix multiply the velocity direction matrix with the
            #   oritinal velocity tuple, then dot product with the zsky unit vector
            vel_dir_matrix = model.vel_direction_emitframe(x, y, z)

            # Need to explicity work this out, as this is a 3x3 matrix multiplication
            #   with a 3-element vector, where the elements themselves are arrays...
            vel_cartesian = [vel[0]*0., vel[1]*0., vel[2]*0.]
            for row in range(vel_dir_matrix.shape[0]):
                for col in range(vel_dir_matrix.shape[1]):
                    vel_cartesian[row] += vel_dir_matrix[row, col] * vel[col]

            v_LOS = vel[0]*0.
            for vcomp, zhat in zip(vel_cartesian, zsky_hat):
                v_LOS += vcomp*zhat

        else:
            # Dotproduct of velocity unit vector and zsky unit vector
            vel_hat = model.vel_direction_emitframe(x, y, z)
            proj_dotprod = vel*0.
            for vhat, zhat in zip(vel_hat, zsky_hat):
                proj_dotprod += vhat*zhat

            # Multiply by velocity magnitude
            v_LOS = vel * proj_dotprod

        return v_LOS

    # def transform_cube_rotate_shift(self, cube, inc=None, pa=None, xshift=None, yshift=None):
    #     """Incline and transform a cube from galaxy/model reference frame to sky frame.
    #         Use scipy.ndimage.rotate and scipy.ndimage.shift"""
    #     # NOTE: SLOWER THAN AFFINE TRANSFORM
    #     if inc is None:     inc = self.inc
    #     if pa is None:      pa = self.pa
    #     if xshift is None:  xshift = self.xshift
    #     if yshift is None:  yshift = self.yshift
    #
    #     offset_arr = np.array([0., yshift, xshift])
    #     cube_inc = scp_ndi.rotate(cube, -inc, axes=(1,0), order=3, reshape=False)
    #     cube_PA  = scp_ndi.rotate(cube_inc, pa, axes=(2,1), order=3, reshape=False)
    #     cube_sky = scp_ndi.shift(cube_PA, offset_arr, order=3)
    #
    #     return cube_sky
