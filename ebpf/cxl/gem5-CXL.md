考虑提一下gem5-CXL这个项目有什么区别？

相关工作上要提一下CXLMemSim，还有gem5-CXL那个论文的

host也要解释一下，模拟器里也要解释一下

互操作性和兼容性

使用gem5本身带有的memory model，现在建模的比较简单。可以将后续的工作完善一下加进去。

实验参数部分，本地DRAM和CXL memory，内存放大一些跑

----

能够对未来体系结构方面的工作有哪些帮助；

比如cache协议的优化，设备端的一些处理上的优化；

没有提到simulation timescales，仿真精度和gem5一样；如果精度足够高，可以不用emulation的方法。

使用gem5实现多host的disaggregated memory，可以扩展多host，same with xxx paper distgem5

-----

使用模拟器对宿主机的要求，使用的计算资源和空间资源的要求，真实的运行时间和模拟器的运行时间，考虑模拟器的限制。

---

workload部分取一些machine learning inference tasks或者large-scale scientific computations的任务，但是gem5上可能运行不了这些真实应用。









```

10%

Number of Edges 67108864, Max Possible Vertex: 4194304
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 1084.1598904400016, Edges/sec: 61899.415936485304
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 1734.2888536359824, Edges/sec: 38695.32105871781
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
/home/hwt/workspace/PageRankBenchmark/code/Python/PageRankPipeline.py:179: RuntimeWarning: divide by zero encountered in true_divide
  dinv=np.squeeze(np.asarray(1/dout))
K2time 1327.0780851779855, Edges/sec: 50568.88871086999
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 48.27560329600237, Edges/sec: 27802392.68622757
[[   61899.41593649    38695.32105872    50568.88871087 27802392.68622757]]

20%

hwt@cxl-2288H-V7:~/workspace/PageRankBenchmark/code/Python$ numactl -c 1 -m 2 python3 runPageRankPipeline.py 
Number of Edges 67108864, Max Possible Vertex: 4194304
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 192.76923546899343, Edges/sec: 348130.5709219059
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 309.5617836249876, Edges/sec: 216786.65633125335
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
/home/hwt/workspace/PageRankBenchmark/code/Python/PageRankPipeline.py:179: RuntimeWarning: divide by zero encountered in true_divide
  dinv=np.squeeze(np.asarray(1/dout))
K2time 224.9648362500011, Edges/sec: 298308.2383836317
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 10.859041691001039, Edges/sec: 123599974.85894832
[[3.48130571e+05 2.16786656e+05 2.98308238e+05 1.23599975e+08]]


30%






40%

hwt@cxl-2288H-V7:~/workspace/PageRankBenchmark/code/Python$ numactl -c 1 -m 2 python3 runPageRankPipeline.py 
Number of Edges 67108864, Max Possible Vertex: 4194304
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 192.76923546899343, Edges/sec: 348130.5709219059
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 309.5617836249876, Edges/sec: 216786.65633125335
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
/home/hwt/workspace/PageRankBenchmark/code/Python/PageRankPipeline.py:179: RuntimeWarning: divide by zero encountered in true_divide
  dinv=np.squeeze(np.asarray(1/dout))
K2time 224.9648362500011, Edges/sec: 298308.2383836317
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 10.859041691001039, Edges/sec: 123599974.85894832
[[3.48130571e+05 2.16786656e+05 2.98308238e+05 1.23599975e+08]]

50%

Number of Edges 67108864, Max Possible Vertex: 4194304
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 154.83952075600973, Edges/sec: 433409.1430426707
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 260.87387040199246, Edges/sec: 257246.39994258102
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
/home/hwt/workspace/PageRankBenchmark/code/Python/PageRankPipeline.py:179: RuntimeWarning: divide by zero encountered in true_divide
  dinv=np.squeeze(np.asarray(1/dout))
K2time 185.9288255770225, Edges/sec: 360938.4601431778
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 10.298378663981566, Edges/sec: 130328989.03729828
[[4.33409143e+05 2.57246400e+05 3.60938460e+05 1.30328989e+08]]
```



```shell




cgroups 50%:

hwt@cxl-2288H-V7:~/workspace/PageRankBenchmark/code/Python$ numactl -c 1 -m 2 python3 runPageRankPipeline.py 
Number of Edges 67108864, Max Possible Vertex: 4194304
Kernel 0: Generate Graph, Write Edges
   Writing: data/K0/0.tsv
^[[D^[[D   Writing: data/K0/1.tsv
   Writing: data/K0/2.tsv
   Writing: data/K0/3.tsv
K0time 481.5626743409957, Edges/sec: 139356.44844533785
Kernel 1: Read, Sort, Write Edges
   Reading:data/K0/0.tsv
   Reading:data/K0/1.tsv
   Reading:data/K0/2.tsv
   Reading:data/K0/3.tsv
   Writing: data/K1/0.tsv
   Writing: data/K1/1.tsv
   Writing: data/K1/2.tsv
   Writing: data/K1/3.tsv
K1time 523.4591158939875, Edges/sec: 128202.68472235583
Kernel 2: Read, Filter Edges
   Reading:data/K1/0.tsv
   Reading:data/K1/1.tsv
   Reading:data/K1/2.tsv
   Reading:data/K1/3.tsv
/home/hwt/workspace/PageRankBenchmark/code/Python/PageRankPipeline.py:179: RuntimeWarning: divide by zero encountered in true_divide
  dinv=np.squeeze(np.asarray(1/dout))
K2time 381.0351698890154, Edges/sec: 176122.4928910024
Kernel 3: Compute PageRank.
Pagerank Sum= [1.]
K3time 22.660432727017906, Edges/sec: 59229993.36194183
[[  139356.44844534   128202.68472236   176122.492891   59229993.36194184]]
```

![image-20240630150609215](/Users/hong/Library/Application%20Support/typora-user-images/image-20240630150609215.png)



查看系统没有挂载的相关信息。

1. **查看当前挂载的 cgroup 子系统**:

   ```shell
   mount | grep cgroup
   ```

2. **查看 cgroup 子系统的配置**:

   ```shell
   cat /proc/cgroups
   ```

3. **查看 cgroup 子系统是否启用**:

   ```shell
   cat /boot/config-$(uname -r) | grep -E 'CONFIG_CGROUPS|CONFIG_CPUSETS'
   ```

![image-20240630153919496](/Users/hong/Library/Application%20Support/typora-user-images/image-20240630153919496.png)

4. **手动挂载 cgroup 子系统**: 如果 cgroup 子系统没有挂载，你可以使用以下命令手动挂载它们：

```shell
mount -t cgroup -o cpuset none /sys/fs/cgroup/cpuset
mount -t cgroup -o cpu none /sys/fs/cgroup/cpu
mount -t cgroup -o memory none /sys/fs/cgroup/memory
```





----

### 通过cgroup的cpu.shares控制

1. **创建 cgroup**: 使用 `cgcreate` 命令创建一个新的 cgroup。例如，创建一个名为 `cpu_limited` 的 cgroup：

   ```
   sudo cgcreate -g cpu:cpu_limited
   ```

2. **设置 CPU 份额**: 使用 `cgset` 命令设置 CPU 份额。CPU 份额是通过 `cpu.shares` 参数来设置的。默认情况下，每个 cgroup 的 CPU 份额是 1024。要设置不同百分比的 CPU 使用，可以按照以下比例进行设置：

   - 10%: 102
   - 20%: 204
   - 30%: 307
   - 40%: 409
   - 50%: 512 (基准值，表示没有限制)
   - 60%: 614
   - 70%: 716
   - 80%: 819
   - 90%: 920
   - 100%: 1024

   例如，要设置 50% 的 CPU 使用，可以执行：

   ```
   sudo cgset -r cpu.shares=512 cpu_limited
   ```

   对于其他百分比，你只需要将 `512` 替换为上面列出的相应值。

3. **将进程添加到 cgroup**: 使用 `echo` 命令将进程 ID 添加到 cgroup。例如，如果你想要限制名为 `my_process` 的进程的 CPU 使用，可以执行：

   ```
   sudo echo $(pgrep my_process) > /sys/fs/cgroup/cpu/cpu_limited/cgroup.procs
   ```

4. **监控 CPU 使用**: 你可以使用 `top`、`htop` 或 `cgget` 等工具来监控进程的 CPU 使用情况。

这些设置**只影响 CPU 调度的相对权重，并不保证绝对百分比的 CPU 时间**。例如，<font color='red'>**如果系统中只有一个进程，即使设置了 50% 的 CPU 份额，该进程也可能使用 100% 的 CPU 时间，因为没有其他进程竞争 CPU 资源**</font>。

另外，如果你使用的是较新的 Linux 系统，可能需要使用 systemd 的 cgroup 管理功能，而不是 `cgcreate` 和 `cgset`。在这种情况下，你可以创建一个 systemd 服务单元文件来设置 CPU 份额，然后启动和启用该服务。

---

### 通过cpu.cfs_period_us和cpu.cfs_quota_us控制

通过设置 `cpu.cfs_period_us` 和 `cpu.cfs_quota_us` 可以精确地控制 cgroup 中进程的 CPU 时间分配。这两个参数定义了 CPU 调度的配额系统：

- `cpu.cfs_period_us`：这是 CPU 调度周期的长度，以微秒为单位。这个值通常设置为 100000 微秒（即 100 毫秒）。
- `cpu.cfs_quota_us`：这是在每个 `cpu.cfs_period_us` 周期内，cgroup 中所有进程可以占用的 CPU 时间，以微秒为单位。

要设置进程的 CPU 使用百分比，可以使用以下公式来计算 `cpu.cfs_quota_us` 的值：

\text{cpu.cfs_quota_us} = \left(\frac{\text{所需百分比}}{100}\right) \times \text{cpu.cfs_period_us}

假设 `cpu.cfs_period_us` 设置为 100000 微秒，以下是如何设置不同百分比 CPU 使用的例子：

- 10% 的 CPU 使用：

  ```
  echo 100000 | sudo tee /sys/fs/cgroup/cpu/cpu.cfs_period_us
  echo 10000 | sudo tee /sys/fs/cgroup/cpu/my_group/cpu.cfs_quota_us
  ```

- 20% 的 CPU 使用：

  ```
  echo 20000 | sudo tee /sys/fs/cgroup/cpu/my_group/cpu.cfs_quota_us
  ```

以此类推，直到 100% 的 CPU 使用，此时 `cpu.cfs_quota_us` 将等于 `cpu.cfs_period_us` 的值。

以下是具体的步骤：

1. **创建 cgroup**:

   ```
   sudo cgcreate -g cpu:my_group
   ```

2. **设置 CPU 调度周期**: 通常，这个周期设置为 100 毫秒（100000 微秒），这是一个合理的默认值，适用于大多数情况。

   ```
   echo 100000 | sudo tee /sys/fs/cgroup/cpu/my_group/cpu.cfs_period_us
   ```

3. **设置 CPU 配额**: 根据你想要限制的 CPU 使用百分比，设置 `cpu.cfs_quota_us`。例如，要限制为 50% 的 CPU 使用：

   ```
   echo 50000 | sudo tee /sys/fs/cgroup/cpu/my_group/cpu.cfs_quota_us
   ```

4. **将进程添加到 cgroup**:

   ```
   echo $(pgrep my_process) | sudo tee /sys/fs/cgroup/cpu/my_group/cgroup.procs
   ```

5. **监控和调整**: 使用 `top`、`htop` 或其他监控工具来观察进程的 CPU 使用情况，并根据需要调整 `cpu.cfs_quota_us` 的值。

请注意，`cpu.cfs_period_us` 应该在所有相关的 cgroup 中设置为相同的值，以保持一致性。另外，这些设置只影响 CPU 调度权重，并不保证绝对 CPU 时间，因为 CPU 时间的实际分配还受到系统中其他进程和它们的 CPU 需求的影响。





![image-20240630191039621](/Users/hong/Library/Application%20Support/typora-user-images/image-20240630191039621.png)



https://icloudnative.io/posts/understanding-cgroups-part-2-cpu/









## FAST25 Important Dates

- Paper submissions due: **Tuesday, September 17, 2024, 11:59 pm PDT**
- Author response period begins: **Wednesday, November 20, 2024**
- Author response period ends: **Friday, November 22, 2024, 11:59 pm PST**
- Notification to authors: **Friday, December 6, 2024**
- Final paper files due: **Tuesday, January 28, 2025**

https://www.usenix.org/conference/fast25/call-for-papers

![image-20240630202542542](/Users/hong/Library/Application%20Support/typora-user-images/image-20240630202542542.png)

The complete submission must be **no longer than 12 pages for long papers and no longer than 6 pages for short papers**, excluding references. The program committee values conciseness: if you can express an idea in fewer pages than the limit, do so.



## DATE





![image-20240630203927849](/Users/hong/Library/Application%20Support/typora-user-images/image-20240630203927849.png)



## HPCA Important Dates

![image-20240630204427686](/Users/hong/Library/Application%20Support/typora-user-images/image-20240630204427686.png)

https://hpca-conf.org/2024/

![image-20240630204548185](/Users/hong/Library/Application%20Support/typora-user-images/image-20240630204548185.png)

![image-20240630204638919](/Users/hong/Library/Application%20Support/typora-user-images/image-20240630204638919.png)



hwt@cxl2-2288H-V7:~/monitor/intel-cmt-cat/pqos$ ./pqos -v
NOTE:  Mixed use of MSR and kernel interfaces to manage
       CAT or CMT & MBM may lead to unexpected behavior.
INFO: Requested interface: AUTO
INFO: resctrl detected
INFO: Selected interface: OS
INFO: CACHE: type 1, level 1, max id sharing this cache 2 (1 bits)
INFO: CACHE: type 2, level 1, max id sharing this cache 2 (1 bits)
INFO: CACHE: type 3, level 2, max id sharing this cache 2 (1 bits)
INFO: CACHE: type 3, level 3, max id sharing this cache 128 (7 bits)
INFO: resctrl detected
INFO: resctrl not mounted
INFO: Unable to mount resctrl
ERROR: os_cap_init() error 3
Error initializing PQoS library!


https://github.com/intel/intel-cmt-cat/issues/152


权限问题导致：
https://github.com/intel/intel-cmt-cat/issues/190


尝试手动挂载resctrl进行修复，确实没有error3，但是会出现创建COS1失败

hwt@cxl2-2288H-V7:~/monitor/intel-cmt-cat/pqos$ pqos -v
NOTE:  Mixed use of MSR and kernel interfaces to manage
       CAT or CMT & MBM may lead to unexpected behavior.
INFO: Requested interface: AUTO
INFO: resctrl detected
INFO: Selected interface: OS
INFO: CACHE: type 1, level 1, max id sharing this cache 2 (1 bits)
INFO: CACHE: type 2, level 1, max id sharing this cache 2 (1 bits)
INFO: CACHE: type 3, level 2, max id sharing this cache 2 (1 bits)
INFO: CACHE: type 3, level 3, max id sharing this cache 128 (7 bits)
INFO: resctrl detected
INFO: Monitoring capability detected
INFO: L3CA capability detected
INFO: L3 CAT details: CDP support=1, CDP on=0, #COS=8, #ways=15, ways contention bit-mask 0x6000
INFO: L3 CAT details: cache size 102236160 bytes, way size 6815744 bytes
INFO: L3 CAT details: I/O RDT support=0, I/O RDT on=0
INFO: L2CA capability detected
INFO: L2 CAT details: CDP support=1, CDP on=0, #COS=8, #ways=16, ways contention bit-mask 0x0
INFO: L2 CAT details: cache size 2097152 bytes, way size 131072 bytes
INFO: MBA capability detected
INFO: MBA details: #COS=8, linear, max=90, step=10
INFO: SMBA capability not detected
INFO: OS support for MBA CTRL unknown
ERROR: Failed to create resctrl group /sys/fs/resctrl/COS1!
ERROR: OS allocation init error!


```bash
sudo mount -t resctrl resctrl /sys/fs/resctrl

unmount /sys/fs/resctrl

ls -l /sys/fs/resctrl

```

以上原因主要是由于手动挂载resctrl
https://github.com/intel/intel-cmt-cat/issues/204

后面又思考了一下，尝试重新挂载，然后由于提示的信息是无法创建/sys/fs/resctrl/COS1，这个目录是在sudoer权限下，所以想到可能是由于权限问题导致无法正常使用，于是考虑使用sudo pqos -v并查看运行结果，仍然报错如下：



API lock initialization error!
Error initializing PQoS library! 

考虑到/var/lock/下pqos创建lock文件可能对权限有影响，于是sudo先删除/var/lock/libpqos,然后再sudo运行pqos，成功！
    Core 161, L2ID 81, L3ID 1 => COS0
    Core 162, L2ID 82, L3ID 1 => COS0
    Core 163, L2ID 83, L3ID 1 => COS0
    Core 164, L2ID 84, L3ID 1 => COS0
    Core 165, L2ID 85, L3ID 1 => COS0
    Core 166, L2ID 86, L3ID 1 => COS0
    Core 167, L2ID 87, L3ID 1 => COS0
    Core 168, L2ID 88, L3ID 1 => COS0
    Core 169, L2ID 89, L3ID 1 => COS0
    Core 170, L2ID 90, L3ID 1 => COS0
    Core 171, L2ID 91, L3ID 1 => COS0
    Core 172, L2ID 92, L3ID 1 => COS0
    Core 173, L2ID 93, L3ID 1 => COS0
    Core 174, L2ID 94, L3ID 1 => COS0
    Core 175, L2ID 95, L3ID 1 => COS0
    Core 176, L2ID 96, L3ID 1 => COS0
    Core 177, L2ID 97, L3ID 1 => COS0
    Core 178, L2ID 98, L3ID 1 => COS0
    Core 179, L2ID 99, L3ID 1 => COS0
    Core 180, L2ID 100, L3ID 1 => COS0
    Core 181, L2ID 101, L3ID 1 => COS0
    Core 182, L2ID 102, L3ID 1 => COS0
    Core 183, L2ID 103, L3ID 1 => COS0
    Core 184, L2ID 104, L3ID 1 => COS0
    Core 185, L2ID 105, L3ID 1 => COS0
    Core 186, L2ID 106, L3ID 1 => COS0
    Core 187, L2ID 107, L3ID 1 => COS0
    Core 188, L2ID 108, L3ID 1 => COS0
    Core 189, L2ID 109, L3ID 1 => COS0
    Core 190, L2ID 110, L3ID 1 => COS0
    Core 191, L2ID 111, L3ID 1 => COS0
PID association information:
    COS1 => (none)
    COS2 => (none)
    COS3 => (none)
    COS4 => (none)
    COS5 => (none)
    COS6 => (none)
    COS7 => (none)
https://github.com/intel/intel-cmt-cat/issues/190


问题终于解决！

