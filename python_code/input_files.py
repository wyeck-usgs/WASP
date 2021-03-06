# -*- coding: utf-8 -*-
"""Module with routines for writing text files which are necessary inputs for
Chen's fortran scripts.
"""


import os
from obspy import read
from obspy.taup import TauPyModel
import numpy as np
import json
import fault_plane as pf
import management as mng
import plane_management as pl_mng
import seismic_tensor as tensor
import subprocess
import errno
import get_outputs

from obspy.geodetics import kilometers2degrees


################################
# velocity models
################################


def write_velmodel(velmodel):
    """Write velocity model file for fortran scripts

    :param velmodel: dictionary with velocity model information
    :type velmodel: dict
    """
    p_vel = velmodel['p_vel']
    s_vel = velmodel['s_vel']
    dens = velmodel['dens']
    thick = velmodel['thick']
    qa = velmodel['qa']
    qb = velmodel['qb']
    zipped = zip(p_vel, s_vel, dens, thick, qa, qb)
    with open('vel_model', 'w') as outfile:
        outfile.write('{}\n'.format(len(thick)))
        for pv, sv, rho, th, qaa, qbb in zipped:
            outfile.write(
                    '{} {} {} {} {} {}\n'.format(pv, sv, rho, th, qaa, qbb))
    return


################################
# fault plane
################################


def forward_model(tensor_info, segments_data, model, vel0, vel1):
    """Rewrite input file Fault.time with input model

    :param tensor_info: dictionary with moment tensor information
    :param segments: dictionary with information of the fault segments
    :param rise_time: dictionary with rise time function information
    :param model: dictionary with properties of the input kinematic model
    :param vel0: minimum rupture velocity to be used
    :param vel1: maximum rupture velocity to be used
    :type tensor_info: dict
    :type segments: dict
    :type rise_time: dict
    :type model: dict
    :type vel0: float
    :type vel1: float
    """
    slip_segs = model['slip']
    rake_segs = model['rake']
    trup_segs = model['trup']
    tris_segs = model['trise']
    tfall_segs = model['tfall']

    segments = segments_data['segments']
    rise_time = segments_data['rise_time']
    hyp_stk = segments[0]['hyp_stk']
    hyp_dip = segments[0]['hyp_dip']
    delta_strike = segments[0]['delta_strike']
    delta_dip = segments[0]['delta_dip']
    rupture_vel = segments[0]['rupture_vel']
    subfaults = {'delta_strike': delta_strike, 'delta_dip': delta_dip}

    subfaults2 = pf._point_sources_def(rise_time, rupture_vel, subfaults)
    strike_ps = subfaults2['strike_ps']
    dip_ps = subfaults2['dip_ps']
    t1 = rise_time['min_rise']
    t2 = rise_time['delta_rise']
    windows = rise_time['windows']

    depth = tensor_info['depth']

    disp_or_vel = 0
    string = '{} {} {} {} {}\n'

    point_sources0 = pf.point_sources_param(segments, tensor_info, rise_time)
    ny = int(dip_ps / 2)
    nx = int(strike_ps / 2)
    times = [point_sources[:, :, ny, nx, 4] for point_sources in point_sources0]
    trup_segs2 = [rupt_seg - time for time, rupt_seg in zip(times, trup_segs)]

    zipped = zip(segments, slip_segs, rake_segs, trup_segs2, tris_segs, tfall_segs)
    with open('Fault.time', 'w') as outfile:
        outfile.write('{} {} {} 10\n'.format(hyp_stk, hyp_dip, depth))
        outfile.write(
                '{} {} {} {} {} {} {} {} {}\n'.format(
                len(segments), delta_strike, delta_dip, strike_ps, dip_ps,
                vel0, vel1, -100, 100))
        outfile.write('{} {} {} {} {}\n'.format(
                t1, t2, windows, rupture_vel, disp_or_vel))
        for i_segment, (segment, slip_seg, rake_seg, trup_seg, tris_seg, tfall_seg)\
        in enumerate(zipped):
            dip = segment['dip']
            strike = segment['strike']
            n_stk = segment['stk_subfaults']
            n_dip = segment['dip_subfaults']
            outfile.write('{} {} {}\n'.format(i_segment + 1, dip, strike))
            outfile.write('{} {} 0\n'.format(n_stk, n_dip))
            for i in range(n_dip):
                for j in range(n_stk):
                    outfile.write(string.format(
                            slip_seg[i, j], rake_seg[i, j], trup_seg[i, j],
                            tris_seg[i, j], tfall_seg[i, j]))
    return


def plane_for_chen(tensor_info, segments_data, min_vel, max_vel, velmodel):
    """Code to create files Fault.time, Fault.pos and Niu_model

    :param tensor_info: dictionary with moment tensor information
    :param segments: dictionary with information of the fault segments
    :param rise_time: dictionary with rise time function information
    :param min_vel: minimum rupture velocity to be used
    :param max_vel: maximum rupture velocity to be used
    :param velmodel: dictionary with velocity model information
    :type tensor_info: dict
    :type segments: dict
    :type rise_time: dict
    :type velmodel: dict
    :type min_vel: float
    :type max_vel: float
    """
    segments = segments_data['segments']
    rise_time = segments_data['rise_time']
    delta_strike = segments[0]['delta_strike']
    delta_dip = segments[0]['delta_dip']
    rupture_vel = segments[0]['rupture_vel']
    subfaults = {'delta_strike': delta_strike, 'delta_dip': delta_dip}
    subfaults2 = pf._point_sources_def(rise_time, rupture_vel, subfaults)
    strike_ps = subfaults2['strike_ps']
    dip_ps = subfaults2['dip_ps']
    t1 = rise_time['min_rise']
    t2 = rise_time['delta_rise']
    windows = rise_time['windows']

    hyp_stk = segments[0]['hyp_stk']
    hyp_dip = segments[0]['hyp_dip']
    delta_strike = segments[0]['delta_strike']
    delta_dip = segments[0]['delta_dip']

    depth = tensor_info['depth']
    point_sources = pf.point_sources_param(segments, tensor_info, rise_time)
    shear = pf.shear_modulous(point_sources, velmodel=velmodel)

    disp_or_vel = 0
    string = '{} {} {} {} {}\n'

    with open('Fault.time', 'w') as outfile:
        outfile.write('{} {} {} 10\n'.format(hyp_stk, hyp_dip, depth))
        outfile.write(
                '{} {} {} {} {} {} {} {} {}\n'.format(
                len(segments), delta_strike, delta_dip, strike_ps, dip_ps,
                min_vel, max_vel, -100, 100))
        outfile.write('{} {} {} {} {}\n'.format(
                t1, t2, windows, rupture_vel, disp_or_vel))
        for i_segment, segment in enumerate(segments):
            dip = segment['dip']
            strike = segment['strike']
            rake = segment['rake']
            n_stk = segment['stk_subfaults']
            n_dip = segment['dip_subfaults']
            outfile.write('{} {} {}\n'.format(i_segment + 1, dip, strike))
            outfile.write('{} {} 0\n'.format(n_stk, n_dip))
            for i in range(n_dip):
                for j in range(n_stk):
                    slip = 300 if j == hyp_stk - 1 and i == hyp_dip - 1 else 0
                    outfile.write(string.format(slip, rake, 0, t1, t1))

    with open('Fault.pos', 'w') as outfile:
        for i_segment, (ps_seg, segment)\
        in enumerate(zip(point_sources, segments)):
            dip = segment['dip']
            strike = segment['strike']
            n_stk = segment['stk_subfaults']
            n_dip = segment['dip_subfaults']
            outfile.write('{} {} {}\n'.format(i_segment + 1, dip, strike))
            for j1 in range(n_dip):
                for i1 in range(n_stk):
                    for j2 in range(dip_ps):
                        for i2 in range(strike_ps):
                            outfile.write(
                                '{} {} {} {} {} {} {}\n'.format(
                                    *ps_seg[j1, i1, j2, i2]))

    with open('Niu_model', 'w') as outfile:
        outfile.write('{}\n'.format(len(shear)))
        for i_segment, (shear_seg, segment) in enumerate(zip(shear, segments)):
            n_stk = segment['stk_subfaults']
            n_dip = segment['dip_subfaults']
            outfile.write('{} {} {}\n'.format(i_segment + 1, n_stk, n_dip))
            ratio = len(shear_seg[0, :]) // 5
            format_str = ('{} ' * 5 + '\n') * ratio
            remain = len(shear_seg[0, :]) % 5
            format_str = format_str if remain == 0\
                else format_str + ('{} ' * remain + '\n')
            for i in range(n_dip):
                outfile.write(format_str.format(*shear_seg[i, :]))
    return


def from_event_mult_in():
    """Code to create files Fault.time, Fault.pos and Niu_model
    """
    if not os.path.isfile('Event_mult.in'):
        raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), 'Event_mult.in')
    pk_dirs = mng.default_dirs()
    create_fault_files = pk_dirs['create_fault_files']
    compute_shear = pk_dirs['compute_shear']
    p = subprocess.Popen(
            [create_fault_files, 'Event_mult.in', 'no'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    p2 = subprocess.Popen([compute_shear, 'vel_model',], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p2.wait()
##
## create a json file with fault properties, and another for rise_time info
##
#    segments, rise_time, point_sources = pl_mng.__read_planes_info()
#    dictionary = {
#            'segments': segments,
#            'rise_time': rise_time
#    }
#    with open('segments_data.json', 'w') as outfile:
#        json.dump(dictionary, outfile, sort_keys=True, indent=4,
#                  separators=(',', ': '), ensure_ascii=False)
    return


################################
# station data
################################


def input_chen_tele_body(tensor_info, data_prop):
    """We write some text files, which are based on teleseismic body wave data,
    as inputs for Chen's scripts.

    :param tensor_info: dictionary with moment tensor information
    :param data_prop: dictionary with properties of waveform data
    :type tensor_info: dict
    :type data_prop: dict

    .. warning::

        Make sure the filters of teleseismic data agree with the values in
        sampling_filter.json!
    """
    if not os.path.isfile('tele_waves.json'):
        return
    traces_info = json.load(open('tele_waves.json'))
    date_origin = tensor_info['date_origin']
    dt = traces_info[0]['dt']
    dt = round(dt, 1)
    filtro = data_prop['tele_filter']
    low_freq = filtro['low_freq']
    high_freq = filtro['high_freq']

    with open('filtro_tele', 'w') as outfile:
        outfile.write('Corners: {} {}\n'.format(low_freq, high_freq))
        outfile.write('dt: {}'.format(dt))

    nsta = len(traces_info)
    model = TauPyModel(model="ak135f_no_mud")
    depth = tensor_info['depth']
    event_lat = tensor_info['lat']
    event_lon = tensor_info['lon']

    string = '{0:2d}   FAR GDSN {1:>6} {1:>6}BHZ.DAT {2:5.2f} {3:6.2f} '\
        '{4:5.2f} {5:6.2f} {6:6.2f} 0 0  {7}  {8} {9}  1 0\n'
    sin_fun = lambda p: p * 3.6 / 111.12
    angle_fun = lambda p:\
    np.arctan2(sin_fun(p), np.sqrt(1 - sin_fun(p)**2)) * 180.0 / np.pi
    string_fun1 = lambda i, name, dist, az, lat, lon, p_slowness, disp_or_vel:\
    string.format(
        i, name, dist, az, lat, lon, angle_fun(p_slowness), disp_or_vel, 1.0, 0)
    string_fun2 = lambda i, name, dist, az, lat, lon, s_slowness, disp_or_vel:\
    string.format(
        i, name, dist, az, lat, lon, angle_fun(s_slowness), disp_or_vel, 4.0, 2)

    with open('Readlp.das', 'w') as outfile:
        outfile.write('30 30 30 0 0 0 0 0 0 1.1e+20\n')
        outfile.write(
            '3 10 {}\n{}{}{}{}{}{}.{}\n{}\n'.format(
                dt, date_origin.year, date_origin.month, date_origin.day,
                date_origin.hour, date_origin.minute, date_origin.second,
                date_origin.microsecond, nsta))
        i = 0
        for file in traces_info:#header in headers:
            name = file['name']
            channel = file['component']
            lat, lon = file['location']
            dist, az, back_azimuth = mng._distazbaz(
                    lat, lon, event_lat, event_lon)
            dist = kilometers2degrees(dist)
            derivative = False if not 'derivative' in file\
                else file['derivative']
            derivative = int(derivative)
            arrivals = mng.theoretic_arrivals(model, dist, depth)
            p_slowness = arrivals['p_slowness']
            s_slowness = arrivals['s_slowness']
            if channel == 'BHZ':
                outfile.write(string_fun1(i + 1, name, dist, az, lat, lon,
                                          p_slowness, derivative))
            else:
                outfile.write(string_fun2(i + 1, name, dist, az, lat, lon,
                                          s_slowness, derivative))
            i = i + 1

    with open('Wave.tele', 'w') as file1, open('Obser.tele', 'w') as file2:
        write_files_wavelet_observed(file1, file2, dt, data_prop, traces_info)
#
# instrumental response common to all body waves
#
    string2 = '\n3\n' + '0. 0.\n' * 3 + '4\n-6.17E-03  6.17E-03\n'\
              '-6.17E-03 -6.17E-03\n-39.18    49.12\n-39.18   '\
              '-49.12\n3948\n'
    with open('instrumental_response', 'w') as outfile:
        outfile.write('{}\n'.format(nsta))
        outfile.write(string2 * len(traces_info))

    write_wavelet_freqs(dt, 'Wavelets_tele_body')

    with open('Weight', 'w') as outfile:
        for info in traces_info:
            sta = info['name']
            channel = info['component']
            weight = info['trace_weight']
            outfile.write('{} {} {}\n'.format(weight, sta, channel))
    return 'tele_body'


def input_chen_tele_surf(tensor_info, data_prop):
    """Based on the teleseismic surface body waves acquired, we write some
    files with such data as input for Chen's fortran scripts.

    :param tensor_info: dictionary with moment tensor information
    :param data_prop: dictionary with properties of waveform data
    :type tensor_info: dict
    :type data_prop: dict
    """
    if not os.path.isfile('surf_waves.json'):
        return
    dirs = mng.default_dirs()
    gf_bank = dirs['long_gf_bank']
    traces_info = json.load(open('surf_waves.json'))

    depth = tensor_info['depth']
    event_lat = tensor_info['lat']
    event_lon = tensor_info['lon']

    nsta = len(traces_info)

    date_origin = tensor_info['date_origin']
    string = '{:3d} {:>6} {:>8.3f} {:>9.3f} 31' + 3 * '  {:>1}'\
            + 2 * ' {:>7.2f}' + '  1' + 3 * '  {:>7.2f}' + ' 0\n'
    string_fun = lambda i, name, lat, lon, a, b, c, d, e, weight:\
        string.format(i, name, lat, lon, a, b, c, d, e,
                      weight, weight, weight)

    with open('Readlp.inf_low', 'w') as outfile:
        outfile.write('{}{}{}{}{}{}.{}\n'.format(
                date_origin.year, date_origin.month, date_origin.day,
                date_origin.hour, date_origin.minute, date_origin.second,
                date_origin.microsecond))
        outfile.write('{} {} {} {} {} {} {} {} {}\n'.format(
                event_lat, event_lon, depth, date_origin.year,
                date_origin.julday, date_origin.hour, date_origin.minute,
                date_origin.second, date_origin.microsecond))
        outfile.write('0.0 90.0 0.0 10 4.0 1.0e+26\n')
        outfile.write('4.0 4.0 10 1.0 {}\n'.format(0))
        outfile.write('{} {}\n'.format(nsta, nsta))
        outfile.write('No STA Lat Lon M V H1 H2 Angle1 Angle2 Io_s Weight\n')
        i = 0
        for file in traces_info:
            weight = file['trace_weight']
            name = file['name']
            channel = file['component']
            lat, lon = file['location']
            if channel == 'BHZ':          # Rayleigh
                outfile.write(
                    string_fun(i + 1, name, lat, lon, 1, 0, 0, 0, 0, weight))
            else:                               # Love
                outfile.write(
                    string_fun(i + 1, name, lat, lon, 0, 1, 0, 90, 0, weight))
            i = i + 1

    with open('Wave.str_low', 'w') as file1, open('Obser.str_low', 'w') as file2:
        write_files_wavelet_observed(file1, file2, 4.0, data_prop, traces_info,
                                     gf_bank=gf_bank)

    write_wavelet_freqs(4.0, 'Wavelets_surf_tele')
    return


def input_chen_strong_motion(tensor_info, data_prop):
    """Based on the strong motion acquired, we write some text files with such
    data as input for Chen's fortran scripts.

    :param tensor_info: dictionary with moment tensor information
    :param data_prop: dictionary with properties of waveform data
    :type tensor_info: dict
    :type data_prop: dict

    .. warning::

        Make sure the filters of strong motion data agree with the values in
        sampling_filter.json!
    """
    if not os.path.isfile('strong_motion_waves.json'):
        return

    traces_info = json.load(open('strong_motion_waves.json'))
    date_origin = tensor_info['date_origin']
    moment_mag = tensor_info['moment_mag']
    event_lat = tensor_info['lat']
    event_lon = tensor_info['lon']
    depth = tensor_info['depth']
    dt_strong = traces_info[0]['dt']
    dt_strong = round(dt_strong, 2)
    filtro = data_prop['strong_filter']
    low_freq = filtro['low_freq']
    high_freq = filtro['high_freq']

    nsta = len(traces_info)

    with open('filtro_strong', 'w') as outfile:
        outfile.write('Corners: {} {}'.format(low_freq, high_freq))

    disp_or_vel = 0
    string = '{0:3d} {1:>5}{2:>9.3f}{3:>10.3f} 31{4:>5} {5} 0\n'
    string_fun = lambda i, name, lat, lon, a, w:\
        string.format(i + 1, name, lat, lon, a, w)

    with open('Readlp.inf', 'w') as outfile:
        outfile.write('{}{}{}{}{}{}{}\n'.format(
                date_origin.year, date_origin.month, date_origin.day,
                date_origin.hour, date_origin.minute, date_origin.second,
                date_origin.microsecond))
        outfile.write('{} {} {}\n'.format(event_lat, event_lon, depth))
        outfile.write('10 {} {}\n'.format(dt_strong, moment_mag))
        outfile.write('{}\n'.format(disp_or_vel))
        outfile.write('{} {}\n'.format(nsta, nsta))
        outfile.write('No STA Lat Lon M Comp Weight\n')
        for i, file in enumerate(traces_info):
            weight = file['trace_weight']
            name = file['name']
            channel = file['component']
            lat, lon = file['location']
            outfile.write(string_fun(i, name, lat, lon, channel, weight))

    with open('Wave.str', 'w') as file1, open('Obser.str', 'w') as file2:
        write_files_wavelet_observed(file1, file2, dt_strong, data_prop,
                                     traces_info)

    write_wavelet_freqs(dt_strong, 'Wavelets_strong_motion')
    return 'strong_motion'


def input_chen_cgps(tensor_info, data_prop):
    """Based on the cGPS data acquired, we write some text files with such
    data as input for Chen's fortran scripts.

    :param tensor_info: dictionary with moment tensor information
    :param data_prop: dictionary with properties of waveform data
    :type tensor_info: dict
    :type data_prop: dict

    .. warning::

        Make sure the filters of cGPS data agree with the values in
        sampling_filter.json!
    """
    if not os.path.isfile('cgps_waves.json'):
        return

    traces_info = json.load(open('cgps_waves.json'))
    date_origin = tensor_info['date_origin']
    moment_mag = tensor_info['moment_mag']
    event_lat = tensor_info['lat']
    event_lon = tensor_info['lon']
    depth = tensor_info['depth']
    filtro = data_prop['strong_filter']
    dt_cgps = traces_info[0]['dt']
    dt_cgps = round(dt_cgps, 2)
    low_freq = filtro['low_freq']
    high_freq = filtro['high_freq']


    nsta = len(traces_info)

    with open('filtro_strong', 'w') as outfile:
        outfile.write('Corners: {} {}'.format(low_freq, high_freq))

    io_vd = 0
    string = '{0:3d} {1:>5}{2:>9.3f}{3:>10.3f} 31{4:>5} {5} 0\n'
    string_fun = lambda i, name, lat, lon, a, w:\
    string.format(i + 1, name, lat, lon, a, w)

    with open('Readlp.cgps', 'w') as outfile:
        outfile.write('{}{}{}{}{}{}{}\n'.format(
                date_origin.year, date_origin.month, date_origin.day,
                date_origin.hour, date_origin.minute, date_origin.second,
                date_origin.microsecond))
        outfile.write('{} {} {}\n'.format(event_lat, event_lon, depth))
        outfile.write('10 {} {}\n'.format(dt_cgps, moment_mag))
        outfile.write('{}\n'.format(io_vd))
        outfile.write('{} {}\n'.format(nsta, nsta))
        outfile.write('No STA Lat Lon M V H1 H2 Weight\n')
        for i, file in enumerate(traces_info):
            name = file['name']
            channel = file['component']
            lat, lon = file['location']
            weight = file['trace_weight']
            outfile.write(string_fun(i, name, lat, lon, channel, weight))

    with open('Wave.cgps', 'w') as file1, open('Obser.cgps', 'w') as file2:
        write_files_wavelet_observed(file1, file2, 1.0, data_prop,
                                     traces_info, cgps=False)
    return 'cgps'


def input_chen_static(tensor_info):
    """Based on the static data acquired, we write some text files with such
    data as input for Chen's fortran scripts.

    :param tensor_info: dictionary with moment tensor information
    :type tensor_info: dict
    """
    if not os.path.isfile('static_data.json'):
        return

    static_info = json.load(open('static_data.json'))
    string = '{0:3d} {1:>5}{2:>10.3f}{3:>10.3f} {4} {5} {6} {7} {8} {9}\n'
    string_fun = lambda i, name, lat, lon, a, b, c, d, e, f:\
        string.format(i, name, lat, lon, a, b, c, d, e, f)
    with open('Readlp.static', 'w') as outfile:
        outfile.write('{}\n\n'.format(len(static_info)))
        for i, info in enumerate(static_info):
            name = info['name']
            lat, lon = info['location']
            ud_disp, ns_disp, ew_disp = info['observed']
            ud_weight, ns_weight, ew_weight = info['trace_weight']
            outfile.write(string_fun(i, name, lat, lon, ud_disp, ns_disp,
                                     ew_disp, ud_weight, ns_weight, ew_weight))


def write_files_wavelet_observed(wavelet_file, obse_file, dt, data_prop,
                                 traces_info, gf_bank=None, cgps=False,
                                 dart=False):
    """Write files with observed waveforms and properties of wavelet for all
    selected stations and channels

    :param wavelet_file: file where to write properties of wavelets for some channels.
    :param obse_file: file where to write observed waveforms for some channels.
    :param dt: sampling interval of data for all channels
    :param data_prop: dictionary with properties of waveform data
    :param traces_info: informaion about channels to be used such as location, name, etc
    :param gf_bank: name of GF_bank to be used
    :param cgps: whether data are cGPS or not
    :param dart: whether data are DART or not
    :type wavelet_file: file_handle
    :type obse_file: file_handle
    :type dt: float
    :type data_prop: dict
    :type traces_info: dict
    :type gf_bank: string, optional
    :type cgps: boolean, optional
    :type dart: boolean, optional
    """
    string = lambda name, channel, a, b: '{} {}\n{}{}'.format(name, channel, a, b)

    n_begin, n_end = data_prop['wavelet_scales']
    input_length = 256
    wavelet_file.write('{} {} {}\n'.format(n_begin, n_end, input_length))
    if not gf_bank:
        wavelet_file.write('\n')
    else:
        wavelet_file.write('{}\n'.format(gf_bank))
    wavelet_file.write('{}\n'.format(len(traces_info)))
    error_norm = '3 ' * (n_end - n_begin) + '3\n'
    for file in traces_info:
        name = file['name']
        channel = file['component']
        error_norm = '3 ' * (n_end - n_begin) + '3\n'
        derivative = False if not 'derivative' in file\
            else file['derivative']
        if derivative:
            error_norm = '3 ' * (5 - n_begin) + '4 ' * (n_end - 5) + '4\n'
        wavelet_file.write(string(name, channel, error_norm, file['wavelet_weight']))
        if file['file']:
            start = file['start_signal']
            stream = read(file['file'])
            waveform = stream[0].data[start:]
            waveform = waveform - waveform[0] if cgps else waveform
            waveform = np.diff(waveform) if derivative else waveform
        else:
            waveform = [0 for i in range(ffm_duration)]
        write_observed_file(file, dt, obse_file, waveform, dart=dart)
    return


def write_observed_file(file, dt, data_file, waveform, dart=False):
    """We use this routine for computing file Obser.x

    :param file: dictionary with station and channel metadata
    :param dt: sampling rate of data
    :param data_file: file where observed waveform is written into
    :param waveform: seismic data of selected channel
    :param dart: whether waveform is DART or not
    :type file: dict
    :type dt: float
    :type data_file: write
    :type waveform: list
    :type dart: bool, optional
    """
    ffm_duration = file['duration']
    channel = file['component'] if not dart else 'dart'
    name = file['name']
    length = len(waveform)
    trace = ['{}\n'.format(val) for val in waveform]
    trace = ''.join(trace)
    data_file.write(
            'name: {}\nchannel: {}\ndt: {}\nlength: {}\nffm_duration: {}\n'\
            'data: \n'.format(name, channel, dt, length, ffm_duration))
    data_file.write(trace)
    return


def write_wavelet_freqs(dt, name):
    """Range of frequencies modelled by different wavelet coefficients

    :param files: list of dictionaries with station and channel metadata
    :param data_type: list of data types to be used in modelling.
    :param tensor_info: dictionary with moment tensor information
    :param add_error: whether to add noise to waveforms
    :type files: list
    :type data_type: list
    :type tensor_info: dict
    :type add_error: bool, optional
    """
    with open(name, 'w') as outfile:
        for j in range(1, 9):
            min_freq = float(2**j) / float(3 * 2**10 * dt)
            outfile.write(
                    'j :{}\nFrequency range for these wavelet coefficients is'\
                    ': {:.4f} {:.4f} Hz\n'.format(j, min_freq, 4 * min_freq))


def from_synthetic_to_obs(files, data_type, tensor_info, data_prop,
                          add_error=False):
    """We write synthetic waveforms in the data files

    :param files: list of dictionaries with station and channel metadata
    :param data_type: list of data types to be used in modelling.
    :param tensor_info: dictionary with moment tensor information
    :param add_error: whether to add noise to waveforms
    :type files: list
    :type data_type: list
    :type tensor_info: dict
    :type add_error: bool, optional
    """
    dt = files[0]['dt']
    if data_type == 'strong_motion':
        max_val = 0.01
        syn_file = 'synm.str'
        obser_file = 'Obser.str'
    if data_type == 'cgps':
        max_val = 1
        dt = 1.0
        syn_file = 'synm.cgps'
        obser_file = 'Obser.cgps'
    if data_type == 'tele_body':
        max_val = 1
        syn_file = 'synm.tele'
        obser_file = 'Obser.tele'
    if data_type == 'surf_tele':
        max_val = 0.005
        dt = 4.0
        syn_file = 'synm.str_low'
        obser_file = 'Obser.str_low'
    if data_type == 'dart':
        max_val = 0.005
        dt = 60.0
        syn_file = 'synm.dart'
        obser_file = 'Obser.dart'

    dart = 'dart' in data_type
    string = '{0:3d} {1:>5}{2:>10.3f}{3:>10.3f} {4} {5} {6} {7} {8} {9}\n'
    string_fun = lambda i, name, lat, lon, a, b, c, d, e, f:\
        string.format(i, name, lat, lon, a, b, c, d, e, f)
    if not data_type == 'gps':
        files = get_outputs.get_data_dict(files, syn_file=syn_file)
        with open(obser_file, 'w') as outfile:
            for file in files:
                trace = np.array(file['synthetic'])
                length = len(trace)
                error = np.zeros(length)
                if add_error:
                    error = max_val * np.random.randn(length)
                waveform = waveform + error
                write_observed_file(file, dt, outfile, waveform, dart=dart)
    else:
        names, lats, lons, observed, synthetic, error = get_outputs.retrieve_gps()
        with open('Readlp.static', 'r') as infile:
            orig_lines = [line.split() for line in infile]
        with open('Readlp.static', 'w') as outfile:
            outfile.write('{}\n\n'.format(orig_lines[0][0]))
            for i, line in enumerate(orig_lines[2:]):
                name = line[1]
                lat = float(line[2])
                lon = float(line[3])
                new_obs = next(
                        syn for name2, syn in zip(names, synthetic) if name2==name)
                weight1 = float(line[7])
                weight2 = float(line[8])
                weight3 = float(line[9])
                error = [1.0, 1.0, 5.0]
                new_obs = new_obs + error
                outfile.write(
                        string_fun(i, name, lat, lon, new_obs[0], new_obs[1],
                                   new_obs[2], weight1, weight2, weight3))


###########################
# inputs annealing
###########################


def inputs_simmulated_annealing(dictionary, data_type):
    r"""We write file HEAT.IN which contains relevant modelling info

    :param dictionary: dictionary with information about annealing algorithm
    :param data_type: list with types of data to be used in modelling
    :type dictionary: dict
    :type data_type: list
    """
    moment_mag = dictionary['seismic_moment']
    weight0 = dictionary['moment_weight']
    weight1 = dictionary['slip_weight']
    weight2 = dictionary['time_weight']
    source_dur = dictionary['max_source_dur']
    iters = dictionary['iterations']
    cooling_rate = dictionary['cooling_rate']
    initial_temp = dictionary['initial_temperature']

    if not data_type:
        data_type = mng.update_data(tensor_info)
    data_type = set(data_type) - {'gps', 'dart'}
    type_of_inversion = 1#dm.set_data_type(data_type)

    with open('HEAT.IN', 'w') as filewrite:
        filewrite.write('{} -7 {} {} 90\n'.format(
                iters, type_of_inversion, moment_mag))
        filewrite.write('{} {} {} 0.1 {} {} {}\n'.format(initial_temp,
                cooling_rate, 4 * 10**-6, weight0, weight1, weight2))
        filewrite.write('0 {} 0 {}\n'.format(10 ** - 4, source_dur))
        filewrite.write('1\n')
    return


def model_space(segments):
    r"""We write a file which describes the space of feasible FFM models.

    :param segments: dictionary with fault segments data
    :param rise_time: dictionary with rise time function properties
    :type segments: dict
    :type rise_time: dict

    .. note::
        Shouldn't yet be used for several fault planes.
    """

    with open('bound.in', 'w') as filewrite:
        filewrite.write('0\n')
        for i, segment in enumerate(segments):
            peak_upper_slip = segment['max_upper_slip']
            peak_lower_slip = segment['max_lower_slip']
            peak_left_slip = segment['max_left_slip']
            peak_right_slip = segment['max_right_slip']
            peak_slip = segment['max_center_slip']
            peak_slip_delta = segment['max_slip_delta']
            nstep = segment['slip_step']
            rake_max = segment['rake_max']
            rake_min = segment['rake_min']
            rstep = segment['rake_step']
            filewrite.write('{}\n'.format(i + 1))
            filewrite.write('{} {}\n'.format(peak_slip_delta, peak_slip_delta))
            filewrite.write('1 1 1 1\n')
            filewrite.write('{} 0.0 {}\n'.format(peak_upper_slip, nstep))
            filewrite.write('{} 0.0 {}\n'.format(peak_lower_slip, nstep))
            filewrite.write('{} 0.0 {}\n'.format(peak_left_slip, nstep))
            filewrite.write('{} 0.0 {}\n'.format(peak_right_slip, nstep))
            filewrite.write('{} 0.0 {}\n'.format(peak_slip, nstep))
            filewrite.write('{} {} {}\n'.format(rake_max, rake_min, rstep))
            filewrite.write('2.6 2.4 3\n')
            filewrite.write('5 8\n')

    with open('continue', 'w') as file:
        file.write('1\n' + '0 0\n' * 4)
    with open('bound.special', 'w') as filewrite:
        filewrite.write('0\n')
    with open('continue.special', 'w') as file:
        file.write('0\n')
    return


################################
# Green functions
################################


def write_green_file(green_dict, cgps=False):
    """We write a file needed to run fortran code to retrieve strong motion
    GF

    :param green_dict: dictionary with properties of GF bank
    :param cgps: whether data are cGPS or strong motion
    :type green_dict: dict
    :type cgps: bool, optional
    """
    dt = green_dict['dt']
    min_depth = green_dict['min_depth']
    max_depth = green_dict['max_depth']
    min_dist = green_dict['min_dist']
    max_dist = green_dict['max_dist']
    location = green_dict['location']
    name = 'Green.in' if not cgps else 'Green_cgps.in'
    with open(name, 'w') as green_file:
        green_file.write('vel_model\n{} {} 1\n{} {} 1\n'.format(
                max_depth, min_depth, max_dist, min_dist))
        green_file.write('10 {} 50000 {}\n'.format(dt, 10))
        green_file.write(location)


###############################
# as program
###############################


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--folder", default=os.getcwd(),
                        help="folder where there are input files")
    parser.add_argument("-gcmt", "--gcmt_tensor",
                        help="location of GCMT moment tensor file")
    parser.add_argument("-p", "--plane", action="store_true",
                        help="compute Fault.pos, Fault.time, Niu_model")
    parser.add_argument("-t", "--tele", action="store_true",
                        help="compute files with teleseismic data")
    parser.add_argument("-su", "--surface", action="store_true",
                        help="compute files with surface waves data")
    parser.add_argument("-st", "--strong", action="store_true",
                        help="compute files with strong motion data")
    parser.add_argument('-l','--list', nargs='+',
                        help='list of strong motion stations')
    parser.add_argument("--cgps", action="store_true",
                        help="compute files with cGPS data")
    parser.add_argument("--gps", action="store_true",
                        help="compute files with static GPS data")
    parser.add_argument("-a", "--annealing", action="store_true",
                        help="compute files for annealing")
    args = parser.parse_args()
    os.chdir(args.folder)
    if args.gcmt_tensor:
        cmt_file = args.gcmt_tensor
        tensor_info = tensor.get_tensor(cmt_file=cmt_file)
    else:
        tensor_info = tensor.get_tensor()
    if args.plane:
        velmodel = json.load(open('velmodel_data.json'))
#        write_velmodel(velmodel)
        segments_data = json.load(open('segments_data.json'))
        plane_for_chen(tensor_info, segments_data, 1.5, 3.25, velmodel)
    if not os.path.isfile('sampling_filter.json'):
        raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT),
                'sampling_filter.json')
    data_prop = json.load(open('sampling_filter.json'))
    if args.tele:
        if not os.path.isfile('tele_waves.json'):
            raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), 'tele_waves.json')
        input_chen_tele_body(tensor_info, data_prop)
    if args.surface:
        if not os.path.isfile('surf_waves.json'):
            raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), 'surf_waves.json')
        input_chen_tele_surf(tensor_info, data_prop)
    if args.strong:
        if not os.path.isfile('strong_motion_waves.json'):
            raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT),
                    'strong_motion_waves.json')
        input_chen_strong_motion(tensor_info, data_prop)
    if args.cgps:
        if not os.path.isfile('cgps_waves.json'):
            raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), 'cgps_waves.json')
        input_chen_cgps(tensor_info, data_prop)
    if args.gps:
        if not os.path.isfile('static_data.json'):
            raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), 'static_data.json')
        input_chen_static(tensor_info)
    if args.annealing:
        if not os.path.isfile('annealing_prop.json'):
            raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT),
                    'annealing_prop.json')
        dictionary = json.load(open('annealing_prop.json'))
        inputs_simmulated_annealing(dictionary, 'dart')
