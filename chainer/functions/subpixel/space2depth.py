from chainer import cuda
from chainer import function
from chainer.utils import type_check


class Space2Depth(function.Function):
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
        X = xp.reshape(X, (bsize, a, b))
        X = xp.split(X, b/self.r, 2)
        X = xp.concatenate([xp.expand_dims(x, 1) for x in X], 1)
        X = xp.split(X, a/self.r, 2)
        X = xp.concatenate([xp.expand_dims(x, 1) for x in X], 1)
        X = xp.transpose(X, (0, 1, 2, 4, 3))
        X = xp.reshape(X, (bsize, a/self.r, b/self.r, self.r**2))
        return X,

    def backward(self, inputs, grad_outputs):
        gy, = grad_outputs
        xp = cuda.get_array_module(gy)
        bsize, a, b, c = gy.shape
        gy = xp.reshape(gy, (bsize, a, b, self.r, self.r))
        gy = xp.transpose(gy, (0, 1, 2, 4, 3))
        gy = xp.split(gy, a, 1)
        gy = xp.concatenate([xp.squeeze(x) for x in gy], 2)
        gy = xp.split(gy, b, 1)  # b, [bsize, a*r, r]
        gy = xp.concatenate([xp.squeeze(x) for x in gy], 2)
        gy = xp.reshape(gy, (bsize, a*self.r, b*self.r, 1))
        return gy,


def space2depth(X, r):
    """Computes the space2depth transformation for subpixel calculations.
    Args:
        X (Variable): Variable holding a 4d array of
        shape (batch, dim1, dim2, channel)
        r (int): int specifying the upscaling factor.
    Returns:
        Variable: A variable holding the downscaled layer array from
        subpixel array sampling.
    .. note::
       This can be used to compute inverse super-resolution transformations.
       See http://arxiv.org/abs/1609.05158 for details.
    """
    c = X.data.shape[3]
    channel = c
    s2d = Space2Depth(r)
    if channel > 1:
        Xc = F.split_axis(X, channel, 3)
        X = F.concat([s2d(x) for x in Xc], 3)
    else:
        X = s2d(X)
    return X
