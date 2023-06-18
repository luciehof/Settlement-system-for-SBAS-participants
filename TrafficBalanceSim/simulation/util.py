import random
import time
from typing import List, Tuple

import matplotlib.pyplot as plt

N_POPS = 3
N_EXIT_POP_CHOICES = 2
assert 0 < N_EXIT_POP_CHOICES < N_POPS

BDCST_PERIOD = 1  # in unit iteration
N_DAYS = 30
iteration_min_factor = 1  # change this iteration factor to 60 if we want the broadcast period to be every min
# instead of 1 every hour
iteration_sec_factor = 1  # change both iteration factors to 60 if we want the broadcast period to be every sec
# instead of 1 every hour
# or every min
traffic_min_factor = 60  # equal to the number of minutes per iteration ; change this traffic factor to 1 if we want
# the broadcast period to be every min instead of 1 every hour
traffic_sec_factor = 60  # equal to the number of seconds per iteration ; change both traffic factors to 1 if we want
# the broadcast period to be every sec instead of 1 every hour
assert N_DAYS > 0
MAX_TRANSFER_ITERATION = iteration_sec_factor * iteration_min_factor * 24 * N_DAYS
assert BDCST_PERIOD > 0 and MAX_TRANSFER_ITERATION > 0

N_ENDPOINTS = 3971741681
PROBA_VISIT_BIG_ENDPOINT = 0.90
PROBA_VISIT_MEDIUM_ENDPOINT = 0.09
PROBA_VISIT_SMALL_ENDPOINT = 0.01
assert PROBA_VISIT_BIG_ENDPOINT + PROBA_VISIT_MEDIUM_ENDPOINT + PROBA_VISIT_SMALL_ENDPOINT == 1.0

PROPORTION_BIG_ENDPOINTS = 0.05
PROPORTION_MEDIUM_ENDPOINTS = 0.20
PROPORTION_SMALL_ENDPOINTS = 0.75
assert PROPORTION_BIG_ENDPOINTS + PROPORTION_MEDIUM_ENDPOINTS + PROPORTION_SMALL_ENDPOINTS == 1.0
TRAFFIC_PER_PERIOD = [30
                      for i in range(16 * iteration_min_factor * iteration_sec_factor)] \
                     + [90
                        for j in range(8 * iteration_min_factor * iteration_sec_factor)]

TIME_SHIFT_BETWEEN_POPS = 5 * iteration_min_factor * iteration_sec_factor
assert MAX_TRANSFER_ITERATION % len(TRAFFIC_PER_PERIOD) == 0
assert 0 <= TIME_SHIFT_BETWEEN_POPS < 24 * iteration_min_factor * iteration_sec_factor

TESTING = False

print("Number of PoPs: " + str(N_POPS))
print("Number of internet endpoints: " + str(N_ENDPOINTS))
print("Number of exit PoPs to choose from when optimizing the balance: " + str(N_EXIT_POP_CHOICES))
print("Number iterations between balance broadcasts: " + str(BDCST_PERIOD))
print("Number of days: " + str(N_DAYS))
print("Total number of transfer iterations: " + str(MAX_TRANSFER_ITERATION))
print("Proportion of highly visited endpoints: " + str(PROPORTION_BIG_ENDPOINTS))
print("Fraction of visits going to big endpoints: " + str(PROBA_VISIT_BIG_ENDPOINT))
print("Proportion of mediumly visited endpoints: " + str(PROPORTION_MEDIUM_ENDPOINTS))
print("Fraction of visits going to medium endpoints: " + str(PROBA_VISIT_MEDIUM_ENDPOINT))
print("Proportion of smally visited endpoints: " + str(PROPORTION_SMALL_ENDPOINTS))
print("Fraction of visits going to small endpoints: " + str(PROBA_VISIT_SMALL_ENDPOINT))

# instantiate lists of internet endpoints
n_small = int(PROPORTION_SMALL_ENDPOINTS * N_ENDPOINTS)
n_med = int(PROPORTION_MEDIUM_ENDPOINTS * N_ENDPOINTS)
n_big = N_ENDPOINTS - n_small - n_med
SMALL_ENDPOINT_LOWER_BOUND = 1
SMALL_ENDPOINT_UPPER_BOUND = n_small
MED_ENDPOINT_LOWER_BOUND = n_small + 1
MED_ENDPOINT_UPPER_BOUND = n_small + n_med
BIG_ENDPOINT_LOWER_BOUND = n_small + n_med + 1
BIG_ENDPOINT_UPPER_BOUND = n_small + n_med + n_big
print('Initialisation done.')


def get_internet_endpoint() -> int:
    """
    Returns an internet endpoint picked randomly following the Zipf law of endpoints' visits distribution, i.e. a small
    fraction of enpoints have the majority of visits, a medium fraction have a medium amount of visits and a big
    fraction have a small amount of visits.
    :return: an integer representing the endpoint to visit.
    """
    endpoint_type = get_endpoint_type()
    if endpoint_type == 'big':
        endpoint = random.randint(BIG_ENDPOINT_LOWER_BOUND, BIG_ENDPOINT_UPPER_BOUND)
    elif endpoint_type == 'medium':
        endpoint = random.randint(MED_ENDPOINT_LOWER_BOUND, MED_ENDPOINT_UPPER_BOUND)
    else:
        endpoint = random.randint(SMALL_ENDPOINT_LOWER_BOUND, SMALL_ENDPOINT_UPPER_BOUND)
    return endpoint


def get_endpoint_type():
    if n_small > 0:
        endpoint_type = \
            random.choices(['big', 'med', 'small'],
                           weights=[PROBA_VISIT_BIG_ENDPOINT, PROBA_VISIT_MEDIUM_ENDPOINT, PROBA_VISIT_SMALL_ENDPOINT],
                           k=1)[0]
    elif n_med > 0:
        endpoint_type = \
            random.choices(['big', 'med'],
                           weights=[PROBA_VISIT_BIG_ENDPOINT + PROBA_VISIT_MEDIUM_ENDPOINT, PROBA_VISIT_SMALL_ENDPOINT],
                           k=1)[0]
    else:
        endpoint_type = 'big'
    return endpoint_type


def set_testing() -> None:
    """
    Sets the global variable testing to true.
    :return: None.
    """
    global TESTING
    TESTING = True


def stats(source: str):
    balances = []
    sum_last_balances = 0
    for pop_id in range(1, N_POPS + 1):
        string_list = __get_string_list_from_file(pop_id, source)
        _, balance = __unzip_tuples(string_list)
        print(balance[-1])
        sum_last_balances += balance[-1]
        balances += balance
    return sum_last_balances, min(balances), max(balances)


def __plot_per_pop(ax, source: str) -> None:
    """
    Plots each PoP's values in a different color.
    :param ax: ax from the subplots.
    :param source: general filename of the data to plot. One element per line, representing the y's values.
    :return: None.
    """
    for pop_id in range(1, N_POPS + 1):
        string_list = __get_string_list_from_file(pop_id, source)
        x, y = __unzip_tuples(string_list)
        plt.rc('font', size=12)
        plt.xlim(xmin=0, xmax=31)
        ax.plot(x, y, label="PoP " + str(pop_id))


def __unzip_tuples(string_list):
    tuple_string_list = list(map(lambda s: s.split(','), string_list))
    str_y = [e for e, f in tuple_string_list]
    str_x = [f for e, f in tuple_string_list]
    y = list(map(lambda s: float(s), str_y))
    len_x = len(list(map(lambda s: float(s), str_x)))
    scale = len_x / 30
    x = [i/scale for i in range(len_x)]

    return x, y


def plot(source: str, xlabel: str, ylabel: str, output: str) -> None:
    """
    Plots the data in the given source file in the given output file.
    :param source: general filename of the data to plot. One element per line, representing the y's values.
    :param xlabel: label to put on the x axis.
    :param ylabel: label to put on the y axis.
    :param output: file where we want to show the plot.
    :return: None.
    """
    plt.rc('axes', labelsize=12)
    plt.rc('xtick', labelsize=12)
    plt.rc('ytick', labelsize=12)
    fig, ax = plt.subplots(figsize=(11, 9))
    __plot_per_pop(ax, source=source)
    if N_POPS <= 10:
        ax.legend()
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout(pad=2)
    plt.savefig(output)


def __get_string_list_from_file(pop_id: int, source: str) -> List[str]:
    """
    Returns the list of strings representing the data in the give source file.
    :param pop_id: ID of the PoP used to identify which source file to use.
    :param source: general filename of the data to plot. One element per line, representing the y's values.
    :return: a list of strings.
    """
    source_file = open(source % pop_id, "r")
    data = source_file.read()
    string_list = data.split("\n")[:-1]  # remove the last empty element after the last \n

    return string_list


def __get_occurrences_list(values: List[int]) -> Tuple[List[int], List[int]]:
    """
    Returns a tuple of two lists: one with the PoPs' IDs and another one with their occurrences in the given values
    list.
    :param values: list of exit PoP IDs representing the exit PoPs used when transferring internet traffic via SBAS.
    :return: a tuple of two lists of integers.
    """
    x = list(range(1, N_POPS + 1))  # list of pop ids
    y = []
    for v in x:
        occ = values.count(v)
        y.append(occ)
    return x, y


def plot_hist(source: str, output: str, xlabel: str = '', ylabel: str = '') -> None:
    """
    Plots the histogram for each PoP representing the usage of other PoPs when transferring traffic to the internet via
    SBAS.
    :param source: general filename of the data to plot. One element per line, representing the y's values.
    :param xlabel: label to put on the x axis.
    :param ylabel: label to put on the y axis.
    :param output: file where we want to show the plots.
    :return: None.
    """
    n_plot_per_row = 4
    n_rows = N_POPS // n_plot_per_row + 1
    plt.figure(figsize=[44, 24])
    for pop_id in range(1, N_POPS + 1):
        string_list = __get_string_list_from_file(pop_id, source)
        values = list(map(lambda s: int(s), string_list))
        x, y = __get_occurrences_list(values)
        plt.ylim(bottom=0)
        plt.subplot(n_rows, n_plot_per_row, pop_id, label='PoP ' + str(pop_id))
        plt.title("PoP " + str(pop_id))
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.yticks(range(0, MAX_TRANSFER_ITERATION + 1, 5))
        plt.xticks(range(1, N_POPS + 1, 1))
        plt.bar(x, y)
    plt.tight_layout(pad=2)
    plt.savefig(output)


def plot_subplots(source: str, output: str, xlabel: str = '', ylabel: str = '') -> None:
    """
    Plots the optimization percentage subplot for each PoP over time.
    :param source: general filename of the data to plot. One element per line, representing the y's values.
    :param xlabel: label to put on the x axis.
    :param ylabel: label to put on the y axis.
    :param output: file where we want to show the plots.
    :return: None.
    """
    n_plot_per_row = 4
    n_rows = N_POPS // n_plot_per_row + 1
    plt.figure(figsize=[44, 24])
    for pop_id in range(1, N_POPS + 1):
        string_list = __get_string_list_from_file(pop_id, source)
        x, y = __unzip_tuples(string_list)
        plt.subplot(n_rows, n_plot_per_row, pop_id, label='PoP ' + str(pop_id))
        plt.title("PoP " + str(pop_id))
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.plot(x, y, 'o')
    plt.tight_layout(pad=2)
    plt.savefig(output)


def write_balance_output(my_balance: float, pop_id: int, iteration: int) -> None:
    """
    Writes to an output file the current PoP's balance.
    :param my_balance: float representing the PoP's balance.
    :param pop_id: integer representing the PoP ID.
    :return: None.
    """
    if not TESTING:
        balance_file = open("output/balance_%d.txt" % pop_id, 'a')
        s = str(my_balance) + ',' + str(iteration) + "\n" #str(time.time()) + "\n"
        balance_file.write(s)
        balance_file.close()


def write_subbalance_output(subbalances: dict, pop_id: int) -> None:
    """
    Writes to an output file the current PoP's subbalance.
    :param subbalances: dictionary pop ids and floats representing the PoP's subbalances.
    :param pop_id: integer representing the PoP ID.
    :return: None.
    """
    if not TESTING:
        subbalance_file = open("output/subbalance_%d.txt" % pop_id, 'a')
        s = str(subbalances) + ',' + str(time.time()) + "\n"
        subbalance_file.write(s)
        subbalance_file.close()


def write_opt_percentage_output(pop_id: int, scion_opt_percentage: float) -> None:
    """
    Writes to an output file the optimality percentage of the selected exit PoP with respect to the max optimality
    achievable.
    :param pop_id: integer representing the PoP ID.
    :param scion_opt_percentage: float representing the percentage of SCION optimization achieved.
    :return: None.
    """
    if not TESTING:
        opt_file = open("output/opt_percentage_%d.txt" % pop_id, 'a')
        s = str(scion_opt_percentage) + ',' + str(time.time()) + "\n"
        opt_file.write(s)
        opt_file.close()


def write_transfer_output(balanced_exit_pop_id: int, pop_id: int) -> None:
    """
    Writes the exit PoP ID selected for the internet transfer in an output file.
    :param balanced_exit_pop_id: ID of the exit PoP.
    :param pop_id: integer representing the PoP ID.
    :return: None.
    """
    if not TESTING:
        transfer_file = open("output/transfer%d.txt" % pop_id, 'a')
        s = str(balanced_exit_pop_id) + ',' + str(time.time()) + "\n"
        transfer_file.write(s)
        transfer_file.close()
