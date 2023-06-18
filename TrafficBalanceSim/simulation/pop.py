import random
import sys
import threading
from typing import Tuple, List

from util import get_internet_endpoint, N_POPS, write_balance_output, TRAFFIC_PER_PERIOD, TIME_SHIFT_BETWEEN_POPS, \
    TESTING, BDCST_PERIOD, N_EXIT_POP_CHOICES, write_subbalance_output, traffic_min_factor, traffic_sec_factor


class PoP(object):
    """
    Class representing a Point-of-Presence (PoP) in the given Secure Backbone AS (SBAS) system.
    Given are the unique ID of this PoP, the number of iterations between each balance broadcast and the number of
    optimised exit PoPs to consider when picking the exit PoP with the lowest balance.
    """

    def __init__(self, pop_id, sbas, n_clients):
        self.__sbas = sbas
        self.pop_id = pop_id
        self.n_clients = n_clients
        print("pop " + str(pop_id) + " clients: " + str(n_clients))
        # make sure to have the 2 extreme of traffic unit costs in the set of PoPs
        if pop_id == 1:
            self.internet_transit_cost = 0.1
        elif pop_id == N_POPS:
            self.internet_transit_cost = 1.0
        else:
            self.internet_transit_cost = round(random.uniform(0.1, 1.0), 1)
        self.__lock_balances = threading.Lock()  # for the __balances variable
        self.__balances = {i: 0.0 for i in range(1, N_POPS + 1)}
        self.other_pops = list(range(1, N_POPS + 1))
        self.other_pops.remove(self.pop_id)
        self.__subbalances = {i: 0.0 for i in self.other_pops}
        if not TESTING:
            write_balance_output(0.0, self.pop_id, 0)

    def run(self, n_iterations) -> int:
        """
        Continuously transfers (random) amount of traffic from customers to the internet via SBAS.
        Every self.__balance_period iterations, the current PoP's balance is broadcasted to other PoPs.
        :return: the ID of the exit PoP used for the single iteration or 0.
        """
        j = 0
        while j < n_iterations:
            ret_wait = 1
            while ret_wait == 1:
                ret_wait = self.__sbas.wait_for_next_epoch(self.pop_id)
            j += 1
            # continuously forward traffic from clients and receive traffic from other PoPs
            exit_pop_id = self.__transfer_clients_traffic(j)  # the exit PoP ID is used for testing
            if n_iterations == 1:
                # return the ID of the exit PoP used for the single iteration
                return exit_pop_id

            ret_sig = 1
            while ret_sig == 1:
                ret_sig = self.__sbas.signal_end_epoch(j, self.pop_id)
            my_balance = self.get_balance()
            write_balance_output(my_balance, self.pop_id, j)
            if j % BDCST_PERIOD == 0:
                # every balance time, broadcast balance and reset priorities
                self.send_subbalances()

        return 0

    def transfer_to_internet(self, entry_pop_id: int, traffic: float) -> float:
        """
        Transfers the given amount of traffic received via SBAS to the internet and updates the current PoPs balance
        accordingly (in this case it increases it).
        :param entry_pop_id: integer representing the ID of the entry PoP using the current PoP as exit PoP to transfer
        internet traffic.
        :param traffic: amount of internet traffic to be transferred from another (entry) PoP.
        :return: a float representing the Internet transit cost.
        """
        traffic_value = traffic * self.internet_transit_cost
        with self.__lock_balances:
            curr_subbalance = self.__subbalances[entry_pop_id]
            self.__subbalances[entry_pop_id] = curr_subbalance + traffic_value
            subbalances = self.__subbalances
            my_balance = sum(subbalances.values())
            self.__balances[self.pop_id] = my_balance

        write_subbalance_output(subbalances, self.pop_id)
        return traffic_value

    def update_balance(self, pop_id: int, new_balance: float) -> None:
        """
        Update the given PoP's balance with the new balance value.
        :param pop_id: ID of the PoP.
        :param new_balance: float representing the updated balance of the PoP.
        :return: None.
        """
        with self.__lock_balances:
            self.__balances[pop_id] = new_balance

    def __transfer_clients_traffic(self, iteration: int) -> int:
        """
        Determines (randomly or depending on the time of the day if the iteration param is not None) the amount of
        customers' traffic destined to the internet and transfer it to an exit PoP via SBAS.
        :param iteration: optional integer representing the iteration number (used to infer traffic amount depending on
        time of day).
        :return: the ID of the exit PoP used for this transfer. Id no transfer was made then return 0.
        """
        ret = 0
        traffics = self.__get_traffic_amounts_from_clients(iteration)
        for traffic in traffics:
            if traffic > 0:
                # determine internet endpoint to send traffic to
                endpoint = get_internet_endpoint()
                exit_pop_id = self.__send_via_sbas(traffic, endpoint)
                ret = exit_pop_id
        return ret

    def __get_traffic_amounts_from_clients(self, iteration: int) -> List[int]:
        """
        Returns the total amount of traffic to be transferred from all clients of this PoP.
        :param iteration: integer representing the current PoP's iteration.
        :return: a list of integers representing the amount of traffic sent by each client.
        """
        total_traffic = []
        for i in range(self.n_clients):
            # determine the amount of traffic to be transferred per client
            hour_shift = self.pop_id * TIME_SHIFT_BETWEEN_POPS
            traffic_idx = (iteration + hour_shift) % len(TRAFFIC_PER_PERIOD)
            max_traffic = TRAFFIC_PER_PERIOD[traffic_idx]
            traffic_per_sec = [random.uniform(0.0, max_traffic) for _ in range(traffic_min_factor * traffic_sec_factor)]
            total_traffic.append(sum(traffic_per_sec))
        return total_traffic

    def __send_via_sbas(self, traffic: float, endpoint: int) -> int:

        """
        Transfers the given amount of traffic to an optimised exit PoP via SBAS.
        Gets the corresponding cost and updates the current PoP's balance accordingly.
        :param traffic: float representing the amount of traffic to be transferred.
        :param: endpoint: integer representing the ID of the internet endpoint to send traffic to.
        :return: the chosen exit PoP's ID.
        """
        balanced_exit_pop_id = self.__get_balanced_optimised_exit_pop(endpoint, traffic)
        # transfer the traffic to this PoP
        cost = self.__sbas.internet_transfer(traffic=traffic, exit_pop_id=balanced_exit_pop_id,
                                             entry_pop_id=self.pop_id)
        # update entry PoP balance
        with self.__lock_balances:
            curr_subbalance = self.__subbalances[balanced_exit_pop_id]
            self.__subbalances[balanced_exit_pop_id] = curr_subbalance - cost
            subbalances = self.__subbalances
            my_balance = sum(subbalances.values())
            self.__balances[self.pop_id] = my_balance
        write_subbalance_output(subbalances, self.pop_id)
        return balanced_exit_pop_id

    def __get_balanced_optimised_exit_pop(self, endpoint: int, traffic: float = None) -> int:
        """
        Returns the optimised exit PoP ID with the lowest balance.
        :param endpoint: integer representing the internet endpoint ID.
        :return: an integer representing the optimised balanced exit PoP ID.
        """

        # get corresponding set of optimal PoPs for this entry PoP
        opt_pops = self.__sbas.get_k_optimal_exit_pop(internet_endpoint=endpoint, entry_pop_id=self.pop_id,
                                                      k=N_EXIT_POP_CHOICES)
        # select exit pop with lowest future balance
        balanced_exit_pop_id = self.__get_low_bal_pop(opt_pops, traffic)
        return balanced_exit_pop_id

    def __get_low_bal_pop(self, opt_pops: List[Tuple[int, int]], traffic: float) -> int:
        """
        Returns the ID of the optimised exit PoP with the lowest future balance.
        :param opt_pops: list of optimised exit PoP and their optimisation score as int.
        :param traffic: float representing the amount of traffic to be sent.
        :return: an integer representing the exit PoP ID.
        """
        balanced_pop_id = 0
        min_bal = sys.float_info.max
        for id, opt in opt_pops:
            cost = traffic * self.__sbas.get_pop_cost(id)
            new_bal = self.get_balance(id) + cost
            if new_bal < min_bal:
                min_bal = new_bal
                balanced_pop_id = id
        return balanced_pop_id

    def send_subbalances(self) -> None:
        """
        Sends the current PoP's sub-balances via SBAS to every peer PoP involved in the respective sub-balance.
        Only debit (negative) sub-balance are sent to be signed.
        :return: None.
        """
        with self.__lock_balances:
            subbalances = self.__subbalances.values()

        self.__sbas.broadcast_balance(self.pop_id, subbalances)

    def set_clients(self, n_clients: int) -> None:
        """
        Sets the number of SBAS clients of this PoP.
        :param n_clients: integer representing the number of clients.
        :return: None.
        """
        self.n_clients = n_clients

    def get_balance(self, pop_id: int = None) -> float:
        """
        Returns the current PoP's balance or the balance of the pop with the given ID.
        :param pop_id: ID of the PoP to get the balance from. Default is the current PoP.
        :return: float representing the balance.
        """
        with self.__lock_balances:
            if pop_id:
                my_balance = self.__balances[pop_id]
            else:
                my_balance = self.__balances[self.pop_id]
        return my_balance

    def get_subbalance(self, pop_id: int) -> float:
        """
        Returns the current PoP's subbalance wrt the given PoP.
        :param pop_id: ID of the PoP to get the subbalance from.
        :return: float representing the balance.
        """
        with self.__lock_balances:
            my_balance = self.__subbalances[pop_id]
        return my_balance
