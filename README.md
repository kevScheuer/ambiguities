:warning:**This repository must be on a JLab ifarm node**:warning:

# Motivations
This repository contains all scripts needed to submit MonteCarlo input output tests, aggregate them into csv files, and analyze those csv's using a python framework to search for signatures of ambiguities within the current Amplitude Analysis models used at GlueX. Its hypothesized that the strength of the m=0 wave and the ratio of reflectivities present heavily influences the range of ambiguous solutions one can have. This can be tested through a series of input-output studies using Monte Carlo (MC) simulated events. The motivation primarily stems from fits to the neutral $b_1$ channel being very stable, as opposed to $\omega\eta$ results that are extremely inconsistent, even though they use the exact same waveset, and the "moment matrix" method tells us they both should be stable. 

# Setup
 To run the scripts, you must have a working version of `conda` in order to source and start the python environment here. [Miniforge](https://github.com/conda-forge/miniforge#mambaforge) or [Miniconda](https://docs.anaconda.com/free/miniconda/index.html) are recommended. 

To create the environment and activate it, run:
```
conda env create --file environment.yml
conda activate ambiguities
```