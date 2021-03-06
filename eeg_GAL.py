# -*- coding: utf-8 -*-
from __future__ import print_function

import os

import re
import cPickle

import collections
import pandas as pd
from scipy.io import loadmat
import numpy as np

from keras.models import Sequential
from keras.layers.convolutional import Convolution1D, MaxPooling1D
from keras.layers.core import Dense, Dropout, Activation, TimeDistributedDense, Flatten
from keras.layers.recurrent import LSTM, SimpleRNN, GRU, JZS1, JZS2, JZS3
from keras.utils import np_utils
import time
import sklearn

from sklearn.metrics import roc_auc_score, confusion_matrix, accuracy_score


from scipy.signal import lfilter, butter

__author__ = 'jinwon'



class GAL_data():

    def __init__(self):
        self.eeg_dict = None
        self.info_dict = None
        self.emg_dict = None
        self.kin_dict = None

        self.total_count = None
        self.trial_length = None

        self.timesteps = None
        self.X_dict = None
        self.y_dict = None

        self.part_data_count = dict.fromkeys(np.arange(12) + 1, 0)
        self.data_description = dict()

    def set_logger(self, logger):
        self.logger = logger
        
    def read_raw_data(self):
        data_dir = u'//media//jinwon//새 볼륨//Downloads//grasp_and_lift_eeg'

        def read_info():
            col_name = \
            ['Part',
            'Run',
            'Lift',
            'CurW',
            'CurS',
            'PrevW',
            'PrevS',
            'StartTime',
            'LEDOn',
            'LEDOff',
            'BlockType',
            'tIndTouch',
            'tThumbTouch',
            'tFirstDigitTouch',
            'tBothDigitTouch',
            'tIndStartLoadPhase',
            'tThuStartLoadPhase',
            'tBothStartLoadPhase',
            'tLiftOff',
            'tReplace',
            'tIndRelease',
            'tThuRelease',
            'tBothReleased',
            'GF_Max',
            'LF_Max',
            'dGF_Max',
            'dLF_Max',
            'tGF_Max',
            'tLF_Max',
            'tdGF_Max',
            'tdLF_Max',
            'GF_Hold',
            'LF_Hold',
            'tHandStart',
            'tHandStop',
            'tPeakVelHandReach',
            'tPeakVelHandRetract',
            'GripAparture_Max',
            'tGripAparture_Max',
            'Dur_Reach',
            'Dur_Preload',
            'Dur_LoadPhase',
            'Dur_Release']
            info_dict = dict()
            for datapath, directory, filelist in os.walk(data_dir):
                for file in filelist:
                    info_match = re.match('P\d+_info.mat', file)
                    if info_match != None:
                        info_mat = loadmat(os.path.join(datapath, file))
                        part_num = [int(x) for x in info_mat['info'][:,0]]
                        series_num = [int(x) for x in info_mat['info'][:,1]]
                        trial_num = [int(x) for x in info_mat['info'][:,2]]
                        row_num = np.arange(info_mat['info'].shape[0])
                        for p, s, t, pos in zip(part_num, series_num, trial_num, row_num):
                            data = info_mat['info'][pos,3:].reshape(1,40)
                            info_dict[(p,s,t)] = pd.DataFrame(data=data, columns=col_name[3:])
            return info_dict

        def read_eeg():
            eeg_dict = dict()
            for datapath, directory, filelist in os.walk(data_dir):
                for file in filelist:
                    eeg_match = re.match('WS_P(\d+)_S(\d+)_T(\d+)_eeg.mat', file)
                    if eeg_match != None:
                        eeg_mat = loadmat(os.path.join(datapath, file))
                        key = tuple([int(x) for x in eeg_match.groups()])
                        eeg_dict[key] = eeg_mat['eeg']
            return eeg_dict

        def read_kin():
            kin_colname = ['Ae1 - angle e sensor 1',
            'Ae2 - angle e sensor 2',
            'Ae3 - angle e sensor 3',
            'Ae4 - angle e sensor 4',
            'Ar1 - angle r sensor 1',
            'Ar2 - angle r sensor 2',
            'Ar3 - angle r sensor 3',
            'Ar4 - angle r sensor 4',
            'Az1 - angle z sensor 1',
            'Az2 - angle z sensor 2',
            'Az3 - angle z sensor 3',
            'Az4 - angle z sensor 4',
            'FX1 - force x plate 1',
            'FX2 - force x plate 2',
            'FY1 - force y plate 1',
            'FY2 - force y plate 2',
            'FZ1 - force z plate 1',
            'FZ2 - force z plate 2',
            'Px1 - position x sensor 1',
            'Px2 - position x sensor 2',
            'Px3 - position x sensor 3',
            'Px4 - position x sensor 4',
            'Py1 - position y sensor 1',
            'Py2 - position y sensor 2',
            'Py3 - position y sensor 3',
            'Py4 - position y sensor 4',
            'Pz1 - position z sensor 1',
            'Pz2 - position z sensor 2',
            'Pz3 - position z sensor 3',
            'Pz4 - position z sensor 4',
            'TX1 - torque x plate 1',
            'TX2 - torque x plate 2',
            'TY1 - torque y plate 1',
            'TY2 - torque y plate 2',
            'TZ1 - torque z plate 1',
            'TZ2 - torque z plate 2',
            'IndLF',
            'ThuLF',
            'LF',
            'IndGF',
            'ThuGF',
            'GF',
            'IndRatio',
            'ThuRatio',
            'GFLFRatio'
            ]
            kin_dict = dict()
            for datapath, directory, filelist in os.walk(data_dir):
                for file in filelist:
                    kin_match = re.match('WS_P(\d+)_S(\d+)_T(\d+)_kin.mat', file)

                    if kin_match != None:
                        kin_mat = loadmat(os.path.join(datapath, file))
                        key = tuple([int(x) for x in kin_match.groups()])
                        kin_dict[key] = pd.DataFrame(kin_mat['kin'], columns = kin_colname)

            return kin_dict

        def read_emg():
            emg_dict = dict()
            for datapath, directory, filelist in os.walk(data_dir):
                for file in filelist:
                    emg_match = re.match('WS_P(\d+)_S(\d+)_T(\d+)_emg.mat', file)
                    if emg_match != None:
                        emg_mat = loadmat(os.path.join(datapath, file))
                        key = tuple([int(x) for x in emg_match.groups()])
                        emg_dict[key] = emg_mat['emg']

            return emg_dict

        self.info_dict = read_info()
        self.eeg_dict = read_eeg()
        self.kin_dict = read_kin()
        self.emg_dict = read_emg()

        self.logger.info( 'read raw data')

        self.count_data()

    def save_raw_data(self):
        # assert not os.path.exists(os.path.join('data', 'eeg_info_dict.pkl')), 'pickled data already exist'
        assert self.eeg_dict != None, 'eeg_dict null'
        assert self.info_dict != None, 'info_dict null'
        assert self.emg_dict != None, 'emg_dict null'
        assert self.kin_dict != None, 'kin_dict null'

        self.eeg_dict = collections.OrderedDict(sorted(self.eeg_dict.items(), key=lambda t: t[0][0]*10000 + t[0][0]*100 + t[0][0]))
        self.emg_dict = collections.OrderedDict(sorted(self.emg_dict.items(), key=lambda t: t[0][0]*10000 + t[0][0]*100 + t[0][0]))
        self.info_dict = collections.OrderedDict(sorted(self.info_dict.items(), key=lambda t: t[0][0]*10000 + t[0][0]*100 + t[0][0]))
        self.kin_dict = collections.OrderedDict(sorted(self.kin_dict.items(), key=lambda t: t[0][0]*10000 + t[0][0]*100 + t[0][0]))


        with open(os.path.join('data', 'eeg_dict.pkl'), 'wb') as f:
            cPickle.dump(self.eeg_dict, f, protocol = cPickle.HIGHEST_PROTOCOL)
        with open(os.path.join('data', 'info_dict.pkl'), 'wb') as f:
            cPickle.dump(self.info_dict, f, protocol = cPickle.HIGHEST_PROTOCOL)
        with open(os.path.join('data', 'kin_dict.pkl'), 'wb') as f:
            cPickle.dump(self.kin_dict, f, protocol = cPickle.HIGHEST_PROTOCOL)
        with open(os.path.join('data', 'emg_dict.pkl'), 'wb') as f:
            cPickle.dump(self.emg_dict, f, protocol = cPickle.HIGHEST_PROTOCOL)

        self.logger.info( 'saved data as pickle')

    def load_data(self, load_list=('eeg', 'info', 'emg', 'kin')):

        for file in load_list:
            with open(os.path.join('data', '{0}_dict.pkl'.format(file)), 'rb') as f:
                exec('self.{0}_dict = cPickle.load(f)'.format(file))

        self.logger.info( 'loaded pickled data')

        self.count_data()

    def count_data(self):
        for key in self.eeg_dict.keys():
            part = key[0]
            self.part_data_count[part] = self.part_data_count[part] + 1

    def examine_time(self):
        assert self.info_dict != None
        on_stop_time = list()
        on_off_time = list()
        led_on_time = list()
        led_off_time = list()
        hand_stop_time = list()
        for key in self.info_dict:
            led_on = self.info_dict[key]['LEDOn']
            led_off = self.info_dict[key]['LEDOff']
            hand_stop = self.info_dict[key]['tHandStop']
            data_len = self.eeg_dict[key].shape[0]

            self.logger.info( 'data len : ', data_len)
            self.logger.info( 'handstop : ', hand_stop/0.002)

            on_stop_time.extend(hand_stop - led_on)
            on_off_time.extend(led_off - led_on)
            led_on_time.extend(led_on)
            led_off_time.extend(led_off)
            hand_stop_time.extend(hand_stop)

        col_list = [on_stop_time, on_off_time, led_on_time, led_off_time, hand_stop_time]
        col_name_list = ['on_stop_time', 'on_off_time', 'led_on_time', 'led_off_time', 'hand_stop_time']
        df = pd.DataFrame(columns = ['min', '20', 'median','95','97','99', 'max'])

        for val, name in zip(col_list, col_name_list):
            row_val = (min(val), np.percentile(val, 20),np.percentile(val, 50), np.percentile(val, 95), np.percentile(val, 97), np.percentile(val, 99), max(val))
            row_val =[val/0.002 for val in row_val[:]]
            df.loc[name,:] = row_val

        df.to_csv(os.path.join('result', 'time_data.csv'))
        self.logger.info( 'saved result/time_data.csv')

    def uniform_trial_length(self, trail_length):
        '''
        :param trail_length: timestep that has to same for each batch
        :return: none
        '''

        '''
            if there are not enough data points, used the 1000 points before LEDOn
            for this, used the same slice for every patient
        '''
        assert self.eeg_dict != None

        add_count = 0
        discard_count = 0
        delete_count = 0
        normal_count = 0

        led_on_step = 1000

        for key in self.eeg_dict.keys():
            temp = self.eeg_dict[key]
            if temp.shape[0] < trail_length:
                add_count = add_count + 1
                add_amount = trail_length - temp.shape[0]

                # if add_amount < led_on_step:
                #     add = temp[:add_amount]
                #     temp = np.vstack((add, temp))  #add to the front
                #     assert temp.shape[0] == timesteps
                # else:
                #     # hand_stop_time = self.info_dict[key]['tHandStop']
                #     # after_stop_time = hand_stop_time - temp.shape[0]
                #     # if after_stop_time + led_on_step > timesteps:           #add to front(before led_on) and end ( after handstop)
                #     #     add_left_amount = timesteps - temp.shape[0] - led_on_step
                #     #     temp = np.vstack((temp[:led_on_step], temp, temp[hand_stop_time:hand_stop_time+add_left_amount]))
                #     # assert temp.shape[0] == timesteps
                #     add = temp[:add_amount]
                #     left_add_amount = int(add_amount - led_on_step)
                #     quotient = left_add_amount / led_on_step
                #     remainder = left_add_amount % led_on_step
                #
                #     if quotient == 0:
                #         add = temp[:remainder]
                #     else:
                #         for i in range(quotient):
                #             if i == 0:
                #                 add = temp[:add_amount]
                #             else:
                #                 add = np.vstack((add, temp[:add_amount]))
                #         add = np.vstack((add, temp[:remainder]))
                #
                #     temp = np.vstack((add, temp))
                #     assert temp.shape[0] == timesteps

                quotient = add_amount / led_on_step
                remainder = add_amount % led_on_step

                if quotient == 0:
                    add = temp[:remainder]
                else:
                    for i in range(quotient):
                        if i == 0:
                            add = temp[:led_on_step]
                        else:
                            add = np.vstack((add, temp[:led_on_step]))
                    add = np.vstack((add, temp[:remainder]))

                temp = np.vstack((add, temp))
                assert temp.shape[0] == trail_length


            elif temp.shape[0] > trail_length:
                discard_count = discard_count + 1
                discard_amount = temp.shape[0] - trail_length
                if discard_amount <= led_on_step:
                    temp = temp[discard_amount:]
                    assert temp.shape[0] == trail_length
                else:
                    stop_step = self.info_dict[key]['tHandStop'].values[0] / 0.002
                    after_stop_step = temp.shape[0] - stop_step
                    if discard_amount < led_on_step + after_stop_step:
                        discard_left_amount = discard_amount - led_on_step
                        temp = temp[led_on_step:-discard_left_amount]
                        assert temp.shape[0] == trail_length
                    else:
                        temp = None
                        discard_count = discard_count - 1
                        delete_count = delete_count + 1
            else:
                normal_count = normal_count + 1
                pass # temp.shape[0] == timesteps necessarily not needed

            if temp != None:
                self.eeg_dict[key] = temp
            else:
                self.eeg_dict.pop(key)

        self.logger.info( 'discarded count :', discard_count)
        self.logger.info( 'added count : ', add_count)
        self.logger.info( 'deleted count :', delete_count)
        self.logger.info( 'total count :', normal_count + add_count + discard_count)

        self.total_count = normal_count + add_count + discard_count
        self.trial_length = trail_length

    def preprocess_filter(self, max_freq, min_freq, low_pass, N_filter=4):

        def butter_lowpass(highcut, fs, order):
            nyq = 0.5 * fs
            high = highcut / nyq
            b, a = butter(order, high, btype="lowpass")
            return b, a

        def butter_bandpass(lowcut, highcut, fs, order):
            nyq = 0.5 * fs
            cutoff = [lowcut / nyq, highcut / nyq]
            b, a = butter(order, cutoff, btype="bandpass")
            return b, a

        def butter_highpass(highcut, fs, order):
            nyq = 0.5 * fs
            high = highcut / nyq
            b, a = butter(order, high, btype="highpass")
            return b, a

        if low_pass == True:
            b, a = butter_lowpass(max_freq, fs=500, order=N_filter)
            for key in self.eeg_dict.keys():
                x = lfilter(b, a, self.eeg_dict[key], axis=0)
                self.eeg_dict[key] = x
        else:
            b, a = butter_bandpass(min_freq, max_freq, fs=500, order=N_filter)
            for key in self.eeg_dict.keys():
                x = lfilter(b, a, self.eeg_dict[key], axis=0)
                self.eeg_dict[key] = x

        self.logger.info('preprocessed by butter band passing')
        self.data_description['preprocess_filter'] = '{}_{}'.format(max_freq, min_freq)

    def preprocess_filter_multiple(self, N_filter=4):

        def butter_lowpass(highcut, fs, order):
            nyq = 0.5 * fs
            high = highcut / nyq
            b, a = butter(order, high, btype="lowpass")
            return b, a

        def butter_bandpass(lowcut, highcut, fs, order):
            nyq = 0.5 * fs
            cutoff = [lowcut / nyq, highcut / nyq]
            b, a = butter(order, cutoff, btype="bandpass")
            return b, a

        def butter_highpass(highcut, fs, order):
            nyq = 0.5 * fs
            high = highcut / nyq
            b, a = butter(order, high, btype="highpass")
            return b, a

        for key in self.eeg_dict.keys():
            agg = None
            for min_freq, max_freq in zip([0.1, 4, 8, 13], [4, 8, 13, 30]):
                b, a = butter_bandpass(min_freq, max_freq, fs=500, order=N_filter)
                x = lfilter(b, a, self.eeg_dict[key], axis=0)
                if agg == None:
                    agg = x
                else :
                    agg = np.hstack((agg, x))
            self.eeg_dict[key] = agg

        self.logger.info('preprocessed by butter band passing')

    def save_individual_eeg(self):
        # for key in self.eeg_dict.keys():
        #     np.savetxt(os.path.join('preprocess_eeg', '{0}_eeg.csv'.format(key)), self.eeg_dict[key], delimiter=',')

        part_list = [x for x in self.eeg_dict.keys()]

        part_list.sort(key = lambda  x : x[0] * 100000 + x[1] * 100 + x[2])

        diff = list()
        for key in part_list:
            height = self.kin_dict[key][u'Pz1 - position z sensor 1']
            diff_temp = np.diff(height)
            diff.extend(diff_temp)

        diff_reach_threshold = 0 #np.percentile(diff, 90)
        diff_retract_threshold = 0 #np.percentile(diff, 20)


        for index, key in enumerate(part_list):

            handstart = int(self.info_dict[key]['tHandStart'].values / 0.002)
            bothdigittouch = int(self.info_dict[key]['tBothDigitTouch'].values / 0.002)
            bothreleased = int(self.info_dict[key]['tBothReleased'].values / 0.002)
            handstop = int(self.info_dict[key]['tHandStop'].values / 0.002)

            height = self.kin_dict[key][u'Pz1 - position z sensor 1']
            diff = np.diff(height)
            after_peak = np.argmax(diff)

            i=0
            while(after_peak + i <= len(diff)):
                if diff[after_peak+i] >= diff_reach_threshold and diff[after_peak+i+1] <= diff_reach_threshold:
                    break
                i = i +1

            stop_reach = after_peak + i

            before_valley = np.argmin(diff)

            i=0
            while(before_valley - i >= 0):
                if diff[before_valley - i] <= diff_retract_threshold and diff[before_valley-i-1] >= diff_retract_threshold:
                    break
                i = i + 1

            start_retract = before_valley - i

            limestones = [handstart, bothdigittouch, stop_reach, start_retract, bothreleased, handstop]

            df = pd.DataFrame(columns=['handstart', 'bothdigittouch', 'stop_reach', 'start_retract', 'both_released', 'handstop'])
            df.loc[0,:] = limestones
            df.to_csv(os.path.join('preprocess_eeg', '{0}_limestones.csv'.format(key)), index=False)

    def data_generator_event(self, part, timesteps, stride, event_list, event_range=None, input_dim=32):

        if event_range != None:
            assert type(event_range) == np.ndarray, 'event_range not numpy array'

        assert input_dim == self.eeg_dict[self.eeg_dict.keys()[0]].shape[1], 'input dim doesn\'t match'

        self.data_description['participator'] = part
        self.data_description['timesteps'] = timesteps
        self.data_description['stride'] = stride
        self.data_description['event_list'] = event_list
        if event_range != None:
            self.data_description['event_range'] = event_range


        part_list = [x for x in self.eeg_dict.keys() if x[0] == part]
        for key in part_list:
            # nb_samples = (self.trial_length - timesteps) / stride + 1
            trial_step_size = self.eeg_dict[key].shape[0]
            nb_samples = (trial_step_size - timesteps) / stride + 1
            X = np.zeros((nb_samples, timesteps, input_dim))
            y = np.zeros((nb_samples, len(event_list)))
            temp = self.eeg_dict[key]

            for i in np.arange(nb_samples):
                X[i,:,:] = temp[i*stride:i*stride+timesteps,:]

            if event_range != None:
                for index, event in enumerate(event_list):
                    event_time_step = int(self.info_dict[key][event].values / 0.002)
                    y[(event_time_step + event_range - trial_step_size)/stride, index] = 1
            else:
                handstart = int(self.info_dict[key]['tHandStart'].values / 0.002) - timesteps
                bothdigittouch = int(self.info_dict[key]['tBothDigitTouch'].values / 0.002) - timesteps
                bothstartload = int(self.info_dict[key]['tBothStartLoadPhase'].values / 0.002) - timesteps
                liftoff = int(self.info_dict[key]['tLiftOff'].values / 0.002) - timesteps
                maxLF = int(self.info_dict[key]['tLF_Max'].values / 0.002) - timesteps
                #max_P1_height = int(self.kin_dict[key]['Pz1 - position z sensor 1'].values / 0.002)
                LEDOff = int(self.info_dict[key]['LEDOff'].values / 0.002) - timesteps
                replace = int(self.info_dict[key]['tReplace'].values / 0.002) - timesteps
                bothreleased = int(self.info_dict[key]['tBothReleased'].values / 0.002) - timesteps
                handstop = int(self.info_dict[key]['tHandStop'].values / 0.002) - timesteps


                y[handstart:bothdigittouch, event_list.index('Dur_Reach')] = 1
                #y[bothdigittouch:bothstartload, event_list.index('Dur_Preload')] = 1
                y[bothdigittouch:maxLF, event_list.index('Dur_LoadReach')] = 1
                y[maxLF:LEDOff, event_list.index('Dur_LoadMaintain')] = 1
                y[LEDOff:replace, event_list.index('Dur_LoadRetract')] = 1
                #y[replace:bothreleased, event_list.index('Dur_Release')] = 1
                y[replace:handstop, event_list.index('Dur_Retract')] = 1
                # TODO fix the DurMaintain and LoadReach by using the x,y,z coordinates information

            X = X.astype('float32')
            y = y.astype('float32')

            yield [X, y]

    def data_generator_event_classify(self, part, timesteps, stride, event_list, input_dim=32):

        assert input_dim == self.eeg_dict[self.eeg_dict.keys()[0]].shape[1], 'input dim doesn\'t match'

        self.data_description['participator'] = part
        self.data_description['timesteps'] = timesteps
        self.data_description['stride'] = stride
        self.data_description['event_list'] = event_list

        part_list = [x for x in self.eeg_dict.keys() if x[0] == part]


        diff = list()
        for key in part_list:
            height = self.kin_dict[key][u'Pz1 - position z sensor 1']
            diff_temp = np.diff(height)
            diff.extend(diff_temp)

        diff_reach_threshold = np.percentile(diff, 90)
        diff_retract_threshold = np.percentile(diff, 20)

        for key in part_list:
            # nb_samples = (self.trial_length - timesteps) / stride + 1
            trial_step_size = self.eeg_dict[key].shape[0]
            nb_samples = (trial_step_size - timesteps) / stride + 1


            LEDOn = int(self.info_dict[key]['LEDOn'].values / 0.002)
            handstart = int(self.info_dict[key]['tHandStart'].values / 0.002)
            bothdigittouch = int(self.info_dict[key]['tBothDigitTouch'].values / 0.002)
            bothstartload = int(self.info_dict[key]['tBothStartLoadPhase'].values / 0.002)
            liftoff = int(self.info_dict[key]['tLiftOff'].values / 0.002)
            # maxLF = int(self.info_dict[key]['tLF_Max'].values / 0.002)
            #max_P1_height = int(self.kin_dict[key]['Pz1 - position z sensor 1'].values / 0.002)
            LEDOff = int(self.info_dict[key]['LEDOff'].values / 0.002)
            replace = int(self.info_dict[key]['tReplace'].values / 0.002)
            bothreleased = int(self.info_dict[key]['tBothReleased'].values / 0.002)
            handstop = int(self.info_dict[key]['tHandStop'].values / 0.002)

            height = self.kin_dict[key][u'Pz1 - position z sensor 1']
            diff = np.diff(height)
            after_peak = np.argmax(diff)

            for i in range(1000):
                if diff[after_peak+i] >= diff_reach_threshold and diff[after_peak+i+1] <= diff_reach_threshold:
                    break

            stop_Reach = after_peak + i

            before_valley = np.argmin(diff)

            for i in range(1000):
                if diff[before_valley - i] <= diff_retract_threshold and diff[before_valley-i-1] >= diff_retract_threshold:
                    break

            start_retract = before_valley - i

            limestones = [handstart, bothdigittouch, stop_Reach, start_retract, bothreleased, handstop]

            assert len(limestones) == len(event_list)

            X = np.zeros((nb_samples, timesteps, input_dim))
            y = np.zeros((nb_samples, len(event_list)))
            temp = self.eeg_dict[key]

            for i in np.arange(nb_samples):
                start = i *stride
                end = i*stride + timesteps
                X[i,:,:] = temp[start:end,:]
                for lime_num, lime in enumerate(limestones):
                    if start - lime + end - lime <= 0 :
                        y[i, lime_num] = 1
                        break
                    if lime_num == len(limestones) - 1:
                        y[i, 0] = 1
                        # same Idle state


            X = X.astype('float32')
            y = y.astype('float32')

            yield [X, y]

    def data_event(self, part, timesteps, stride, event_list, partition_ratio, input_dim=32):

        assert input_dim == self.eeg_dict[self.eeg_dict.keys()[0]].shape[1], 'input dim doesn\'t match'

        self.data_description['participator'] = part
        self.data_description['timesteps'] = timesteps
        self.data_description['stride'] = stride
        self.data_description['event_list'] = event_list

        part_list = [x for x in self.eeg_dict.keys() if x[0] == part]

        train_num = int(len(part_list) * partition_ratio[0])
        val_num = int(len(part_list) * partition_ratio[1])
        test_num = int(len(part_list) - train_num - val_num)

        def make_data(part_list):
            total_samples = 0
            nb_samples_list = list()
            for key in part_list:
                trial_step_size = self.eeg_dict[key].shape[0]
                nb_samples = (trial_step_size - timesteps) / stride + 1
                nb_samples_list.append(nb_samples)
                total_samples = total_samples + nb_samples

            X = np.zeros((total_samples, timesteps, input_dim))
            y = np.zeros((total_samples, len(event_list)))

            cum_index = 0

            for index, key in enumerate(part_list):
                temp = self.eeg_dict[key]
                for i in np.arange(nb_samples_list[index]):
                    X[i+cum_index,:,:] = temp[i*stride:i*stride+timesteps,:]

                handstart = int(self.info_dict[key]['tHandStart'].values / 0.002)
                bothdigittouch = int(self.info_dict[key]['tBothDigitTouch'].values / 0.002)
                bothstartload = int(self.info_dict[key]['tBothStartLoadPhase'].values / 0.002)
                liftoff = int(self.info_dict[key]['tLiftOff'].values / 0.002)
                maxLF = int(self.info_dict[key]['tLF_Max'].values / 0.002)
                #max_P1_height = int(self.kin_dict[key]['Pz1 - position z sensor 1'].values / 0.002)
                LEDOff = int(self.info_dict[key]['LEDOff'].values / 0.002)
                replace = int(self.info_dict[key]['tReplace'].values / 0.002)
                bothreleased = int(self.info_dict[key]['tBothReleased'].values / 0.002)
                handstop = int(self.info_dict[key]['tHandStop'].values / 0.002)


                y[cum_index + np.arange(handstart, bothdigittouch), event_list.index('Dur_Reach')] = 1
                #y[bothdigittouch:bothstartload, event_list.index('Dur_Preload')] = 1
                y[cum_index + np.arange(bothdigittouch, maxLF), event_list.index('Dur_LoadReach')] = 1
                y[cum_index + np.arange(maxLF, LEDOff), event_list.index('Dur_LoadMaintain')] = 1
                y[cum_index + np.arange(LEDOff, replace), event_list.index('Dur_LoadRetract')] = 1
                #y[replace:bothreleased, event_list.index('Dur_Release')] = 1
                y[cum_index + np.arange(replace, handstop), event_list.index('Dur_Retract')] = 1

                cum_index = cum_index + nb_samples_list[index]

            X = X.astype('float32')
            y = y.astype('float32')

            return [X, y]

        train_X , train_y = make_data(part_list[:train_num])
        val_X , val_y = make_data(part_list[train_num:train_num+val_num])
        test_X , test_y = make_data(part_list[train_num+val_num:])

        return [train_X, train_y, val_X, val_y, test_X, test_y]

    def data_event_classify(self, part, timesteps, stride, event_list, partition_ratio, input_dim=32):

        assert input_dim == self.eeg_dict[self.eeg_dict.keys()[0]].shape[1], 'input dim doesn\'t match'

        self.data_description['participator'] = part
        self.data_description['timesteps'] = timesteps
        self.data_description['stride'] = stride
        self.data_description['event_list'] = event_list
        self.data_description['data_sorted'] = 'sorted'
        part_list = [x for x in self.eeg_dict.keys() if x[0] == part]

        part_list.sort(key = lambda  x : x[0] * 100000 + x[1] * 100 + x[2])

        train_num = int(len(part_list) * partition_ratio[0])
        val_num = int(len(part_list) * partition_ratio[1])
        test_num = int(len(part_list) - train_num - val_num)

        def make_data(part_list):
            total_samples = 0
            nb_samples_list = list()
            for key in part_list:
                trial_step_size = self.eeg_dict[key].shape[0]
                nb_samples = (trial_step_size - timesteps) / stride + 1
                nb_samples_list.append(nb_samples)
                total_samples = total_samples + nb_samples


            print (total_samples)

            diff = list()
            for key in part_list:
                height = self.kin_dict[key][u'Pz1 - position z sensor 1']
                diff_temp = np.diff(height)
                diff.extend(diff_temp)

            diff_reach_threshold = 0 #np.percentile(diff, 90)
            diff_retract_threshold = 0 #np.percentile(diff, 20)

            X = np.zeros((total_samples, timesteps, input_dim))
            y = np.zeros((total_samples, len(event_list)))


            cum_index = 0

            for index, key in enumerate(part_list):

                handstart = int(self.info_dict[key]['tHandStart'].values / 0.002)
                bothdigittouch = int(self.info_dict[key]['tBothDigitTouch'].values / 0.002)
                bothreleased = int(self.info_dict[key]['tBothReleased'].values / 0.002)
                handstop = int(self.info_dict[key]['tHandStop'].values / 0.002)

                height = self.kin_dict[key][u'Pz1 - position z sensor 1']
                diff = np.diff(height)
                after_peak = np.argmax(diff)

                for i in range(1000):
                    if diff[after_peak+i] >= diff_reach_threshold and diff[after_peak+i+1] <= diff_reach_threshold:
                        break

                stop_reach = after_peak + i

                before_valley = np.argmin(diff[1000:]) + 1000

                for i in range(1000):
                    if diff[before_valley - i] <= diff_retract_threshold and diff[before_valley-i-1] >= diff_retract_threshold:
                        break

                start_retract = before_valley - i

                limestones = [handstart, bothdigittouch, stop_reach, start_retract, bothreleased, handstop]


                assert len(limestones) == len(event_list)
                assert np.all(np.diff(limestones) > 0), 'not aligned {} {} {} {} {} {}'.format(*limestones)



                temp = self.eeg_dict[key]

                for i in np.arange(nb_samples_list[index]):
                    start = i *stride
                    end = i*stride + timesteps
                    X[cum_index+i,:,:] = temp[start:end,:]
                    # X[cum_index+i,:,:] = np.mean(temp[start:end,:], axis= 0), np.mean(temp[start-100:end-100,:], axis= 0)


                    for lime_num, lime in enumerate(limestones):

                        if end < lime:
                            y[cum_index+i, lime_num] = 1
                            break
                        if lime_num == len(limestones) - 1:
                            y[cum_index +i, 0] = 1

                        '''
                        if start - lime + end - lime <= 0 :
                            y[cum_index+i, lime_num] = 1
                            break
                        if lime_num == len(limestones) - 1:
                            y[cum_index+i, 0] = 1
                            # same Idle state
                        '''

                cum_index = cum_index + nb_samples_list[index]

            X = X.astype('float32')
            y = y.astype('float32')

            # mask = np.where(y[:, 0] != 1)
            #
            #
            # X = X[mask[0], :, :]
            #
            # y = y[mask[0],1:]
            #
            # mask_2 = np.where(np.sum(y, axis= 1) != 0)
            #
            # X =X[mask_2[0], :,:]
            # y = y[mask_2[0], :]

            return [X, y]

        train_X , train_y = make_data(part_list[:train_num])
        val_X , val_y = make_data(part_list[train_num:train_num+val_num])
        test_X , test_y = make_data(part_list[train_num+val_num:])

        # train_X , train_y = make_data(train_list[:int(len(train_list) * 0.9)])
        # val_X , val_y = make_data(train_list[int(len(train_list) * 0.9):])
        # test_X , test_y = make_data(test_list)

        return [train_X, train_y, val_X, val_y, test_X, test_y]

    def data_intention_classify(self, part, timesteps, stride, event_list, partition_ratio, input_dim=32):

        assert input_dim == self.eeg_dict[self.eeg_dict.keys()[0]].shape[1], 'input dim doesn\'t match'

        self.data_description['participator'] = part
        self.data_description['timesteps'] = timesteps
        self.data_description['stride'] = stride
        self.data_description['event_list'] = event_list
        self.data_description['data_sorted'] = 'sorted'
        part_list = [x for x in self.eeg_dict.keys() if x[0] == part]

        part_list.sort(key = lambda  x : x[0] * 100000 + x[1] * 100 + x[2])

        train_num = int(len(part_list) * partition_ratio[0])
        val_num = int(len(part_list) * partition_ratio[1])
        test_num = int(len(part_list) - train_num - val_num)

        def make_data(part_list):
            total_samples = 0
            nb_samples_list = list()
            for key in part_list:
                trial_step_size = self.eeg_dict[key].shape[0]
                nb_samples = (trial_step_size - timesteps) / stride + 1
                nb_samples_list.append(nb_samples)
                total_samples = total_samples + nb_samples

            diff = list()
            for key in part_list:
                height = self.kin_dict[key][u'Pz1 - position z sensor 1']
                diff_temp = np.diff(height)
                diff.extend(diff_temp)

            diff_reach_threshold = np.percentile(diff, 90)
            diff_retract_threshold = np.percentile(diff, 20)

            X = np.zeros((total_samples, timesteps, input_dim))
            y = np.zeros((total_samples, len(event_list)))


            cum_index = 0

            for index, key in enumerate(part_list):

                handstart = int(self.info_dict[key]['tHandStart'].values / 0.002)
                bothdigittouch = int(self.info_dict[key]['tBothDigitTouch'].values / 0.002)
                bothreleased = int(self.info_dict[key]['tBothReleased'].values / 0.002)
                handstop = int(self.info_dict[key]['tHandStop'].values / 0.002)

                height = self.kin_dict[key][u'Pz1 - position z sensor 1']
                diff = np.diff(height)
                after_peak = np.argmax(diff)

                for i in range(1000):
                    if diff[after_peak+i] >= diff_reach_threshold and diff[after_peak+i+1] <= diff_reach_threshold:
                        break

                stop_Reach = after_peak + i

                before_valley = np.argmin(diff)

                for i in range(1000):
                    if diff[before_valley - i] <= diff_retract_threshold and diff[before_valley-i-1] >= diff_retract_threshold:
                        break

                start_retract = before_valley - i

                limestones = [handstart, bothdigittouch, stop_Reach, start_retract, bothreleased, handstop]

                assert len(limestones) == len(event_list)

                temp = self.eeg_dict[key]

                for i in np.arange(nb_samples_list[index]):
                    start = i *stride
                    end = i*stride + timesteps
                    X[cum_index+i,:,:] = temp[start:end,:]
                    for lime_num, lime in enumerate(limestones):
                        if start - lime + end - lime <= 0 :
                            y[cum_index+i, lime_num] = 1
                            break
                        if lime_num == len(limestones) - 1:
                            y[cum_index+i, 0] = 1
                            # same Idle state

                cum_index = cum_index + nb_samples_list[index]

            X = X.astype('float32')
            y = y.astype('float32')

            return [X, y]

        train_X , train_y, limestones = make_data(part_list[:train_num])
        val_X , val_y = make_data(part_list[train_num:train_num+val_num])
        test_X , test_y = make_data(part_list[train_num+val_num:])

        return [train_X, train_y, val_X, val_y, test_X, test_y]

    def preprocess_kin(self):
        for key in self.eeg_dict.keys():
            self.eeg_dict[key] = self.eeg_dict[key][1000:,:]
        self.data_description['preprocess'] = 'sliced after 1000'

    def data_generator_kin(self, part, timesteps, stride, input_dim=32):
        assert input_dim == self.eeg_dict[self.eeg_dict.keys()[0]].shape[1], 'input dim doesn\'t match'

        self.data_description['participator'] = part
        self.data_description['timesteps'] = timesteps
        self.data_description['stride'] = stride

        part_list = [x for x in self.eeg_dict.keys() if x[0] == part]
        for key in part_list:
            # nb_samples = (self.trial_length - timesteps) / stride + 1
            trial_step_size = self.eeg_dict[key].shape[0]
            nb_samples = (trial_step_size - timesteps) / stride + 1

            columns = ['Px2 - position x sensor 2',
                    'Px3 - position x sensor 3',
                    'Px4 - position x sensor 4',
                    'Py2 - position y sensor 2',
                    'Py3 - position y sensor 3',
                    'Py4 - position y sensor 4',
                    'Pz2 - position z sensor 2',
                    'Pz3 - position z sensor 3',
                    'Pz4 - position z sensor 4']

            X = np.zeros((nb_samples, timesteps, input_dim))
            y = np.zeros((nb_samples, timesteps, len(columns)))

            temp_eeg = self.eeg_dict[key]
            temp_kin = self.kin_dict[key]

            for i in np.arange(nb_samples):
                X[i,:,:] = temp_eeg[i*stride:i*stride+timesteps,:]
                y[i,:,:] = temp_kin.loc[i*stride:i*stride+timesteps-1,columns]
                                ## pandas include to end index so I excluded it

            X = X.astype('float32')
            y = y.astype('float32')

            yield [X, y, key]

    def get_data_description(self):
        return self.data_description

class EEG_model():

    def __init__(self, event_list):
        self.X_dict = None
        self.y_dict = None
        self.event_list = event_list
        self.model_config = dict()
        self.data_description = None

    def select_model(self, model_name):

        def conv_2():

            model = Sequential()
            fs = np.asarray([3])
            ps = np.asarray([2])
            nb_f = np.asarray([8])
            model.add(Convolution1D(input_dim=1, nb_filter=nb_f[0], filter_length=fs[0], border_mode='full'))
            model.add(Activation('relu'))
            model.add(MaxPooling1D(pool_length=ps[0], stride=None)) # stride = None means stride = pool_length
            out_dim = (32 + fs[0] - 1) / ps[0]

            model.add(Flatten())
            model.add(Dense(nb_f[0] * out_dim , 64))
            model.add(Activation('relu'))
            model.add(Dropout(0.5))
            model.add(Dense(64, self.nb_classes))
            model.add(Activation('sigmoid'))

            model.compile(loss='binary_crossentropy', optimizer='adadelta', class_mode='binary')
            return model

        def lstm_1():
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=64)) # try using a GRU instead, for fun
            # model.add(Dropout(0.5))
            model.add(Dense(64, len(self.event_list)))
            model.add(Activation('sigmoid'))
            model.compile(loss='binary_crossentropy', optimizer='adadelta', class_mode='binary')
            return model

        def lstm_2():
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=64, return_sequences=True)) # try using a GRU instead, for fun
            model.add(LSTM(input_dim=64, output_dim=64, return_sequences=False))
            model.add(Dense(64, len(self.event_list)))
            model.add(Activation('sigmoid'))
            model.compile(loss='binary_crossentropy', optimizer='adadelta', class_mode='binary')
            return model

        def lstm_3():
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=64, return_sequences=True)) # try using a GRU instead, for fun
            model.add(LSTM(input_dim=64, output_dim=64, return_sequences=False))
            model.add(Dropout(0.5))
            model.add(Dense(64, 128))
            model.add(Dropout(0.5))
            model.add(Dense(128, len(self.event_list)))
            model.add(Activation('sigmoid'))
            model.compile(loss='binary_crossentropy', optimizer='adadelta', class_mode='binary')

            self.model_config['dropout'] = [0.5,0.5]

            return model

        def lstm_4():
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=64, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.5))
            model.add(Dense(64, 128))
            model.add(Dropout(0.5))
            model.add(Dense(128, len(self.event_list)))
            model.add(Activation('sigmoid'))
            model.compile(loss='binary_crossentropy', optimizer='adadelta', class_mode='binary')

            self.model_config['dropout'] = [0.5,0.5]

        def lstm_5():
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=64, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.5))
            model.add(Dense(64, len(self.event_list)))
            model.add(Activation('sigmoid'))
            model.compile(loss='binary_crossentropy', optimizer='adadelta', class_mode='binary')
            self.model_config['dropout'] = [0.5]

            return model

        def simple_rnn_1():
            model = Sequential()
            model.add(SimpleRNN(input_dim=32, output_dim=64)) # try using a GRU instead, for fun
            # model.add(Dropout(0.5))
            model.add(Dense(64, len(self.event_list)))
            model.add(Activation('sigmoid'))
            model.compile(loss='binary_crossentropy', optimizer='adadelta', class_mode='binary')
            return model

        def simple_rnn_2():
            self.model_config['dropout'] = [0.0,0.0]
            model = Sequential()
            model.add(SimpleRNN(input_dim=32, output_dim=64, return_sequences = True))
            model.add(SimpleRNN(input_dim=64, output_dim=64, return_sequences = False))
            model.add(Dropout(0.0))
            model.add(Dense(64, 128))
            model.add(Dropout(0.0))
            model.add(Dense(128, len(self.event_list)))
            model.add(Activation('sigmoid'))
            model.compile(loss='binary_crossentropy', optimizer='adadelta', class_mode='binary')
            return model

        def seq_to_seq():
            self.model_config['dropout'] = [0.0, 0.0]
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=64, return_sequences=True))
            model.add(LSTM(input_dim=64, output_dim=64, return_sequences=True))
            model.add(Dropout(0.0))
            model.add(TimeDistributedDense(64,128))# output shape: (nb_samples, nb_timesteps, 9)
            model.add(Activation('relu'))
            model.add(Dropout(0.0))
            model.add(TimeDistributedDense(128,12))
            model.add(Activation('linear'))
            model.compile(loss='mean_squared_error', optimizer='adadelta')
            return model

        def seq_to_seq_2():
            self.model_config['dropout'] = [0.0, 0.0]
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=32, return_sequences=True))
            model.add(Dropout(0.0))
            model.add(TimeDistributedDense(32,9))# output shape: (nb_samples, nb_timesteps, 9)
            model.add(Activation('linear'))
            model.compile(loss='mean_squared_error', optimizer='adadelta')
            return model

        def seq_to_seq_3():
            self.model_config['dropout'] = [0.0, 0.0]
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=64, return_sequences=True))
            model.add(Dropout(0.5))
            model.add(TimeDistributedDense(64,64))# output shape: (nb_samples, nb_timesteps, 9)
            model.add(Activation('relu'))
            model.add(Dropout(0.5))
            model.add(TimeDistributedDense(64,9))
            model.add(Activation('linear'))
            model.compile(loss='mean_squared_error', optimizer='adadelta')
            return model

        def simple_rnn_softmax():
            model = Sequential()
            model.add(SimpleRNN(input_dim=32, output_dim=32)) # try using a GRU instead, for fun
            # model.add(Dropout(0.5))
            model.add(Dense(32, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode='categorical')
            return model

        def simple_rnn_softmax_2():
            model = Sequential()
            model.add(SimpleRNN(input_dim=32, output_dim=16)) # try using a GRU instead, for fun
            # model.add(Dropout(0.5))
            model.add(Dense(16, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode='categorical')
            return model

        def gru_softmax():
            model = Sequential()
            model.add(GRU(input_dim=32, output_dim=32)) # try using a GRU instead, for fun
            # model.add(Dropout(0.5))
            model.add(Dense(32, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adam', class_mode='categorical')
            return model

        def lstm_softmax():
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=32, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.5))
            model.add(Dense(32, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode = 'categorical')
            self.model_config['dropout'] = [0.5]
            return model

        def lstm_softmax_2():
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=64, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.0))
            model.add(Dense(64, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode = 'categorical')
            return model

        def lstm_softmax_3():
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=32, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.0))
            model.add(Dense(32, 32))
            model.add(Activation('relu'))
            model.add(Dense(32, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode = 'categorical')
            return model

        def lstm_softmax_4():
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=32, return_sequences=True)) # try using a GRU instead, for fun
            model.add(LSTM(input_dim=32, output_dim=32, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.0))
            model.add(Dense(32, 32))
            model.add(Activation('relu'))
            model.add(Dropout(0.0))
            model.add(Dense(32, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode = 'categorical')
            return model

        def lstm_softmax_5():
            self.model_config['dropout'] = 0.5
            model = Sequential()
            model.add(LSTM(input_dim=32, output_dim=32, return_sequences=True)) # try using a GRU instead, for fun
            model.add(LSTM(input_dim=32, output_dim=16, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.5))
            model.add(Dense(16, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode = 'categorical')
            return model

        def gru_softmax_5():
            self.model_config['dropout'] = 0.0
            model = Sequential()
            model.add(GRU(input_dim=32, output_dim=32, return_sequences=True)) # try using a GRU instead, for fun
            model.add(GRU(input_dim=32, output_dim=16, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.50))
            model.add(Dense(16, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode = 'categorical')
            return model

        def jzs1_softmax_5():
            self.model_config['dropout'] = 0.0
            model = Sequential()
            model.add(JZS1(input_dim=32, output_dim=32, return_sequences=True)) # try using a GRU instead, for fun
            model.add(JZS1(input_dim=32, output_dim=16, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.50))
            model.add(Dense(16, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode = 'categorical')
            return model
        def jzs2_softmax_5():

            self.model_config['dropout'] = 0.0
            model = Sequential()
            model.add(JZS2(input_dim=32, output_dim=32, return_sequences=True)) # try using a GRU instead, for fun
            model.add(JZS2(input_dim=32, output_dim=16, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.50))
            model.add(Dense(16, len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode = 'categorical')
            return model

        def jzs3_softmax_5():

            self.model_config['dropout'] = 0.5
            model = Sequential()
            model.add(JZS3(input_dim=32, output_dim=32, return_sequences=True)) # try using a GRU instead, for fun
            model.add(JZS3(input_dim=32, output_dim=32, return_sequences=False)) # try using a GRU instead, for fun
            model.add(Dropout(0.50))
            model.add(Dense(32 , len(self.event_list)))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode = 'categorical')
            return model

        def simple_softmax(timesteps):
            model = Sequential()
            model.add(Dense(input = 32 * timesteps, output_dim = 1))
            model.add(Activation('softmax'))
            model.compile(loss='categorical_crossentropy', optimizer='adadelta', class_mode='categorical')
            return model

        self.model = eval('{0}()'.format(model_name))
        self.model_config['model'] = model_name
        self.logger.info('selected model {0}'.format(model_name))

    def load_model_weight(self, model_name, folder_name):
        self.model.load_weights(os.path.join('output', folder_name, 'weight.hdf'))
        self.model_config['weight_loaded_from'] = folder_name
        self.logger.info('loaded model weight from {0}'.format(folder_name))

    def run_model_with_generator_event(self, generator, train_list, validate_list, test_list):

        self.model_config['train_data_size'] = len(train_list)
        self.model_config['validate_data_size'] = len(validate_list)
        self.model_config['test_data_size'] = len(test_list)

        def run(data_list, data_type, generator=generator):
            loss_total = 0
            accuracy_total = 0
            auc_total = 0
            for i in data_list:
                X, y = generator.next()
                if data_type == 'train':
                    loss, accuracy = self.model.train_on_batch(X = X, y = y, accuracy = True)
                    loss_total = loss_total + loss
                    accuracy_total = accuracy_total + accuracy
                    print( '{0} : complete {1:.2f}%,  loss : {2}'.format(data_type, float(i+1)/len(data_list) * 100, loss_total/(i+1)), end = '\r')
                if data_type == 'test' or data_type == 'validate':
                    pred = self.model.predict(X)
                    temp_loss_total = 0
                    for j in range(y.shape[1]):
                        temp_loss = sklearn.metrics.log_loss(y[:,j], pred[:,j])
                        temp_loss_total = temp_loss_total + temp_loss
                    temp_loss_total = temp_loss_total / y.shape[1]
                    loss_total = loss_total + temp_loss_total
                    auc = np.asarray([roc_auc_score(y[:, j], pred[:, j]) for j in range(y.shape[1])])
                    auc_total = auc_total + auc
                    mean_auc_total = np.mean(auc_total)
                    print( '{0} : complete {1:.2f}%,  loss : {2}, auc : {3}'.format(data_type, float(i+1)/len(data_list) * 100, loss_total/(i+1), mean_auc_total/(i+1)), end = '\r')

            if data_type == 'test' or data_type == 'validate':
                self.logger.info( '{0} : complete {1:.2f}%,  loss : {2}, auc : {3}'.format(data_type, float(i+1)/len(data_list) * 100, loss_total/(i+1), mean_auc_total/(i+1)))

            elif data_type == 'train':
                self.logger.info( '{0} : complete {1:.2f}%,  loss : {2}'.format(data_type, float(i+1)/len(data_list) * 100, loss_total/(i+1)))

        run(data_list=train_list, data_type = 'train')
        run(data_list = validate_list, data_type='validate')
        run(data_list=test_list, data_type= 'test')

    def run_model_with_generator_event_classify(self, generator, train_list, validate_list, test_list):

        self.model_config['train_data_size'] = len(train_list)
        self.model_config['validate_data_size'] = len(validate_list)
        self.model_config['test_data_size'] = len(test_list)

        def run(data_list, data_type, generator=generator):
            loss_total = 0
            accuracy_total = 0
            for i in data_list:
                X, y = generator.next()
                if data_type == 'train':
                    loss, accuracy = self.model.train_on_batch(X = X, y = y, accuracy = True)
                    loss_total = loss_total + loss
                    accuracy_total = accuracy_total + accuracy
                    print( '{0} : complete {1:.2f}%,  loss : {2}, accuracy : {3}'.format(data_type, float(i+1)/len(data_list) * 100, loss_total/(i+1), accuracy_total/(i+1)), end = '\r')
                if data_type == 'test' or data_type == 'validate':
                    loss, accuracy = self.model.test_on_batch(X = X, y = y, accuracy = True)
                    loss_total = loss_total + loss
                    accuracy_total = accuracy_total + accuracy
                    print( '{0} : complete {1:.2f}%,  loss : {2}, accuracy : {3}'.format(data_type, float(i+1)/len(data_list) * 100, loss_total/(i+1), accuracy_total/(i+1)), end = '\r')

            if data_type == 'test' or data_type == 'validate':
                self.logger.info( '{0} : complete {1:.2f}%,  loss : {2}, accuracy : {3}'.format(data_type, float(i+1)/len(data_list) * 100, loss_total/(i+1), accuracy_total/(i+1)))

            elif data_type == 'train':
                self.logger.info( '{0} : complete {1:.2f}%,  loss : {2}, accuracy : {3}'.format(data_type, float(i+1)/len(data_list) * 100, loss_total/(i+1), accuracy_total/(i+1)))

        run(data_list=train_list, data_type = 'train')
        run(data_list = validate_list, data_type='validate')
        run(data_list=test_list, data_type= 'test')

    def run_model_event(self, data, nb_epoch, batch_size):
        [train_X, train_y, val_X, val_y, test_X, test_y] = data
        print('train')
        loss_train = self.model.fit(X=train_X, y=train_y, show_accuracy=True, nb_epoch = nb_epoch, validation_data = (val_X, val_y), batch_size=batch_size)
        print('test')
        loss_test = self.model.evaluate(X=test_X, y=test_y, show_accuracy=True)
        return loss_train, loss_test

    def run_model_with_generator_kin(self, generator, train_list, test_list):

        self.model_config['train_data_size'] = len(train_list)
        self.model_config['test_data_size'] = len(test_list)

        def run(data_list, data_type, generator=generator):
            loss_total = 0
            for i in data_list:
                X, y, key = generator.next()
                loss, accuracy = self.model.train_on_batch(X = X, y = y, accuracy = True)
                loss_total = loss_total + loss
                print( '{0} : complete {1:.2f}%,  loss : {2}'.format(data_type, float(i+1)/len(data_list) * 100, loss_total/(i+1)), end = '\r')
            self.logger.info( '{0} : complete {1:.2f}%,  loss : {2}'.format(data_type, float(i+1)/len(data_list) * 100, loss_total/(i+1)))
            return loss_total / len(data_list)

        train_loss = run(data_list=train_list, data_type = 'train')
        test_loss = run(data_list=test_list, data_type= 'test')
        return train_loss, test_loss

    def save_event_generator(self, generator, train_list, validate_list, test_list, event_list, output_dir):
        assert self.data_description != None, 'data_description is not set'

        def evaluate_score_revised(self, data_list, data_type, param_threshold_list = None, generator=generator, event_list=event_list, output_dir = output_dir):
            start = time.clock()
            self.logger.info('predicting values : {0}'.format(data_type))

            pred = None
            for _ in data_list:
                X , y_temp = generator.next()
                if pred == None:
                    pred = self.model.predict(X)
                    y = y_temp
                else:
                    pred = np.vstack((pred, self.model.predict(X)))
                    y = np.vstack((y, y_temp))

            nb_classes = len(event_list)

            if param_threshold_list == None:
                param_threshold_list = list()

            if data_type == 'validate' or data_type == 'test':
                f1_score_list = list()
                precision_list = list()
                recall_list = list()
            elif data_type =='train':
                f1_score_list = None
                precision_list = None
                recall_list = None


            for i in range(nb_classes):
                if data_type == 'validate':
                    precision, recall, thresholds = sklearn.metrics.precision_recall_curve(y[:,i], pred[:,i], pos_label = 1)
                    f1_score = np.asarray([2 * prec * rec / (prec + rec) for prec, rec in zip(precision, recall)])
                    max_f1_score = max(f1_score)
                    index = np.where(f1_score == max_f1_score)
                    param_threshold_list.append(thresholds[index])
                    f1_score_list.append(max_f1_score)
                    precision_list.append(precision[index])
                    recall_list.append(recall[index])
                elif data_type == 'test':
                    pred_binary_one_class = (pred[:,i] > param_threshold_list[i]).astype(int)
                    f1_score = sklearn.metrics.f1_score(y[:,i], pred_binary_one_class)
                    precision = sklearn.metrics.precision_score(y[:,i], pred_binary_one_class)
                    recall = sklearn.metrics.recall_score(y[:,i], pred_binary_one_class)
                    f1_score_list.append(f1_score)
                    precision_list.append(precision)
                    recall_list.append(recall)

            auc_roc_score = [sklearn.metrics.roc_auc_score(y[:, i], pred[:, i]) for i in range(nb_classes)]
            auc_pr_score = [sklearn.metrics.average_precision_score(y[:, i], pred[:, i]) for i in range(nb_classes)]

            score = pd.DataFrame(index = event_list)
            score['auc_roc_score'] = auc_roc_score
            score['auc_pr_score'] = auc_pr_score
            score['f1_score'] = f1_score_list
            score['precision_score'] = precision_list
            score['recall_score'] = recall_list


            self.logger.info( ('time elapsed : {0} seconds'.format(time.clock() - start)))
            self.logger.info( (data_type+' auc_roc : ', auc_roc_score))
            self.logger.info( (data_type+' auc_pr : ', auc_pr_score))

            if data_type == 'validate':
                self.logger.info((data_type+' threshold : ', param_threshold_list))
                self.logger.info( (data_type+' max f1 : ', f1_score_list))
                self.logger.info( (data_type+' precision : ', precision_list))
                self.logger.info( (data_type+' recall : ', recall_list))
            elif data_type == 'test':
                self.logger.info( (data_type+' max f1 : ', f1_score_list))
                self.logger.info( (data_type+' precision : ', precision_list))
                self.logger.info( (data_type+' recall : ', recall_list))
            elif data_type == 'train':
                pass

            return score, param_threshold_list

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        train_score, _ = evaluate_score_revised(self, train_list, 'train')
        validate_score, param_threshold_list = evaluate_score_revised(self, validate_list, 'validate')
        test_score, _ = evaluate_score_revised(self, test_list, 'test', param_threshold_list=param_threshold_list)

        validate_score.to_csv(os.path.join(output_dir, 'validate_score.csv'))
        train_score.to_csv(os.path.join(output_dir, 'train_score.csv'))
        test_score.to_csv(os.path.join(output_dir, 'test_score.csv'))

        self.model.save_weights(os.path.join(output_dir, 'weight.hdf'))

        self.model_config['threshold'] = param_threshold_list
        with open(os.path.join(output_dir, 'data_description.txt'), 'w') as f:
            for key in self.data_description.keys():
                f.write('{0} : {1}\n'.format(key, self.data_description[key]))

        self.logger.info('data_description.txt saved')

        with open(os.path.join(output_dir, 'model_config.txt'), 'w') as f:
            for key in self.model_config.keys():
                if isinstance(self.model_config[key], collections.Iterable) and not isinstance(self.model_config[key], basestring):
                    self.model_config[key] = ', '.join([str(i) for i in self.model_config[key]])
                f.write('{0} : {1}\n'.format(key, self.model_config[key]))
        self.logger.info('model_config.txt saved')

    def save_event_generator_classify(self, generator, train_list, validate_list, test_list, event_list, output_dir):
        assert self.data_description != None, 'data_description is not set'

        def evaluate_score_revised(self, data_list, data_type, generator=generator, event_list=event_list, output_dir = output_dir):
            self.logger.info('predicting values : {0}'.format(data_type))

            pred = None
            for _ in data_list:
                X , y_temp = generator.next()
                pred_temp = np.expand_dims(self.model.predict_classes(X, verbose=False), axis=1)


                if pred == None:
                    pred = pred_temp
                    y = np.zeros((y_temp.shape[0],1))
                    for i in range(y_temp.shape[1]):
                        y[np.where(y_temp[:,i] == 1)] = i
                else:

                    pred = np.vstack((pred, pred_temp))

                    y_temp_categorize = np.zeros((y_temp.shape[0], 1))
                    for i in range(y_temp.shape[1]):
                        y_temp_categorize[np.where(y_temp[:,i] == 1)] = i
                    y = np.vstack((y, y_temp_categorize))

            cm = confusion_matrix(y, pred)
            cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

            cm_df = pd.DataFrame(data = cm_normalized, columns=event_list, index=event_list)

            return cm_df, accuracy_score(y, pred), np.hstack((y, pred))

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        train_confmat, train_acc, train_y_pred = evaluate_score_revised(self, train_list, 'train')
        validate_confmat, validate_acc, validate_y_pred = evaluate_score_revised(self, validate_list, 'validate')
        test_confmat, test_acc, test_y_pred = evaluate_score_revised(self, test_list, 'test')

        train_confmat.to_csv(os.path.join(output_dir, 'train_confusion_matrix.csv'))
        validate_confmat.to_csv(os.path.join(output_dir, 'validate_confusion_matrix.csv'))
        test_confmat.to_csv(os.path.join(output_dir, 'test_confusion_matrix.csv'))

        np.savetxt(os.path.join(output_dir, 'train_y_pred.txt'), train_y_pred, fmt = '%d', delimiter=',')
        np.savetxt(os.path.join(output_dir, 'validate_y_pred.txt'), validate_y_pred, fmt = '%d', delimiter =',')
        np.savetxt(os.path.join(output_dir, 'test_y_pred.txt'), test_y_pred, fmt = '%d', delimiter=',')

        with open(os.path.join(output_dir, 'accuracy_score.txt'), 'w') as f:
            f.write('train accuracy : {}'.format(train_acc))
            f.write('validate accuracy : {}'.format(validate_acc))
            f.write('test accuracy : {}'.format(test_acc))

        self.model.save_weights(os.path.join(output_dir, 'weight.hdf'))

        self.model_config['threshold'] = 'None'
        with open(os.path.join(output_dir, 'data_description.txt'), 'w') as f:
            for key in self.data_description.keys():
                f.write('{0} : {1}\n'.format(key, self.data_description[key]))

        self.logger.info('data_description.txt saved')

        with open(os.path.join(output_dir, 'model_config.txt'), 'w') as f:
            for key in self.model_config.keys():
                if isinstance(self.model_config[key], collections.Iterable) and not isinstance(self.model_config[key], basestring):
                    self.model_config[key] = ', '.join([str(i) for i in self.model_config[key]])
                f.write('{0} : {1}\n'.format(key, self.model_config[key]))
        self.logger.info('model_config.txt saved')

    def save_event_classify(self, data, event_list, output_dir):
        assert self.data_description != None, 'data_description is not set'

        def evaluate_score_revised(self, data, data_type, param_window=0, event_list=event_list, output_dir = output_dir):
            self.logger.info('predicting values : {0}'.format(data_type))

            [X, temp_y] = data

            y = np.zeros((temp_y.shape[0], 1))
            pred = np.expand_dims(self.model.predict_classes(X, verbose=False), axis=1)

            def mean_prediction(pred_proba, window):
                ave_pred = np.zeros(pred_proba.shape[0])
                for i in np.arange(1, pred_proba.shape[0], dtype=int):
                    if i < window:
                        ave_pred[i] = np.argmax(np.mean(pred_proba[:i], axis = 0))
                    else:
                        ave_pred[i] = np.argmax(np.mean(pred_proba[i-window/2:i+window/2], axis = 0))
                return ave_pred

            for i in range(temp_y.shape[1]):
                y[np.where(temp_y[:,i] == 1)] = i


            pred_proba = self.model.predict(X, verbose=False)
            pred = self.model.predict_classes(X, verbose=False)
            best_score = 0
            best_window = 10

            if data_type == 'validate':
                for window in np.arange(10, 50, step=5):
                    ave_pred = mean_prediction(pred_proba, window=window)
                    temp_score = accuracy_score(y, ave_pred)
                    if temp_score > best_score:
                        best_score = temp_score
                        best_window = window
                        best_ave_pred = ave_pred
            else:
                best_ave_pred = mean_prediction(pred_proba, window=param_window)
                best_score = accuracy_score(y, best_ave_pred)

            score = accuracy_score(y, pred)
            non_smoothed_cm = confusion_matrix(y, pred)
            non_smoothed_cm_normalized = non_smoothed_cm.astype('float') / non_smoothed_cm.sum(axis=1)[:, np.newaxis]

            non_smoothed_cm_df = pd.DataFrame(data = non_smoothed_cm, columns=event_list, index=event_list)
            non_smoothed_n_cm_df = pd.DataFrame(data = non_smoothed_cm_normalized, columns=event_list, index=event_list)

            cm = confusion_matrix(y, best_ave_pred)
            cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

            cm_df = pd.DataFrame(data = cm, columns=event_list, index=event_list)
            n_cm_df = pd.DataFrame(data = cm_normalized, columns=event_list, index=event_list)


            new_pred = np.hstack((y, np.expand_dims(best_ave_pred, axis=1)))
            pred_total = np.hstack((new_pred, pred.reshape(pred.shape[0],1)))

            return n_cm_df, cm_df, best_score, non_smoothed_n_cm_df, non_smoothed_cm_df, score, best_window, pd.DataFrame(pred_total, columns=['True', 'Predict', 'Non-smoothed'])

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        [train_X, train_y, val_X, val_y, test_X, test_y] = data


        validate_n_confmat, validate_confmat, validate_acc, validate_n_confmat_non, validate_confmat_non, validate_acc_non, best_window, valid_pred = evaluate_score_revised(self, [val_X, val_y], 'validate')
        train_n_confmat, train_confmat, train_acc, train_n_confmat_non, train_confmat_non, train_acc_non,_, train_pred = evaluate_score_revised(self, [train_X, train_y], 'train', param_window=best_window)
        test_n_confmat, test_confmat, test_acc, test_n_confmat_non, test_confmat_non, test_acc_non,_, test_pred = evaluate_score_revised(self, [test_X, test_y], 'test', param_window=best_window)


        self.model_config['window_size'] = best_window

        train_n_confmat.to_csv(os.path.join(output_dir, 'normalized_train_confusion_matrix.csv'))
        validate_n_confmat.to_csv(os.path.join(output_dir, 'normalized_validate_confusion_matrix.csv'))
        test_n_confmat.to_csv(os.path.join(output_dir, 'normalized_test_confusion_matrix.csv'))

        train_confmat.to_csv(os.path.join(output_dir, 'train_confusion_matrix.csv'))
        validate_confmat.to_csv(os.path.join(output_dir, 'validate_confusion_matrix.csv'))
        test_confmat.to_csv(os.path.join(output_dir, 'test_confusion_matrix.csv'))

        train_n_confmat_non.to_csv(os.path.join(output_dir, 'non_normalized_train_confusion_matrix.csv'))
        validate_n_confmat_non.to_csv(os.path.join(output_dir, 'non_normalized_validate_confusion_matrix.csv'))
        test_n_confmat_non.to_csv(os.path.join(output_dir, 'non_normalized_test_confusion_matrix.csv'))

        train_confmat_non.to_csv(os.path.join(output_dir, 'non_train_confusion_matrix.csv'))
        validate_confmat_non.to_csv(os.path.join(output_dir, 'non_validate_confusion_matrix.csv'))
        test_confmat_non.to_csv(os.path.join(output_dir, 'non_test_confusion_matrix.csv'))

        train_pred.to_csv(os.path.join(output_dir, 'train_pred.csv'))
        valid_pred.to_csv(os.path.join(output_dir, 'validate_pred.csv'))
        test_pred.to_csv(os.path.join(output_dir, 'test_pred.csv'))

        # np.savetxt(os.path.join(output_dir, 'train_y_pred.txt'), train_y_pred, fmt = '%d', delimiter=',')
        # np.savetxt(os.path.join(output_dir, 'validate_y_pred.txt'), validate_y_pred, fmt = '%d', delimiter =',')
        # np.savetxt(os.path.join(output_dir, 'test_y_pred.txt'), test_y_pred, fmt = '%d', delimiter=',')

        with open(os.path.join(output_dir, 'accuracy_score.txt'), 'w') as f:
            f.write('train accuracy : {}'.format(train_acc))
            f.write('validate accuracy : {}'.format(validate_acc))
            f.write('test accuracy : {}'.format(test_acc))

            f.write('non-smoothed train accuracy : {}'.format(train_acc_non))
            f.write('non-smoothed validate accuracy : {}'.format(validate_acc_non))
            f.write('non-smoothed test accuracy : {}'.format(test_acc_non))

        self.model.save_weights(os.path.join(output_dir, 'weight.hdf'))

        self.model_config['threshold'] = 'None'
        with open(os.path.join(output_dir, 'data_description.txt'), 'w') as f:
            for key in self.data_description.keys():
                f.write('{0} : {1}\n'.format(key, self.data_description[key]))

        self.logger.info('data_description.txt saved')

        with open(os.path.join(output_dir, 'model_config.txt'), 'w') as f:
            for key in self.model_config.keys():
                if isinstance(self.model_config[key], collections.Iterable) and not isinstance(self.model_config[key], basestring):
                    self.model_config[key] = ', '.join([str(i) for i in self.model_config[key]])
                f.write('{0} : {1}\n'.format(key, self.model_config[key]))
        self.logger.info('model_config.txt saved')

    def save_event(self, data, event_list, output_dir):
        assert self.data_description != None, 'data_description is not set'

        def evaluate_score_revised(self, data, data_type, param_threshold_list = None, event_list=event_list, output_dir = output_dir):
            start = time.clock()
            self.logger.info('predicting values : {0}'.format(data_type))


            [X, y]  = data

            pred = self.model.predict(X)

            nb_classes = len(event_list)

            if param_threshold_list == None:
                param_threshold_list = list()

            if data_type == 'validate' or data_type == 'test':
                f1_score_list = list()
                precision_list = list()
                recall_list = list()
            elif data_type =='train':
                f1_score_list = None
                precision_list = None
                recall_list = None


            for i in range(nb_classes):
                if data_type == 'validate':
                    precision, recall, thresholds = sklearn.metrics.precision_recall_curve(y[:,i], pred[:,i], pos_label = 1)
                    f1_score = np.asarray([2 * prec * rec / (prec + rec) for prec, rec in zip(precision, recall)])
                    max_f1_score = max(f1_score)
                    index = np.where(f1_score == max_f1_score)
                    param_threshold_list.append(thresholds[index])
                    f1_score_list.append(max_f1_score)
                    precision_list.append(precision[index])
                    recall_list.append(recall[index])
                elif data_type == 'test':
                    pred_binary_one_class = (pred[:,i] > param_threshold_list[i]).astype(int)
                    f1_score = sklearn.metrics.f1_score(y[:,i], pred_binary_one_class)
                    precision = sklearn.metrics.precision_score(y[:,i], pred_binary_one_class)
                    recall = sklearn.metrics.recall_score(y[:,i], pred_binary_one_class)
                    f1_score_list.append(f1_score)
                    precision_list.append(precision)
                    recall_list.append(recall)

            auc_roc_score = [sklearn.metrics.roc_auc_score(y[:, i], pred[:, i]) for i in range(nb_classes)]
            auc_pr_score = [sklearn.metrics.average_precision_score(y[:, i], pred[:, i]) for i in range(nb_classes)]

            score = pd.DataFrame(index = event_list)
            score['auc_roc_score'] = auc_roc_score
            score['auc_pr_score'] = auc_pr_score
            score['f1_score'] = f1_score_list
            score['precision_score'] = precision_list
            score['recall_score'] = recall_list


            self.logger.info( ('time elapsed : {0} seconds'.format(time.clock() - start)))
            self.logger.info( (data_type+' auc_roc : ', auc_roc_score))
            self.logger.info( (data_type+' auc_pr : ', auc_pr_score))

            if data_type == 'validate':
                self.logger.info((data_type+' threshold : ', param_threshold_list))
                self.logger.info( (data_type+' max f1 : ', f1_score_list))
                self.logger.info( (data_type+' precision : ', precision_list))
                self.logger.info( (data_type+' recall : ', recall_list))
            elif data_type == 'test':
                self.logger.info( (data_type+' max f1 : ', f1_score_list))
                self.logger.info( (data_type+' precision : ', precision_list))
                self.logger.info( (data_type+' recall : ', recall_list))
            elif data_type == 'train':
                pass

            return score, param_threshold_list

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        [train_X, train_y, val_X, val_y, test_X, test_y, train_num, val_num, test_num] = data

        validate_score, param_threshold_list = evaluate_score_revised(self, [val_X, val_y], 'validate')
        train_score, _ = evaluate_score_revised(self, [train_X, train_y], 'train')
        test_score, _ = evaluate_score_revised(self, [test_X, test_y], 'test', param_threshold_list=param_threshold_list)

        validate_score.to_csv(os.path.join(output_dir, 'validate_score.csv'))
        train_score.to_csv(os.path.join(output_dir, 'train_score.csv'))
        test_score.to_csv(os.path.join(output_dir, 'test_score.csv'))

        self.model.save_weights(os.path.join(output_dir, 'weight.hdf'))

        self.model_config['threshold'] = param_threshold_list
        with open(os.path.join(output_dir, 'data_description.txt'), 'w') as f:
            for key in self.data_description.keys():
                f.write('{0} : {1}\n'.format(key, self.data_description[key]))

        self.logger.info('data_description.txt saved')

        with open(os.path.join(output_dir, 'model_config.txt'), 'w') as f:
            for key in self.model_config.keys():
                if isinstance(self.model_config[key], collections.Iterable) and not isinstance(self.model_config[key], basestring):
                    self.model_config[key] = ', '.join([str(i) for i in self.model_config[key]])
                f.write('{0} : {1}\n'.format(key, self.model_config[key]))
        self.logger.info('model_config.txt saved')

    def save_kin_generator(self, generator, train_list, test_list, output_dir):

        self.model.save_weights(os.path.join(output_dir, 'weight.hdf'))

        with open(os.path.join(output_dir, 'data_description.txt'), 'w') as f:
            for key in self.data_description.keys():
                f.write('{0} : {1}\n'.format(key, self.data_description[key]))

        self.logger.info('data_description.txt saved')

        with open(os.path.join(output_dir, 'model_config.txt'), 'w') as f:
            for key in self.model_config.keys():
                if isinstance(self.model_config[key], collections.Iterable) and not isinstance(self.model_config[key], basestring):
                    self.model_config[key] = ', '.join([str(i) for i in self.model_config[key]])
                f.write('{0} : {1}\n'.format(key, self.model_config[key]))
        self.logger.info('model_config.txt saved')

        self.logger.info('predicted model output')

        def save_prediction(data_list, data_type, generator=generator):
            if not os.path.exists(os.path.join(output_dir, data_type)):
                os.makedirs(os.path.join(output_dir, data_type))

            save_dir = os.path.join(output_dir, data_type)
            for _ in data_list:
                X, y, key = generator.next()
                np.save(os.path.join(save_dir, '{0}_{1}_pred'.format(data_type, key)), self.model.predict(X))
                np.save(os.path.join(save_dir, '{0}_{1}_true'.format(data_type, key)), np.asarray(y))

        save_prediction(train_list, 'train')
        save_prediction(test_list, 'test')

    def set_data_description(self, data_description):
        self.data_description = data_description

    def set_model_config(self, key, val):
        self.model_config[key] = val

    def set_logger(self, logger):
        self.logger = logger



