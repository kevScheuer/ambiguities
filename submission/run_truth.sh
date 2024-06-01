#!/bin/sh

# cleanup local directory
rm ./*.fit

export my_code_dir=$1
export my_data_out_dir=$2

echo -e "code dir: \t\t$my_code_dir\n
data out dir: \t\t$my_data_out_dir\n
"

source $my_code_dir/setup_gluex.sh

# print details to log file
echo -e "check if GPU Card is active for GPU fits:\n"
nvidia-smi
echo -e "\nCheck that needed commands resolve:\n"
which fitMPI
which nvcc
which mpirun
pwd
ls -al

echo -e "\n\n\n\n##### GENERATING SIGNAL EVENTS #####\n\n"

# generate 10k events of signal MC. "_0" is artifact of config writer
gen_vec_ps -c gen_signal.cfg\
 -o anglesOmegaPiAmplitude_0.root\
 -l 1.200 -u 1.2500 -tmin 0.4 -tmax 0.5 -a 8.2 -b 8.8\
 -n 10000

fit -c truth.cfg

if ! [ -f "truth.fit" ]; then
    echo "ERROR: truth.fit not found, assuming fit failed. Exiting."
    exit
fi

vecps_plotter truth.fit 

root -l -b -q "$my_code_dir/plot_plotter.C(\"vecps_plot.root\", \"\", \"Truth\")"

ls -al

# cleanup data out directory
rm $my_data_outdir/*.fit

# move fit results and plots to output directory
cp -f truth.cfg $my_data_out_dir
mv -f truth.fit $my_data_out_dir
mv -f *.ni $my_data_out_dir
mv -f vecps_* $my_data_out_dir
mv -f fit.pdf $my_data_out_dir