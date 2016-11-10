import numpy as np
from scipy import misc, linalg
from copt.prox_tv import prox_tv1d, prox_tv2d, prox_tv1d_rows, prox_tv1d_cols
from copt import fmin_three_split, proximal_gradient
from copt.utils import Trace
import pylab as plt

face = misc.imresize(misc.face(gray=True), 0.15)
face = face.astype(np.float) / 255.

# generate measurements as
# b = A ground_truth + noise
# where X is a random matrix
n_rows, n_cols = face.shape
n_features = face.shape[0] * face.shape[1]
np.random.seed(0)
n_samples = n_features // 10


print('n_samples: %s, n_features: %s (%s)' % (n_samples, n_features, face.shape))
A = np.random.uniform(-1, 1, size=(n_samples, n_features))
for i in range(A.shape[0]):
    A[i] /= linalg.norm(A[i])
b = A.dot(face.ravel()) + 20.0 * np.random.randn(n_samples)
print(A.shape)


def TV(w):
    img = w.reshape((n_rows, n_cols))
    tmp1 = np.abs(np.diff(img, axis=0))
    tmp2 = np.abs(np.diff(img, axis=1))
    return tmp1.sum() + tmp2.sum()

l2_reg = 0
def obj_fun(x):
    return 0.5 * np.linalg.norm(b - A.dot(x)) ** 2 / A.shape[0] + 0.5 * l2_reg * x.dot(x)

def grad(x):
    return - A.T.dot(b - A.dot(x)) / A.shape[0] + l2_reg * x


from lightning.impl.sag import get_auto_step_size, get_dataset
ds = get_dataset(A, order="c")
eta = get_auto_step_size(ds, l2_reg, 'squared')
# eta = A.shape[0] / linalg.norm(A.T.dot(A))  # XXX need to divide by A.shape[0]??
# print(eta2, eta)

for beta in [1e-1]:

    max_iter = 50000
    step_size = eta
    backtracking = False
    # eta = 100 * eta
    trace_three = Trace(lambda x: obj_fun(x) + beta * TV(x))
    fmin_three_split(obj_fun, grad, prox_tv1d_cols, prox_tv1d_rows,
                     np.zeros(n_features), verbose=False,
                     step_size=step_size, g_prox_args=(n_rows, n_cols), h_prox_args=(n_rows, n_cols),
                     callback=trace_three, max_iter=max_iter, tol=0., backtracking=backtracking)

    trace_gd = Trace(lambda x: obj_fun(x) + beta * TV(x))
    proximal_gradient(obj_fun, grad, np.zeros(n_features), g_prox=prox_tv2d, callback=trace_gd,
                      g_prox_args=(n_rows, n_cols, int(1e3), 1.0),
                      step_size=step_size, max_iter=max_iter, tol=0.,
                      backtracking=backtracking, verbose=False)


    # plotting code
    fmin = min(np.min(trace_three.vals), np.min(trace_gd.vals))
    scale = (np.array(trace_three.vals) - fmin)[0]
    plt.figure()
    plt.title(r'$\lambda=%s$' % beta)
    plt.plot(trace_three.times, (np.array(trace_three.vals) - fmin) / scale,
             label='Three operator splitting', lw=4, marker='o',
             markevery=5000)
    plt.plot(np.array(trace_gd.times), (np.array(trace_gd.vals) - fmin) / scale, label='ProxGD', lw=4, marker='h',
             markevery=5000)
    plt.legend()
    plt.yscale('log')
    plt.grid()
    plt.show()
