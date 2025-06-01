## 使用PageBank测试Intel MBA和CPU quota对应用性能的影响

### 测试一

在不同的限制🚫条件(Intel MBA, CPU quota)下pagerank的执行时间和最大带宽

1. 先将pagerank应用绑定在NUMA1 6CPU cores和NUMA1 memory上运行，同时监控运行时间和运行带宽

   ```shell
   # 监控内存带宽（无法运行）
   perf stat -e mem/bytes-read,mem/bytes-written
   ```

   10-21图规模范围的点

   ```shell
   # 1. 监控内存带宽
   # 使用PCM tools
   # /home/hwt/monitor/pcm/build/bin
   sudo ./monitor/pcm/build/bin/pcm-memory 0.1 -csv=bw.csv --external-program $cmt
   cmt="numactl --physcpubind=12-17 --membind=1 $pagerank"
   pagerank="python3 /home/hwt/workspace/PageRankBenchmark/code/Python/runPageRankPipeline.py"
   
   # 延迟
   # 2. pagerank已有测试代码,直接整合输出
   
   # 使用MBA调控内存CLOS的带宽为50%
   sudo ./pqos -e "mba@1:0=50;"
   
   # 使用cgroup的CPU quota来调控
   
   
   ```

#### intel-cmt-cat配置出现如下bug

![image-20240629202713943](/Users/hong/Library/Application%20Support/typora-user-images/image-20240629202713943.png)

Intel MBA debug解决方案: https://github.com/intel/intel-cmt-cat/issues/190

https://www.cnblogs.com/sky-heaven/p/9796285.html

发生以上错误的原因：

1. **死锁或未正常释放的锁**： 应用程序可能因为异常退出或崩溃而未能释放它所持有的锁。在这种情况下，锁文件仍然存在于 `/var/lock` 目录下，导致系统认为资源仍然被占用。删除这些遗留的锁文件后，应用程序可以重新获取锁并使用相应的资源。
2. **应用程序的容错机制**： 某些应用程序可能设计有容错机制，当检测到锁文件存在时，它们会尝试删除它并重新获取锁，从而允许应用程序继续运行。
3. **锁文件的非阻塞性**： 在一些情况下，锁文件可能被设计为非阻塞性的，即它们的存在只是用来提供一种资源使用状态的提示，而不是严格的互斥机制。删除这些文件后，应用程序检查到资源实际上并未被使用，因此可以继续运行。
4. **系统状态的临时性问题**： 有时系统可能遇到临时性的问题，如资源分配错误或状态同步问题，删除锁文件可以作为清除这些临时状态的一种手段，使系统恢复到正常状态。
5. **锁文件的版本控制**： 如果应用程序在设计时考虑到了锁文件可能被意外删除的情况，它可能会在启动时检查锁文件的状态，并在必要时重新创建它。
6. **权限问题**： 有时应用程序可能因为权限不足而无法创建或更新锁文件。删除旧的锁文件后，应用程序可能以更高的权限重新创建它，并成功运行。
7. **重启服务或应用程序**： 删除锁文件后重启服务或应用程序，可以确保在没有任何旧状态干扰的情况下重新初始化。

```shell
# show current MBA settings

# pid monitoring
# Monitoring by PIDs is available only when pqos uses OS interface ( --iface os ).
 pqos --iface os -s
 ...
 Core information for socket 0:
    Core 0, L2ID 0, L3ID 0 => COS0
    Core 1, L2ID 1, L3ID 0 => COS0
    Core 2, L2ID 2, L3ID 0 => COS0
    Core 3, L2ID 3, L3ID 0 => COS0
    Core 4, L2ID 4, L3ID 0 => COS0
    Core 5, L2ID 5, L3ID 0 => COS0
    Core 6, L2ID 6, L3ID 0 => COS0
    Core 7, L2ID 7, L3ID 0 => COS0
    Core 8, L2ID 8, L3ID 0 => COS0
    Core 9, L2ID 9, L3ID 0 => COS0
    Core 10, L2ID 10, L3ID 0 => COS0
    Core 11, L2ID 11, L3ID 0 => COS0
Core information for socket 1:
    Core 12, L2ID 64, L3ID 1 => COS0
    Core 13, L2ID 65, L3ID 1 => COS0
    Core 14, L2ID 66, L3ID 1 => COS0
    Core 15, L2ID 67, L3ID 1 => COS0
    Core 16, L2ID 68, L3ID 1 => COS0
    Core 17, L2ID 69, L3ID 1 => COS0
    Core 18, L2ID 70, L3ID 1 => COS0
    Core 19, L2ID 71, L3ID 1 => COS0
    Core 20, L2ID 72, L3ID 1 => COS0
    Core 21, L2ID 73, L3ID 1 => COS0
    Core 22, L2ID 74, L3ID 1 => COS0
    Core 23, L2ID 75, L3ID 1 => COS0
# 当前PID的绑定信息
PID association information:
    COS1 => (none)
    COS2 => (none)
    COS3 => (none)
    COS4 => (none)
    COS5 => (none)
    COS6 => (none)
    COS7 => (none)
```

目前全部绑定到COS0上，后面可能会根据进程的PID进行修改。

```shell
# Set COS 1 to 50% available and COS 2 to 70% available
sudo pqos -e "mba:1=50;mba:2=70;"

# Set COS 1 on all sockets, COS 2 on socket 0 and 1 and COS 3 on sockets 2 to 3
# Note: MBA rounds numbers given to it.
sudo pqos -e "mba:1=80;mba@0,1:2=64;mba@2-3:3=85"

hwt@cxl-2288H-V7:~/monitor/intel-cmt-cat/pqos$ sudo ./pqos -e "mba@1:0=50;"
NOTE:  Mixed use of MSR and kernel interfaces to manage
       CAT or CMT & MBM may lead to unexpected behavior.
SOCKET 1 MBA COS0 => 50% requested, 50% applied
Allocation configuration altered.

# Console output for pqos -s to show current configuration
sudo pqos -s
```

如果直接修改CLOS的throttling value会出现如下报错，查看了一下CLOS的状态，没有发生改变，估计是要reset才行：

![image-20240629210943006](/Users/hong/Library/Application%20Support/typora-user-images/image-20240629210943006.png)

```shell
# 监控12-17cores上的所有信息 按s输出，很好的格式
pqos -m "all:[12-17];" > bw.txt
```

由于使用python脚本运行pagerank虽然用numactl绑定在12-17 cores上，但是仍然只有第12个core在运行，推测是由于python的全局解释器锁GIL，如果python代码没有被设计成多线程或多进程运行，即使使用numactl绑定到多个cores上也还是会只在一个core上运行。于是去编译C++下的文件，出现很多如下报错：

![image-20240629215616957](/Users/hong/Library/Application%20Support/typora-user-images/image-20240629215616957.png)

原因是linux gcc 11 取消了头文件多层关联造成的，只需要将对应函数的所在的头文件包括在当前文件中即可。

参考：https://blog.csdn.net/donglynn/article/details/21807583

```shell
# 尝试用C++运行，查看是否成功
numactl --physcpubind=12-17 --membind=1 ./runpagerankpipeline
```

结果比较离谱，好像CPU 限制并没有对最后的输出结果造成什么影响，还有可能是监控的不太对，感觉还是**规模的问题**，应该就是规模的问题，因为越往后计算的越慢，后面SCALE改成22-42看一下结果有没有什么变化！

再做一遍python下的测试看看结果是不是一样。好像有不同

没有CPU受限：

```
hwt@cxl-2288H-V7:~/workspace/PageRankBenchmark/code/Python$ numactl -c 1 -m 2 python3 runPageRankPipeline.py 
Number of Edges 16384, Max Possible Vertex: 1024
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.025305713003035635, Edges/sec: 647442.733505853
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 0.034770886006299406, Edges/sec: 471198.80687054474
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
/home/hwt/workspace/PageRankBenchmark/code/Python/PageRankPipeline.py:179: RuntimeWarning: divide by zero encountered in true_divide
  dinv=np.squeeze(np.asarray(1/dout))
K2time 0.015741848008474335, Edges/sec: 1040792.6687629034
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.0011244099878240377, Edges/sec: 291423949.93673754
Number of Edges 32768, Max Possible Vertex: 2048
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.030580406018998474, Edges/sec: 1071535.8056280368
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 0.08039936100249179, Edges/sec: 407565.4282747898
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 0.029833336011506617, Edges/sec: 1098368.6164819614
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.0013734450039919466, Edges/sec: 477165083.49091697
Number of Edges 65536, Max Possible Vertex: 4096
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.062001787999179214, Edges/sec: 1057001.7755111768
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 0.12748995597939938, Edges/sec: 514048.3381341014
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 0.059305417991708964, Edges/sec: 1105059.2377438785
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.0020840409852098674, Edges/sec: 628931968.8537736
Number of Edges 131072, Max Possible Vertex: 8192
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.127328305010451, Edges/sec: 1029401.9070562647
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 0.2726837410009466, Edges/sec: 480674.0567621338
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 0.14224999898578972, Edges/sec: 921420.0417189011
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.0036980579898227006, Edges/sec: 708869359.8679025
Number of Edges 262144, Max Possible Vertex: 16384
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.26137826300691813, Edges/sec: 1002929.6123720189
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 0.5528913349844515, Edges/sec: 474132.95056861767
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 0.3494059340155218, Edges/sec: 750256.2906912585
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.007627705985214561, Edges/sec: 687346891.7342547
Number of Edges 524288, Max Possible Vertex: 32768
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.5536749750026502, Edges/sec: 946923.7796010023
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 1.197352587012574, Edges/sec: 437872.6915420229
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 0.7928932780050673, Edges/sec: 661234.00783409
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.014318670990178362, Edges/sec: 732313774.5948993
Number of Edges 1048576, Max Possible Vertex: 65536
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 1.2399777920218185, Edges/sec: 845640.951593389
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 2.8753590369888116, Edges/sec: 364676.54526306037
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 1.8317210599780083, Edges/sec: 572453.9739760318
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.02770100298221223, Edges/sec: 757067172.3860157
Number of Edges 2097152, Max Possible Vertex: 131072
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 2.95637377499952, Edges/sec: 709366.3249669236
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 6.8680097769829445, Edges/sec: 305350.7592590033
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 4.768226343992865, Edges/sec: 439818.04736305075
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.07037653800216503, Edges/sec: 595980438.8034785
Number of Edges 4194304, Max Possible Vertex: 262144
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 6.7269418299838435, Edges/sec: 623508.2903950239
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 15.191624329017941, Edges/sec: 276093.188533391
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 10.9530578039994, Edges/sec: 382934.52614378533
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.2646056300145574, Edges/sec: 317023035.3578833
Number of Edges 8388608, Max Possible Vertex: 524288
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 15.90956103100325, Edges/sec: 527268.3503745307
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 32.86966057898826, Edges/sec: 255208.2331316305
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 21.75835087901214, Edges/sec: 385535.100828416
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.6814878779987339, Edges/sec: 246185097.9546135
Number of Edges 16777216, Max Possible Vertex: 1048576
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 34.93739941201056, Edges/sec: 480207.9228092871
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 65.25425199000165, Edges/sec: 257105.3301257768
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 45.98567997501232, Edges/sec: 364835.6620825526
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 1.7348258899874054, Edges/sec: 193416712.2687084
Number of Edges 33554432, Max Possible Vertex: 2097152
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 73.9796148710011, Edges/sec: 453563.2154683308
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 129.52829828500398, Edges/sec: 259050.97530247358
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 92.82992307600216, Edges/sec: 361461.37891903834
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 4.281723235006211, Edges/sec: 156733306.46720946
[[6.47442734e+05 4.71198807e+05 1.04079267e+06 2.91423950e+08]
 [1.07153581e+06 4.07565428e+05 1.09836862e+06 4.77165083e+08]
 [1.05700178e+06 5.14048338e+05 1.10505924e+06 6.28931969e+08]
 [1.02940191e+06 4.80674057e+05 9.21420042e+05 7.08869360e+08]
 [1.00292961e+06 4.74132951e+05 7.50256291e+05 6.87346892e+08]
 [9.46923780e+05 4.37872692e+05 6.61234008e+05 7.32313775e+08]
 [8.45640952e+05 3.64676545e+05 5.72453974e+05 7.57067172e+08]
 [7.09366325e+05 3.05350759e+05 4.39818047e+05 5.95980439e+08]
 [6.23508290e+05 2.76093189e+05 3.82934526e+05 3.17023035e+08]
 [5.27268350e+05 2.55208233e+05 3.85535101e+05 2.46185098e+08]
 [4.80207923e+05 2.57105330e+05 3.64835662e+05 1.93416712e+08]
 [4.53563215e+05 2.59050975e+05 3.61461379e+05 1.56733306e+08]]
```

CPU受限50%（论文上写的是10%，）：

```
hwt@cxl-2288H-V7:~/workspace/PageRankBenchmark/code/Python$ numactl -c 1 -m 2 python3 runPageRankPipeline.py 
Number of Edges 16384, Max Possible Vertex: 1024
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.09130801999708638, Edges/sec: 179436.5927606667
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 0.10319727301248349, Edges/sec: 158763.8851466363
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
/home/hwt/workspace/PageRankBenchmark/code/Python/PageRankPipeline.py:179: RuntimeWarning: divide by zero encountered in true_divide
  dinv=np.squeeze(np.asarray(1/dout))
K2time 0.016986939997877926, Edges/sec: 964505.6733023578
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.0012307720026001334, Edges/sec: 266239400.3988895
Number of Edges 32768, Max Possible Vertex: 2048
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.03078593499958515, Edges/sec: 1064382.160244331
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 0.09565260697854683, Edges/sec: 342572.9944542889
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 0.0308772079879418, Edges/sec: 1061235.8479042726
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.0014720990147907287, Edges/sec: 445187445.5558718
Number of Edges 65536, Max Possible Vertex: 4096
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.06329726098920219, Edges/sec: 1035368.6553858897
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 0.15218430900131352, Edges/sec: 430635.72342030576
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 0.06274163900525309, Edges/sec: 1044537.583637446
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.002121291996445507, Edges/sec: 617887590.2969875
Number of Edges 131072, Max Possible Vertex: 8192
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.13152538900612853, Edges/sec: 996552.8404093342
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 0.3194779390178155, Edges/sec: 410269.3300293603
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 0.16955205600243062, Edges/sec: 773048.7207900387
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.0038385810039471835, Edges/sec: 682919025.8859702
Number of Edges 262144, Max Possible Vertex: 16384
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.2785902210162021, Edges/sec: 940966.2659507146
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 0.6513246829854324, Edges/sec: 402478.2214585028
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 0.4498324480082374, Edges/sec: 582759.2054791022
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.007688095996854827, Edges/sec: 681947780.3275146
Number of Edges 524288, Max Possible Vertex: 32768
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 0.6021156560163945, Edges/sec: 870743.0121792492
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 1.421109401009744, Edges/sec: 368928.6691281308
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 1.0388203150068875, Edges/sec: 504695.5594014581
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.014952602999983355, Edges/sec: 701266528.6446562
Number of Edges 1048576, Max Possible Vertex: 65536
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 1.423829922976438, Edges/sec: 736447.5089890017
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 3.4081088560051285, Edges/sec: 307670.923759491
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 2.3398837939894293, Edges/sec: 448131.6562358896
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.03305816199281253, Edges/sec: 634382516.6250806
Number of Edges 2097152, Max Possible Vertex: 131072
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 3.284820019995095, Edges/sec: 638437.4142980082
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 8.050193306000438, Edges/sec: 260509.52073869194
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 5.66825555198011, Edges/sec: 369981.9072672888
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.11754154600203037, Edges/sec: 356835871.4566804
Number of Edges 4194304, Max Possible Vertex: 262144
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 7.1727755820029415, Edges/sec: 584753.2732689754
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 16.004232782986946, Edges/sec: 262074.66842513627
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 11.339032151998254, Edges/sec: 369899.64785141265
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.34614480499294586, Edges/sec: 242343894.20262864
Number of Edges 8388608, Max Possible Vertex: 524288
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 16.201794068998424, Edges/sec: 517757.96953568945
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 33.449017339997226, Edges/sec: 250787.87561179505
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 22.502537257998483, Edges/sec: 372784.9843696308
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 0.8554980019980576, Edges/sec: 196110522.30181706
Number of Edges 16777216, Max Possible Vertex: 1048576
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 35.66034964102437, Edges/sec: 470472.5603895695
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 66.36519095502445, Edges/sec: 252801.44242137246
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 48.17902784200851, Edges/sec: 348226.53655480203
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 2.3204187839874066, Edges/sec: 144605069.70358205
Number of Edges 33554432, Max Possible Vertex: 2097152
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 75.72045744897332, Edges/sec: 443135.6218709024
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 132.4285734469886, Edges/sec: 253377.58405614708
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
K2time 97.7489774459973, Edges/sec: 343271.4374791039
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 5.660432939010207, Edges/sec: 118557828.9206528
[[1.79436593e+05 1.58763885e+05 9.64505673e+05 2.66239400e+08]
 [1.06438216e+06 3.42572994e+05 1.06123585e+06 4.45187446e+08]
 [1.03536866e+06 4.30635723e+05 1.04453758e+06 6.17887590e+08]
 [9.96552840e+05 4.10269330e+05 7.73048721e+05 6.82919026e+08]
 [9.40966266e+05 4.02478221e+05 5.82759205e+05 6.81947780e+08]
 [8.70743012e+05 3.68928669e+05 5.04695559e+05 7.01266529e+08]
 [7.36447509e+05 3.07670924e+05 4.48131656e+05 6.34382517e+08]
 [6.38437414e+05 2.60509521e+05 3.69981907e+05 3.56835871e+08]
 [5.84753273e+05 2.62074668e+05 3.69899648e+05 2.42343894e+08]
 [5.17757970e+05 2.50787876e+05 3.72784984e+05 1.96110522e+08]
 [4.70472560e+05 2.52801442e+05 3.48226537e+05 1.44605070e+08]
 [4.43135622e+05 2.53377584e+05 3.43271437e+05 1.18557829e+08]]
```

















https://smartkeyerror.com/Linux-Cgroup

https://egonlin.com/?p=7582







### 测试二

寻找一个应用测试在不同Intel MBA的throttling value下对带宽和延迟的影响

直接用MLC或者用Stream测试带宽；因为之前的MT2使用fio也都是差不多的workload







### 测试三

寻找一个应用测试在不同的CPU quota下对带宽和延迟的影响



