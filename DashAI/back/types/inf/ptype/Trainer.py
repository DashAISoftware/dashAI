# flake8: noqa

from copy import deepcopy

import numpy as np
from scipy import optimize

from DashAI.back.types.inf.ptype.Column import ANOMALIES_INDEX, MISSING_INDEX
from DashAI.back.types.inf.ptype.Machine import PI
from DashAI.back.types.inf.ptype.utils import (
    LOG_EPS,
    log_weighted_sum_normalize_probs,
    normalize_log_probs,
)


def likelihoods(PI, logP, k):
    _, _, _, log_mx, sm = likelihoods_normalize(PI, logP, k)
    return log_mx + np.log(sm)


def likelihoods_normalize(PI, logP, k):
    return log_weighted_sum_normalize_probs(
        PI[0],
        logP[:, k + LLHOOD_TYPE_START_INDEX],
        PI[1],
        logP[:, MISSING_INDEX - 1],
        PI[2],
        logP[:, ANOMALIES_INDEX - 1],
    )


def sum_weighted_likelihoods(counts_array, logP, k):
    return (counts_array * likelihoods(PI, logP, k)).sum()


def _vecnorm(x, ord=2):
    if ord == np.Inf:
        return np.amax(np.abs(x))
    elif ord == -np.Inf:
        return np.amin(np.abs(x))
    else:
        return np.sum(np.abs(x) ** ord, axis=0) ** (1.0 / ord)


# todo: rename
def wurble(a, b, c):
    return str(a) + "*" + str(b) + "*" + str(c)


LLHOOD_TYPE_START_INDEX = 2


class Trainer:
    """A Trainer object.

    :param machines: PFSMs to train.
    :param dfs: data frames to train with.
    :param labels: column types labeled by hand, where _label[i][j] denotes the type of j^th column in i^th dataframe.
    """

    def __init__(self, machines, dfs, labels):
        self.machines = machines
        self.dfs = dfs
        self.labels = labels
        self.unique_vals = np.concatenate([np.unique(df.values) for df in dfs])
        self.dfs_unique_vals_counts = Trainer.get_unique_vals_counts(dfs)
        self.machines.set_unique_values(self.unique_vals)

    @staticmethod
    def get_unique_vals_counts(dfs):
        # Finding unique values and their counts
        return {
            i: {
                col: [vs, np.array(counts)]
                for col, (vs, counts) in {
                    col: np.unique(df[col].tolist(), return_counts=True)
                    for col in df.columns
                }.items()
            }
            for i, df in enumerate(dfs)
        }

    def train(self, max_iter=20, uniformly=False, threshold=1e-10):
        """Train the PFSMs.

        :param max_iter: the maximum number of iterations the optimization algorithm runs as long as it's not converged.
        :param uniformly: a binary variable used to initialize the PFSMs - True allows initializing uniformly rather than using hand-crafted values.
        :param threshold:
        :return:
        """
        if uniformly:
            self.machines.initialize_uniformly()
            self.machines.normalize_params()

        initial = deepcopy(
            self.machines
        )  # shouldn't need this, but too much mutation going on
        training_error = [self.calculate_total_error(self.dfs, self.labels)]

        # Iterates over whole data points
        for n in range(max_iter):
            # Trains machines using all of the training data frames
            self.update_PFSMs()

            # Calculate training and validation error at each iteration
            training_error.append(self.calculate_total_error(self.dfs, self.labels))
            print(training_error)

            if n > 0 and training_error[-2] - training_error[-1] < threshold:
                break

        return initial, self.machines, training_error

    def calculate_total_error(self, dfs, labels):
        all_probs = self.machines.machine_probabilities(self.unique_vals)

        error = 0.0
        for j, (df, df_labels) in enumerate(zip(dfs, labels)):
            for i, column_name in enumerate(list(df.columns)):
                error += self.f_col(all_probs, j, column_name, df_labels[i] - 1)
                # print(
                #     column_name, self.f_col(all_probs, j, column_name, df_labels[i] - 1)
                # )

        return error

    def update_PFSMs(self):
        w_j_z, _ = self.conjugate_gradient(self.machines.get_all_parameters_z())
        self.machines.set_all_probabilities_z(w_j_z)

        for machine in self.machines.forType.values():
            machine.normalize()

    def conjugate_gradient(self, w, J=10, gtol=1e-5):
        d, g = [], []

        gnorm = gtol + 1
        j = 0
        while gnorm > gtol and j < J:
            if j == 0:
                g.append(self.g_cols(w))
                d.append(-g[j])

            res = optimize.line_search(
                self.f_cols, self.g_cols, w, d[j], g[j], self.f_cols(w)
            )
            if res[0] is None:
                return w, j
            else:
                alpha = res[0]
                w = w + alpha * d[j]

                g.append(self.g_cols(w))
                gnorm = _vecnorm(g[j + 1], ord=np.Inf)

                beta_j = max(
                    0, np.dot(g[j + 1].T, g[j + 1] - g[j]) / np.dot(g[j], g[j])
                )  # eq. 7.74 Polak-Ribiere
                d.append(-g[j + 1] + beta_j * d[j])  # eq.7.67

                j += 1

        return w, j

    def f_col(self, all_probs, i, column_name, y_i):
        [temp_x, counts_array] = self.dfs_unique_vals_counts[i][column_name]
        logP = np.array([all_probs[x_i] for x_i in temp_x])
        q = [
            sum_weighted_likelihoods(counts_array, logP, k)
            for k in range(len(self.machines.forType))
        ]

        temp = normalize_log_probs(q)[y_i]
        if temp == 0:
            return 800.0
        else:
            return -np.log(temp)

    def f_cols(self, w_j_z):
        # f: the objective function to minimize. (it is equal to - \sum_{all columns} log p(t=k|X) where k is the correct column type.)
        # Set params: init-transition-final
        self.machines.set_all_probabilities_z(w_j_z)

        # Generate probabilities
        all_probs = self.machines.machine_probabilities(self.unique_vals)

        error = 0.0
        for i, (data_frame, labels) in enumerate(zip(self.dfs, self.labels)):
            for j, column_name in enumerate(list(data_frame.columns)):
                error += self.f_col(all_probs, i, column_name, labels[j] - 1)
        return error

    def do_some_stuff(
        self,
        marginals,
        x_i,
        l,
        temp_g_j,
        state_indices,
        machine,
        alpha,
        t,
        r,
        y_i,
        temp_gra_i,
        counts_array_i,
    ):
        indices_nonzero = np.where(marginals[x_i][l] != 0.0)
        if len(indices_nonzero[0]) != 0:
            q_s = indices_nonzero[0]
            q_primes = indices_nonzero[1]
            for q, q_prime in zip(q_s, q_primes):
                temp_g_j[
                    state_indices[
                        wurble(machine.states[q], alpha, machine.states[q_prime])
                    ]
                ] += self.gradient_transition_marginals(
                    marginals,
                    machine.states[q],
                    alpha,
                    machine.states[q_prime],
                    t,
                    r,
                    str(x_i),
                    y_i,
                    temp_gra_i,
                    counts_array_i,
                )

    def g_col_marginals(self, all_probs, i, col_name, y_i):
        [xs, counts] = self.dfs_unique_vals_counts[i][col_name]
        logP = np.array([all_probs[x] for x in xs])

        # calculates posterior values of types
        r = [
            sum_weighted_likelihoods(counts, logP, k)
            for k in range(len(self.machines.forType))
        ]

        # calculates the gradients for initial, transition, and final probabilities. (note that it is only for non-zero probabilities at the moment.)
        g_j = []
        for t, ty in enumerate(self.machines.types):
            machine = self.machines.forType[ty]
            x_i_indices = np.where(logP[:, t + 2] != LOG_EPS)[0]

            possible_states = [q for q in machine.states if machine.I[q] != LOG_EPS]
            A = likelihoods(PI, logP, t)
            temp_gra = np.exp(PI[0] + logP[:, t + 2] - A)

            # gradient for initial state parameters
            temp_g_j = [
                self.gradient_initial(
                    q,
                    t,
                    xs[x_i_indices],
                    r,
                    temp_gra[x_i_indices],
                    counts[x_i_indices],
                    y_i,
                )
                for q in possible_states
            ]
            g_j = g_j + temp_g_j

            # gradient for transition parameters
            if t == 1:
                marginals = {
                    x_i: np.ones((len(x_i), 1, 1))
                    if p_x_i[t + 2] != LOG_EPS
                    else np.zeros((len(x_i), 1, 1))
                    for x_i, p_x_i in zip(xs, logP)
                }
            else:
                marginals = {
                    x_i: machine.run_forward_backward(str(x_i))
                    if p_x_i[t + 2] != LOG_EPS
                    else np.zeros((len(x_i), len(x_i)))
                    for x_i, p_x_i in zip(xs, logP)
                }
            state_indices = {}
            counter = 0
            temp_g_j = []
            for a in machine.T:
                for b in machine.T[a]:
                    for c in machine.T[a][b]:
                        state_indices[wurble(a, b, c)] = counter
                        temp_g_j.append(0)
                        counter += 1

            for x_i_index, (x_i, temp_gra_i, counts_array_i) in enumerate(
                zip(xs[x_i_indices], temp_gra[x_i_indices], counts[x_i_indices])
            ):
                if logP[x_i_index, t + 2] != LOG_EPS:
                    if t == 1:
                        common_chars = [
                            x for x in machine.alphabet if x in list(str(x_i))
                        ]
                        for alpha in common_chars:
                            common_char_ls = np.where(list(str(x_i)) == alpha)[0]
                            for l in common_char_ls:
                                self.do_some_stuff(
                                    marginals,
                                    x_i,
                                    l,
                                    temp_g_j,
                                    state_indices,
                                    machine,
                                    alpha,
                                    t,
                                    r,
                                    y_i,
                                    temp_gra_i,
                                    counts_array_i,
                                )

                    else:
                        for l, alpha in enumerate(str(x_i)):
                            if alpha in machine.alphabet:
                                self.do_some_stuff(
                                    marginals,
                                    x_i,
                                    l,
                                    temp_g_j,
                                    state_indices,
                                    machine,
                                    alpha,
                                    t,
                                    r,
                                    y_i,
                                    temp_gra_i,
                                    counts_array_i,
                                )
            g_j = g_j + temp_g_j

            # gradient for final-state parameters
            for state in machine.F:
                if machine.F[state] != LOG_EPS:
                    g_j.append(
                        self.gradient_final(
                            state,
                            t,
                            xs[x_i_indices],
                            r,
                            temp_gra[x_i_indices],
                            counts[x_i_indices],
                            y_i,
                        )
                    )

        return -np.array(g_j) / counts.sum()

    def g_cols(self, w_j_z):
        # calculates the gradient vector, i.e. df/dw (=df/dz * dz/dw) where f is the object function to minimize.
        # it returns -g_j because of minimizing instead of maximizing. see the objective function.

        self.machines.set_all_probabilities_z(w_j_z)
        all_probs = self.machines.machine_probabilities(self.unique_vals)

        q_total = None

        for i, (df, labels) in enumerate(zip(self.dfs, self.labels)):
            for j, column_name in enumerate(list(df.columns)):
                if q_total is None:
                    q_total = self.g_col_marginals(
                        all_probs, i, column_name, labels[j] - 1
                    )
                else:
                    q_total += self.g_col_marginals(
                        all_probs, i, column_name, labels[j] - 1
                    )

        return q_total

    ###################### GRADIENT HELPERS #######################
    def scale_wrt_type(self, gradient, q, t, y_i):
        temp = normalize_log_probs(q)[t]
        return gradient * (1 - temp) if t == y_i else -1 * gradient * temp

    def gradient_initial(self, state, t, x, q, temp, counter, y_i):
        machine = self.machines.forType[self.machines.types[t]]
        exp_param = 1 - np.exp(machine.I[state])

        cs = np.array([machine.gradient_initial_state(str(x_i), state) for x_i in x])

        gradient = (temp * counter * cs * exp_param).sum()
        return self.scale_wrt_type(gradient, q, t, y_i)

    def gradient_transition_marginals(
        self, marginals, a, b, c, t, q, x, y_i, temp_gra, counts_array
    ):
        machine = self.machines.forType[self.machines.types[t]]
        temp_mult = (
            temp_gra
            * machine.gradient_abc_new_optimized_marginals(
                marginals[x], str(x), a, b, c
            )
            * counts_array
        )
        exp_param = 1 - np.exp(machine.T[a][b][c])
        gradient = exp_param * temp_mult

        return self.scale_wrt_type(gradient, q, t, y_i)

    def gradient_final(self, final_state, t, x, q, temp, counter, y_i):
        machine = self.machines.forType[self.machines.types[t]]
        exp_param = 1 - np.exp(machine.F[final_state])

        cs = np.array(
            [machine.gradient_final_state(str(x_i), final_state) for x_i in x]
        )
        gradient = sum(temp * counter * cs * exp_param)

        return self.scale_wrt_type(gradient, q, t, y_i)
