import h5py as h5
import pandas as pd
import numpy as np
import random

from predict.evaluation import evaluate

MASK = -1


def load_model(json_file, weights_file=None):
    import keras.models as kmodels
    with open(json_file, 'r') as f:
        model = f.read()
    model = kmodels.model_from_json(model)
    model.load_weights(weights_file)
    return model


def evaluate_all(y, z):
    keys = sorted(z.keys())
    p = [evaluate(y[k][:], z[k][:]) for k in keys]
    p = pd.concat(p)
    p.index = keys
    return p


def read_and_stack(reader, callback):
    x = []
    for o in reader:
        x.append(callback(*o))
    y = dict()
    for k in x[0].keys():
        y[k] = dict()
        for l in x[0][k].keys():
            y[k][l] = np.hstack([x[i][k][l] for i in range(len(x))])
    return y


def read_labels(path):
    f = h5.File(path)
    g = f['labels']
    l = dict()
    for k in g.keys():
        l[k] = [x.decode() for x in g[k].value]
    f.close()
    return l


def read_chromos(path):
    f = h5.File(path)
    chromos = sorted([x for x in f.keys() if x != 'labels'])
    f.close()
    return chromos


class DataReader(object):

    def __init__(self, path, chromos=None, shuffle=False, chunk_size=1,
                 loop=False, max_chunks=None):
        self.path = path
        if chromos is None:
            chromos = read_chromos(self.path)
        self.chromos = chromos
        self.shuffle = shuffle
        self.chunk_size = chunk_size
        self.loop = loop
        self.max_chunks = max_chunks

    def __iter__(self):
        self._iter_chromos = list(reversed(self.chromos))
        if self.shuffle:
            random.shuffle(self._iter_chromos)
        self._iter_idx = []
        self._n = 0
        return self

    def __next__(self):
        if self.max_chunks is not None and self._n == self.max_chunks:
            raise StopIteration
        if len(self._iter_idx) == 0:
            if len(self._iter_chromos) == 0:
                if self.loop:
                    iter(self)
                else:
                    raise StopIteration
            self._iter_chromo = self._iter_chromos.pop()
            f = h5.File(self.path)
            n = f['/%s/pos' % (self._iter_chromo)].shape[0]
            f.close()
            self._iter_idx = list(reversed(range(0, n, self.chunk_size)))
            if self.shuffle:
                random.shuffle(self._iter_idx)
        self._iter_i = self._iter_idx.pop()
        self._iter_j = self._iter_i + self.chunk_size
        self._n += 1
        return (self._iter_chromo, self._iter_i, self._iter_j)

    def next(self):
        return self.__next__()