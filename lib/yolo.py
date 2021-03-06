import numpy as np
import tensorflow as tf
from time import time
from .configs.process import cfg_yielder

class layer:
    def __init__(self, type, size = 0, c = 0, n = 0, h = 0, w = 0):
        self.type = type
        self.size = size
        self.c, self.n = (c, n) 
        self.h, self.w = (h, w)

class maxpool_layer(layer):
    def __init__(self, size, c, n, h, w, stride, pad):
        layer.__init__(self, 'MAXPOOL', size, c, n, h, w)
        self.stride = stride
        self.pad = pad

class convolu_layer(layer):
    def __init__(self, size, c, n, h, w, stride, pad):
        layer.__init__(self, 'CONVOLUTIONAL', size, c, n, h, w)
        self.stride = stride
        self.pad = pad

class connect_layer(layer):
    def __init__(self, size, c, n, h, w, 
        input_size, output_size):
        layer.__init__(self, 'CONNECTED', size, c, n, h, w)
        self.output_size = output_size
        self.input_size = input_size

class YOLO(object):

    layers = []
    S = int()
    model = str()

    def __init__(self, model):
        pick = ['face']
        self.labels = pick
        self.model = model
        self.layers = []
        self.build(model)
        self.layer_number = len(self.layers)
        weight_file = model +  '/yolo-face.weights'
        start = time()
        self.loadWeights(weight_file)
        stop = time()

    def build(self, model):
        cfg = model.split('-')[0]
        layers = cfg_yielder(cfg)
        for i, info in enumerate(layers):
            if i == 0: 
                self.S = info
                continue
            if len(info) == 1: new = layer(type = info[0])
            if info[0] == 'conv': new = convolu_layer(*info[1:])
            if info[0] == 'pool': new = maxpool_layer(*info[1:])
            if info[0] == 'conn': new = connect_layer(*info[1:])
            self.layers.append(new)

    def loadWeights(self, weight_path):
        self.startwith = np.array(
            np.memmap(weight_path, mode = 'r',
                offset = 0, shape = (),
                dtype = '(4)i4,'))
        offset = 16
        chunkMB = 1000
        chunk = int(chunkMB * 2**18) 
        
        for i in range(self.layer_number):
            l = self.layers[i]
            if l.type == "CONVOLUTIONAL":
                weight_number = l.n * l.c * l.size * l.size
                l.biases = np.memmap(weight_path, mode = 'r',
                    offset = offset, shape = (),
                    dtype = '({})float32,'.format(l.n))
                offset += 4 * l.n
                l.weights = np.memmap(weight_path, mode = 'r',
                    offset = offset, shape = (),
                    dtype = '({})float32,'.format(weight_number))
                offset += 4 * weight_number

            elif l.type == "CONNECTED":
                bias_number = l.output_size
                weight_number = l.output_size * l.input_size
                l.biases = np.memmap(weight_path, mode = 'r',
                    offset = offset, shape = (),
                    dtype = '({})float32,'.format(bias_number))
                offset += bias_number * 4
            
                chunks  = [chunk] * int(weight_number / chunk) 
                chunks += [weight_number % chunk]
                l.weights = np.array([], dtype = np.float32)
                for c in chunks:
                    l.weights = np.concatenate((l.weights,
                        np.memmap(weight_path, mode = 'r',
                        offset = offset, shape = (),
                        dtype = '({})float32,'.format(c))))
                    offset += c * 4

        for i in range(self.layer_number):
            l = self.layers[i]
            
            if l.type == 'CONVOLUTIONAL':
                weight_array = l.weights
                weight_array = np.reshape(weight_array,
                	[l.n, l.c, l.size, l.size])
                weight_array = weight_array.transpose([2,3,1,0])
                l.weights = weight_array

            if l.type == 'CONNECTED':
                weight_array = l.weights
                weight_array = np.reshape(weight_array,
                	[l.input_size, l.output_size])
                l.weights = weight_array
