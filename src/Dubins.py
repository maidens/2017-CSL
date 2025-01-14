import numpy as np
import time
from scipy.interpolate import RegularGridInterpolator
import warnings 
warnings.simplefilter("ignore")

def mod2pi(x):
    if x>=2*np.pi:
        return mod2pi(x-2.*np.pi)
    if x<0:
        return mod2pi(x+2.*np.pi)
    return x

def g_N(x):
    r = 0.25
    eps = 15.*np.pi/180
    cos_eps = np.cos(eps)
    if ((x[0] - x[3])**2 + (x[1] - x[4])**2 < r) and (((x[3] - x[0])*np.cos(x[2]) + (x[1] - x[4])*np.sin(x[2]))/np.sqrt((x[0] - x[3])**2 + (x[1] - x[4])**2) > cos_eps):
        return 1
    else:
        return 0

def g(k, x):
    return g_N(x)

def f(k, x, u, w, theta):
    z1, y1, th1, z2, y2, th2 = x
    v1, s1 = u
    v2, s2 = w
    L1, V_max1, S_max1, L2, V_max2, S_max2 = theta
    x_plus = [z1 + V_max1*v1*np.cos(th1), y1 + V_max1*v1*np.sin(th1), mod2pi(th1 + 1/L1*V_max1*v1*np.tan(S_max1*s1)), z2 + V_max2*v2*np.cos(th2), y2 + V_max2*v2*np.sin(th2), mod2pi(th2 + 1/L2*V_max2*v2*np.tan(S_max2*s2))]
    return np.array(x_plus)

def rho(x):
    return [(x[3] - x[0])*np.cos(x[2]) + (x[4] - x[1])*np.sin(x[2]),
           -(x[3] - x[0])*np.sin(x[2]) + (x[4] - x[1])*np.cos(x[2]),
            mod2pi(x[5] - x[2])
        ]

def rho_bar_inverse(x_bar):
    return [0, 0, 0, x_bar[0], x_bar[1], x_bar[2]]

def J_layer_reduced(k, x_bar, U, W, theta0, J_interpolated):
    x =  g(k, rho_bar_inverse(x_bar)) + min([max([J_interpolated(rho(f(k, rho_bar_inverse(x_bar), u, w, theta0))) for w in W] ) for u in U])
    return x
    
def J_layer_full(k, x, U, W, theta0, J_interpolated):
    x_plus = g(k, x) + min([max([J_interpolated(f(k, x, u, w, theta0)) for w in W] ) for u in U])
    return x_plus 

def compute_J_reduced(n, N, theta0, U, W, verbose=False):

    x0_all = np.linspace(-0.1, 1.5, n)
    x1_all = np.linspace(-0.5, 0.5, n)
    x2_all = np.linspace(0, 2*np.pi, n)

    # Initialize J_N
    J = np.zeros((n, n, n, N+1))
    for k in range(n):
        for j in range(n):
            for i in range(n):
                J[i, j, k, N] = g_N(rho_bar_inverse([x0_all[i], x1_all[j], x2_all[k]]))

    # Compute J_k for k < N by dynamic programming
    for t in range(N, 0, -1):
        if verbose:
            print "=========", t, "========="
        J_interpolated = RegularGridInterpolator((x0_all, x1_all, x2_all), J[:, :, :, t], method='nearest', bounds_error=False, fill_value=None)
        for k in range(n):
            if verbose:
                print k
            for j in range(n):
                for i in range(n):
                    J[i, j, k, t-1] = J_layer_reduced(t-1, [x0_all[i], x1_all[j], x2_all[k]], U, W, theta0, J_interpolated)
                    
    return J
    
def compute_J_full(n, N, theta0, U, W, verbose=False):
    
    t0 = time.time()

    x0_all = np.linspace(-0.1, 1.5, n)
    x1_all = np.linspace(-0.5, 0.5, n)
    x2_all = np.linspace(0, 2*np.pi, n)
    x3_all = np.linspace(-0.1, 1.5, n)
    x4_all = np.linspace(-0.5, 0.5, n)
    x5_all = np.linspace(0, 2*np.pi, n)

    # Initialize J_N
    J = np.zeros((n, n, n, n, n, n, N+1))
    for k in range(n):
        for j in range(n):
            for i in range(n):
                for h in range(n):
                    for g in range(n):
                        for l in range(n):
                            J[i, j, k, l, g, h, N] = g_N([x0_all[i], x1_all[j], x2_all[k], x3_all[l], x4_all[g], x5_all[h]])

    # Compute J_k for k < N by dynamic programming
    for t in range(N, 0, -1):
        if verbose:
            print "=========", t, "========="
        J_interpolated = RegularGridInterpolator((x0_all, x1_all, x2_all, x3_all, x4_all, x5_all), J[:, :, :, :, :, :, t], method='nearest', bounds_error=False, fill_value=None)
        for k in range(n):
            if verbose:
                print k
            for j in range(n):
                for i in range(n):
                    for h in range(n):
                        dt = time.time() - t0
                        if dt > 7200:
                            print "Timeout after %i seconds" %dt
                            return None
                        for g in range(n):
                            for l in range(n):
                                x = J_layer_full(t-1, [x0_all[i], x1_all[j], x2_all[k], x3_all[l], x4_all[g], x5_all[h]], U, W, theta0, J_interpolated)
                                J[i, j, k, l, g, h, t-1] = x
                    
    return J


if __name__ == '__main__':
    from mayavi import mlab
    
    # vehicle 1
    L1 = 1.        # car length (determines turning radius)
    V_max1 = 0.05  # maximum velocity
    S_max1 = 1.    # maximum steering angle
    
    # vehicle 2
    L2 = 1.
    V_max2 = 0.05
    S_max2 = 1.
    
    U = [(u1, u2) for u1 in [0, 1] for u2 in [-1, 0, 1]]
    W = [(w1, w2) for w1 in [0, 1] for w2 in [-1, 0, 1]]
    
    # vector of parameters
    theta0 = [L1, V_max1, S_max1, L2, V_max2, S_max2]
    
    n = 51
    N = 10

    # J = compute_J_reduced(n, N, theta0, U, W)
    # np.save('J.npy', J)


    # Load saved value function
    J = np.load('J.npy')

    # Plot the results
    J[:, :, 0, :] = 0
    J[:, :, -1, :] = 0
    mlab.contour3d(J[:, :, :, 0], contours=[0.5], opacity=0.4, color=(1.0, 0.0, 0.0))
    mlab.contour3d(J[:, :, :, N], contours=[0.5], color=(0.0, 0.0, 1.0))
    mlab.show()
