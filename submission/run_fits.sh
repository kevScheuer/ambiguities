#!/usr/bin/bash

source ~/work/my_build/setup_gluex.sh
which fitMPI

exec 3>&1 # connect fd 3 to the console

# these are for both the real and imaginary parts, since having them not be
#   equal makes the fit fractions more difficult to understand
m_values=('200' '400')

for m in "${m_values[@]}"; do
    echo "Performing I/O Fits for m=${m}" 1>&3

    # go to the running dir 
    cd ~/volatile/ambiguityFits/p1p0s
    mkdir -p $m && cd "$_"

    # create log and err files and redirect stdout and stderr to them
    log_file="${m}.log"
    err_file="${m}.err"
    touch $log_file $err_file
    exec 1>>${log_file} 2>>${err_file}
    
    # copy in the cfg files
    cp ~/work/ambiguities/gen_phasespace.cfg ./
    cp ~/work/ambiguities/gen_signal.cfg ./
    cp ~/work/ambiguities/truth.cfg ./

    pwd
    ls

    # replace m0 component in truth and gen_signal cfgs
    sed -i "s/ImagPosSign::1p0s cartesian.*/ImagPosSign::1p0s cartesian $m $m fixed/" truth.cfg  
    sed -i "s/ImagPosSign::1p0d cartesian.*/ImagPosSign::1p0d cartesian $m $m fixed/" truth.cfg
    sed -i "s/RealNegSign::1p0s cartesian.*/RealNegSign::1p0s cartesian $m $m fixed/" truth.cfg
    sed -i "s/RealNegSign::1p0d cartesian.*/RealNegSign::1p0d cartesian $m $m fixed/" truth.cfg

    sed -i "s/ImagPosSign::1p0s cartesian.*/ImagPosSign::1p0s cartesian $m $m fixed/" gen_signal.cfg
    sed -i "s/ImagPosSign::1p0d cartesian.*/ImagPosSign::1p0d cartesian $m $m fixed/" gen_signal.cfg
    sed -i "s/RealNegSign::1p0s cartesian.*/RealNegSign::1p0s cartesian $m $m fixed/" gen_signal.cfg
    sed -i "s/RealNegSign::1p0d cartesian.*/RealNegSign::1p0d cartesian $m $m fixed/" gen_signal.cfg

    # generate the phasespace
    gen_vec_ps -c gen_phasespace.cfg\
    -o anglesOmegaPiPhaseSpace.root\
    -l 1.200 -u 1.2500 -tmin 0.4 -tmax 0.5 -a 8.2 -b 8.8\
    -n 100000

    # copy gen as "accepted" so no detector acceptance effects are applied
    cp anglesOmegaPiPhaseSpace.root anglesOmegaPiPhaseSpaceAcc.root

    # generate the signal MC
    gen_vec_ps -c gen_signal.cfg\
    -o anglesOmegaPiAmplitude.root\
    -l 1.200 -u 1.2500 -tmin 0.4 -tmax 0.5 -a 8.2 -b 8.8\
    -n 10000

    # use gen cfg to do a single truth fit 
    fit -c truth.cfg 

    # perform fit to signal MC 
    mpirun -np 8 fitMPI -c ~/work/ambiguities/fit.cfg -r 100 -m 1000000

    # get diagnostic plots 
    mv omegapi.fit best.fit 
    vecps_plotter best.fit
    root -l -q '~/work/neutralb1/batch_scripts/plot_plotter.C("vecps_plot.root", "", "Thrown MC")'
done
