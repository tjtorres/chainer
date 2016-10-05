from chainer import cuda
from chainer import function
from chainer.utils import type_check


class Depth2Space(function.Function):

    """Depth to space transformation."""
    def __init__(self, r):
        self.r = r

    def check_type_forward(self, in_types):
        type_check.expect(in_types.size() == 1)
        type_check.expect(in_types[0].dtype == numpy.float32,
                          in_types[0].ndim == 4
                          )

    def forward(self, inputs):
        X, = inputs
        xp = cuda.get_array_module(X)
        bsize, a, b, c = X.shape
        X = xp.reshape(X, (bsize, a, b, self.r, self.r))
        X = xp.transpose(X, (0, 1, 2, 4, 3))
        X = xp.split(X, a, 1)
        X = xp.concatenate([xp.squeeze(x) for x in X], 2)
        X = xp.split(X, b, 1)
        X = xp.concatenate([xp.squeeze(x) for x in X], 2)
        X = xp.reshape(X, (bsize, a*self.r, b*self.r, 1))
        return X,

    def backward(self, inputs, grad_outputs):

        gy, = grad_outputs
        xp = cuda.get_array_module(gy)
        bsize, a, b, c = gy.shape
        gy = xp.reshape(gy, (bsize, a, b))
        gy = xp.split(gy, b/self.r, 2)
        gy = xp.concatenate([xp.expand_dims(x, 1) for x in gy], 1)
        gy = xp.split(gy, a/self.r, 2)
        gy = xp.concatenate([xp.expand_dims(x, 1) for x in gy], 1)
        gy = xp.transpose(gy, (0, 1, 2, 4, 3))
        gy = xp.reshape(gy, (bsize, a/self.r, b/self.r, self.r**2))
        return gy,


def depth2space(X, r):
    """Computes the depth2space transformation for subpixel calculations.
    Args:
        X (Variable): Variable holding a 4d array of
        shape (batch, dim1, dim2, channel*r)
        r (int): int specifying the upscaling factor.
    Returns:
        Variable: A variable holding the upscaled array from
        interspersed depth layers.
    .. note::
       This can be used to compute super-resolution transformations.
       See http://arxiv.org/abs/1609.05158 for details.
    """
    c = X.data.shape[3]
    channel = c / r**2
    d2s = Depth2Space(r)
    if channel > 1:
        Xc = F.split_axis(X, channel, 3)
        X = F.concat([d2s(x) for x in Xc], 3)
    else:
        X = d2s(X)
    return X
