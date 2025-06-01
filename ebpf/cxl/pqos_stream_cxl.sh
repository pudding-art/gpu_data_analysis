#!/bin/bash
LOW=12
read=17
write=12
mask_read=0x$(echo "obase=16;2^(${read}+1)-2^${LOW}" | bc)
mask_write=0x$(echo "obase=16;2^(${write}+1)-2^${LOW}" | bc)

sudo pqos -R 


# write operation
for i in {1..10}
do
echo "Intel MBA throttling value is $[i*10]\% " 
echo "Intel MBA throttling value is $[i*10]\% " >> res.txt
echo "================================================" >> res.txt
sudo pqos -e "mba@1:0=$[i*10];"
#  --loaded_latency -d0 -W6 -b200000 -m0x1000 
sudo numactl --membind=2 ./mlc --loaded_latency -d0 -W6 -b200000 -m${mask_write} | grep 0000 >> res.txt 

sudo pqos -R
echo "MLC write successfully!" >> res.txt
echo "================================================" >> res.txt
echo "MLC write successfully!"
done

echo "================================================" >> res.txt
echo "================================================" >> res.txt


# read operation
for i in {1..10}
do
echo "Intel MBA throttling value is $[i*10]\% " 
echo "Intel MBA throttling value is $[i*10]\% " >> res.txt
echo "================================================" >> res.txt
sudo pqos -e "mba@1:0=$[i*10];"

sudo numactl --membind=2 ./mlc --loaded_latency -d0 -R -r -b200000 -m${mask_read} | grep 0000  >> res.txt

sudo pqos -R
echo "MLC read successfully!" >> res.txt
echo "================================================" >> res.txt
echo "MLC read successfully!"
done
