# # flake8: noqa

import numpy as np

LOG_EPS = -1e150


def contains_all(_str, _list):
    res = True
    for s in _str:
        if s not in _list:
            res = False
            break
    return res
    # return 0 not in [s in list for s in str]


# ###################### STABLE CALCULATION METHODS #######################
def normalise_safe(xs):
    return xs if np.max(xs) == 0.0 else xs / xs.sum()


def log_sum_probs(log_p1, log_p2):
    log_mx = np.max([log_p1, log_p2])

    return log_mx + np.log(np.exp(log_p1 - log_mx) + np.exp(log_p2 - log_mx))


def log_weighted_sum_normalize_probs(pi_1, log_p1, pi_2, log_p2, pi_3, log_p3):
    x_1 = np.log(pi_1) + log_p1
    x_2 = np.log(pi_2) + log_p2
    x_3 = np.log(pi_3) + log_p3

    xs = [x_1, x_2, x_3]
    log_mx = np.max(xs, axis=0)

    sm = (
        (log_p1 != LOG_EPS) * np.exp(x_1 - log_mx)
        + (log_p2 != LOG_EPS) * np.exp(x_2 - log_mx)
        + (log_p3 != LOG_EPS) * np.exp(x_3 - log_mx)
    )
    return x_1, x_2, x_3, log_mx, sm


def normalize_log_probs(probs):
    reduced_probs = np.exp(probs - max(probs))
    return reduced_probs / reduced_probs.sum()
