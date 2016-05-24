#!/bin/bash

HTSOHM_DIR=${PWD}          # specifies HTSOHM directory
RASPA_DIR=$(raspa-dir)    # specifies RASPA directory

mkdir $HTSOHM_DIR/config

#writing environment variables to .bashrc
DEST=~/.bashrc
echo $'\n# HTSOHM directories' >> $DEST
echo "export HTSOHM_DIR=${HTSOHM_DIR}" >> $DEST
echo "export RASPA_DIR=${RASPA_DIR}" >> $DEST
echo "export FF_DIR=\${RASPA_DIR}/forcefield" >> $DEST
echo "export MAT_DIR=\${RASPA_DIR}/structures/cif" >> $DEST
echo "# " >> $DEST

#load updated .bashrc into this console
source $DEST

#create local database/table...
python $HTSOHM_DIR/htsohm/runDB_declarative.py
