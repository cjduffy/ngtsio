# -*- coding: utf-8 -*-
"""
Created on Fri Nov 10 15:57:31 2017

@author:
Maximilian N. Guenther
Battcock Centre for Experimental Astrophysics,
Cavendish Laboratory,
JJ Thomson Avenue
Cambridge CB3 0HE
Email: mg719@cam.ac.uk
"""

import warnings
import astropy.io.fits as pyfits
import fitsio
import os, sys, glob, socket, collections, datetime
import numpy as np




###############################################################################
# Helper function
###############################################################################
def warning_on_one_line(message, category, filename, lineno, file=None, line=''):
    return '\n%s: %s, line %s\n\t %s\n\n' % (category.__name__, filename, lineno, message)
warnings.formatwarning = warning_on_one_line



###############################################################################
# Getter (Main Program)
###############################################################################

def get(fieldname, ngts_version, keys, obj_id=None, obj_row=None, time_index=None, time_date=None, time_hjd=None, time_actionid=None, bls_rank=1, indexing='fits', fitsreader='fitsio', simplify=True, fnames=None, root=None, roots=None, silent=False, set_nan=False):

    """
    Convenient wrapper for astropy and cfitsio readers for various NGTS data files.
    Can handle either data formats as in prodstore/ or the MegaFile during pipeline runs.

    Parameters
    ----------

    fieldname : str
        name of the NGTS-field, e.g. 'NG0304-1115'

    keys : str / array of str
        which parameters shall be read out from the fits files, e.g. ['RA','DEC','HJD','FLUX','PERIOD','CANVAS_PERIOD','DILUTION']. See below for other valid requests.

    obj_id, obj_row : int / str / textfilename / array of int / array of str
        identifier of the objects to be read out. If empty, all objects will be retrieved. Only either obj_id or obj_row can be chosen as input, not both. obj_id reads out objects by their object IDs. obj_row reads the requested rows from the fits file. Examples:
            obj_id = 46,    obj_id = '046',    obj_id = '00046',    obj_id = [46,57,1337],    obj_id = range(1,100),    obj_id = 'object_ids.txt'
            obj_row = 1,    obj_row = [1,2,3,1337],     obj_row = range(1,100),     obj_row = 'object_rows.txt'

    time_index, time_date, time_hjd, time_actionid : int / str / textfilename / array of int / array of str
        identifier of the times/exposures to be read out. If empty, all times/exposures will be retrieved. Only either of these can be chosen as input, not more than one. time_index reads out the requested columns from the fits file, and hence allows to read out as little as one exposure. time_date reads all exposures per given calendar date(s). time_hjd reads all exposures per given HJD-date (only HJD values given as integers are accepted). time_actionid reads all exposures per given action ID. Examples:
            time_index = 1,    time_index = [1,2,3,1337],    time_index = range(1,100),    time_index = 'time_indices.txt'
            time_date = 20151104,    time_date = '20151104',    time_date = '2015-11-04',    time_date = '2015/11/04',    time_date = 'dates.txt'
            time_hjd = 674,    time_hjd = [674,675,680],    time_hjd = 'hjds.txt'
            time_actionid = 108583,    time_actionid = [108583,133749],    time_actionid = 'actionids.txt'

    bls_rank : int
        which BLS RANK should be read out from the BLS fits files (e.g. when reading 'PERIOD')

    indexing : str
        following which format are the obj_rows and time_indices given (standard is 'fits')?
            'fits': indexing rows from 1
            'python': indexing rows from 0

    fitsreader : str
        'pyfits' or 'astropy': use the astropy.io.fits module.
        'fitsio' or 'cfitsio': use the fitsio module (standard)
        fitsio seems to perform best, see below for performance tests.

    simplify : bool
        if True and only one object is requested, it simplifies the dictionary entries into 1D nd.arrays (otherwise they will be 2D nd.arrays with an empty dimension). Standard is True.

    fnames : dict
        This allows to manually pass a dictionary of filenames. Leave blank if you want to run it on Warwick's or Cambridge's NGTS cluster. Contains the following keys:
        a) if used in a pipeline run:
        fnames['BLSPipe_megafile']
        b) if used for final data prodcuts:
        fnames['nights']
        fnames['sysrem'] (optional)
        fnames['bls'] (optional)
        fnames['decorr'] (optional)
        fnames['canvas'] (optional)
        fnames['dilution'] (optional)


    root : str
        This allows to manually pass a single root directory. Leave blank if you want to run it on Warwick's or Cambridge's NGTS cluster. The root directory structure has to contain all individual fits files.

    roots : dict
        This allows to manually pass different root directories, such as for prodstore/0*/[MergePipe*, BLSPipe*, SysremPipe*]. Leave blank if you want to run it on Warwick's or Cambridge's NGTS cluster. Contains the following keys:
            roots['nights']
            roots['sysrem'] (optional)
            roots['bls'] (optional)
            roots['decorr'] (optional)
            roots['canvas'] (optional)
            roots['dilution'] (optional)

    silent : bool
        Whether a short report should be printed or not.

    ngtsversion : str
        From which directory shall the files be read? Standard is usually the latest release. Irrelevant if filenames are given manually via fnames=fnames.

    set_nan : bool
        Whether all flagged values in CCDX/Y, CENDTX/Y and FLUX should be replaced with NAN or not (if not, they might be zeros or any reasonable/unreasonable real numbers).


    Possible keys
    -------------

    a) Nightly Summary Fits file

        From 'CATALOGUE' (per object):
        ['OBJ_ID', 'RA', 'DEC', 'REF_FLUX', 'CLASS', 'CCD_X', 'CCD_Y', 'FLUX_MEAN', 'FLUX_RMS', 'MAG_MEAN', 'MAG_RMS', 'NPTS', 'NPTS_CLIPPED']

        From 'IMAGELIST' (per image):
        ['ACQUMODE', 'ACTIONID', 'ACTSTART', 'ADU_DEV', 'ADU_MAX', 'ADU_MEAN', 'ADU_MED', 'AFSTATUS', 'AGREFIMG', 'AGSTATUS', 'AG_APPLY', 'AG_CORRX', 'AG_CORRY', 'AG_DELTX', 'AG_DELTY', 'AG_ERRX', 'AG_ERRY', 'AIRMASS', 'BIASMEAN', 'BIASOVER', 'BIASPRE', 'BIAS_ID', 'BKG_MEAN', 'BKG_RMS', 'CAMERAID', 'CAMPAIGN', 'CCDTEMP', 'CCDTEMPX', 'CHSTEMP', 'CMD_DEC', 'CMD_DMS', 'CMD_HMS', 'CMD_RA', 'COOLSTAT', 'CROWDED', 'CTS_DEV', 'CTS_MAX', 'CTS_MEAN', 'CTS_MED', 'DARK_ID', 'DATE-OBS', 'DATE', 'DITHER', 'EXPOSURE', 'FCSR_ENC', 'FCSR_PHY', 'FCSR_TMP', 'FIELD', 'FILTFWHM', 'FLAT_ID', 'FLDNICK', 'GAIN', 'GAINFACT', 'HSS_MHZ', 'HTMEDXF', 'HTRMSXF', 'HTXFLAGD', 'HTXNFLAG', 'HTXRAD1', 'HTXSIG1', 'HTXTHTA1', 'HTXVAL1', 'IMAGE_ID', 'IMGCLASS', 'IMGTYPE', 'LST', 'MINPIX', 'MJD', 'MOONDIST', 'MOONFRAC', 'MOONPHSE', 'MOON_ALT', 'MOON_AZ', 'MOON_DEC', 'MOON_RA', 'NBSIZE', 'NIGHT', 'NUMBRMS', 'NXOUT', 'NYOUT', 'OBJECT', 'OBSSTART', 'PROD_ID', 'PSFSHAPE', 'RCORE', 'READMODE', 'READTIME', 'ROOFSTAT', 'SATN_ADU', 'SEEING', 'SKYLEVEL', 'SKYNOISE', 'STDCRMS', 'SUNDIST', 'SUN_ALT', 'SUN_AZ', 'SUN_DEC', 'SUN_RA', 'TC3_3', 'TC3_6', 'TC6_3', 'TC6_6', 'TCRPX2', 'TCRPX5', 'TCRVL2', 'TCRVL5', 'TEL_ALT', 'TEL_AZ', 'TEL_DEC', 'TEL_HA', 'TEL_POSA', 'TEL_RA', 'THRESHOL', 'TIME-OBS', 'TV6_1', 'TV6_3', 'TV6_5', 'TV6_7', 'VI_MINUS', 'VI_PLUS', 'VSS_USEC', 'WCSPASS', 'WCS_ID', 'WXDEWPNT', 'WXHUMID', 'WXPRES', 'WXTEMP', 'WXWNDDIR', 'WXWNDSPD', 'XENCPOS0', 'XENCPOS1', 'YENCPOS0', 'YENCPOS1', 'TMID']

        From image data (per object and per image):
        HJD
        FLUX
        FLUX_ERR
        FLAGS
        CCDX
        CCDY
        CENTDX_ERR
        CENTDX
        CENTDY_ERR
        CENTDY
        SKYBKG


    b) Sysrem Fits File

        Sysrem flux data (per object and per image):
        SYSREM_FLUX3


    c) BLS Fits File

        From 'CATALOGUE' (for all objects):
        ['OBJ_ID', 'BMAG', 'VMAG', 'RMAG', 'JMAG', 'HMAG', 'KMAG', 'MU_RA', 'MU_RA_ERR', 'MU_DEC', 'MU_DEC_ERR', 'DILUTION_V', 'DILUTION_R', 'MAG_MEAN', 'NUM_CANDS', 'NPTS_TOT', 'NPTS_USED', 'OBJ_FLAGS', 'SIGMA_XS', 'TEFF_VK', 'TEFF_JH', 'RSTAR_VK', 'RSTAR_JH', 'RPMJ', 'RPMJ_DIFF', 'GIANT_FLG', 'CAT_FLG']

        From 'CANDIDATE' data (only for candidates):
        ['OBJ_ID', 'RANK', 'FLAGS', 'PERIOD', 'WIDTH', 'DEPTH', 'EPOCH', 'DELTA_CHISQ', 'CHISQ', 'NPTS_TRANSIT', 'NUM_TRANSITS', 'NBOUND_IN_TRANS', 'AMP_ELLIPSE', 'SN_ELLIPSE', 'GAP_RATIO', 'SN_ANTI', 'SN_RED', 'SDE', 'MCMC_PERIOD', 'MCMC_EPOCH', 'MCMC_WIDTH', 'MCMC_DEPTH', 'MCMC_IMPACT', 'MCMC_RSTAR', 'MCMC_MSTAR', 'MCMC_RPLANET', 'MCMC_PRP', 'MCMC_PRS', 'MCMC_PRB', 'MCMC_CHISQ_CONS', 'MCMC_CHISQ_UNC', 'MCMC_DCHISQ_MR', 'MCMC_PERIOD_ERR', 'MCMC_EPOCH_ERR', 'MCMC_WIDTH_ERR', 'MCMC_DEPTH_ERR', 'MCMC_RPLANET_ERR', 'MCMC_RSTAR_ERR', 'MCMC_MSTAR_ERR', 'MCMC_CHSMIN', 'CLUMP_INDX', 'CAT_IDX', 'PG_IDX', 'LC_IDX']


    d) CANVAS Text File (if existant)

        ['CANVAS_PERIOD','CANVAS_EPOCH','CANVAS_WIDTH','CANVAS_DEPTH','CANVAS_Rp','CANVAS_Rs',...]


    e) DILUTION Fits File (if existant)

        'DILUTION'


    Returns
    -------
    dic : dict
        dictionary containing all the requested keys


    Note
    ----
    ngtsio can be used for either final products or within a pipeline run
    If used in pipeline run, fnames['BLSPipe_megafile'] is required
    If used for final products from prodstore/0* fnames['nights'], fnames['sysrem'] and fnames['bls'] may be required

    Naming conventions differ between pipeline and final prodcuts
    In pipeline: FLUX
    In final prodcuts: FLUX3, SYSREM_FLUX3, DECORR_FLUX3
    """


    #'FLUX' vs 'SYSREM_FLUX3'
    if ('FLUX' in keys) and ( (fnames is None) or ('BLSPipe_megafile' not in fnames)):
        warnings.warn('FLUX key is deprecated unless for in-pipeline use.  \
                       Please use FLUX3, FLUX4, FLUX5, SYSREM_FLUX3 or DECORR_FLUX3 for final products.')

    if not silent:
        print('Field name:', fieldname)
        print('NGTS version:', ngts_version)

    if (roots is None) and (fnames is None):
        roots = standard_roots(fieldname, ngts_version, root, silent)

    if fnames is None:
        fnames = standard_fnames(fieldname, ngts_version, roots, silent)

    elif 'BLSPipe_megafile' in fnames:
        fnames['nights'] = fnames['BLSPipe_megafile']
        fnames['CATALOGUE'] = fnames['BLSPipe_megafile']
        fnames['IMAGELIST'] = fnames['BLSPipe_megafile']

    if fnames is not None:
        keys_0 = 1*keys #copy list
        keys_0.append('OBJ_ID')

        #::: in pipeline only
        if ('SYSREM_FLUX3' in keys) and (fnames is not None) and ('BLSPipe_megafile' in fnames):
            keys.append('FLUX')

        #::: append FLAGS for set_nan
        if set_nan and ('FLAGS' not in keys_0):
            keys.append('FLAGS')

        #::: objects
        ind_objs, obj_ids = get_obj_inds(fnames, obj_id, obj_row, indexing, fitsreader, obj_sortby = 'obj_ids')
        if not silent: print('Object IDs (',len(obj_ids),'):', obj_ids)

        #::: only proceed if at least one of the requested objects exists
        if isinstance(ind_objs,slice) or len(ind_objs)>0:

            #::: time
            ind_time = get_time_inds(fnames, time_index, time_date, time_hjd, time_actionid, fitsreader, silent)

            #::: get dictionary
            dic, keys = get_data(fnames, obj_ids, ind_objs, keys, bls_rank, ind_time, fitsreader)

            #::: in pipeline only
            if ('SYSREM_FLUX3' in keys) and (fnames is not None) and ('BLSPipe_megafile' in fnames):
                dic['SYSREM_FLUX3'] = dic['FLUX']
                if 'FLUX' not in keys_0:
                    del dic['FLUX']

            #::: set flagged values and flux==0 values to nan
            if set_nan:
                dic = set_nan_dic(dic)

            #::: remove entries that were only needed for readout / computing things
            if ('FLAGS' in dic.keys()) and ('FLAGS' not in keys_0):
                del dic['FLAGS']
            #        if ('FLUX' in dic.keys()) and ('FLUX' not in keys_0): del dic['FLUX']
            #        if ('FLUX3_ERR' in dic.keys()) and ('FLUX3_ERR' not in keys_0): del dic['FLUX3_ERR']
            #        if ('SYSREM_FLUX3' in dic.keys()) and ('SYSREM_FLUX3' not in keys_0): del dic['SYSREM_FLUX3']

            #::: convert RA and DEC from radian into degree if <CYCLE1706 and not in pipeline
            if ('BLSPipe_megafile' not in fnames) and (ngts_version in ('TEST10','TEST16','TEST16A','TEST18')):
                if 'RA' in keys:
                    dic['RA'] = dic['RA']*180./np.pi
                if 'DEC' in keys:
                    dic['DEC'] = dic['DEC']*180./np.pi
    #
            #::: simplify output if only for 1 object
            if simplify:
                dic = simplify_dic(dic)

            #::: add fieldname and ngts_version
            dic['FIELDNAME'] = fieldname
            dic['NGTS_VERSION'] = ngts_version

            #::: check if all keys were retrieved
            check_dic(dic, keys_0, silent)

        else:
            dic = None

    else:
        dic = None

    return dic




###############################################################################
# Fielnames Formatting
###############################################################################
def standard_roots(fieldname, ngts_version, root, silent):

    try:
        if (root is None):
            if ngts_version[-3:] == "_DC":
                ngts_version = ngts_version[:-3]

            #::: on laptop (OS X)
            if sys.platform == "darwin":
                roots = {}
                roots['nights'] = scalify(glob.glob('/Users/mx/Big_Data/BIG_DATA_NGTS/2017/prodstore/*/MergePipe*'+fieldname+'*'+ngts_version+'*'))
                roots['sysrem'] = scalify(glob.glob('/Users/mx/Big_Data/BIG_DATA_NGTS/2017/prodstore/*/SysremPipe*'+fieldname+'*'+ngts_version+'*'))
                roots['bls'] = scalify(glob.glob('/Users/mx/Big_Data/BIG_DATA_NGTS/2017/prodstore/*/BLSPipe*'+fieldname+'*'+ngts_version+'*'))
                roots['decorr'] = scalify(glob.glob('/Users/mx/Big_Data/BIG_DATA_NGTS/2017/prodstore/*/DecorrPipe*'+fieldname+'*'+ngts_version+'*'))
                roots['dilution'] = None
                roots['canvas'] = None

            #::: on Cambridge servers
            elif 'ra.phy.cam.ac.uk' in socket.gethostname():
                roots = {}
                roots['nights'] = scalify(glob.glob('/appcg/data2/NGTS/ngts_pipeline_output/prodstore/*/MergePipe*'+fieldname+'*'+ngts_version+'*'))
                roots['sysrem'] = scalify(glob.glob('/appcg/data2/NGTS/ngts_pipeline_output/prodstore/*/SysremPipe*'+fieldname+'*'+ngts_version+'*'))
                roots['bls'] = scalify(glob.glob('/appcg/data2/NGTS/ngts_pipeline_output/prodstore/*/BLSPipe*'+fieldname+'*'+ngts_version+'*'))
                roots['decorr'] = scalify(glob.glob('/appcg/data2/NGTS/ngts_pipeline_output/prodstore/*/DecorrPipe*'+fieldname+'*'+ngts_version+'*'))
                roots['dilution'] = None
                roots['canvas'] = None

            #::: on ngtshead (LINUX)
            if 'ngts' in socket.gethostname():
                roots = {}
                roots['nights'] = scalify(glob.glob('/ngts/prodstore/*/MergePipe*'+fieldname+'*'+ngts_version+'*'))
                roots['sysrem'] = scalify(glob.glob('/ngts/prodstore/*/SysremPipe*'+fieldname+'*'+ngts_version+'*'))
                roots['phot'] = scalify(glob.glob('/ngts/prodstore/*/PhotPipe*'+fieldname+'*'+ngts_version+'*'))
                roots['bls'] = scalify(glob.glob('/ngts/prodstore/*/BLSPipe*'+fieldname+'*'+ngts_version+'*'))
                roots['decorr'] = scalify(glob.glob('/ngts/prodstore/*/DecorrPipe*'+fieldname+'*'+ngts_version+'*'))
                roots['dilution'] = None
                roots['canvas'] = None

        #if a single root is given, it will overwrite individual roots
        elif root is not None:
            roots = {}
            roots['nights'] = root
            roots['sysrem'] = root
            roots['bls'] = root
            roots['dilution'] = root
            roots['canvas'] = root

        #otherwise roots has been given (try-except will catch the None or non-existing entries)
        else:
            pass

    except:
#        raise ValueError('Requested files do not exist. Please check file directories.')
        warnings.warn('Requested roots do not exist. Please check file directories.')
        roots = None

    return roots




def standard_fnames(fieldname, ngts_version, roots, silent):

    try:
        fnames = {}

        #Nights
        #a list of all single files (e.g. FLAGS, FLUX3, FLUX3_ERR, CCDX etc.)
        try:
            f_nights = os.path.join( roots['nights'], '*'+fieldname+'*.fits' )
            fnames['nights'] = glob.glob( f_nights )
        except:
            fnames['nights'] = None
#            warnings.warn( str(fieldname)+': Fits files "nights" do not exist.' )

        #BLS
        try:
            f_bls = os.path.join( roots['bls'], '*'+fieldname+'*.fits' )
            fnames['bls'] = glob.glob( f_bls )[-1]
        except:
            fnames['bls'] = None
#            warnings.warn( str(fieldname)+': Fits files "bls" do not exist.' )

        #SYSREM
        try:
            f_sysrem = os.path.join( roots['sysrem'], '*'+fieldname+'*SYSREM_FLUX3*.fits' )
            fnames['sysrem'] = glob.glob( f_sysrem )[-1]
        except:
            fnames['sysrem'] = None
#            warnings.warn( str(fieldname)+': Fits files "sysrem" do not exist.' )
        try:
            f_sysrem_im = os.path.join( roots['sysrem'], '*'+fieldname+'*SYSREM_IMAGELIST*.fits' )
            fnames['sysrem_im'] = glob.glob( f_sysrem_im )[-1]
        except:
            fnames['sysrem_im'] = None

        #DECORR
        try:
            f_decorr = os.path.join( roots['decorr'], '*'+fieldname+'*DECORR_FLUX3*.fits' )
            fnames['decorr'] = glob.glob( f_decorr )[-1]
        except:
            fnames['decorr'] = None
#            warnings.warn( str(fieldname)+': Fits files "decorr" does not exist.' )

        #set all individual filenames instead of 'nights'
        keys = ['CATALOGUE','CCDX','CCDY','CENTDX_ERR','CENTDX','CENTDY_ERR','CENTDY',
                'FLAGS','FLUX3_ERR','FLUX3','FLUX4_ERR','FLUX4','FLUX5_ERR','FLUX5',
                'HJD','IMAGELIST','SKYBKG','SUB_PROD_LIST']
        fnames = get_name(fnames,keys)

        #TODO:
        fnames['dilution'] = None
        fnames['canvas'] = None

    except:
#        raise ValueError('Requested files do not exist. Please check file directories.')
        warnings.warn('Requested files do not exist. Please check file directories.')
        fnames = None

    return fnames




def get_name(fnames, keys):
    for key in keys:
        fnames[key] = scalify([x for x in fnames['nights'] if key+'.fits' in x])
    return fnames




def scalify(l, out='first'):
    if len(l) == 0:
        return None
    else:
        if out=='first':
            return l[0]
        elif out=='last':
            return l[-1]
        elif out=='all':
            return l




###############################################################################
# Object Input Formatting
###############################################################################

def get_obj_inds(fnames, obj_ids, obj_rows, indexing,fitsreader, obj_sortby = 'obj_ids'):

    inputtype = None


    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #::: if no input is given, use all objects
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    if obj_ids is None and obj_rows is None:

        inputtype = None
        ind_objs = slice(None)
        obj_ids = get_objids_from_indobjs(fnames, ind_objs, fitsreader)


    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #::: if obj_id is given
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    elif obj_ids is not None and obj_rows is None:

        inputtype = 'obj_ids'

        # b) test if non-empty list
        if isinstance(obj_ids, (collections.Sequence, np.ndarray)) and not isinstance(obj_ids, (str)) and len(np.atleast_1d(obj_ids)) > 0:
            #make sure its not a 0-dimensional ndarray
            obj_ids = np.atleast_1d(obj_ids)
            # if list of integer or float -> convert to list of str
            if not isinstance(obj_ids[0], str):
                obj_ids = map(int, obj_ids)
                if not all(x>0 for x in obj_ids):
                    error = '"obj_id" data type not understood.'
                    sys.exit(error)
                obj_ids = map(str, obj_ids)
            # give all strings 6 digits
            obj_ids = objid_6digit(obj_ids)
            # connect obj_ids to ind_objs
            ind_objs, obj_ids = get_indobjs_from_objids(fnames, obj_ids, fitsreader)


        #c) test if file
        elif isinstance(obj_ids, str) and os.path.isfile(obj_ids):
            # load the file
            obj_ids = np.loadtxt(obj_ids, dtype='S6').tolist()
            # cast to list
            if isinstance(obj_ids, str):
                obj_ids = [obj_ids]
            # give all strings 6 digits
            obj_ids = objid_6digit(obj_ids)
            # connect obj_ids to ind_objs
            ind_objs, obj_ids = get_indobjs_from_objids(fnames, obj_ids, fitsreader)


        # d) test if str
        elif isinstance(obj_ids, str) and not os.path.isfile(obj_ids):

            # d1) a single value given as a string
            if (obj_ids != 'bls') and (obj_ids != 'canvas'):
                # cast to list
                obj_ids = [obj_ids]
                # give all strings 6 digits
                obj_ids = objid_6digit(obj_ids)

            #d2) the command 'bls' which reads out all 'bls' candidates
            elif obj_ids == 'bls':
                if fnames['bls'] is not None:
                    if fitsreader=='astropy' or fitsreader=='pyfits':
                        with pyfits.open(fnames['bls'], mode='denywrite') as hdulist:
                            obj_ids = np.unique( hdulist['CANDIDATES'].data['OBJ_ID'].strip() )
                            del hdulist['CANDIDATES'].data

                    elif fitsreader=='fitsio' or fitsreader=='cfitsio':
                        with fitsio.FITS(fnames['bls'], vstorage='object') as hdulist_bls:
                            obj_ids = np.unique( np.char.strip(hdulist_bls['CANDIDATES'].read(columns='OBJ_ID')) )

                    else: sys.exit('"fitsreader" can only be "astropy"/"pyfits" or "fitsio"/"cfitsio".')

                else:
                    warnings.warn('BLS files not found or could not be loaded.')
                    obj_ids = ['bls']

            #d3) the command 'canvas' which reads out all 'canvas' candidates
            elif obj_ids == 'canvas':
                if fnames['canvas'] is not None:
                    canvasdata = np.genfromtxt(fnames['canvas'], dtype=None, names=True)
                    obj_ids = objid_6digit( canvasdata['OBJ_ID'].astype('|S6') )
                else:
                    warnings.warn('CANVAS files not found or could not be loaded.')
                    obj_ids = ['canvas']

            else:
                sys.exit('Error: invalid input for "obj_id".')

            # connect obj_ids to ind_objs
            ind_objs, obj_ids = get_indobjs_from_objids(fnames, obj_ids, fitsreader)


        # e) test if int/float
        elif isinstance(obj_ids, (int, float)) and obj_ids>=0:
            # cast to list of type str
            obj_ids = [ str(int(obj_ids)) ]
            # give all strings 6 digits
            obj_ids = objid_6digit(obj_ids)
            # connect obj_ids to ind_objs
            ind_objs, obj_ids = get_indobjs_from_objids(fnames, obj_ids, fitsreader)


        # problems:
        else:
            error = '"obj_id" data type not understood.'
            sys.exit(error)


    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #::: if obj_row is given
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    elif obj_ids is None and obj_rows is not None:

        inputtype = 'ind_objs'

        ind_objs = obj_rows

        # a) test if non-empty list
        if isinstance(ind_objs, (collections.Sequence, np.ndarray)) and not isinstance(ind_objs, (str, unicode)) and len(ind_objs) > 0:
            # if list of str or float -> convert to list of int
            if isinstance(ind_objs[0], (str,float)):
                ind_objs = map(int, ind_objs)
            # count from 0 (python) or from 1 (fits)?
            if (indexing=='fits'):
                if 0 in ind_objs:
                    warnings.warn('"indexing" was set to "fits" (starts counting from 1) but "obj_rows" contained 0. "indexing" is now automatically set to "python" to avoid errors.')
                    indexing = 'python'
                else:
                    ind_objs = [x-1 for x in ind_objs]
            # connect obj_ids to ind_objs
            obj_ids = get_objids_from_indobjs(fnames, ind_objs, fitsreader)

        # b) test if file
        elif isinstance(ind_objs, str) and os.path.isfile(ind_objs):
            # load the file
            ind_objs = np.loadtxt(obj_rows, dtype='int').tolist()
            # count from 0 (python) or from 1 (fits)?
            if (indexing=='fits'):
                ind_objs = [x-1 for x in ind_objs]
            # connect obj_ids to ind_objs
            obj_ids = get_objids_from_indobjs(fnames, ind_objs, fitsreader)

        # c) test if str
        elif isinstance(ind_objs, str) and not os.path.isfile(ind_objs):
            # cast to list of type int
            ind_objs = [ int(ind_objs) ]
            # count from 0 (python) or from 1 (fits)?
            if (indexing=='fits'):
                if 0 in ind_objs:
                    warnings.warn('"indexing" was set to "fits" (starts counting from 1) but "obj_rows" contained 0. "indexing" is now automatically set to "python" to avoid errors.')
                    indexing = 'python'
                else:
                    ind_objs = [x-1 for x in ind_objs]
            # connect obj_ids to ind_objs
            obj_ids = get_objids_from_indobjs(fnames, ind_objs, fitsreader)

        # d) test if int/float
        elif isinstance(ind_objs, (int, float)):
            # cast to list of type int
            ind_objs = [ int(ind_objs) ]
            # count from 0 (python) or from 1 (fits)?
            if (indexing=='fits'):
                if 0 in ind_objs:
                    warnings.warn('"indexing" was set to "fits" (starts counting from 1) but "obj_rows" contained 0. "indexing" is now automatically set to "python" to avoid errors.')
                    indexing = 'python'
                else:
                    ind_objs = [x-1 for x in ind_objs]
            # connect obj_ids to ind_objs
            obj_ids = get_objids_from_indobjs(fnames, ind_objs, fitsreader)


        # problems:
        else:
#            print '--- Warning: "obj_row" data type not understood. ---'
            error = '"obj_row" data type not understood.'
            sys.exit(error)



    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #::: if obj_id and obj_row are both given
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    else:
        error = 'Only use either "obj_id" or "obj_row".'
        sys.exit(error)



    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    #:::
    #::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    if inputtype is not None:

        #::: typecast to numpy arrays
        obj_ids = np.array(obj_ids)
        ind_objs = np.array(ind_objs)

        #::: sort
        #TODO: UNCLEAN!!! This currently assumes the object IDs in the fits files are sorted like the row number!!!

        ind_objs = np.sort(ind_objs)
        obj_ids = np.sort(obj_ids)

#        if obj_sortby == 'obj_ids':
#            ind_sort = np.argsort( obj_ids )
#            obj_ids = obj_ids[ind_sort]
#            ind_objs = ind_objs[ind_sort]
#
#        elif obj_sortby == 'ind_objs':
#            ind_sort = np.argsort( ind_objs )
#            obj_ids = obj_ids[ind_sort]
#            ind_objs = ind_objs[ind_sort]
#
#        elif obj_sortby == 'original':
#            if inputtype == 'obj_ids':
#                pass
                #TODO: allow to keep the sorting of the input, e.g.  OBJ_IDs ['001337','000001'] corresponding to IND_OBJS [100, 1]


    #::: return
    return ind_objs, obj_ids



def get_indobjs_from_objids(fnames, obj_list, fitsreader):

    if fitsreader=='astropy' or fitsreader=='pyfits':
        with pyfits.open(fnames['CATALOGUE'], mode='denywrite') as hdulist:
            obj_ids_all = hdulist['CATALOGUE'].data['OBJ_ID'].strip()
            del hdulist['CATALOGUE'].data

    elif fitsreader=='fitsio' or fitsreader=='cfitsio':
        with fitsio.FITS(fnames['CATALOGUE'], vstorage='object') as hdulist:
            obj_ids_all = np.char.strip( hdulist['CATALOGUE'].read(columns='OBJ_ID') )#indices of the candidates

    else: sys.exit('"fitsreader" can only be "astropy"/"pyfits" or "fitsio"/"cfitsio".')

    ind_objs = np.in1d(obj_ids_all, obj_list, assume_unique=True).nonzero()[0]

    #::: check if all obj_ids were read out
    for obj_id in obj_list:
        if obj_id not in obj_ids_all[ind_objs]:
            warnings.warn('obj_id '+str(obj_id)+' not found in fits file.')

    #::: truncate the list of obj_ids, remove obj_ids that are not in fits files
    obj_ids = obj_ids_all[ind_objs]
    del obj_ids_all

    return ind_objs, obj_ids



def get_objids_from_indobjs(fnames, ind_objs, fitsreader):

    if fitsreader=='astropy' or fitsreader=='pyfits':
        with pyfits.open(fnames['CATALOGUE'], mode='denywrite') as hdulist:
            obj_ids = hdulist['CATALOGUE'].data['OBJ_ID'][ind_objs].strip() #copy.deepcopy( hdulist['CATALOGUE'].data['OBJ_ID'][ind_objs].strip() )
            del hdulist['CATALOGUE'].data

    elif fitsreader=='fitsio' or fitsreader=='cfitsio':
        with fitsio.FITS(fnames['CATALOGUE'], vstorage='object') as hdulist:
            if isinstance(ind_objs, slice): obj_ids = np.char.strip( hdulist['CATALOGUE'].read(columns='OBJ_ID') ) #copy.deepcopy( hdulist['CATALOGUE'].data['OBJ_ID'][ind_objs].strip() )
            else: obj_ids = np.char.strip( hdulist['CATALOGUE'].read(columns='OBJ_ID', rows=ind_objs) ) #copy.deepcopy( hdulist['CATALOGUE'].data['OBJ_ID'][ind_objs].strip() )

    else: sys.exit('"fitsreader" can only be "astropy"/"pyfits" or "fitsio"/"cfitsio".')

    obj_ids = objid_6digit(obj_ids)


    return obj_ids



def objid_6digit(obj_list):
    for i, obj_id in enumerate(obj_list):
        while len(obj_id)<6:
            obj_id = '0'+obj_id
        obj_list[i] = obj_id

#    formatter = "{:06d}".format
#    map(formatter, obj_list)

    return obj_list




###############################################################################
# Time Input Formatting
###############################################################################

def get_time_inds(fnames, time_index, time_date, time_hjd, time_actionid, fitsreader, silent):

    if time_index is None and time_date is None and time_hjd is None and time_actionid is None:
        ind_time = slice(None)



    elif time_index is not None and time_date is None and time_hjd is None and time_actionid is None:
        # A) test if file
        if isinstance(time_index, str) and os.path.isfile(time_index):
            # load the file
            time_index = np.loadtxt(time_index, dtype='int').tolist()
            # cast to list
            if isinstance(time_index, str):
                time_index = [time_index]

        # B) work with the data

        # if not list, make list
        if not isinstance(time_index, (tuple, list, np.ndarray)):
            ind_time = [time_index]
        else:
            ind_time = time_index



    elif time_index is None and time_date is not None and time_hjd is None and time_actionid is None:

        # A) test if file
        if isinstance(time_date, str) and os.path.isfile(time_date):
            # load the file
            time_date = np.loadtxt(time_date, dtype='S22').tolist()
            # cast to list
            if isinstance(time_date, str):
                time_date = [time_date]

        # B) work with the data
        # a) test if non-empty list
        if isinstance(time_date, (collections.Sequence, np.ndarray)) and not isinstance(time_date, (str, unicode)) and len(time_date) > 0:
            # if list of int or float -> convert to list of str
            if isinstance(time_date[0], (int,float)):
                time_date = map(str, time_date)
            # format if necessary
            if len(time_date[0]) == 8:
                time_date = [ x[0:4]+'-'+x[4:6]+'-'+x[6:] for x in time_date ]
            elif len(time_date[0]) == 10:
                time_date = [ x.replace('/','-') for x in time_date ]
            elif len(time_date[0]) > 10:
                error = '"time_date" format not understood.'
                sys.exit(error)
            # connect to ind_time
            ind_time = get_indtime_from_timedate(fnames, time_date, fitsreader, silent)

        # c) test if int/float
        elif isinstance(time_date, (int, float)):
            # convert to str
            time_date = str(time_date)
            # format
            time_date = time_date[0:4]+'-'+time_date[4:6]+'-'+time_date[6:]
            # connect to ind_time
            ind_time = get_indtime_from_timedate(fnames, time_date, fitsreader, silent)

        # d) test if str
        elif isinstance(time_date, str):

            # if single date, format if necessary
            if len(time_date) == 8:
                time_date = time_date[0:4]+'-'+time_date[4:6]+'-'+time_date[6:]

            # if single date, format if necessary
            elif len(time_date) == 10:
                time_date = time_date.replace('/','-')

            # if dates are given in a range ('20151104:20160101' or '2015-11-04:2016-01-01')
            elif len(time_date) > 10:
                time_date = get_time_date_from_range(time_date)

            else:
                sys.exit('Invalid format of value "time_date". Use e.g. 20151104, "20151104", "2015-11-04" or a textfile name like "dates.txt".')

            # connect to ind_time
            ind_time = get_indtime_from_timedate(fnames, time_date, fitsreader, silent)



    elif time_index is None and time_date is None and time_hjd is not None and time_actionid is None:

        # A) test if file
        if isinstance(time_hjd, str) and os.path.isfile(time_hjd):
            # load the file
            time_hjd = np.loadtxt(time_hjd, dtype='int').tolist()
            # cast to list
            if isinstance(time_hjd, str):
                time_hjd = [time_hjd]

        # B) work with the data
        # a) test if non-empty list
        if isinstance(time_hjd, (collections.Sequence, np.ndarray)) and not isinstance(time_hjd, (str, unicode)) and len(time_hjd) > 0:
            # if list of str or float -> convert to list of int
            if isinstance(time_hjd[0], (str,float)):
                time_hjd = map(int, time_hjd)
            # connect obj_ids to ind_objs
            ind_time = get_indtime_from_timehjd(fnames, time_hjd, fitsreader, silent)

       # b) test if str/int/float
        if isinstance(time_hjd, (str, int, float)):
            time_hjd = int(time_hjd)
            ind_time = get_indtime_from_timehjd(fnames, time_hjd, fitsreader, silent)



    elif time_index is None and time_date is None and time_hjd is None and time_actionid is not None:

       # A) test if file
        if isinstance(time_actionid, str) and os.path.isfile(time_actionid):
            # load the file
            time_actionid = np.loadtxt(time_actionid, dtype='S13').tolist()

        # B) work with the data
        # a) test if non-empty list
        if isinstance(time_actionid, (collections.Sequence, np.ndarray)) and not isinstance(time_actionid, (str, unicode)) and len(time_actionid) > 0:
            # if list of str or float -> convert to list of int
            if isinstance(time_actionid[0], (str,float)):
                time_actionid = map(int, time_actionid)
            # connect to ind_time
            ind_time = get_indtime_from_timeactionid(fnames, time_actionid, fitsreader)

        # c) test if int/float
        elif isinstance(time_actionid, (int, float)):
            # convert to int
            time_actionid = int(time_actionid)
            # connect to ind_time
            ind_time = get_indtime_from_timeactionid(fnames, time_actionid, fitsreader)

        # d) test if str
        elif isinstance(time_actionid, str):

            # if single actioniod, convert to int
            if len(time_actionid) == 6:
                time_actionid = int(time_actionid)

            # if actionids are given in a range ('108583:108600')
            elif len(time_actionid) > 6:
                time_actionid = get_time_actionid_from_range(time_actionid)

            # connect to ind_time
            ind_time = get_indtime_from_timeactionid(fnames, time_actionid, fitsreader)

    else:
        error = 'Only use either "time_index" or "time_date" or "time_hjd" or "time_actionid".'
        sys.exit(error)

    return ind_time



def get_indtime_from_timedate(fnames, time_date, fitsreader):


    # if not list, make list
    if not isinstance(time_date, (tuple, list, np.ndarray)):
        time_date = [time_date]


    if fitsreader=='astropy' or fitsreader=='pyfits':
        with pyfits.open(fnames['IMAGELIST'], mode='denywrite') as hdulist:
            time_date_all = hdulist['IMAGELIST'].data['DATE-OBS'].strip()
            del hdulist['IMAGELIST'].data

    elif fitsreader=='fitsio' or fitsreader=='cfitsio':
        with fitsio.FITS(fnames['IMAGELIST'], vstorage='object') as hdulist:
            time_date_all = np.char.strip( hdulist['IMAGELIST'].read(columns='DATE-OBS') )

    else: sys.exit('"fitsreader" can only be "astropy"/"pyfits" or "fitsio"/"cfitsio".')

    ind_time = np.in1d(time_date_all, time_date).nonzero()[0]


    #::: check if all dates were found in fits file
    for date in time_date:
        if date not in time_date_all[ind_time]:
            warnings.warn('Date '+ date +' not found in fits file.')

    #::: clean up
    del time_date_all


    return ind_time



def get_indtime_from_timehjd(fnames, time_hjd, fitsreader, silent):

    # if not list, make list
    if not isinstance(time_hjd, (tuple, list, np.ndarray)):
        time_hjd = [time_hjd]


    if fitsreader=='astropy' or fitsreader=='pyfits':
        with pyfits.open(fnames['IMAGELIST'], mode='denywrite') as hdulist:
            time_hjd_all = np.int64( hdulist['HJD'].data[0]/3600./24. )
            del hdulist['IMAGELIST'].data

    elif fitsreader=='fitsio' or fitsreader=='cfitsio':
        with fitsio.FITS(fnames['IMAGELIST'], vstorage='object') as hdulist:
            time_hjd_all = np.int64( hdulist['HJD'][0,:]/3600./24. )[0]

    else: sys.exit('"fitsreader" can only be "astropy"/"pyfits" or "fitsio"/"cfitsio".')

    ind_time = np.in1d(time_hjd_all, time_hjd).nonzero()[0]


    #::: check if all dates were found in fits file
    for hjd in time_hjd:
        if hjd not in time_hjd_all[ind_time]:
            if silent is False:
                warnings.warn('Date-HJD '+ str(hjd) +' not found in fits file.')
            else:
                warnings.warn('One ore more Date-HJDs not found in fits file.')
                break

    #::: clean up
    del time_hjd_all


    return ind_time



def get_indtime_from_timeactionid(fnames, time_actionid, fitsreader):

    # if not list, make list
    if not isinstance(time_actionid, (tuple, list, np.ndarray)):
        time_actionid = [time_actionid]


    if fitsreader=='astropy' or fitsreader=='pyfits':
        with pyfits.open(fnames['IMAGELIST'], mode='denywrite') as hdulist:
            time_actionid_all = hdulist['IMAGELIST'].data['ACTIONID']
            del hdulist['IMAGELIST'].data

    elif fitsreader=='fitsio' or fitsreader=='cfitsio':
        with fitsio.FITS(fnames['IMAGELIST'], vstorage='object') as hdulist:
            time_actionid_all = hdulist['IMAGELIST'].read(columns='ACTIONID')

    else: sys.exit('"fitsreader" can only be "astropy"/"pyfits" or "fitsio"/"cfitsio".')

    ind_time = np.in1d(time_actionid_all, time_actionid).nonzero()[0]


    for actionid in time_actionid:
        if actionid not in time_actionid_all[ind_time]:
            warnings.warn('Action-ID '+ str(actionid) +' not found in fits file.')

    del time_actionid_all

    return ind_time



# mother
def get_time_date_from_range(date_range):
    start_date, end_date = solve_range(date_range)

    time_date = []
    start_date, end_date = format_date(start_date, end_date)
    for bufdate in perdelta(start_date, end_date, datetime.timedelta(days=1)):
        time_date.append(bufdate.strftime("%Y-%m-%d"))

    return time_date



# daughter of get_time_date_from_range(date_range)
def format_date(start_date, end_date):
    if isinstance(start_date, int):
        start_date = str(start_date)

    if isinstance(start_date, str):
        if len(start_date) == 8:
            start_date = datetime.datetime.strptime(str(start_date), '%Y%m%d')
        elif len(start_date) == 10:
            start_date.replace('/','-')
            start_date = datetime.datetime.strptime(str(start_date), '%Y-%m-%d')

    if isinstance(end_date, int):
        end_date = str(end_date)

    if isinstance(end_date, str):
        if len(end_date) == 8:
            end_date = datetime.datetime.strptime(str(end_date), '%Y%m%d')
        elif len(end_date) == 10:
            end_date = end_date.replace('/','-')
            end_date = datetime.datetime.strptime(str(end_date), '%Y-%m-%d')

    return start_date, end_date



# daughter of get_time_date_from_range(date_range)
def perdelta(start, end, delta):
    curr = start
    while curr < end:
        yield curr
        curr += delta



# daughter of
# 1) get_time_date_from_range(date_range)
# 2) get_time_actionid_from_range(actionid_range)
def solve_range(date_range):
    # input:
    # 1) '20151104:20160101' or '2015-11-04:2016-01-01'
    # 2) '108583:108600'
    try:
        start_date, end_date = date_range.split(':')
    except:
        sys.exit('"time_date" data type not understood.')
    return start_date, end_date



# mother
def get_time_actionid_from_range(actionid_range):
    start_actionid, end_actionid = solve_range(actionid_range)
    start_actionid = int(start_actionid)
    end_actionid = int(end_actionid)

    time_actionid = range(start_actionid, end_actionid+1)

    return time_actionid



###############################################################################
# get dictionary with fitsio/pyfits getters
###############################################################################
def get_data(fnames, obj_ids, ind_objs, keys, bls_rank, ind_time, fitsreader):

    #::: check keys
    if isinstance (keys, str): keys = [keys]

    #::: check ind_objs
    if not isinstance(ind_objs, slice) and len(ind_objs) == 0:
        warnings.warn('None of the given objects found in the fits files. Return empty dictionary.')
        dic = {}

    elif not isinstance(ind_time, slice) and len(ind_time) == 0:
        warnings.warn('None of the given objects found in the fits files. Return empty dictionary.')
        dic = {}

    else:

        # in case OBJ_IDs was not part of the keys, add it to have array sizes/indices that are always confirm with the nightly fits files
#        dont_save_obj_id = False
        if 'OBJ_ID' not in keys:
#            dont_save_obj_id = True
            keys.append('OBJ_ID')


        if fitsreader=='astropy' or fitsreader=='pyfits': dic = pyfits_get_data(fnames, obj_ids, ind_objs, keys, bls_rank, ind_time=ind_time)
        elif fitsreader=='fitsio' or fitsreader=='cfitsio': dic = fitsio_get_data(fnames, obj_ids, ind_objs, keys, bls_rank, ind_time=ind_time)
        else: sys.exit('"fitsreader" can only be "astropy"/"pyfits" or "fitsio"/"cfitsio".')

        dic = get_canvas_data( fnames, keys, dic )


        #TODO: make clear that from now on OBJ_IDs is always part of the dictionary!
        # in case OBJ_IDs was not part of the keys, remove it again
#        if dont_save_obj_id == True:
#            del dic['OBJ_ID']
#            keys.remove('OBJ_ID')


        #TODO: read out dimensions
#        if not isinstance(ind_objs, slice):
#            dic['N_objects'] = np.array( [len(ind_objs)] )
#        else:
#            dic['N_objects'] = np.array( [np.nan] )
#
#        if not isinstance(ind_time, slice):
#            dic['N_times'] = np.array( [len(ind_time)] )
#        else:
#            dic['N_times'] = np.array( [np.nan] )


    return dic, keys



###############################################################################
# pyfits getter
###############################################################################


def pyfits_get_data(fnames, obj_ids, ind_objs, keys, bls_rank, ind_time=slice(None), CCD_bzero=0., CCD_precision=32., CENTD_bzero=0., CENTD_precision=1024.):

    dic = {}

    ###################### in pipeline: BLSPipe_megafile #####################
    if 'BLSPipe_megafile' in fnames:

        with pyfits.open(fnames['BLSPipe_megafile'], mode='denywrite') as hdulist:

            #::: CATALOGUE
            hdukey = 'CATALOGUE'
            hdu = hdulist[hdukey].data
            for key in np.intersect1d(hdu.names, keys):
                dic[key] = hdu[key][ind_objs] #copy.deepcopy( hdu[key][ind_objs] )
            del hdu, hdulist[hdukey].data

            #::: IMAGELIST
            hdukey = 'IMAGELIST'
            hdu = hdulist[hdukey].data
            for key in np.intersect1d(hdu.names, keys):
                dic[key] = hdu[key][ind_time] #copy.deepcopy( hdu[key][ind_time] )
            del hdu, hdulist[hdukey].data

            #::: DATA HDUs
            for _, hdukeyinfo in enumerate(hdulist.info(output=False)):
                hdukey = hdukeyinfo[1]
                if hdukey in keys:
                    key = hdukey
                    dic[key] = hdulist[key].data[ind_objs][:,ind_time] #copy.deepcopy( hdulist[key].data[ind_objs][:,ind_time] )
                    if key in ['CCDX','CCDY']:
                        dic[key] = (dic[key] + CCD_bzero) / CCD_precision
                    if key in ['CENTDX','CENTDX_ERR','CENTDY','CENTDY_ERR']:
                        dic[key] = (dic[key] + CENTD_bzero) / CENTD_precision
                    del hdulist[key].data

            del hdulist


    ##################### final data prodcuts: prodstore/0*/  #####################
    elif ('nights' in fnames) and (fnames['nights'] is not None):

        #::: CATALOGUE
        with pyfits.open(fnames['CATALOGUE'], mode='denywrite') as hdulist:
            hdukey = 'CATALOGUE'
            hdu = hdulist[hdukey].data
            for key in np.intersect1d(hdu.names, keys):
                dic[key] = hdu[key][ind_objs] #copy.deepcopy( hdu[key][ind_objs] )
            del hdu, hdulist[hdukey].data, hdulist

        #::: IMAGELIST
        with pyfits.open(fnames['IMAGELIST'], mode='denywrite') as hdulist:
            hdukey = 'IMAGELIST'
            hdu = hdulist[hdukey].data
            for key in np.intersect1d(hdu.names, keys):
                dic[key] = hdu[key][ind_time] #copy.deepcopy( hdu[key][ind_time] )
            del hdu, hdulist[hdukey].data, hdulist

        #::: DATA HDUs
        for key in keys:
            if key in fnames:
                with pyfits.open(fnames[key], mode='denywrite') as hdulist:
                    dic[key] = hdulist[key].data[ind_objs][:,ind_time] #copy.deepcopy( hdulist[key].data[ind_objs][:,ind_time] )
                    if key in ['CCDX','CCDY']:
                        dic[key] = (dic[key] + CCD_bzero) / CCD_precision
                    if key in ['CENTDX','CENTDX_ERR','CENTDY','CENTDY_ERR']:
                        dic[key] = (dic[key] + CENTD_bzero) / CENTD_precision
                    del hdulist[key].data, hdulist



    if ('sysrem' in fnames) and (fnames['sysrem'] is not None):
        with pyfits.open(fnames['sysrem'], mode='denywrite') as hdulist_sysrem:
            for i, hdukey in enumerate(hdulist_sysrem.info(output=False)):
                if hdukey[1] in keys:
                    key = hdukey[1]
                    dic[key] = hdulist_sysrem[key].data[ind_objs][:,ind_time] #copy.deepcopy( hdulist_sysrem[key].data[ind_objs][:,ind_time] )#in s
                    del hdulist_sysrem[key].data

            del hdulist_sysrem



    if ('bls' in fnames) and (fnames['bls'] is not None):
        with pyfits.open(fnames['bls'], mode='denywrite') as hdulist_bls:

            #first little hack: transform from S26 into S6 dtype with .astype('|S6') or .strip()!
            #second little hack: only choose rank 1 output (5 ranks output by orion into the fits files, in 5 subsequent rows)
            ind_objs_bls = np.in1d(hdulist_bls['CANDIDATES'].data['OBJ_ID'].strip(), obj_ids).nonzero()[0] #indices of the candidates
            ind_rank1 = np.where( hdulist_bls['CANDIDATES'].data['RANK'] == bls_rank )[0]
            ind_objs_bls = np.intersect1d( ind_objs_bls, ind_rank1 )


            #::: CATALOGUE
            hdukey = 'CATALOGUE'
            hdu = hdulist_bls[hdukey].data
            for key in np.intersect1d(hdu.names, keys):
                if key!='OBJ_ID':
                    dic[key] = hdu[key][ind_objs] #copy.deepcopy( hdu[key][ind_objs] )
            del hdu, hdulist_bls[hdukey].data


            #::: CANDIDATES (different indices!)
            hdukey = 'CANDIDATES'
            hdu = hdulist_bls[hdukey].data
            subkeys = np.intersect1d(hdu.names, keys)
            N_objs = len(dic['OBJ_ID'])
            # EXCLUDE OBJ_IDs from subkeys
            if 'OBJ_ID' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='OBJ_ID'))
            if 'FLAGS' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='FLAGS'))
            if 'SIGMA_XS' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='SIGMA_XS'))

            if subkeys.size!=0:
                # see if any BLS candidates are in the list
                if len(ind_objs_bls)!=0:
                    bls_data_objid = np.char.strip( hdu['OBJ_ID'][ind_objs_bls] )

                    # go through all subkeys
                    for key in subkeys:
                        # read out data for this key
                        bls_data = hdu[key][ind_objs_bls]

                        # write them at the right place into the dictionary
                        # initialize empty dictionary entry, size of all requested ind_objs
                        dic[key] = np.zeros( N_objs ) * np.nan
                        # go through all requested obj_ids
                        for i, singleobj_id in enumerate(obj_ids):
                            if singleobj_id in bls_data_objid:
                                i_bls = np.where( bls_data_objid == singleobj_id )[0]
                                dic[key][i] = bls_data[i_bls]
                else:
                    # go through all subkeys
                    for key in subkeys:
                        # initialize empty dictionary entry, size of all requested ind_objs
                        dic[key] = np.zeros( N_objs )



    if ('decorr' in fnames) and (fnames['decorr'] is not None):
        with pyfits.open(fnames['decorr'], mode='denywrite') as hdulist_sysrem:
            for i, hdukey in enumerate(hdulist_sysrem.info(output=False)):
                if hdukey[1] in keys:
                    key = hdukey[1]
                    dic[key] = hdulist_sysrem[key].data[ind_objs][:,ind_time] #copy.deepcopy( hdulist_sysrem[key].data[ind_objs][:,ind_time] )#in s
                    del hdulist_sysrem[key].data

            del hdulist_sysrem



    ##################### fnames['dilution'] #####################
    '''
    dilution fits files contain all object IDs as in the nightly fits files
    row indices in the fits file consequently match
    '''

    if ('dilution' in fnames) and (fnames['dilution'] is not None):
        with pyfits.open(fnames['dilution'], mode='denywrite') as hdulist_dil:
            hdukey = 1
            hdu = hdulist_dil[hdukey].data
            hdunames = hdu.names

            dilkeys = [ x.lower() for x in keys ]
            subkeys = np.intersect1d(hdunames, dilkeys)
            if 'OBJ_ID' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='OBJ_ID'))
            if 'obj_id' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='obj_id'))
#
            if subkeys.size!=0:
                for key in subkeys:
                    dic[key.upper()] = hdu[key][ind_objs]

            del hdulist_dil

    ##################### fnames['sysrem_im'] #####################
    '''
    sysrem imagelist fits contains additional metadata on a per image basis
    '''

    if ('sysrem_im' in fnames) and (fnames['sysrem_im'] is not None):
    	with pyfits.open(fnames['sysrem_im'], mode='denywrite') as hdulist_sysrem_im:
    		hdu = hdulist_sysrem_im[1].data
    		for key in np.intersect1d(hdu.names, keys):
    			dic[key] = hdu[key][ind_name]
    		del hdu, hdulist_sysrem_im[1].data, hdulist_sysrem_im


    #::: output as numpy ndarrays
    for key, value in dic.items():
        dic[key] = np.array(value)


    return dic




###############################################################################
# fitsio getter
###############################################################################
def fitsio_get_data(fnames, obj_ids, ind_objs, keys, bls_rank, ind_time=slice(None), CCD_bzero=0., CCD_precision=32., CENTD_bzero=0., CENTD_precision=1024.):

    dic = {}

    ###################### in pipeline: BLSPipe_megafile #####################
    if ('BLSPipe_megafile' in fnames) and (fnames['BLSPipe_megafile'] is not None):

        with fitsio.FITS(fnames['nights'], vstorage='object') as hdulist:

            #::: fitsio does not work with slice arguments, convert to list
            allobjects = False
            if isinstance (ind_objs, slice):
                N_objs = int( hdulist['CATALOGUE'].get_nrows() )
                ind_objs = range(N_objs)
                allobjects = True

            if isinstance (ind_time, slice):
                N_time = int( hdulist['IMAGELIST'].get_nrows() )
                ind_time = range(N_time)


            #::: CATALOGUE
            hdukey = 'CATALOGUE'
            hdunames = hdulist[hdukey].get_colnames()
            subkeys = np.intersect1d(hdunames, keys)
            if subkeys.size!=0:
                data = hdulist[hdukey].read(columns=subkeys, rows=ind_objs)
                if isinstance(subkeys, str): subkeys = [subkeys]
                for key in subkeys:
                    dic[key] = data[key] #copy.deepcopy( data[key] )
                del data

            #::: IMAGELIST
            hdukey = 'IMAGELIST'
            hdunames = hdulist[hdukey].get_colnames()
            subkeys = np.intersect1d(hdunames, keys)
            if subkeys.size!=0:
                data = hdulist[hdukey].read(columns=subkeys, rows=ind_time)
                if isinstance(subkeys, str): subkeys = [subkeys]
                for key in subkeys:
                    dic[key] = data[key] #copy.deepcopy( data[key] )
                del data

            # TODO: very inefficient - reads out entire image first, then cuts
            # TODO: can only give ind_time in a slice, not just respective dates
            #::: DATA HDUs
            j = 0
            while j!=-1:
                try:
                    hdukey = hdulist[j].get_extname()
                    if hdukey in keys:
                        key = hdukey

                        #::: read out individual objects (more memory efficient)
                        if allobjects == False:
                            dic[key] = np.zeros(( len(ind_objs), len(ind_time) ))
                            for i, ind_singleobj in enumerate(ind_objs):
                                buf = hdulist[hdukey][slice(ind_singleobj,ind_singleobj+1), slice( ind_time[0], ind_time[-1]+1)]
                                #::: select the wished times only (if some times within the slice are not wished for)
                                if buf.shape[1] != len(ind_time):
                                    ind_timeX = [x - ind_time[0] for x in ind_time]
                                    buf = buf[:,ind_timeX]
                                dic[key][i,:] = buf
                            del buf

                        #::: read out all objects at once
                        else:
                            buf = hdulist[hdukey][:, slice( ind_time[0], ind_time[-1]+1)]
                            if buf.shape[1] != len(ind_time):
                                ind_timeX = [x - ind_time[0] for x in ind_time]
                                buf = buf[:,ind_timeX]
                            dic[key] = buf
                            del buf

                        if key in ['CCDX','CCDY']:
                            dic[key] = (dic[key] + CCD_bzero) / CCD_precision
                        if key in ['CENTDX','CENTDX_ERR','CENTDY','CENTDY_ERR']:
                            dic[key] = (dic[key] + CENTD_bzero) / CENTD_precision
                    j += 1
                except:
                    break



    ##################### final data prodcuts: prodstore/0*/  #####################
    elif ('nights' in fnames) and (fnames['nights'] is not None):

            #::: CATALOGUE
            with fitsio.FITS(fnames['CATALOGUE'], vstorage='object') as hdulist:

                #::: fitsio does not work with slice arguments, convert to list
                allobjects = False
                if isinstance (ind_objs, slice):
                    N_objs = int( hdulist['CATALOGUE'].get_nrows() )
                    ind_objs = range(N_objs)
                    allobjects = True

                hdukey = 'CATALOGUE'
                hdunames = hdulist[hdukey].get_colnames()
                subkeys = np.intersect1d(hdunames, keys)
                if subkeys.size!=0:
                    data = hdulist[hdukey].read(columns=subkeys, rows=ind_objs)
                    if isinstance(subkeys, str): subkeys = [subkeys]
                    for key in subkeys:
                        dic[key] = data[key] #copy.deepcopy( data[key] )
                    del data

            #::: IMAGELIST
            with fitsio.FITS(fnames['IMAGELIST'], vstorage='object') as hdulist:

                #::: fitsio does not work with slice arguments, convert to list
                if isinstance (ind_time, slice):
                    N_time = int( hdulist['IMAGELIST'].get_nrows() )
                    ind_time = range(N_time)

                hdukey = 'IMAGELIST'
                hdunames = hdulist[hdukey].get_colnames()
                subkeys = np.intersect1d(hdunames, keys)
                if subkeys.size!=0:
                    data = hdulist[hdukey].read(columns=subkeys, rows=ind_time)
                    if isinstance(subkeys, str): subkeys = [subkeys]
                    for key in subkeys:
                        dic[key] = data[key] #copy.deepcopy( data[key] )
                    del data

            #::: DATA HDUs
            for key in keys:
                if (key in fnames) and (fnames[key] is not None):
                    with fitsio.FITS(fnames[key], vstorage='object') as hdulist:

                        hdukey = hdulist[0].get_extname()
                        if hdukey in keys:

                            #::: read out individual objects (more memory efficient)
                            if allobjects == False:
                                dic[key] = np.zeros(( len(ind_objs), len(ind_time) ))
                                for i, ind_singleobj in enumerate(ind_objs):
                                    buf = hdulist[hdukey][slice(ind_singleobj,ind_singleobj+1), slice( ind_time[0], ind_time[-1]+1)]
                                    #::: select the wished times only (if some times within the slice are not wished for)
                                    if buf.shape[1] != len(ind_time):
                                        ind_timeX = [x - ind_time[0] for x in ind_time]
                                        buf = buf[:,ind_timeX]
                                    dic[key][i,:] = buf
                                del buf

                            #::: read out all objects at once
                            else:
                                buf = hdulist[hdukey][:, slice( ind_time[0], ind_time[-1]+1)]
                                if buf.shape[1] != len(ind_time):
                                    ind_timeX = [x - ind_time[0] for x in ind_time]
                                    buf = buf[:,ind_timeX]
                                dic[key] = buf
                                del buf

                            if key in ['CCDX','CCDY']:
                                dic[key] = (dic[key] + CCD_bzero) / CCD_precision
                            if key in ['CENTDX','CENTDX_ERR','CENTDY','CENTDY_ERR']:
                                dic[key] = (dic[key] + CENTD_bzero) / CENTD_precision



    if ('sysrem' in fnames) and (fnames['sysrem'] is not None):
        with fitsio.FITS(fnames['sysrem'], vstorage='object') as hdulist_sysrem:
            j = 0
            while j!=-1:
                try:
                    hdukey = hdulist_sysrem[j].get_extname()
                    if hdukey in keys:
                        key = hdukey

                        #::: read out individual objects (more memory efficient)
                        if allobjects == False:
                            dic[key] = np.zeros(( len(ind_objs), len(ind_time) ))
                            for i, ind_singleobj in enumerate(ind_objs):
                                buf = hdulist_sysrem[hdukey][slice(ind_singleobj,ind_singleobj+1), slice( ind_time[0], ind_time[-1]+1)]
                                #::: select the wished times only (if some times within the slice are not wished for)
                                if buf.shape[1] != len(ind_time):
                                    ind_timeX = [x - ind_time[0] for x in ind_time]
                                    buf = buf[:,ind_timeX]
                                dic[key][i,:] = buf
                            del buf

                        #::: read out all objects at once
                        else:
                            buf = hdulist_sysrem[hdukey][:, slice( ind_time[0], ind_time[-1]+1)]
                            if buf.shape[1] != len(ind_time):
                                ind_timeX = [x - ind_time[0] for x in ind_time]
                                buf = buf[:,ind_timeX]
                            dic[key] = buf
                            del buf
                    j += 1
                except:
                    break



    if ('bls' in fnames) and (fnames['bls'] is not None):
        with fitsio.FITS(fnames['bls'], vstorage='object') as hdulist_bls:

            #first little hack: transform from S26 into S6 dtype with .astype('|S6') or .strip()!
            #second little hack: only choose rank 1 output (5 ranks output by orion into the fits files, in 5 subsequent rows)
            ind_objs_bls = np.in1d( np.char.strip(hdulist_bls['CANDIDATES'].read(columns='OBJ_ID')), obj_ids).nonzero()[0] #indices of the candidates
            ind_rank1 = np.where( hdulist_bls['CANDIDATES'].read(columns='RANK') == bls_rank )[0]
            ind_objs_bls = np.intersect1d( ind_objs_bls, ind_rank1 ) #indices of the objects in the BLS file


            #::: CATALOGUE
            hdukey = 'CATALOGUE'
            hdunames = hdulist_bls[hdukey].get_colnames()
            subkeys = np.intersect1d(hdunames, keys)
            # EXCLUDE OBJ_IDs from subkeys
            if 'OBJ_ID' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='OBJ_ID'))
            if 'FLAGS' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='FLAGS'))

            if subkeys.size!=0:
                data = hdulist_bls[hdukey].read(columns=subkeys, rows=ind_objs)
                if isinstance(subkeys, str): subkeys = [subkeys]
                for key in subkeys:
                    dic[key] = data[key] #copy.deepcopy( data[key] )
                del data


            #::: CANDIDATES (different indices!)
            hdukey = 'CANDIDATES'
            hdunames = hdulist_bls[hdukey].get_colnames()
            subkeys = np.intersect1d(hdunames, keys)
            # EXCLUDE OBJ_IDs from subkeys
            if 'OBJ_ID' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='OBJ_ID'))
            if 'FLAGS' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='FLAGS'))

            if subkeys.size!=0:

                # see if any BLS candidates are in the list
                if len(ind_objs_bls)!=0:

                    # Now, for this one, again INCLUDE OBJ_IDs in subkeys (as last subkey)
                    if 'OBJ_ID' not in subkeys: subkeys = np.append(subkeys, 'OBJ_ID')

                    bls_data = hdulist_bls[hdukey].read(columns=subkeys, rows=ind_objs_bls)
                # write them at the right place into the dictionary
                    # EXCLUDE OBJ_IDs from subkeys
                    if 'OBJ_ID' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='OBJ_ID'))
                    #typecast to list if needed
                    if isinstance(subkeys, str): subkeys = [subkeys]
                    # go through all subkeys
                    for key in subkeys:
                        # initialize empty dictionary entry, size of all requested ind_objs
                        dic[key] = np.zeros( len(ind_objs) ) * np.nan
                        #go through all requested obj_ids
                        for i, singleobj_id in enumerate(obj_ids):
                            if singleobj_id in np.char.strip(bls_data['OBJ_ID']):
                                i_bls = np.where( np.char.strip(bls_data['OBJ_ID']) == singleobj_id )
                                dic[key][i] = bls_data[key][i_bls]

                else:
                    # go through all subkeys
                    for key in subkeys:
                        # initialize empty dictionary entry, size of all requested ind_objs
                        dic[key] = np.zeros( len(ind_objs) ) * np.nan



    if ('decorr' in fnames) and (fnames['decorr'] is not None):
        '''
        Note: the extension name in the .fits for DECORR_FLUX3 is DECORR_FLUX (without 3), that's why I needed to put a little hack and do +'3'
        '''
        with fitsio.FITS(fnames['decorr'], vstorage='object') as hdulist_sysrem:
            j = 0
            while j!=-1:
                try:
                    hdukey = hdulist_sysrem[j].get_extname()
                    if hdukey + '3' in keys: #little hack because of inconsistent extname convention
                        key = hdukey + '3' #little hack because of inconsistent extname convention

                        #::: read out individual objects (more memory efficient)
                        if allobjects == False:
                            dic[key] = np.zeros(( len(ind_objs), len(ind_time) ))
                            for i, ind_singleobj in enumerate(ind_objs):
                                buf = hdulist_sysrem[hdukey][slice(ind_singleobj,ind_singleobj+1), slice( ind_time[0], ind_time[-1]+1)]
                                #::: select the wished times only (if some times within the slice are not wished for)
                                if buf.shape[1] != len(ind_time):
                                    ind_timeX = [x - ind_time[0] for x in ind_time]
                                    buf = buf[:,ind_timeX]
                                dic[key][i,:] = buf
                            del buf

                        #::: read out all objects at once
                        else:
                            buf = hdulist_sysrem[hdukey][:, slice( ind_time[0], ind_time[-1]+1)]
                            if buf.shape[1] != len(ind_time):
                                ind_timeX = [x - ind_time[0] for x in ind_time]
                                buf = buf[:,ind_timeX]
                            dic[key] = buf
                            del buf
                    j += 1
                except:
                    break


    ##################### fnames['dilution'] #####################
    '''
    dilution fits files contain all object IDs as in the nightly fits files
    row indices in the fits file consequently match
    '''

    if ('dilution' in fnames) and (fnames['dilution'] is not None):
        with fitsio.FITS(fnames['dilution'], vstorage='object') as hdulist_dil:
            hdukey = 1
            hdunames = hdulist_dil[hdukey].get_colnames()

            dilkeys = [ x.lower() for x in keys ]
            subkeys = np.intersect1d(hdunames, dilkeys)
            if 'OBJ_ID' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='OBJ_ID'))
            if 'obj_id' in subkeys: subkeys = np.delete(subkeys, np.where(subkeys=='obj_id'))
#
            if subkeys.size!=0:
                dil_data = hdulist_dil[hdukey].read(columns=np.append(subkeys, 'obj_id'), rows=ind_objs)
                for key in subkeys:
                    dic[key.upper()] = dil_data[key]

            del hdulist_dil

    ##################### fnames['sysrem_im'] #####################
    '''
    sysrem imagelist fits contains additional metadata on a per image basis
    '''

    if ('sysrem_im' in fnames) and (fnames['sysrem_im'] is not None):
    	with fitsio.FITS(fnames['sysrem_im'], vstorage='object') as hdulist_sysrem_im:
    		hdunames = hdulist_sysrem_im[1].get_colnames()
    		subkeys = np.intersect1d(hdunames, keys)
    		if "FLAGS" in subkeys:
    			subkeys = np.delete(subkeys, np.where(subkeys=="FLAGS"))
    		if subkeys.size!=0:
    			data = hdulist_sysrem_im[1].read(columns=subkeys, rows=ind_time)
    			if isinstance(subkeys, str): subkeys = [subkeys]
    			for key in subkeys:
    				dic[key] = data[key]
    				del data

    return dic




###############################################################################
# Get CANVAS data
###############################################################################
def get_canvas_data( fnames, keys, dic ):
    if ('canvas' in fnames) and (fnames['canvas'] is not None):
        #::: load canvasdata
        canvasdata = np.genfromtxt(fnames['canvas'], dtype=None, names=True)
        canvas_obj_ids = objid_6digit( canvasdata['OBJ_ID'].astype('|S6') )
        #::: cycle through all canvaskeys
        for canvaskey in canvasdata.dtype.names:
            #::: if canvaskey is requested
            if ('CANVAS_' + canvaskey) in keys:
                #::: initialize dic nan-array
                dic[ 'CANVAS_' + canvaskey ] = np.zeros( len(dic['OBJ_ID']) ) * np.nan

                #::: crossmatch objects
                for i, obj_id in enumerate( dic['OBJ_ID'] ):
                    if obj_id in canvas_obj_ids:
                        dic[ 'CANVAS_' + canvaskey ][i] = canvasdata[canvaskey][ canvas_obj_ids == obj_id ]

                #:: rescale period (given in days in canvas)
                if ('CANVAS_' + canvaskey) == 'CANVAS_PERIOD':
                     dic[ 'CANVAS_' + canvaskey ] *= 24.*3600. #reconvert into s

                #::: rescale width (given as fraction of period in canvas)
                if ('CANVAS_' + canvaskey) == 'CANVAS_WIDTH':
                    for i, obj_id in enumerate( dic['OBJ_ID'] ):
                        if obj_id in canvas_obj_ids:
                            dic[ 'CANVAS_WIDTH' ][i] = ( canvasdata['WIDTH'][ canvas_obj_ids == obj_id ] * canvasdata['PERIOD'][ canvas_obj_ids == obj_id ] ) *24.*3600.

    return dic



###############################################################################
# Simplify output if only one object is retrieved
###############################################################################
def simplify_dic(dic):

    for key, value in dic.items():
        if value.shape[0] == 1:
            dic[key] = value[0]
        elif (len(value.shape) > 1) and (value.shape[1] == 1):
            dic[key] = value[:,0]

    return dic



###############################################################################
# Set flagged values to nan
###############################################################################
def set_nan_dic(dic):
    if len(dic['OBJ_ID']) == 1:
        dic = set_nan_single(dic)
    elif len(dic['OBJ_ID']) > 1:
        dic = set_nan_multi(dic)
    return dic


#::: if only 1 object is contained in dic
def set_nan_single(dic):
    ###### REMOVE BROKEN ITEMS #######
    #::: nan
    ind_broken = np.where( dic['FLAGS'] > 0 ) #(dic[key] == 0.) |
#    if key in dic: dic[key][ind_broken] = np.nan
#    dic['HJD'][ind_broken] = np.nan #this is not allowed to be set to nan!!! Otherwise the binning will be messed up!!!
    for key in ['FLUX','FLUX_ERR','FLUX3','FLUX3_ERR',
                'FLUX4','FLUX4_ERR','FLUX5','FLUX5_ERR',
                'SYSREM_FLUX3','SYSREM_FLUX3_ERR',
                'DECORR_FLUX3','DECORR_FLUX3_ERR',
                'CCDX','CCDX_ERR','CCDY','CCDY_ERR',
                'CENTDX','CENTDX_ERR','CENTDY','CENTDY_ERR']:
        if key in dic:
            dic[key][ind_broken] = np.nan
    return dic


#::: if multiple objects are contained in dic
def set_nan_multi(dic):
    ###### REMOVE BROKEN ITEMS #######
    #::: nan
    N_obj = dic['FLAGS'].shape[0]
    for obj_nr in range(N_obj):
        ind_broken = np.where( dic['FLAGS'][obj_nr] > 0 )
#        if key in dic: dic[key][obj_nr,ind_broken] = np.nan
#    #    dic['HJD'][ind_broken] = np.nan #this is not allowed to be set to nan!!! Otherwise the binning will be messed up!!!
#        if 'CCDX' in dic: dic['CCDX'][obj_nr,ind_broken] = np.nan
#        if 'CCDY' in dic: dic['CCDY'][obj_nr,ind_broken] = np.nan
#        if 'CENTDX' in dic: dic['CENTDX'][obj_nr,ind_broken] = np.nan
#        if 'CENTDY' in dic: dic['CENTDY'][obj_nr,ind_broken] = np.nan
        for key in ['FLUX','FLUX_ERR','FLUX3','FLUX3_ERR',
                'FLUX4','FLUX4_ERR','FLUX5','FLUX5_ERR',
                'SYSREM_FLUX3','SYSREM_FLUX3_ERR',
                'DECORR_FLUX3','DECORR_FLUX3_ERR',
                'CCDX','CCDX_ERR','CCDY','CCDY_ERR',
                'CENTDX','CENTDX_ERR','CENTDY','CENTDY_ERR']:
            if key in dic:
                dic[key][obj_nr,ind_broken] = np.nan
    return dic



###############################################################################
# Check if all keys are retrieved
###############################################################################
def check_dic(dic, keys, silent):

    if not silent: print('###############################################################################')

    fail = False

    for key in keys:
        if key not in dic:
            print('Failure: key',key,'not read into dictionary.')
            fail = True

    if fail == False:
        if not silent: print('Success: All keys successfully read into dictionary.')

    if not silent: print('###############################################################################')

    return



###############################################################################
# MAIN
###############################################################################
if __name__ == '__main__':
    pass

#    import matplotlib.pyplot as plt
#    from pprint import pprint


#    obj_id = '012109'
#    fieldname = 'NG0304-1115'
#    ngts_version = 'CYCLE1706'
#    dic = get(fieldname, ngts_version, ['OBJ_ID', 'FLUX_MEAN', 'RA', 'DEC', 'NIGHT', 'AIRMASS', 'HJD', 'CCDX', 'CCDY', 'CENTDX', 'CENTDY', 'SYSREM_FLUX3', 'PERIOD', 'WIDTH', 'EPOCH', 'DEPTH', 'NUM_TRANSITS'], obj_id=obj_id, time_hjd=None, fnames=None)
#    dic = get(fieldname, ngts_version, ['OBJ_ID'], time_index=0, fnames=None)

#    print get('NULL','NULL',['HJD','SYSREM_FLUX3'],obj_id=7619,fnames={'BLSPipe_megafile':'/Users/mx/Big_Data/BIG_DATA_NGTS/2016/TEST18/NG0304-1115_809_2016_TEST18.fits'})

#    fname = '/Users/mx/Big_Data/BIG_DATA_NGTS/2016/TEST18/NG0304-1115_809_2016_TEST18.fits'
#    dic = get('NULL', 'NULL', ['SYSREM_FLUX3', 'RA', 'DEC', 'CCDX', 'CENTDX', 'DILUTION', 'PERIOD', 'CANVAS_PERIOD'], obj_row=100, fnames={'BLSPipe_megafile':fname})
#    pprint(dic)

#    dic = get( 'NG0304-1115', 'CYCLE1706', ['HJD', 'RA', 'DEC', 'FLUX3_ERR', 'SYSREM_FLUX3', 'DECORR_FLUX3', 'DILUTION', 'PERIOD', 'CANVAS_PERIOD'], obj_row=100, set_nan=True)#, fitsreader='fitsio', time_index=range(1000))
#    pprint(dic)
#    plt.figure()
#    plt.plot(dic['HJD'],dic['FLUX3'],'k.',rasterized=True)
#    plt.plot(dic['HJD'],dic['SYSREM_FLUX3'],'r.',rasterized=True)
#    plt.figure()
#    plt.plot(dic['HJD'],dic['SYSREM_FLUX3']-dic['FLUX3'],'r.',rasterized=True)

#    dic = get( 'NG0409-1941', 'CYCLE1706', ['HJD', 'FLUX3', 'SYSREM_FLUX3', 'DECORR_FLUX3', 'PERIOD', 'EPOCH'], obj_row=4277, set_nan=True)
#    pprint(dic)
#    fig, axes = plt.subplots(4,1, figsize=(6,10))
#    axes[0].plot(dic['HJD'],dic['FLUX3'],'k.',rasterized=True)
#    axes[0].plot(dic['HJD'],dic['SYSREM_FLUX3'],'r.',rasterized=True)
#    axes[0].plot(dic['HJD'],dic['DECORR_FLUX3'],'g.',rasterized=True)
#    axes[1].plot(dic['HJD'],dic['SYSREM_FLUX3']-dic['FLUX3'],'k.',rasterized=True)
#    axes[2].plot(dic['HJD'],dic['DECORR_FLUX3']-dic['FLUX3'],'k.',rasterized=True)
#    axes[3].plot(dic['HJD'],dic['DECORR_FLUX3']-dic['SYSREM_FLUX3'],'k.',rasterized=True)
#    plt.show()


