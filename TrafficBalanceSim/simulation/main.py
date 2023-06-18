from sbas import SBAS
from util import plot, plot_hist, plot_subplots, stats

# General parameters for the simulation are set in the util.py file

# initialise an SBAS instance
sbas = SBAS()

# start running
print("Starting simulation...")
pops_threads = sbas.run_pops_threads()

# wait for all PoPs threads to finish their activities
for pop_thread in pops_threads:
    pop_thread.join()

print("All PoPs finished running.")

# plot all PoPs balances
plot(source="output/balance_%d.txt", xlabel="Days", ylabel="Balance", output="output/balances.png")
# mean and variance computation
print("Sum final balances, Max, Min: ", stats(source="output/balance_%d.txt"))
