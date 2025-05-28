# 其他工程问题及调优


DMA与cache一致性

DMA传输外设数据到memory，cache中可能是老的数据

CPU写数据到memory，cache中是新数据，MEM是老数据

![alt text](image-58.png)
