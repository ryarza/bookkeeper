"""FLASH hydrodynamical simulation submodule."""
import functools
import glob
import os
import pathlib
import subprocess
import yt
import bookkeeper


class ParameterFile(bookkeeper.ParameterFile):
    """Cholla parameter file class.

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


class Checkpoint:
    """FLASH checkpoint file."""

    def __init__(self, path: pathlib.Path):
        """Set the checkpoint file path."""
        self.path = pathlib.Path(path)

    @functools.cached_property
    def yt_dataset(self):
        """Dataset (yt) associated with this checkpoint.

        :return: yt dataset associated with this checkpoint
        :rtype: yt.frontends.flash.data_structures.FLASHDataset
        """
        return yt.load(self.path)

    @property
    def number(self) -> int:
        """Checkpoint number.

        :return: Checkpoint number
        :rtype: int
        """
        return int(self.path.parts[-1].split("_")[-1])


class Simulation(bookkeeper.Simulation):
    """A FLASH simulation specified by its folder."""

    @property
    def _default_par_name(self) -> str:
        return 'input.txt'

    @property
    def _parameter_file_type(self) -> type:
        return ParameterFile

    @property
    def complete(self) -> bool:
        """Whether the simulation ran to completion.

        Determined by searching for 'reached max SimTime' in the
        most recent SLURM file
        :return: Whether the simulation ran to completion
        :rtype: bool
        """
        if len(self.slurm_files) == 0:
            return False
        with open(self.slurm_files[-1], encoding="utf-8") as myfile:
            finished = "reached max SimTime" in myfile.read()
        return finished

    @property
    def checkpoints(self) -> list[Checkpoint]:
        """List of checkpoints in the simulation.

        :return: List of checkpoints in the simulation
        :rtype: typing.List[Checkpoint]
        """
        checkpoint_files = sorted(glob.glob(os.path.join(self.path, "*chk*")))
        return [Checkpoint(pathlib.Path(f)) for f in checkpoint_files]

    @property
    def slurm_files(self) -> list[pathlib.Path]:
        """List of SLURM files in the simulation.

        :return: List of SLURM files in the simulation
        :rtype: typing.List[pathlib.Path]
        """
        files = list(self.path.glob("slurm*.out"))
        files.sort(key=os.path.getmtime)
        flash_slurm_files = []
        for fil in files:
            with open(fil, encoding="utf-8") as myfile:
                content = myfile.read()
                if any(
                    text in content
                    for text in ["Driver init all done", "RuntimeParameters"]
                ):
                    flash_slurm_files.append(fil)
        return flash_slurm_files

    @property
    def reason_incomplete(self) -> str:
        """Reason a simulation failed.

        Determined from the last SLURM file. Detects when the simulation:

        - runs out of time
        - is preempted
        - crashes (i.e. "DRIVER_ABORT" was called in FLASH)

        There's probably a better way to implement this function using
        the Python slurm package.

        :return: Reason for failure
        :rtype: str
        """
        assert not self.complete, "Simulation finished"

        if len(self.slurm_files) == 0:
            return "not ran"

        reason = "unknown"
        with open(self.slurm_files[-1], encoding="utf-8") as myfile:
            contents = myfile.read()
            if "DUE TO TIME LIMIT" in contents:
                reason = "time limit"
            elif "DUE TO PREEMPTION" in contents:
                reason = "preemption"
            elif "DRIVER_ABORT" in contents:
                reason = "crashed"
        return reason

    @property
    def failed(self) -> bool:
        """Whether the simulation failed."""
        if self.complete:
            sim_failed = False
        else:
            sim_failed = self.reason_incomplete not in\
                ['unknown', "not ran"]
        return sim_failed

    def run(self, run_command: list[str]) -> None:
        """Submit a simulation using SLURM."""
        subprocess.run(run_command, cwd=self.path, check=True)

    def restart(self, submit_command: list[str]) -> None:
        """Restarts a simulation after writing an updated parameter file.

        :param submit_command: SLURM command to submit the simulation
        :type submit_command: str
        """
        self.par.params['restart'] = True
        self.par.params['checkpointfilenumber'] =\
            self.checkpoints[-1].number
        self.par.write()
        self.run(submit_command)


# class SimulationGrid(bookkeeper.SimulationGrid):

#     @property
#     def _simulation_type(self) -> type:
#         return Simulation

#     def _is_sim_folder(self, path: pathlib.Path) -> bool:
#         """Whether a folder belongs to a FLASH simulation.

#         A folder is a FLASH simulation folder if it contains a flash.par
#         file.

#         :param path: Folder to check
#         :type path: pathlib.Path
#         :return: Whether folder belongs to FLASH simulation
#         :rtype: bool
#         """
#         return (path / "flash.par").is_file()
