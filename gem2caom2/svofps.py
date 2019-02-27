# -*- coding: utf-8 -*-
# ***********************************************************************
# ******************  CANADIAN ASTRONOMY DATA CENTRE  *******************
# *************  CENTRE CANADIEN DE DONNÉES ASTRONOMIQUES  **************
#
#  (c) 2018.                            (c) 2018.
#  Government of Canada                 Gouvernement du Canada
#  National Research Council            Conseil national de recherches
#  Ottawa, Canada, K1A 0R6              Ottawa, Canada, K1A 0R6
#  All rights reserved                  Tous droits réservés
#
#  NRC disclaims any warranties,        Le CNRC dénie toute garantie
#  expressed, implied, or               énoncée, implicite ou légale,
#  statutory, of any kind with          de quelque nature que ce
#  respect to the software,             soit, concernant le logiciel,
#  including without limitation         y compris sans restriction
#  any warranty of merchantability      toute garantie de valeur
#  or fitness for a particular          marchande ou de pertinence
#  purpose. NRC shall not be            pour un usage particulier.
#  liable in any event for any          Le CNRC ne pourra en aucun cas
#  damages, whether direct or           être tenu responsable de tout
#  indirect, special or general,        dommage, direct ou indirect,
#  consequential or incidental,         particulier ou général,
#  arising from the use of the          accessoire ou fortuit, résultant
#  software.  Neither the name          de l'utilisation du logiciel. Ni
#  of the National Research             le nom du Conseil National de
#  Council of Canada nor the            Recherches du Canada ni les noms
#  names of its contributors may        de ses  participants ne peuvent
#  be used to endorse or promote        être utilisés pour approuver ou
#  products derived from this           promouvoir les produits dérivés
#  software without specific prior      de ce logiciel sans autorisation
#  written permission.                  préalable et particulière
#                                       par écrit.
#
#  This file is part of the             Ce fichier fait partie du projet
#  OpenCADC project.                    OpenCADC.
#
#  OpenCADC is free software:           OpenCADC est un logiciel libre ;
#  you can redistribute it and/or       vous pouvez le redistribuer ou le
#  modify it under the terms of         modifier suivant les termes de
#  the GNU Affero General Public        la “GNU Affero General Public
#  License as published by the          License” telle que publiée
#  Free Software Foundation,            par la Free Software Foundation
#  either version 3 of the              : soit la version 3 de cette
#  License, or (at your option)         licence, soit (à votre gré)
#  any later version.                   toute version ultérieure.
#
#  OpenCADC is distributed in the       OpenCADC est distribué
#  hope that it will be useful,         dans l’espoir qu’il vous
#  but WITHOUT ANY WARRANTY;            sera utile, mais SANS AUCUNE
#  without even the implied             GARANTIE : sans même la garantie
#  warranty of MERCHANTABILITY          implicite de COMMERCIALISABILITÉ
#  or FITNESS FOR A PARTICULAR          ni d’ADÉQUATION À UN OBJECTIF
#  PURPOSE.  See the GNU Affero         PARTICULIER. Consultez la Licence
#  General Public License for           Générale Publique GNU Affero
#  more details.                        pour plus de détails.
#
#  You should have received             Vous devriez avoir reçu une
#  a copy of the GNU Affero             copie de la Licence Générale
#  General Public License along         Publique GNU Affero avec
#  with OpenCADC.  If not, see          OpenCADC ; si ce n’est
#  <http://www.gnu.org/licenses/>.      pas le cas, consultez :
#                                       <http://www.gnu.org/licenses/>.
#
#  $Revision: 4 $
#
# ***********************************************************************
#

import io
import logging
import re

import requests
from astropy.io.votable import parse_single_table
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

SVO_URL = 'http://svo2.cab.inta-csic.es/svo/theory/fps/fps.php?ID=Gemini/'
SVO_KPNO_URL = 'http://svo2.cab.inta-csic.es/svo/theory/fps/fps.php?ID=KPNO/'


def get_votable(url):
    """
    Download the VOTable XML for the given url and return a astropy.io.votable
    object.

    :param url: query url for the SVO service
    :return: astropy.io.votable of the first table and
             an error_message if there was an error downloading the data
    """
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    vo_table = None
    response = None
    error_message = None
    try:
        response = session.get(url)
        fh = io.BytesIO(bytes(response.text, 'utf-8'))
        response.close()
        vo_table = parse_single_table(fh)
    except Exception as e:
        error_message = str(e)
    if response:
        response.close()
    return vo_table, error_message


def filter_metadata(instrument, filters):
    """
    For the given instrument and filters, go to the SVO Filter Profile Service

    http://svo2.cab.inta-csic.es/svo/theory/fps/

    and return energy metadata.

    :param instrument: The instrument name.
    :param filters: The filter name.
    :return: Energy metadata dictionary.
    """

    try:
        filter_names = filters.split('+')
        # use detector maximums as defaults
        w_min = 0.0
        wl_min = 0.0
        w_max = 100000.0
        wl_max = 100000.0
        width_min = 100000.0
        wl_width = wl_max - wl_min
        wl_eff = (wl_max + wl_min)/2.0

        # filter_name_found = True

        # 0 = min
        # 1 = max
        # units are Angstroms
        lookup = {'GG455': [4600.0, 11000.0],
                  'OG515': [5200.0, 11000.0],
                  'RG610': [6150.0, 11000.0],
                  'RG780': [780.0, 11000.0],
                  }

        for index in filter_names:
            filter_name = index.strip()
            if filter_name in lookup:
                w_min = lookup[filter_name][0]
                w_max = lookup[filter_name][1]
                wl_width = w_max - w_min
                wl_eff = (w_max + w_min)/2.0
            if 'Hartmann' in filter_name:
                continue
            if filter_name == 'open':
                if 'GMOS' in instrument:
                    w_min = 3500.0
                    w_max = 11000.0
                    wl_width = w_max - w_min
                    wl_eff = (w_max + w_min)/2.0
            else:
                filter_id = "{}.{}".format(instrument, filter_name)
                if instrument == 'Flamingos':
                    url = "{}{}".format(SVO_KPNO_URL, filter_id)
                else:
                    url = "{}{}".format(SVO_URL, filter_id)

                # Open the URL and fetch the VOTable document.
                # Some Gemini filters in SVO filter database have bandpass info
                # only for 'w'arm filters.  First check for filter without 'w'
                # appended to the ID (which I assume means bandpass is for cold
                # filter), then search for 'w' if nothing is found...
                votable, error_message = get_votable(url)
                if not votable:
                    url += 'w'
                    votable, error_message = get_votable(url)
                if not votable:
                    logging.error(
                        'Unable to download SVO filter data from {} because {}'
                        .format(url, error_message))
                    continue

                # DB - 14-04-19 After discussion with a few others use the
                # wavelength lookup values “WavelengthCen” and “FWHM” returned
                # from the SVO. Looking at some of the IR filters
                # use the more common “WavelengthCen” and “FWHM” values that
                # the service offers.

                wl_width = votable.get_field_by_id('FWHM').value
                wl_eff = votable.get_field_by_id('WavelengthCen').value
                w_min = wl_eff - wl_width/2.0
                w_max = wl_eff + wl_width/2.0

            if w_min > wl_min:
                wl_min = w_min
            if w_max < wl_max:
                wl_max = w_max
            if wl_width < width_min:
                width_min = wl_width

        fm = FilterMetadata(instrument)
        # if filter_name_found:
        fm.central_wl = wl_eff / 1.0e4
        fm.bandpass = wl_width / 1.0e4
        logging.info(
            'Filter(s): {}  MD: {}, {}'.format(filter_names, fm.central_wl,
                                               fm.bandpass))
        return fm
    except Exception as e:
        logging.error(e)
        import traceback
        tb = traceback.format_exc()
        logging.error(tb)


class FilterMetadata(object):

    # DB - 22-02-19
    # For imaging energy WCS, use standard imaging algorithm. i.e central
    # wavelength, bandpass from SVO filter, and
    # resolution = central_wavelength/bandpass

    # Choose this representation because CRPIX values should all be 1.0
    # for imaging spectral WCS as long as you use the central wavelength
    # of the filter for the corresponding CRVAL. DB - 13-02-19

    # CRVAL == central_wl
    # bandpass == delta without the NAXIS adjustment
    # CDELT == delta

    # naxis changes with each observation, central wavelength and
    # bandpass change with the hardware

    # NAXIS = 1
    # CTYPE = ‘WAVE’
    # CUNIT = ‘um’
    # CRPIX = NAXIS / 2.0
    # CRVAL = wl_eff
    # CDELT = (wl_max - wl_min) / n_axis
    # resolving power = (wl_max  + wl_min)/(2*CDELT)
    # bandpass_name = filter name
    # CDELT is the SVO’s effective width, W_effective in their tables which
    # corresponds more or less to wl_max - wl_min.

    # CRPIX values should all be 1.0 for imaging spectral WCS as long as
    # you use the central wavelength of the filter for the
    # corresponding CRVAL. DB - 13-02-19

    def __init__(self, instrument=None, delta=None):
        self.central_wl = None
        self.bandpass = None
        self.resolving_power = None
        self.delta = delta
        self.instrument = instrument

    @property
    def central_wl(self):
        """Central wavelength for a filter."""
        return self._central_wl

    @central_wl.setter
    def central_wl(self, value):
        self._central_wl = value

    @property
    def bandpass(self):
        """Width of a filter."""
        return self._bandpass

    @bandpass.setter
    def bandpass(self, value):
        self._bandpass = value

    def get_delta(self, n_axis):
        """Delta for a filter - adjusted for naxis."""
        if self.delta is None:
            return self._bandpass / n_axis
        else:
            return self.delta

    @property
    def resolving_power(self):
        if self.instrument in ['Phoenix', 'GNIRS', 'michelle']:
            return None
        elif self._resolving_power is None:
            if self.instrument in ['NIFS', 'NIRI']:
                return None
            else:
                # return self.central_wl / self.bandpass
                self.adjust_resolving_power()
                return self._resolving_power
        else:
            return self._resolving_power

    @resolving_power.setter
    def resolving_power(self, value):
        self._resolving_power = value

    def adjust_bandpass(self, variance):
        self.bandpass = ((self.central_wl + variance) -
                         (self.central_wl - variance))

    def set_bandpass(self, w_max, w_min):
        self.bandpass = (w_max - w_min)

    def set_central_wl(self, w_max, w_min):
        self.central_wl = (w_max + w_min) / 2.0

    def set_resolving_power(self, w_max, w_min):
        self.resolving_power = (w_max + w_min) / (2 * self.bandpass)

    def adjust_resolving_power(self):
        self.resolving_power = self.central_wl / self.bandpass
