"""FLASH hydrodynamical simulation submodule."""
import pathlib
import subprocess
import bookkeeper


class ParameterFile(bookkeeper.ParameterFile):
    """FLASH parameter file class.

    Equivalent to the general ParameterFile class, but uses the following
    string representations for boolean values:

    - True: '.true.'
    - False: '.false.'
    """

    @property
    def _quotes_around_string(self) -> bool:
        return False

    @property
    def _true_string(self) -> str:
        return "1"

    @property
    def _false_string(self) -> str:
        return "0"


class Simulation:

    def __init__(self, path: pathlib.Path, par_name: str = 'input.txt'):
        """Set simulation path and load the folder's parameter file."""
        self.path = path
        self.par = ParameterFile(path / par_name)

    @property
    def complete(self) -> bool:
        """Whether the simulation ran to completion.

        Determined by searching for 'reached max SimTime' in the
        most recent SLURM file
        :return: Whether the simulation ran to completion
        :rtype: bool
        """
        if not self.log.is_file():
            finished = False
        else:
            with open(self.log, encoding="utf-8") as myfile:
                finished = "Integration complete" in myfile.read()
        return finished

    @property
    def log(self) -> pathlib.Path:
        return self.path / "output.log"

    @property
    def reason_incomplete(self) -> str:
        raise NotImplementedError

    @property
    def failed(self) -> bool:
        raise NotImplementedError

    def run(self, run_command: list[str]) -> None:
        """Submit a simulation using SLURM."""
        with open(self.path / 'output.log', "w", encoding='utf-8') as outfile:
            subprocess.run(
                run_command,
                cwd=self.path,
                check=True,
                stdout=outfile
            )

    def restart(self, submit_command: list[str]) -> None:
        raise NotImplementedError


class SimulationGrid(bookkeeper.SimulationGrid):

    @property
    def _simulation_type(self):
        return Simulation

    def _is_sim_folder(self, path: pathlib.Path) -> bool:
        """Whether a folder belongs to a FLASH simulation.

        A folder is a FLASH simulation folder if it contains a flash.par
        file.

        :param path: Folder to check
        :type path: pathlib.Path
        :return: Whether folder belongs to FLASH simulation
        :rtype: bool
        """
        return (path / "input.txt").is_file()
