import random
import threading
from typing import Tuple, List

from pop import PoP
from util import N_EXIT_POP_CHOICES, BDCST_PERIOD, N_POPS, MAX_TRANSFER_ITERATION


class SBAS(object):
    """
    Class representing an abstraction of the Secure Backbone AS system, given a number of Point-of-Presence (PoPs)
    in the system.
    """

    def __init__(self):
        self.pops = {i: PoP(pop_id=i, sbas=self, n_clients=random.randint(1, 10)) for i in
                     range(1, N_POPS + 1)}
        self.barrier = threading.Barrier(N_POPS)
        self.signaled = []
        self.waiting = []
        for pop in self.pops.values():
            print("PoP "+str(pop.pop_id)+" cost: "+str(pop.internet_transit_cost))

    def run_pops_threads(self) -> List[threading.Thread]:
        """
        Creates a new thread for each PoP and starts them.
        :return: a list of threads representing the list of running PoPs.
        """
        threads = []
        for pop in self.pops.values():
            x = threading.Thread(target=pop.run, args=(MAX_TRANSFER_ITERATION,), daemon=True)
            x.start()
            threads.append(x)
        return threads

    def wait_for_next_epoch(self, pop_id: int) -> int:
        """
        Waits for all PoPs to finish the previous iteration before moving on to the next one.
        :param: pop_id: ID of the PoP that is ready for the next iteration.
        :return: 0 if PoP was successfully put to wait, 1 otherwise.
        """
        # only move on once all PoP IDs have called this function
        if pop_id not in self.waiting:
            self.barrier.wait()
            self.waiting.append(pop_id)
            if len(self.waiting) == N_POPS:
                self.waiting = []
            return 0
        return 1

    def signal_end_epoch(self, iteration: int, pop_id: int) -> int:
        """
        Signals which PoP IDs finished the current iteration.
        :param: iteration: number of the current finished iteration.
        :param: pop_id: ID of the PoP that is finished the current iteration.
        :return: 0 if PoP was successfully signaled as done, 1 otherwise.
        """
        if pop_id not in self.signaled:
            self.barrier.wait()
            self.signaled.append(pop_id)
            if len(self.signaled) == N_POPS:
                self.signaled = []
            return 0
        return 1

    def internet_transfer(self, traffic: float, exit_pop_id: int, entry_pop_id: int) -> float:
        """
        Returns the total cost of transferring the given amount of traffic to the internet using the given exit PoP.
        :param entry_pop_id: ID of the entry PoP sending the internet traffic via SBAS to the exit PoP.
        :param traffic: amount of traffic to transfer.
        :param exit_pop_id: ID of the exit PoP transferring the traffic to the internet.
        :return: a float representing the transferring cost.
        """
        exit_pop = self.pops[exit_pop_id]
        traffic_cost = exit_pop.transfer_to_internet(entry_pop_id=entry_pop_id, traffic=traffic)
        return traffic_cost

    def broadcast_balance(self, pop_id: int, subbalances: List[float]) -> None:
        """
        Broadcasts the list of sub-balances for the given PoP.
        :param pop_id: integer representing the ID of the PoP.
        :param subbalances: list of float representing all the PoP's sub-balances with other PoPs.
        :return: None.
        """
        for pop in self.pops.values():
            pop.update_balance(pop_id, sum(subbalances))

    def get_k_optimal_exit_pop(self, internet_endpoint: int, entry_pop_id: int, k: int) -> List[Tuple[int, int]]:
        """
        Gets the first k exit PoPs with the highest optimality for the path from the entry PoP to the internet endpoint.
        :param internet_endpoint: ID of the internet endpoint that the entry PoP wants to reach.
        :param entry_pop_id: ID of the entry PoP.
        :param k: number of exit PoPs to return in the list of most optimal exit PoPs.
        :return: the list of k exit PoPs with the highest optimality.
        """
        opt_list = self.__get_optimality_list(entry_pop_id, internet_endpoint)
        opt_list_ordered = sorted(opt_list, key=lambda x: x[1], reverse=True)
        for i in range(0, k - 1):
            assert opt_list_ordered[i][1] > opt_list_ordered[i + 1][1]
        return opt_list_ordered[:k]

    def __get_optimality_list(self, entry_pop_id: int, internet_endpoint: int) -> List[Tuple[int, int]]:
        """
        Lists all other exit PoPs in (random) decreasing order of optimality for reaching the internet endpoint.
        :param entry_pop_id: ID of the entry PoP from which the traffic comes from.
        :param internet_endpoint: ID of the endpoint the entry PoP wants to reach via SBAS on the BGP Internet.
        :return: a list of int tuples, respectively the exit PoP ID and the corresponding optimality.
        """
        optimality_list = self.__unique_opt_sample(entry_pop_id, internet_endpoint)
        # optimality_list = self.__skewed_opt_distr(entry_pop_id)

        return optimality_list

    def __unique_opt_sample(self, entry_pop_id: int, internet_endpoint: int) -> List[Tuple[int, int]]:
        """
        Associates all exit PoPs (for the given entry PoP and internet endpoint to reach) to an optimality value sampled
        randomly and without replacement in the range going from 1 to the number of exit PoPs
        (total number of PoPs - 1).
        :param entry_pop_id: ID of the entry PoP.
        :param internet_endpoint: ID of the internet endpoint that the entry PoP wants to reach.
        :return: a list of tuples (exit_pop_id, optimality).
        """
        exit_pop_list = list(self.pops.keys())
        exit_pop_list.remove(entry_pop_id)
        optimalities = range(1, N_POPS)
        scion_optimisation_choice = random.randint(1, 3)
        seed = internet_endpoint + scion_optimisation_choice
        random.seed(seed)
        opt_list = random.sample(optimalities, len(optimalities))
        optimality_list = list(map(lambda x, y: (x, y), exit_pop_list, opt_list))
        return optimality_list

    def __skewed_opt_distr(self, entry_pop_id: int) -> List[Tuple[int, int]]:
        """
        Associates all exit PoPs to the same optimality value for all tuple of entry pop and internet endpoint.
        :param entry_pop_id: ID of the entry PoP.
        :return: a list of tuples (exit_pop_id, optimality).
        """
        exit_pop_list = list(self.pops.keys())
        exit_pop_list.remove(entry_pop_id)
        if entry_pop_id == 1:
            assert exit_pop_list[0] == 2
        else:
            assert exit_pop_list[0] == 1
        optimalities = list(range(1, N_POPS))
        optimalities.reverse()
        optimality_list = list(map(lambda x, y: (x, y), exit_pop_list, optimalities))
        return optimality_list

    def get_pop_cost(self, pop_id: int) -> float:
        """
        Returns the cost of the given PoP.
        :param pop_id: integer representing the ID of the PoP.
        :return: float representing the internet transit cost for this PoP.
        """
        if pop_id in self.pops:
            pop = self.pops.get(pop_id)
            cost = pop.internet_transit_cost
        else:
            cost = 0.0
        return cost
