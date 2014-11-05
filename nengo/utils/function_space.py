from __future__ import absolute_import

import numpy as np

import matplotlib.pyplot as plt

import nengo

def generate_functions(function, n, *arg_dists):
    """
    Parameters:

    function: callable,
       the function to be used as a basis, ex. gaussian
    n: int,
       number of functions to generate
    arg_dists: instances of nengo distributions
       distributions to sample arguments from, ex. mean of a gaussian function
    """

    # get argument samples to make different functions
    arg_samples = [arg_dist.sample(n) for arg_dist in arg_dists]

    functions = []
    for i in range(n):
        def func(point, i=i):
            args = [point]
            for arg_sample in arg_samples:
                args.append(arg_sample[i])
            return function(*args)
        functions.append(func)

    return functions


def uniform_cube(domain_dim, radius=1, d=0.001):
    """Returns uniformly spaced points in a hypercube.

    The hypercube is defined by the given radius and dimension.

    Parameters:
    ----------
    domain_dim: int
       the dimension of the domain

    radius: float, optional
       2 * radius is the length of a side of the hypercube

    d: float, optional
       the discretization spacing (a small float)

    Returns:
    -------
    ndarray of shape (domain_dim, radius/d)

    """

    if domain_dim == 1:
        domain_points = np.arange(-radius, radius, d)
        domain_points = domain_points.reshape(domain_points.shape[0], 1)
    else:
        axis = np.arange(-radius, radius, d)
        # uniformly spaced points in the hypercube of the domain
        grid = np.meshgrid(*[axis for _ in range(domain_dim)])
        domain_points = np.vstack(map(np.ravel, grid))
    return domain_points


def function_values(functions, domain_points):
    """The values of the function on the domain.

    Returns:
    --------
    ndarray of shape (n_points, n_functions)"""

    values = np.empty((len(domain_points), len(functions)))
    for j, point in enumerate(domain_points):
        for i, function in enumerate(functions):
            values[j, i] = function(point)
    return values


class Function_Space(object):
    """A helper class for using function spaces in nengo.

    Parameters:
    -----------
    fn: callable,
      The function that will be used for tiling the space.

    domain_dim: int,
      The dimension of the domain of ``fn``.

    n_functions: int, optional
      Number of functions used to tile the space.

    n_basis: int, optional
      Number of orthonormal basis functions to use

    d: float, optional
       the discretization factor (used in spacing the domain points)

    radius: float, optional
       2 * radius is the length of a side of the hypercube

    dist_args: list of nengo Distributions
       The distributions to sample functions from.

    """

    def __init__(self, fn, domain_dim, dist_args, n_functions=200, n_basis=20,
                 d=0.001, radius=1):

        self.domain = uniform_cube(domain_dim, radius, d)
        self.fns = function_values(generate_functions(fn, n_functions,
                                                      *dist_args),
                                   self.domain)

        self.dx = d ** self.domain.shape[1] # volume element for integration
        self.n_basis = n_basis

        #basis must be orthonormal
        self.U, self.S, V = np.linalg.svd(self.fns)
        self.basis = self.U[:, :self.n_basis] / np.sqrt(self.dx)

    def select_top_basis(self, n_basis):
        self.n_basis = n_basis
        self.basis = self.U[:, :n_basis] / np.sqrt(self.dx)

    def get_basis(self):
        return self.basis

    def singular_values(self):
        return self.S

    def reconstruct(self, coefficients):
        """Linear combination of the basis functions"""
        return np.dot(self.basis, coefficients)

    def encoder_coeffs(self):
        """Project encoder functions onto basis to get encoder coefficients."""
        return np.dot(self.fns.T, self.basis) * self.dx

    def signal_coeffs(self, signal):
        """Project a given signal onto basis to get signal coefficients.
           Size returned is (n_signals, n_basis)"""
        signal_coeff = np.dot(signal.T, self.basis) * self.dx
        if signal_coeff.shape[0] == 1:
            signal_coeff = signal_coeff.reshape((self.n_basis,))

        return signal_coeff
