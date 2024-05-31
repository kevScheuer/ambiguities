#!/bin/sh

# cleanup local directory
rm ./*.fit

export my_code_dir=$1
export my_data_out_dir=$2
export my_num_rand_fits=$3
export my_reaction=$4

echo -e "code dir: \t\t$my_code_dir\n
data out dir: \t\t$my_data_out_dir\n
num rand fits: \t\t$my_num_rand_fits\n
reaction: \t\t$my_reaction\n
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

# cfg files have already been copied to this directory, just need to run them. All
#   files will be in same TEM bin
echo -e "\n\n\n\n##### GENERATING SIGNAL EVENTS #####\n\n"

# generate 10k events of signal MC. "_0" is artifact of config writer
gen_vec_ps -c gen_signal.cfg\
 -o anglesOmegaPiAmplitude_0.root\
 -l 1.200 -u 1.2500 -tmin 0.4 -tmax 0.5 -a 8.2 -b 8.8\
 -n 10000

mpirun fitMPI -c fit.cfg -m 1000000 -r $my_num_rand_fits

if ! [ -f "$my_reaction.fit" ]; then
    echo "ERROR: $my_reaction.fit not found, assuming fit failed. Exiting."
    exit
fi

mv $my_reaction.fit best.fit 
vecps_plotter best.fit 

root -l -b -q "$my_code_dir/plot_plotter.C(\"vecps_plot.root\", \"\", \"Thrown MC\")"

ls -al

# cleanup data out directory
rm $my_data_outdir/*.fit

# move fit results and plots to output directory
cp -f fit.cfg $my_data_out_dir
mv -f best.fit $my_data_out_dir
mv -f "$my_reaction"_*.fit $my_data_out_dir
mv -f *.ni $my_data_out_dir
mv -f vecps_* $my_data_out_dir
mv -f fit.pdf $my_data_out_dir