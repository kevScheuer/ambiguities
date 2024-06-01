After jobs have been submitted by `submission/submit.py` and complete, the output of those files is analyzed here. The process is as follows:

1. Aggregate `.fit` result files from /volatile using `root 'fitsToCsv.C("[args]")'` (symlinked from the neutralb1 repo). This creates a csv file where columns contain all the coherent sums, phase difference, and fit result information
   1. rootlogon info here
2. Read the csv into a pandas dataframe and observe any of the data's correlations, spread, etc. The philosophy here is the more plots, the better. These ambiguity issues are rooted in non-linear correlations between a variety of coherent sums, and so understanding these is going to take a *lot* of information