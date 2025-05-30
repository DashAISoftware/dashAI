from datetime import timedelta

import functools
import numpy.ma as ma
import numpy as np
import matplotlib.pyplot as plt
import os
import pandas as pd
import pathlib

LOG_EPS = -1e150

report_begin_str = (
    "\\documentclass[a4paper]{article} \n \\usepackage[english]{babel} \n \\usepackage[utf8x]"
    "{inputenc} \n \\usepackage[T1]{fontenc} \n \\usepackage[a4paper, top = 3cm, bottom = 2cm, "
    "left = 3cm, right = 3cm, marginparwidth = 1.75cm]{geometry}"
)
report_being_str2 = (
    "\\usepackage{amsmath} \n \\usepackage{amsthm} \n \\usepackage{amsfonts} \n \\usepackage{graphicx} \n \\usepackage[colorinlistoftodos]{todonotes} \n \\usepackage[colorlinks = true, allcolors = blue]{hyperref} \n \\usepackage{multirow} \n \\usepackage{siunitx, etoolbox} \n \\usepackage{subcaption} \n \\usepackage{tikz} \n \\usepackage{standalone} \n \\usetikzlibrary{arrows, automata} \n \\usepackage{listings} \n "
    "\\usepackage{color} \n \\usepackage{textcomp} \n \\theoremstyle{definition} \n \\newtheorem{definition}{Definition} \n \\sisetup{ \n table - align - uncertainty = true, \n separate - uncertainty = true, \n} \n \\renewrobustcmd{\\bfseries}{\\fontseries{b}\\selectfont} \n \\renewrobustcmd {\\boldmath}{} \n \\begin{document}"
)


# https://stackoverflow.com/questions/25389095/python-get-path-of-root-project-structure
def project_root():
    return os.path.dirname(os.path.abspath(__file__))
    return Path(__file__).parent.parent

# TEXT MANIPULATION METHODS #######################
def chop_microseconds(delta):
    return delta - timedelta(microseconds=delta.microseconds)


def convert_to_bold(string):
    return "\033[1m" + string + "\033[0m"


def convert_to_bold_for_latex(string):
    return "\\textbf{" + string + "}"


def remove_digits(s):
    return "".join(i for i in s if not i.isdigit())


def remove_whitespaces_head_and_tail(s):
    if len(s) != 0:
        # remove leading and trailing whitespace
        if s[0] == " ":
            s = s[1:]
        if s[-1] == " ":
            s = s[:-1]
    return s


def set_precision(val, prec=10):
    return round(val, prec)


def llhoods_with_precision(llhoods, prec=40):
    for i in range(len(llhoods)):
        llhoods[i] = set_precision(llhoods[i], prec)
    return llhoods


def contains_all(_str, _list):
    res = True
    for s in _str:
        if s not in _list:
            res = False
            break
    return res
    # return 0 not in [s in list for s in str]


###################### STABLE CALCULATION METHODS #######################
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


def logdot(a, b):
    max_a, max_b = np.max(a), np.max(b)
    exp_a, exp_b = np.exp(a - max_a), np.exp(b - max_b)
    c = np.log(np.dot(exp_a, exp_b)) + max_a + max_b

    return c


def ma_multidot(arrays):
    return functools.reduce(ma.dot, arrays)


def multi_logdot(Xs):
    max_Xs = [np.max(X) for X in Xs]
    exp_Xs = [np.exp(X - max_X) for X, max_X in zip(Xs, max_Xs)]
    res = np.linalg.multi_dot(exp_Xs)
    res[np.where(res == 0)] = LOG_EPS
    return np.log(res) + sum(max_Xs)


###############################################################
###################### DATA I/O METHODS #######################
###############################################################
# writing data
def write_data(data, filepath="../../automata/example.dat"):
    f = open(filepath, "w")
    for line in data:
        f.write(str(line) + "\n")
    f.close()


def print_to_file(txt, filename="output.txt"):
    with open(filename, "a+") as f:
        f.write(txt + "\n")


def create_folders(model, _start_over_report):
    """ Creates folders for a column in a dataset
    :param _start_over_report: True/False. True allows creating a new report and False allows appending to the existing report
    :return:
    """
    main_folder = model.config.current_experiment_folder

    # Create inputs, outputs, and results folders
    pathlib.Path(main_folder).mkdir(parents=True, exist_ok=True)
    pathlib.Path(main_folder + "/inputs").mkdir(parents=True, exist_ok=True)
    pathlib.Path(main_folder + "/outputs").mkdir(parents=True, exist_ok=True)
    pathlib.Path(main_folder + "/results").mkdir(parents=True, exist_ok=True)

    # Either creates a new file or appends to an existing one
    if _start_over_report:
        with open(
            model.config.main_experiments_folder
            + "/"
            + model.config.dataset_name
            + "/report.tex",
            "w",
        ) as f:
            # Prints latex file structure
            print(report_begin_str, file=f)
            print(report_being_str2, file=f)

            # Prints title, and section header, etc.
            print(
                "\\title{The Report for the File Named "
                + model.config.dataset_name
                + "} \n \\maketitle",
                file=f,
            )
            print("The number of columns is " + str(model.data.shape[1]) + ".", file=f)
            print("The number of rows is " + str(model.data.shape[0]) + ".", file=f)
            print(
                "\section{Column Name: "
                + model.config.current_column_name.replace("_", "\_")
                + "}",
                file=f,
            )
    else:
        with open(
            model.config.main_experiments_folder
            + "/"
            + model.config.dataset_name
            + "/report.tex",
            "a",
        ) as f:
            print(
                "\section{Column Name: "
                + model.config.current_column_name.replace("_", "\_")
                + "}",
                file=f,
            )


# copies some columns directly
def copy_columns_between_dicts(dict_source, dict_target, columns):
    for column in columns:
        dict_target[column] = dict_source[column]
    return dict_target


###############################################################
#################### VISUALISATION METHODS ####################
###############################################################
def plot_matrix(
    X,
    title="Title",
    xlabel="xlabel",
    ylabel="ylabel",
    figsize=None,
    vmax_=None,
    xticklabels=None,
    yticklabels=None,
    cmap=plt.cm.gray_r,
):
    if figsize is None:
        plt.figure(figsize=(18, 6))
    else:
        plt.figure(figsize=figsize)
    if vmax_ is None:
        VMAX = np.max(X)
    else:
        VMAX = vmax_
    if yticklabels is None:
        pass
    else:
        plt.yticks(range(len(yticklabels)), yticklabels)

    if xticklabels is None:
        pass
    else:
        plt.xticks(range(len(xticklabels)), xticklabels, rotation=90)

    plt.imshow(X, interpolation="none", vmax=VMAX, vmin=0, aspect="auto", cmap=cmap)
    plt.colorbar()
    plt.xlabel(xlabel, fontsize=20)
    plt.ylabel(ylabel, fontsize=20)
    plt.title(title, fontsize=20)
    plt.show()


def plot_normal_type_histogram(x, current_experiment_folder):
    plt.figure()
    plt.hist(np.array(x), bins=20)
    plt.ylabel("data values")
    plt.savefig(current_experiment_folder + "/outputs/histogram.eps", dpi=1000)
    plt.close()


def bar_plot_type_posteriors(
    x, y, current_experiment_folder, _display=False, _save=False
):
    # plots the column posterior in order to show the prediction for column's type
    N = len(y)
    y_pos = np.arange(N)
    plt.figure(figsize=(N * 1.2, 4))
    plt.bar(y_pos, x, align="center", alpha=0.5, width=0.4)
    plt.xticks(y_pos, y)
    plt.ylim(0, 1)
    plt.ylabel("Probability")
    plt.title("Posterior of column type: p(t=k|X)")
    if _save:
        plt.savefig(
            current_experiment_folder + "/outputs/type_posteriors.eps", dpi=1000
        )
    if _display:
        plt.show()
    else:
        plt.close()


# source: http://scipy-cookbook.readthedocs.io/items/Matplotlib_HintonDiagrams.html
def _blob(x, y, area, colour):
    """
    Draws a square-shaped blob with the given area (< 1) at
    the given coordinates.
    """
    hs = np.sqrt(area) / 2
    xcorners = np.array([x - hs, x + hs, x + hs, x - hs])
    ycorners = np.array([y - hs, y - hs, y + hs, y + hs])
    plt.fill(xcorners, ycorners, colour, edgecolor=colour)


# def plot_hinton(W, method=None, _max_value=None, xticklabels=None, yticklabels=None, path=None):
#     """
#     Draws a Hinton diagram for visualizing a weight matrix.
#     Temporarily disables matplotlib interactive mode if it is on,
#     otherwise this takes forever.
#     """
#
#     reenable = False
#     if plt.isinteractive():
#         plt.ioff()
#     plt.clf()
#
#     if reenable:
#         plt.ion()
#
#     special.hinton(W, max_value=_max_value)
#     if xticklabels is not None:
#         plt.xticks(np.arange(len(xticklabels)), xticklabels, rotation=90, fontsize=13)
#     if yticklabels is not None:
#         plt.yticks(np.arange(len(xticklabels)), yticklabels, fontsize=13)
#
#     plt.xlabel('true type', fontsize=17)
#     plt.ylabel('predicted type', fontsize=17)
#
#     if path is not None:
#         plt.savefig(path, dpi=1000, bbox_inches="tight")
#
#     # plt.show()


###############################################################
#################### LATEX METHODS ############################
###############################################################
def print_figure_latex(column_name, f):
    print(
        "\\begin{figure}[!h] \n \\centering \n \\includegraphics[width = \\textwidth]{"
        + column_name
        + "/outputs/type_posteriors.eps} \n \\caption{The posterior probability distribution of the column type for column named "
        + column_name.replace("_", "\\_")
        + ".} \n \\label{fig:"
        + column_name
        + "} \n \\end{figure}",
        file=f,
    )


def print_line_latex(txt, f):
    print(txt, file=f)


def print_row_type_dist_table_latex(
    current_experiment_folder, num_normal_cells, num_missings, num_catch_alls, num_data
):
    table_row_type_dist = pd.DataFrame(
        columns=["", "Number of Entries", "Proportion to the Total Num. of Rows"]
    )

    table_row_type_dist.loc[0] = [
        "Row Type",
        "Number of Entries",
        "Proportion to the Total Num. of Rows",
    ]
    table_row_type_dist.loc[1] = [
        "Normal",
        num_normal_cells,
        round(1.0 * num_normal_cells / num_data, 2),
    ]
    table_row_type_dist.loc[2] = [
        "Missing",
        num_missings,
        round((1.0 * num_missings) / num_data, 2),
    ]
    table_row_type_dist.loc[3] = [
        "Catch-all",
        num_catch_alls,
        round((1.0 * num_catch_alls) / num_data, 2),
    ]

    with open(current_experiment_folder + "/outputs/table_row_type_dist.tex", "w") as f:
        f.write(
            "\\begin{tabular}{|"
            + " | ".join(["c"] * len(table_row_type_dist.columns))
            + "|}\n"
        )
        for i, row in table_row_type_dist.iterrows():
            f.write("\\hline ")
            if i == 0:
                f.write(
                    " & ".join(["\\bfseries " + str(x) for x in row.values]) + " \\\\\n"
                )
            else:
                f.write(" & ".join([str(x) for x in row.values]) + " \\\\\n")
        f.write("\\hline ")
        f.write("\\end{tabular}")


def print_statistics_table_latex(x, current_experiment_folder):
    table_histogram = pd.DataFrame(columns=["Min.", "Max.", "Mean", "Std"])
    table_histogram.loc[0] = ["Min.", "Max.", "Avg.", "Std."]
    table_histogram.loc[1] = [
        round(np.min(x), 2),
        round(np.max(x), 2),
        round(np.mean(x), 2),
        round(np.std(x), 2),
    ]
    with open(
        current_experiment_folder + "/outputs/table_histogram_detail.tex", "w"
    ) as f:
        f.write(
            "\\begin{tabular}{|"
            + " | ".join(["c"] * len(table_histogram.columns))
            + "|}\n"
        )
        for i, row in table_histogram.iterrows():
            f.write("\\hline ")
            if i == 0:
                f.write(
                    " & ".join(["\\bfseries " + str(x) for x in row.values]) + " \\\\\n"
                )
            else:
                f.write(" & ".join([str(x) for x in row.values]) + " \\\\\n")
        f.write("\\hline ")
        f.write("\\end{tabular}")


def print_table_latex(x, current_experiment_folder):
    table_histogram = pd.DataFrame(columns=["Min.", "Max.", "Mean", "Std"])
    table_histogram.loc[0] = ["Min.", "Max.", "Avg.", "Std."]
    table_histogram.loc[1] = [
        round(np.min(x), 2),
        round(np.max(x), 2),
        round(np.mean(x), 2),
        round(np.std(x), 2),
    ]
    with open(
        current_experiment_folder + "/outputs/table_histogram_detail.tex", "w"
    ) as f:
        f.write(
            "\\begin{tabular}{|"
            + " | ".join(["c"] * len(table_histogram.columns))
            + "|}\n"
        )
        for i, row in table_histogram.iterrows():
            f.write("\\hline ")
            if i == 0:
                f.write(
                    " & ".join(["\\bfseries " + str(x) for x in row.values]) + " \\\\\n"
                )
            else:
                f.write(" & ".join([str(x) for x in row.values]) + " \\\\\n")
        f.write("\\hline ")
        f.write("\\end{tabular}")


def evaluate_types(
    _dataset_name, _ptype, _header=None,
):
    dataset_path = "../data/" + _dataset_name + ".csv"
    annotation_path = "../annotations/" + _dataset_name + ".csv"

    df = pd.read_csv(
        dataset_path,
        sep=",",
        encoding="ISO-8859-1",
        dtype=str,
        header=_header,
        keep_default_na=False,
        skipinitialspace=True,
    )
    annotations = pd.read_csv(
        annotation_path,
        sep=",",
        encoding="ISO-8859-1",
        dtype=str,
        keep_default_na=False,
    )

    true_values = annotations["Type"].values.tolist()
    true_values = [true_value.split("-")[0] for true_value in true_values]

    predictions = [col.type for col in _ptype.cols.values()]
    predictions = [
        prediction.replace("date-eu", "date")
        .replace("date-iso-8601", "date")
        .replace("date-non-std-subtype", "date")
        .replace("date-non-std", "date")
        for prediction in predictions
    ]

    column_names = list(_ptype.cols.keys())

    correct_, false_ = 0.0, 0.0
    for i, (prediction, true_value) in enumerate(zip(predictions, true_values)):
        column_name = column_names[i]
        unique_vals, unique_vals_counts = np.unique(
            [str(int_element) for int_element in df[df.columns[i]].tolist()],
            return_counts=True,
        )
        if prediction == true_value:
            correct_ += 1
        else:
            false_ += 1
            print("column name : ", column_names[i])
            indices = _ptype.normal_types[column_name]
            print(
                "\tsome normal data values: ",
                [unique_vals[ind] for ind in indices][:20],
            )
            print("\ttheir counts: ", [unique_vals_counts[ind] for ind in indices][:20])

            indices = _ptype.missing_types[column_name]
            if len(indices) != 0:
                print(
                    "\tsome missing data values: ",
                    [unique_vals[ind] for ind in indices][:20],
                )
                print(
                    "\ttheir counts: ",
                    [unique_vals_counts[ind] for ind in indices][:20],
                )

            indices = _ptype.anomaly_types[column_name]
            if len(indices) != 0:
                print(
                    "\tsome anomalous data values: ",
                    [unique_vals[ind] for ind in indices][:20],
                )
                print(
                    "\ttheir counts: ",
                    [unique_vals_counts[ind] for ind in indices][:20],
                )

            print(
                "\ttrue/annotated type : ",
                true_value,
                "\n\tpredicted type : ",
                prediction,
            )
            print(
                "\tposterior probs: ",
                _ptype.p_t_columns[list(_ptype.p_t_columns.keys())[i]],
            )
            print("\ttypes: ", _ptype.types, "\n")

    print(
        "correct/total = ",
        round(correct_ / len(column_names), 2),
        "(" + str(int(correct_)) + "/" + str(len(column_names)) + ")",
    )
