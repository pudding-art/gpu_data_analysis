#!/bin/bash

# 注意MERCI源码直接放在$Home目录下（一般是/home下，若是root用户则是/root），否则其内置运行脚本会出错
# Dataset:DBLP
# Download from http://networkrepository.com/ca-coauthors-dblp.php
# Dataset path /MERCI/data/1_raw_data/dblp/
tar -zxvf MERCI.tar.gz
mkdir MERCI/data
mkdir MERCI/data/1_raw_data
mkdir MERCI/data/1_raw_data/dblp
chmod -R 777 MERCI
# 生成后续目录，这里报错的话需要根据data所在路径修改control_dir_path.sh里面写的路径
cd MERCI 
./control_dir_path.sh dblp 3300

# 1. Preprocess
cd 1_preprocess/scripts
./lastfm_dblp.sh dblp

# 2. Partition
cd ../../2_partition/scripts
./run_patoh.sh dblp 3300

# 3. Clustering
cd ../../3_clustering
mkdir bin
make

cd bin
./clustering -d dblp -p 3300
./clustering -d dblp -p 3300 --remap-only

# 4. Performance evaluation
cd ../../4_performance_evaluation
mkdir bin
make all

# Baseline
./bin/eval_baseline -d dblp -r 1

# Remap only
./bin/eval_remap_only -d dblp -p 3300 -r 2

# MERCI
mem_sizes=( 1.25 1.5 2.0 9.0 )
./bin/eval_merci -d dblp -p 3300 -r 2 --memory_ratio 1.25
./bin/eval_merci -d dblp -p 3300 -r 2 --memory_ratio 1.5
./bin/eval_merci -d dblp -p 3300 -r 2 --memory_ratio 2.0
./bin/eval_merci -d dblp -p 3300 -r 2 --memory_ratio 9.0
