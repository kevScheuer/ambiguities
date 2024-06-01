""" Submits jobs via slurm to ifarm GPU nodes combined with mpi 

This file takes a set of user inputs, accessed using "-h" or "--help" from the terminal,
and performs all the steps necessary to to create Monte Carlo Input Output fit results.

SLURM INFO (https://scicomp.jlab.org/scicomp/slurmJob/slurmInfo)
    
Potential additions, may be unnecessary:
    all angles*.root are reaction dependently named. Either add reaction flag to it
        or remove it
    custom TEM binning in run_mc
    custom polarization fraction in cfg files (currently fixed to 35%)
"""

import argparse
import os
import pathlib
import pwd
import subprocess
import time

import submission.write_config as write_config
import submission.write_signal_and_truth_config as write_signal_and_truth_config

# CONSTANTS
USER = pwd.getpwuid(os.getuid())[0]
VOLATILE_DIR = f"/volatile/halld/home/{USER}"
USER_PATH = f"/w/halld-scshelf2101/{USER}/"
CODE_DIR = f"{USER_PATH}ambiguities/submission/"


def main(
    waveset: list,
    phase_reference: str,
    ds_option: str,
    m0_strengths: list,
    ratios: list,
    num_rand_fits: int,
    reaction: str,
    n_gpus: int,
    gpu_type: str,
):
    waveset_str = "_".join(sorted(waveset))  # make string for directory creation
    # parent directory for our fits
    reaction_dir = "/".join(
        (
            VOLATILE_DIR,
            "TMPDIR",
            "ambiguityFits",
            f"{reaction}/",
        )
    )
    pathlib.Path(reaction_dir).mkdir(parents=True, exist_ok=True)
    # make common phasespace file if not yet done
    if "anglesOmegaPiPhaseSpace.root" not in os.listdir(reaction_dir):
        print(
            f"\nPhasespace file not found in {reaction_dir}. Submitting slurm job"
            " to create file and exiting. Please re-attempt fits once job completes"
        )
        os.system(f"cp -f {CODE_DIR}beam.config  {reaction_dir}")
        pathlib.Path(f"{reaction_dir}log/").mkdir(parents=True, exist_ok=True)
        phasespace_command = " ".join(
            (
                f"source {CODE_DIR}setup_gluex.sh\ngen_vec_ps -c",
                f"{CODE_DIR}gen_phasespace.cfg",
                f"-o anglesOmegaPiPhaseSpace.root",
                "-l 1.200 -u 1.2500",
                "-tmin 0.4 -tmax 0.5",
                "-a 8.2 -b 8.8",
                "-n 100000",
            )
        )
        submit_slurm_job(
            f"{reaction}_phasespace",
            phasespace_command,
            reaction_dir,
            reaction_dir + "log/",
            gpu_type,
            n_gpus,
            "0:05:00",  # time and memory are small to let system know its a fast job
            "1000M",
        )
        exit()

    # write the fit.cfg file. Writer is copied in from neutralb1 repo, so some args
    # are fixed here. This fit file is common to all fits submitted
    write_config.main(
        waveset,
        phase_reference,
        False,
        ds_option,
        "",
        0,
        0,
        100,
        100,
        reaction,
        "template.cfg",
        "",
        ["PARA_0"],
    )

    # when True, will always skip asking user input if they want to overwrite files
    is_skip_all = False

    for m0 in m0_strengths:
        for ratio in ratios:
            # make gen_signal.cfg and truth.cfg for this bin
            write_signal_and_truth_config.main(float(m0), float(ratio), phase_reference)

            for i in range(100):  # for 100 independent datasets
                # start by making necessary dirs
                running_dir = (
                    f"{reaction_dir}{waveset_str}/m0-{m0}_ratio-{ratio}/dataset_{i}/"
                )
                data_out_dir = running_dir.replace("TMPDIR/", "")
                log_dir = running_dir + "log/"

                pathlib.Path(running_dir).mkdir(parents=True, exist_ok=True)
                pathlib.Path(data_out_dir).mkdir(parents=True, exist_ok=True)
                pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)

                # if a completed fit is found in the output directory, ask if the user
                # is sure they want to overwrite it
                if not is_skip_all:
                    if os.path.isfile(f"{data_out_dir}best.fit"):
                        print(
                            f"best.fit already exists at {data_out_dir}, are"
                            " you sure you want to submit this job and overwrite the"
                            " file? (Answer 'skip_all' to not show this prompt again)"
                        )
                        while True:
                            ans = str(input())
                            match ans:
                                case "yes" | "y" | "no" | "n":
                                    break
                                case "skip_all":
                                    is_skip_all = True
                                    break
                                case _:
                                    print("Please answer yes, no, or skip_all")
                        if ans == "no" or ans == "n":
                            continue

                # copy files to running dir
                os.system(f"cp -f {CODE_DIR}beam.config  {running_dir}")
                os.system(
                    f"cp -f {reaction_dir}anglesOmegaPiPhaseSpace.root {running_dir}"
                )
                os.system(
                    f"cp -f {reaction_dir}anglesOmegaPiPhaseSpace.root"
                    f" {running_dir}anglesOmegaPiPhaseSpaceAcc.root"
                )
                os.system(f"cp -f {CODE_DIR}gen_signal.cfg  {running_dir}")
                os.system(f"cp -f {CODE_DIR}fit.cfg  {running_dir}")

                # setup and submit job
                job_name = "_".join(
                    (
                        reaction,
                        f"m0-{m0}",
                        f"ratio-{ratio}",
                        f"dataset-{i}",
                    )
                )
                script_command = " ".join(
                    (
                        f"{CODE_DIR}run_mc.sh",
                        CODE_DIR,
                        data_out_dir,
                        str(num_rand_fits),
                        reaction,
                    )
                )
                submit_slurm_job(
                    job_name, script_command, running_dir, log_dir, gpu_type, n_gpus
                )

            # now that all 100 dataset jobs are submitted, lets do a truth fit job
            truth_name = "_".join((reaction, f"m0-{m0}", f"ratio-{ratio}", "truth"))
            truth_running_dir = (
                f"{reaction_dir}{waveset_str}/m0-{m0}_ratio-{ratio}/truth/"
            )
            truth_out_dir = truth_running_dir.replace("TMPDIR/", "")
            truth_log_dir = truth_running_dir + "log/"
            truth_command = " ".join(
                (
                    f"{CODE_DIR}run_truth.sh",
                    CODE_DIR,
                    truth_out_dir,
                )
            )
            pathlib.Path(truth_running_dir).mkdir(parents=True, exist_ok=True)
            pathlib.Path(truth_out_dir).mkdir(parents=True, exist_ok=True)
            pathlib.Path(truth_log_dir).mkdir(parents=True, exist_ok=True)

            os.system(f"cp -f {CODE_DIR}truth.cfg  {truth_running_dir}")
            os.system(f"cp -f {CODE_DIR}beam.config  {truth_running_dir}")
            os.system(
                f"cp -f {reaction_dir}anglesOmegaPiPhaseSpace.root {truth_running_dir}"
            )
            os.system(
                f"cp -f {reaction_dir}anglesOmegaPiPhaseSpace.root"
                f" {truth_running_dir}anglesOmegaPiPhaseSpaceAcc.root"
            )
            os.system(f"cp -f {CODE_DIR}gen_signal.cfg  {truth_running_dir}")

            submit_slurm_job(
                truth_name,
                truth_command,
                truth_running_dir,
                truth_log_dir,
                gpu_type,
                n_gpus,
            )

    return


def submit_slurm_job(
    job_name: str,
    script_command: str,
    running_dir: str,
    log_dir: str,
    gpu_type: str,
    n_gpus: int,
    time_limit: str = "0:30:00",
    mem_per_cpu: str = "5000M",
) -> None:
    """Submit a slurm job to the ifarm using an mpi+gpu build

    Args:
        job_name (str): shown on the scicomp webpage
        script_command (str): bash script with its arguments
        running_dir (str): /volatile/TMPDIR location
        log_dir (str): where slurm log files are stored
        gpu_type (str): card type to be used
        n_gpus (int): how many gpu cards to use (supported by mpi)
        time_limit (str, optional): Max wall-time in Hour:Min:Sec. Defaults to "1:00:00"
        mem_per_cpu (str, optional): Default of 5GB appear to be min needed for fit
            jobs, though small jobs like phasespace generation can use less
    """
    with open("tempSlurm.txt", "w") as slurm_out:
        slurm_out.write(
            "#!/bin/sh \n"
            "#SBATCH -A halld\n"
            f"#SBATCH --time={time_limit} \n"
            f"#SBATCH --chdir={running_dir}\n"
            f"#SBATCH --error={log_dir}log.err \n"
            f"#SBATCH --output={log_dir}log.out \n"
            f"#SBATCH --job-name={job_name} \n"
            f"#SBATCH --mem-per-cpu={mem_per_cpu} \n"
            "#SBATCH --cpus-per-task=1 \n"
            "#SBATCH --ntasks-per-core=1 \n"
            "#SBATCH --threads-per-core=1 \n"
            "#SBATCH --partition=gpu \n"
            f"#SBATCH --gres=gpu:{gpu_type}:{n_gpus} \n"
            f"#SBATCH --ntasks={n_gpus+1} \n"  # mpigpu always needs n_gpus+1
            "#SBATCH -w sciml2402\n"  # temp: issue with sciml2401 node
            "#SBATCH --constraint=el9 \n"
            f"{script_command}"
        )
    time.sleep(0.5)  # jobs can be skipped if too many submitted quickly
    subprocess.call(["sbatch", "tempSlurm.txt"])

    # remove temporary submission file
    os.remove("tempSlurm.txt")
    return


def check_positive_float(val) -> float:
    fl = float(val)
    if fl < 0.0:
        raise argparse.ArgumentTypeError(f"{fl} must be >= 0")
    return fl


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submit MC I/O jobs to ifarm")

    # waveset and modifications
    parser.add_argument(
        "-w",
        "--waveset",
        nargs="+",
        choices=[
            "0m",
            "1p",
            "1m",
            "2p",
            "2m",
            "3m",
            "iso",
            "b1",
            "b1free",
            "rho",
            "rhofree",
            "nodalitz",
        ],
        help="Waveset to fit with",
    )
    parser.add_argument(
        "-m0",
        "--m0_strength",
        nargs="+",
        default=["100"],
        help=(
            "Set the strength of the m=0 amplitude at the cfg level in each J^P."
            " Unless using data, all amplitudes are intitialized/generated with"
            " real=imaginary=100"
        ),
    )
    parser.add_argument(
        "-r",
        "--ratios",
        nargs="+",
        type=check_positive_float,
        default=[1],
        help=(
            "Set the ratio of the positive reflectivity to the negative reflectivity"
            " at the squared complex value level. This means a ratio of 2 here (refl=+1"
            " is twice as strong as the refl=-1 waves) will multiply all the positive"
            " reflectivity waves by sqrt(2). By default the ratio is 1, so each"
            " reflectivity is equal strength."
        ),
    )
    parser.add_argument(
        "--phase_reference",
        type=str,
        metavar="JPmL",
        default="",
        help=(
            "Flag the wave (in 'JPmL' format) whose phase will be constrained to 0."
            " Empty (default) picks lowest JP, m, L combination"
        ),
    )
    parser.add_argument(
        "-ds",
        "--ds_option",
        type=str,
        default="",
        choices=["free", "fixed", "split"],
        help=(
            "option to modify the ratio & phase between the D/S waves."
            " Leaving empty (default) lets them float within some bounds."
            " 'Free' removes the parameters, allowing them to float freely."
            " 'Fixed' sets to E852 nominal values"
            " (ratio=0.27 & phase=0.184 radians)."
            " 'Split' gives each reflectivity its own ratio & phase"
        ),
    )

    parser.add_argument(
        "-n", "--nrand", type=int, default=25, help="number of random fits"
    )
    parser.add_argument(
        "--reaction",
        type=str,
        default="omegapi",
        help="base reaction name to be used in cfg files",
    )
    parser.add_argument(
        "-g",
        "--gpu",
        nargs=2,
        default=["0", ""],
        choices=["1", "2", "3", "4", "T4", "TitanRTX", "A100", "A800"],
        metavar=("#GPUs", "CARD"),
        help="set # of GPUs to use for a card. Default assumes only CPU fits",
    )

    args = parser.parse_args()

    waveset = args.waveset
    phase_reference = args.phase_reference.lower()
    ds_option = args.ds_option
    m0_strengths = args.m0_strength
    ratios = args.ratios

    num_rand_fits = args.nrand
    reaction = args.reaction
    n_gpus, gpu_type = int(args.gpu[0]), args.gpu[1]

    main(
        waveset,
        phase_reference,
        ds_option,
        m0_strengths,
        ratios,
        num_rand_fits,
        reaction,
        n_gpus,
        gpu_type,
    )
