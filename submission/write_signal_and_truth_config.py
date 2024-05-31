"""Use fit.cfg copy to create gen_signal.cfg and truth.cfg files

The gen_signal.cfg file is essentially a copy of the fit.cfg file, but with modified
amplitude values according to the user passed reflectivity ratio and m0 amplitude
strength. Similarly, truth.cfg is just gen_signal.cfg with some added parameter scales.
This module copies fit.cfg and makes the necessary replacements and edits to simply 
construct gen_signal.cfg and truth.cfg
"""

import numpy as np


def main(m0_strength: float, ratio: float, phase_reference: str):

    m0_list = []
    reaction = ""

    # Write gen_signal.cfg
    with (
        open("submission/fit.cfg", "r") as fcfg,
        open("submission/gen_signal.cfg", "w") as fgen_signal,
    ):
        for line in fcfg:
            line = line.splitlines()[0]  # removes newline characters

            # store reaction name for writing later
            if reaction == "" and "::" in line and "#" not in line:
                reaction = [x.split("::")[0] for x in line.split() if "::" in x][0]

            # store amplitudes with m=0 components
            if "loop LOOPAMP" in line:
                m0_list.extend([x for x in line.split() if "0" in x])

            match line:
                case line if "parScale" in line:
                    # TODO: it'd be better to not write these in 1st place, but requires
                    # a write_config different from neutralb1 version. So its a quick
                    # fix that needs a better solution
                    continue
                case line if "initialize" not in line or "#" in line:
                    # simply write lines that don't need to be edited
                    fgen_signal.write(line + "\n")
                    continue
                case line if "ImagPosSign" in line or "RealNegSign" in line:
                    line = line.replace(" real", "")
                    line = line.replace("100", str(100 * np.sqrt(ratio))) + " fixed "
                case line if "real" in line:
                    line = line.replace("real", "fixed")
                case _:
                    line += " fixed "

            fgen_signal.write(line + "\n")

        # need to have this line in the cfg file due to deprecated check in AmpTools
        fgen_signal.write("\ndefine vector 0.782 0.009\n")

        # WRITE M=0 AMP INITIALIZATIONS
        m0_set = set(m0_list)  # just in case values somehow got repeated
        fgen_signal.write("\n# set custom m0 values\n")

        refl_list = ["ImagNegSign", "RealPosSign", "ImagPosSign", "RealNegSign"]
        for m0_amp in sorted(m0_set):
            # properly handle if an m0 amplitude is the phase reference
            if m0_amp == phase_reference:
                im = 0
            else:
                im = 1
            for refl in refl_list:
                if refl == "ImagPosSign" or refl == "RealNegSign":
                    factor = np.sqrt(ratio)
                else:
                    factor = 1
                fgen_signal.write(
                    f"initialize {reaction}::{refl}::{m0_amp}"
                    f" cartesian {m0_strength*factor} {m0_strength*factor*im} fixed\n"
                )

    # WRITE GEN_TRUTH CFG FILE
    amplitude_set = set()
    with (
        open("submission/gen_signal.cfg", "r") as fgen_signal,
        open("submission/truth.cfg", "w") as ftruth,
    ):
        for line in fgen_signal:
            line = line.splitlines()[0]  # removes newline characters

            if "fit" in line and "#" not in line:
                line = "fit truth"

            ftruth.write(line + "\n")

            # capture full amplitude name always written right after 'amplitude'
            if "amplitude" in line and "#" not in line and "ComplexCoeff" not in line:
                amplitude_set.add(line.split()[1])

        # Only difference between gen_signal and truth is a scaling parameter that
        # allows all amplitudes to properly scale to the overall intensity, while
        # keeping their values fixed
        ftruth.write(
            "\n# Add scale parameter to allow all fixed amps to move\n"
            "parameter par_scale 1.0\n"
        )
        for amplitude in sorted(amplitude_set):
            ftruth.write(f"scale {amplitude} [par_scale]\n")

    return
