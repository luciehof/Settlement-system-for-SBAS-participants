import unittest

from sbas import SBAS
from util import N_POPS, set_testing, N_ENDPOINTS, N_EXIT_POP_CHOICES, TESTING, BDCST_PERIOD


def init_test() -> SBAS:
    set_testing()
    sbas = SBAS()
    return sbas


class PoPTestCase(unittest.TestCase):

    def test_balance_computation(self):
        sbas = init_test()
        pop_1 = sbas.pops[1]
        init_bal_1 = 0.0
        assert BDCST_PERIOD == 1
        for i in range(100):
            pop_1.run(n_iterations=1)
            self.assertGreaterEqual(init_bal_1, pop_1.get_balance(), "After transferring traffic to another PoP, "
                                                                     "PoP_1's balance should decrease.")

    def test_subbalance_computation(self):
        sbas = init_test()
        pop_1 = sbas.pops[1]
        pop_2 = sbas.pops[2]
        pop_3 = sbas.pops[3]
        assert BDCST_PERIOD == 1
        assert N_POPS == 3
        assert N_EXIT_POP_CHOICES == 1
        # make sure skewed distribution is on in SBAS to ensure PoP1 always transfers to PoP2 and vice versa
        for i in range(1000):
            pop_1.run(n_iterations=1)
            print(pop_1.get_subbalance(2))
            self.assertEqual(pop_1.get_subbalance(2), -1 * pop_2.get_subbalance(1), "After transferring traffic to "
                                                                                    "PoP2, PoP1's and PoP2 "
                                                                                    "sub-balances should be opposite "
                                                                                    "values.")
            self.assertEqual(pop_3.get_balance(1), pop_1.get_subbalance(2),
                             "PoP3 got balance for PoP1 equal to " + str(pop_3.get_balance(1)) + " instead of " + str(
                                 pop_1.get_subbalance(2)))
            pop_2.run(n_iterations=1)
            self.assertEqual(pop_1.get_subbalance(2), -1 * pop_2.get_subbalance(1), "After transferring traffic to "
                                                                                    "PoP2, PoP1's and PoP2 "
                                                                                    "sub-balances should be opposite "
                                                                                    "values.")
            self.assertEqual(pop_3.get_balance(2), pop_2.get_subbalance(1),
                             "PoP3 got balance for PoP2 equal to " + str(pop_3.get_balance(2)) + " instead of " + str(
                                 pop_2.get_subbalance(1)))

    def test_choose_lowest_balance_pop(self):
        sbas = init_test()
        pop_1 = sbas.pops[1]
        pop_1.set_clients(1)
        assert N_ENDPOINTS == 1  # We want PoP1 to have a determined internet endpoint to reach
        assert N_POPS > 4  # We want to have enough PoPs to test the property
        assert N_EXIT_POP_CHOICES == N_POPS - 1  # We want PoP1 to have enough exit PoPs to choose from

        for i in range(100):
            optimal_pops = sbas.get_k_optimal_exit_pop(internet_endpoint=1, entry_pop_id=1, k=N_EXIT_POP_CHOICES)
            exit_pop_id = pop_1.run(n_iterations=1)
            exit_balance = pop_1.get_balance(exit_pop_id)
            for pop_id, opt in optimal_pops:
                balance = pop_1.get_balance(pop_id)
                self.assertGreaterEqual(balance, exit_balance, "PoP1 must choose the optimal exit PoP with the "
                                                               "smallest balance.")


class SBASTestCase(unittest.TestCase):

    def test_ordered_optimalities(self):
        sbas = init_test()
        assert N_POPS == 5  # N_POPS can be set in util.py
        optimal_pops = sbas.get_k_optimal_exit_pop(internet_endpoint=1, entry_pop_id=1, k=4)
        self.assertEqual(optimal_pops[0][1], 4, "First optimal PoP should have max optimality.")
        self.assertEqual(optimal_pops[1][1], 3)
        self.assertEqual(optimal_pops[2][1], 2)
        self.assertEqual(optimal_pops[3][1], 1)

    def test_random_optimality_consistency(self):
        sbas = init_test()
        assert N_POPS > 4  # N_POPS can be set in util.py
        optimal_pops_1 = sbas.get_k_optimal_exit_pop(internet_endpoint=1, entry_pop_id=1, k=4)
        optimal_pops_2 = sbas.get_k_optimal_exit_pop(internet_endpoint=1, entry_pop_id=1, k=4)
        optimal_pops_3 = sbas.get_k_optimal_exit_pop(internet_endpoint=1, entry_pop_id=1, k=4)
        optimal_pops_4 = sbas.get_k_optimal_exit_pop(internet_endpoint=1, entry_pop_id=1, k=4)
        self.assertEqual(optimal_pops_1, optimal_pops_2, "Given the same entry, exit PoPs and internet endpoint, "
                                                         "the list of optimal PoPs must be the same (1 and 2).")
        self.assertEqual(optimal_pops_2, optimal_pops_3, "Given the same entry, exit PoPs and internet endpoint, "
                                                         "the list of optimal PoPs must be the same (2 and 3).")
        self.assertEqual(optimal_pops_3, optimal_pops_4, "Given the same entry, exit PoPs and internet endpoint, "
                                                         "the list of optimal PoPs must be the same (3 and 4).")


if __name__ == '__main__':
    unittest.main()
