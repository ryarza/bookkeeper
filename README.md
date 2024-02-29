# bookkeeper
A Python package for managing simulations

## Example usage
```python
import bookkeeper.flash

# Finds all subdirectories containing a flash.par file
grid = bookkeeper.flash.SimulationGrid("/path/to/simulations")

slurm_command = ["sbatch", "--qos=cpuq", "--account=cpuq",
                 "--partition=cpuq", "/path/to/runfile"]

for sim in grid.incomplete_sims:
    print(f"""Simulation at {sim.path} failed."""
          f""" Reason: {sim.reason_incomplete}""")
    # If the simulation crashed, restart it with a smaller CFL
    if sim.reason_incomplete == 'crashed':
        sim.par["cfl"] = 0.75 * sim.par["cfl"]
    sim.restart()
```

bookkeeper is released under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

If you use this code please cite [Yarza et al. 2023](https://ui.adsabs.harvard.edu/abs/2023ApJ...954..176Y/abstract)
