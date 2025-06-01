# MESS benchmark使用

Mess工具中主要使用perf, vtune, likwid采样工具采集x86硬件数据进行分析统计。

SPR使用likwid进行带宽数据采集，使用perf进行延迟数据采集；

Skylake使用vtune进行带宽数据采集，使用perf进行延迟数据采集；

AMD使用perf同时进行带宽和延迟的采集

### 相关工具安装

#### 1. likwid安装

https://github.com/RRZE-HPC/likwid



```shell
#!/bin/sh


VERSION=stable
wget http://ftp.fau.de/pub/likwid/likwid-$VERSION.tar.gz
tar -xaf likwid-$VERSION.tar.gz
cd likwid-*
vi config.mk # configure build, e.g. change installation prefix and architecture flags
make
sudo make install # sudo required to install the access daemon with proper permissions

```

#### 2. mwget加速

https://blog.csdn.net/woai8339/article/details/139521249

#### 3. vtune安装

https://www.intel.cn/content/www/cn/zh/developer/tools/oneapi/base-toolkit-download.html?operatingsystem=linux&linux-install-type=online

```shell
wget https://registrationcenter-download.intel.com/akdlm/IRC_NAS/e6ff8e9c-ee28-47fb-abd7-5c524c983e1c/l_BaseKit_p_2024.2.1.100.sh

sudo sh ./l_BaseKit_p_2024.2.1.100.sh -a --silent --cli --eula accept
```

在服务器上使用vtune https://seekstar.github.io/2021/09/19/%E5%9C%A8%E6%9C%8D%E5%8A%A1%E5%99%A8%E4%B8%8A%E4%BD%BF%E7%94%A8vtune/

![image-20240912205933393](/Users/hong/Library/Application%20Support/typora-user-images/image-20240912205933393.png)

#### 4. MPI安装

https://blog.csdn.net/murongjunxiaoxiao/article/details/123801286

```shell
sudo apt install mpich
```

### 5. module工具安装

EnvironmentModules是一个用于管理shell环境的工具，它允许用户通过modulefiles轻松修改会话期间的环境。用户可以使用module命令加载、卸载和管理模块，这些模块定义了如PATH、MANPATH等环境变量。modulefiles包含在modulepath目录下，可以设置环境变量、加载其他模块并处理依赖关系和冲突。常见的module命令包括moduleavail、moduleload、moduleunload和modulelist。

官方安装指南 https://modules.readthedocs.io/en/latest/INSTALL.html#install

使用指南 https://blog.csdn.net/bleauchat/article/details/130978158

module安装和使用介绍 https://blog.csdn.net/Michael177/article/details/121152904

```shell
$ curl -LJO https://github.com/cea-hpc/modules/releases/download/v5.4.0/modules-5.4.0.tar.gz
$ tar xfz modules-5.4.0.tar.gz

# 运行会报没有Tcl相关工具的问题
```

https://www.cnblogs.com/h2285409/p/17092669.html



```shell
sudo apt install environment-modules
# 尝试使用以上指令安装

module list # 仍然 command not found
modulecmd bash  # Then I guess "module" is usually a symbolic link to "modulecmd". Posts: 17,809

In the directory were it was installed there's 'modulecmd' which does the same as "module" should do
So--put that in $PATH---or just make a soft link to someplace that's already in $PATH

```

https://www.linuxquestions.org/questions/linux-newbie-8/bash-module-command-not-found-4175420132/

### 6. Tcl安装

![image-20240912221955195](/Users/hong/Library/Application%20Support/typora-user-images/image-20240912221955195.png)

arraygen.c实现了一个随机游走生成器，用于生成一个随机化的数组并将其写入到名为"array.dat"的文件中

ptr_chase.c从"array.dat"中读取数据，并通过**汇编指令**在数组中进行一系列跳转操作.









除了运行时参数是，主要代码在stream_mpi.c文件中，內含array size 默认是80，000 ，000。该参数可以通过修改源码或

该基准测试生成针对主存储器的流量，具有两个运行时参数：

1. 特定数量的读请求（占总流量读取量的50%到100%，步长为2%）。
2. 一个暂停时间，通过在内存请求之间执行nop指令注入延迟，从而降低生成的带宽。

这些参数允许在基准测试中模拟不同的读取请求量和延迟条件，以评估系统的性能和响应能力。通过调整这两个参数，可以更全面地了解系统在不同负载条件下的表现。



这个基准测试是基于修改后的STREAM基准测试[1]。它使用MPI库和可选的OpenMP指令。与原始STREAM基准测试相比，有以下明显的不同之处：

1. 它仅包含了复制（Copy）内核，而不同读取/写入比例的特定内核函数是用x86汇编编码实现的，使用了AVX指令和非临时存储（在utils.c文件中定义并详细解释）。
2. 不会检查数组的内容是否正确。
3. 不需要任何类型的计时。
4. 基准测试会无限循环运行，而不是使用NTIMES宏来定义迭代次数。



不同比例读写的细节实现：

复制（Copy）内核 复制内核是一个用汇编语言编写的函数，从内存中对两个独立数组执行加载和存储操作，从而生成具有所需内存读取和写入比例的内存流量。针对每个读取百分比都编写了特定的内核函数，它们都位于utils.c文件中。每个内核由100个矢量移动指令组成。加载和存储指令之间的比例取决于内核的读取百分比。例如，对应于60%读取的内核STREAM_copy_60包含60个矢量加载指令和40个矢量存储指令。

每个内核都有不同读写指令组合，以满足特定的读取百分比需求。这种实现方式可以有效地控制内存流量的读取和写入比例，并对系统性能进行详细的测试和评估。

汇编代码目前是按照AT&T语法（GNU工具使用）编写的。对于感兴趣的读者，可以在AT&T语法（Wikibooks）和AT&T与Intel语法之间的主要区别（维基百科）中找到更多信息。这里提供一个简短的总结：

- 第一个操作数是源操作数，第二个操作数是目的地操作数。
- 寻址使用以下格式：
  - $200 - 立即值200
  - %r10 - 寄存器r10
  - 32(%r10,%rbx,8) - 内存地址计算为%r10 + %rbx*8 + 32。一般格式为位移（基址寄存器，索引寄存器，缩放因子），这在我们的情况下翻译为基址寄存器 + 索引寄存器 * 缩放因子 + 位移。在我们的情况下，缩放因子为8，因为数组由双精度浮点数组成，大小为8字节。
- 使用指令vmovupd执行加载操作，从给定内存地址加载256位（32字节）到矢量寄存器%ymm0。使用指令vmovntpd执行存储操作，将来自寄存器%ymm1的256位（32字节）存储到给定内存地址，使用非临时提示绕过缓存（更多关于非临时内存指令的信息，第6.1节）。
- 加载和存储指令块与在文件nop.c中实现的函数nop的调用交错进行。此函数将要执行的nop指令数作为暂停参数通过寄存器rdi传递。注意：注意函数nop和nop指令之间的区别。



这个文件夹包含用于后处理性能计数器数据的脚本。 当前实现的功能包括：

- 解析性能分析工具的输出
- 检测性能计数器读数中的异常
- 从上述异常中恢复
- 数据过滤和曲线平滑
- 绘图



CXL Switch模拟器

https://github.com/JackrabbitLabs/cse







### Graph 500

```shell
hwt@cxl2:~/benchmarks/graph500-2.1.4$  ./seq-csr/seq-csr -s 22 -e 16
SCALE: 22
nvtx: 4194304
edgefactor: 16
terasize: 1.07374182399999998e-03
A: 5.69999999999999951e-01
B: 1.90000000000000002e-01
C: 1.90000000000000002e-01
D: 5.00000000000000444e-02
generation_time: 6.34470069690000003e+01
construction_time: 1.71784277619999983e+01
nbfs: 64
min_time: 9.90447925000000007e-01
firstquartile_time: 1.00601843925000001e+00
median_time: 1.00923956100000001e+00
thirdquartile_time: 1.01185624700000010e+00
max_time: 1.01924919800000002e+00
mean_time: 1.00859829173437499e+00
stddev_time: 5.36747616767517532e-03
min_nedge: 6.71081140000000000e+07
firstquartile_nedge: 6.71081140000000000e+07
median_nedge: 6.71081140000000000e+07
thirdquartile_nedge: 6.71081140000000000e+07
max_nedge: 6.71081140000000000e+07
mean_nedge: 6.71081140000000000e+07
stddev_nedge: 0.00000000000000000e+00
min_TEPS: 6.58407326997965425e+07
firstquartile_TEPS: 6.63384999659192637e+07
median_TEPS: 6.65308421130542606e+07
thirdquartile_TEPS: 6.67418579976652414e+07
max_TEPS: 6.77553178780196905e+07
harmonic_mean_TEPS: 6.65360179071903750e+07
harmonic_stddev_TEPS: 4.46106372606793229e+04
```

1. **SCALE**：图的规模，这是一个参数，它决定了图中顶点的数量。对于Graph500，顶点数量是2SCALE2*SC**A**L**E*。
2. **nvtx**：图中顶点的数量。
3. **edgefactor**：边因子，这是每个顶点的平均边数。
4. **terasize**：图的大小，以TB为单位。
5. **A, B, C, D**：这些是图生成算法中的参数，它们决定了图的形状和分布。
6. **generation_time**：生成图所需的时间，以秒为单位。
7. **construction_time**：构建图所需的时间，以秒为单位。
8. **nbfs**：执行的BFS（广度优先搜索）遍历的数量。
9. **min_time, firstquartile_time, median_time, thirdquartile_time, max_time**：这些是64次BFS遍历的时间统计数据。最小时间是所有遍历中最快的，第一四分位数是所有遍历中第25快的，中位数是中间值，第三四分位数是第75快的，最大时间是最慢的遍历。
10. **mean_time**：所有BFS遍历的平均时间。
11. **stddev_time**：所有BFS遍历时间的标准差。
12. **min_nedge, firstquartile_nedge, median_nedge, thirdquartile_nedge, max_nedge, mean_nedge, stddev_nedge**：这些是每次BFS遍历处理的边数的统计数据。最小边数是所有遍历中最少的，第一四分位数是所有遍历中第25少的，中位数是中间值，第三四分位数是第75少的，最大边数是最多的，平均边数是所有遍历的平均值，标准差是边数的变异程度。
13. **min_TEPS, firstquartile_TEPS, median_TEPS, thirdquartile_TEPS, max_TEPS, harmonic_mean_TEPS, harmonic_stddev_TEPS**：这些是遍历效率的统计数据，以每秒遍历的边数（TEPS）为单位。最小TEPS是所有遍历中最低的效率，第一四分位数是所有遍历中第25低的效率，中位数是中间值，第三四分位数是第75低的效率，最大TEPS是最高的效率，调和平均TEPS是所有遍历的效率的调和平均值，调和标准差是效率的变异程度



Graph500运行：

https://blog.csdn.net/lpn19961107/article/details/105061495





关于MLC预取器是否可以关闭的问题：

https://huataihuang.gitbooks.io/cloud-atlas/content/server/memory/mlc_intel_memory_latency_checker.html



以下benchmarks可以参考：

https://github.com/ustcadsl/SmartMD

```shell
# 1. Graph500
cd ~/graph500-master && make
./seq-csr/seq-csr -s 22 -e 16 # The main indicator of this application is harmonic_mean_TEPS, the bigger the better. （此应用的主要关注的指标为harmonic_mean_TEPS，越大越好）

# 2. Liblinear-2.1
cd ~/liblinear-2.1 && wget https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/binary/url_combined.bz2
bzip2 -d url_combined.bz2
time ./train -s 7 url_combined # The main indicator of this application is the execution time, the shorter the better. （此应用的主要关注指标为运行时长，越短越好）

# 3. SPECjbb2005-master
cd ~/SPECjbb2005-master 
# Modify the SPECjbb.props file to configure according to personal needs, or you can directly use what we have configured. （首先根据个人需求修改SPECjbb.props文件进行配置，也可以直接用我们已经配置好的）
# Run benchmark
chmod +x run.sh && ./run.sh

#4. Sysbench-0.4.8
sudo apt-get install mysql-server
# update mysql configuration, just `vim /etc/mysql/mysql.conf.d/mysqld.cnf` or `vim /etc/mysql/my.cnf` （更新mysql的配置文件/etc/mysql/mysql.conf.d/mysqld.cnf或/etc/mysql/my.cnf）
sudo service mysql restart
sudo apt-get install sysbench
# Enter mysql （进入mysql中）
mysql -u root -p
# Create database. （创建数据库）
create database sbtest;
exit #Exit the mysql database. （退出mysql数据库）
# Create test data, remember to modify the mysql password in the following command. （创建测试数据，记得修改下面指令中mysql的密码）
sysbench --test=oltp --oltp-test-mode=nontrx --mysql-table-engine=innodb --
mysql-user=root --db-driver=mysql --num-threads=8 --max-requests=5000000 --
oltp-nontrx-mode=select --mysql-db=sbtest --oltp-table-size=7000000 --oltptable-name=sbtest --mysql-host=127.0.0.1 --mysqlsocket=/var/run/mysqld/mysqld.sock --mysql-password=123 prepare
# Test, also remember to modify the mysql password in the following command. （进行测试，同样记得修改下面指令中mysql的密码）
time sysbench --test=oltp --oltp-test-mode=nontrx --mysql-table-engine=innodb --
mysql-user=root --db-driver=mysql --num-threads=8 --max-requests=5000000 --
oltp-nontrx-mode=select --mysql-db=sbtest --oltp-table-size=7000000 --oltptable-name=sbtest --mysql-host=127.0.0.1 --mysqlsocket=/var/run/mysqld/mysqld.sock --mysql-password=123 run
# Note: The performance indicator is the number of transactions processed per second. （注：性能指标为每秒处理的事务数）
# If you need to read the test data into the memory in advance, you can use the following command.  （如果需要提前将测试数据读入内存，可以使用如下指令）
mysql -u root -p 
use sbtest; 
select count(id) from (select * from sbtest) aa;
# If you need to recreate the test data, just delete the original data first. （如果需要重新创建测试数据，需要先删除原先的数据）
drop table sbtest;
# To view the cache hit situation, you can use the following commands. （查看cache hit情况可以使用如下指令）
show global status like 'innodb%read%';
exit 
```





![image-20241006123313386](/Users/hong/Library/Application%20Support/typora-user-images/image-20241006123313386.png)





CPU SPEC使用

https://www.cnblogs.com/LCharles/p/13539911.html

resctrl内核实现

https://www.cnblogs.com/wodemia/p/17745677.html

用户态使用resctrl文件系统

https://cloud.tencent.com/developer/article/2318118





```shell
hwt@cxl2:~/benchmarks/graph500-2.1.4$ numactl -C 1 -m 0 ./seq-csr/seq-csr -s 22 -e 16
SCALE: 22
nvtx: 4194304
edgefactor: 16
terasize: 1.07374182399999998e-03
A: 5.69999999999999951e-01
B: 1.90000000000000002e-01
C: 1.90000000000000002e-01
D: 5.00000000000000444e-02
generation_time: 6.33900900780000001e+01
construction_time: 1.72276103039999988e+01
nbfs: 64
min_time: 1.00882904299999998e+00
firstquartile_time: 1.02403469899999999e+00
median_time: 1.02552676650000008e+00
thirdquartile_time: 1.02869469574999983e+00
max_time: 1.04100967499999997e+00
mean_time: 1.02565115639062499e+00
stddev_time: 5.38250984691524426e-03
min_nedge: 6.71081140000000000e+07
firstquartile_nedge: 6.71081140000000000e+07
median_nedge: 6.71081140000000000e+07
thirdquartile_nedge: 6.71081140000000000e+07
max_nedge: 6.71081140000000000e+07
mean_nedge: 6.71081140000000000e+07
stddev_nedge: 0.00000000000000000e+00
min_TEPS: 6.44644479408896938e+07
firstquartile_TEPS: 6.52592903061561137e+07
median_TEPS: 6.54438872727431878e+07
thirdquartile_TEPS: 6.55747581693496406e+07
max_TEPS: 6.65207990051888302e+07
harmonic_mean_TEPS: 6.54297648687498793e+07
harmonic_stddev_TEPS: 4.32603714230337791e+04
hwt@cxl2:~/benchmarks/graph500-2.1.4$ numactl -C 1 -m 3 ./seq-csr/seq-csr -s 22 -e 16
SCALE: 22
nvtx: 4194304
edgefactor: 16
terasize: 1.07374182399999998e-03
A: 5.69999999999999951e-01
B: 1.90000000000000002e-01
C: 1.90000000000000002e-01
D: 5.00000000000000444e-02
generation_time: 6.37454071359999972e+01
construction_time: 3.59872085339999970e+01
nbfs: 64
min_time: 4.58148729500000051e+00
firstquartile_time: 4.65243467750000050e+00
median_time: 4.66548090750000011e+00
thirdquartile_time: 4.68666628300000010e+00
max_time: 4.73768992000000022e+00
mean_time: 4.66528824062500025e+00
stddev_time: 3.13668261782383689e-02
min_nedge: 6.71081140000000000e+07
firstquartile_nedge: 6.71081140000000000e+07
median_nedge: 6.71081140000000000e+07
thirdquartile_nedge: 6.71081140000000000e+07
max_nedge: 6.71081140000000000e+07
mean_nedge: 6.71081140000000000e+07
stddev_nedge: 0.00000000000000000e+00
min_TEPS: 1.41647332630836256e+07
firstquartile_TEPS: 1.43227742344123088e+07
median_TEPS: 1.43892554145737384e+07
thirdquartile_TEPS: 1.44299433464901298e+07
max_TEPS: 1.46476699986134078e+07
harmonic_mean_TEPS: 1.43845590108725317e+07
harmonic_stddev_TEPS: 1.21847991084322093e+04
hwt@cxl2:~/benchmarks/graph500-2.1.4$ numactl -C 1 -m 1 ./seq-csr/seq-csr -s 22 -e 16
SCALE: 22
nvtx: 4194304
edgefactor: 16
terasize: 1.07374182399999998e-03
A: 5.69999999999999951e-01
B: 1.90000000000000002e-01
C: 1.90000000000000002e-01
D: 5.00000000000000444e-02
generation_time: 6.34352993159999983e+01
construction_time: 1.84824221289999997e+01
nbfs: 64
min_time: 1.26711638600000009e+00
firstquartile_time: 1.28170626124999987e+00
median_time: 1.29556774550000009e+00
thirdquartile_time: 1.30279463799999995e+00
max_time: 1.32492480199999996e+00
mean_time: 1.29269551996874998e+00
stddev_time: 1.22496657638316471e-02
min_nedge: 6.71081140000000000e+07
firstquartile_nedge: 6.71081140000000000e+07
median_nedge: 6.71081140000000000e+07
thirdquartile_nedge: 6.71081140000000000e+07
max_nedge: 6.71081140000000000e+07
mean_nedge: 6.71081140000000000e+07
stddev_nedge: 0.00000000000000000e+00
min_TEPS: 5.06505077863279358e+07
firstquartile_TEPS: 5.15510459883208126e+07
median_TEPS: 5.18986533771460280e+07
thirdquartile_TEPS: 5.23646361713726446e+07
max_TEPS: 5.29612865412033200e+07
harmonic_mean_TEPS: 5.19133183053208813e+07


hwt@cxl2:~/benchmarks/graph500-2.1.4$ numactl -C 1 -m 3 ./seq-csr/seq-csr -s 22 -e 16
SCALE: 22
nvtx: 4194304
edgefactor: 16
terasize: 1.07374182399999998e-03
A: 5.69999999999999951e-01
B: 1.90000000000000002e-01
C: 1.90000000000000002e-01
D: 5.00000000000000444e-02
generation_time: 6.37574010840000014e+01
construction_time: 3.59123285579999987e+01
nbfs: 64
min_time: 4.56066146399999983e+00
firstquartile_time: 4.64856290550000040e+00
median_time: 4.66568061400000023e+00
thirdquartile_time: 4.67864649925000009e+00
max_time: 4.70924871700000036e+00
mean_time: 4.65851558087500006e+00
stddev_time: 2.98371376899848294e-02
min_nedge: 6.71081140000000000e+07
firstquartile_nedge: 6.71081140000000000e+07
median_nedge: 6.71081140000000000e+07
thirdquartile_nedge: 6.71081140000000000e+07
max_nedge: 6.71081140000000000e+07
mean_nedge: 6.71081140000000000e+07
stddev_nedge: 0.00000000000000000e+00
min_TEPS: 1.42502802533544749e+07
firstquartile_TEPS: 1.43467274670072831e+07
median_TEPS: 1.43882382242820561e+07
thirdquartile_TEPS: 1.44486939091460574e+07
max_TEPS: 1.47145572039766740e+07
harmonic_mean_TEPS: 1.44054716217982918e+07
harmonic_stddev_TEPS: 1.16243000772597206e+04


hwt@cxl2:~/benchmarks/graph500-2.1.4$ SCALE: 22
nvtx: 4194304
edgefactor: 16
terasize: 1.07374182399999998e-03
A: 5.69999999999999951e-01
B: 1.90000000000000002e-01
C: 1.90000000000000002e-01
D: 5.00000000000000444e-02
generation_time: 6.69697912459999998e+01
construction_time: 5.69480235580000027e+01
nbfs: 64
min_time: 5.50741942800000039e+00
firstquartile_time: 6.08688236450000009e+00
median_time: 6.26504639600000068e+00
thirdquartile_time: 6.43060441000000083e+00
max_time: 9.41336253799999945e+00
mean_time: 6.34660834271875007e+00
stddev_time: 6.28720455713848381e-01
min_nedge: 6.71081140000000000e+07
firstquartile_nedge: 6.71081140000000000e+07
median_nedge: 6.71081140000000000e+07
thirdquartile_nedge: 6.71081140000000000e+07
max_nedge: 6.71081140000000000e+07
mean_nedge: 6.71081140000000000e+07
stddev_nedge: 0.00000000000000000e+00
min_TEPS: 7.12902682002281211e+06
firstquartile_TEPS: 1.04977697491303831e+07
median_TEPS: 1.07291524964015372e+07
thirdquartile_TEPS: 1.10693676496202219e+07
max_TEPS: 1.21850378162264042e+07
harmonic_mean_TEPS: 1.05738546285104994e+07
harmonic_stddev_TEPS: 1.31971135331137397e+05
```





numactl -C 0 /home/hwt/workspace/pcm-202307/build/bin/pcm-memory 5  >>${BW_TOOL_OUTPUT_FILE} 2>&1



```shell
hwt@cxl2:~/benchmarks/graph500-2.1.4$ numactl -C 1 -m 1 ./seq-csr/seq-csr -s 22 -e 16
SCALE: 22
nvtx: 4194304
edgefactor: 16
terasize: 1.07374182399999998e-03
A: 5.69999999999999951e-01
B: 1.90000000000000002e-01
C: 1.90000000000000002e-01
D: 5.00000000000000444e-02
generation_time: 6.34112000650000027e+01
construction_time: 1.86807617049999983e+01
nbfs: 64
min_time: 1.26494346199999996e+00
firstquartile_time: 1.28964592425000024e+00
median_time: 1.29957932900000017e+00
thirdquartile_time: 1.30907275725000005e+00
max_time: 1.31865137900000007e+00
mean_time: 1.29871958520312503e+00
stddev_time: 1.20287589741643591e-02
min_nedge: 6.71081140000000000e+07
firstquartile_nedge: 6.71081140000000000e+07
median_nedge: 6.71081140000000000e+07
thirdquartile_nedge: 6.71081140000000000e+07
max_nedge: 6.71081140000000000e+07
mean_nedge: 6.71081140000000000e+07
stddev_nedge: 0.00000000000000000e+00
min_TEPS: 5.08914752365340665e+07
firstquartile_TEPS: 5.12777669265033901e+07
median_TEPS: 5.16801447112593353e+07
thirdquartile_TEPS: 5.20624268505719602e+07
max_TEPS: 5.30522636117629111e+07
harmonic_mean_TEPS: 5.16725201995810494e+07
harmonic_stddev_TEPS: 6.02968746232452249e+04
hwt@cxl2:~/benchmarks/graph500-2.1.4$ numactl -C 1 --interleave 1-2 ./seq-csr/seq-csr -s 22 -e 16
SCALE: 22
nvtx: 4194304
edgefactor: 16
terasize: 1.07374182399999998e-03
A: 5.69999999999999951e-01
B: 1.90000000000000002e-01
C: 1.90000000000000002e-01
D: 5.00000000000000444e-02
generation_time: 6.36866251579999982e+01
construction_time: 2.73138528029999996e+01
nbfs: 64
min_time: 3.12872337099999998e+00
firstquartile_time: 3.19289490675000032e+00
median_time: 3.20664849749999981e+00
thirdquartile_time: 3.21632298975000008e+00
max_time: 3.23761602399999981e+00
mean_time: 3.20297676709374990e+00
stddev_time: 2.04407667611308345e-02
min_nedge: 6.71081140000000000e+07
firstquartile_nedge: 6.71081140000000000e+07
median_nedge: 6.71081140000000000e+07
thirdquartile_nedge: 6.71081140000000000e+07
max_nedge: 6.71081140000000000e+07
mean_nedge: 6.71081140000000000e+07
stddev_nedge: 0.00000000000000000e+00
min_TEPS: 2.07276321535774581e+07
firstquartile_TEPS: 2.08780139755666777e+07
median_TEPS: 2.09395880999884792e+07
thirdquartile_TEPS: 2.10357147269309498e+07
max_TEPS: 2.14490404047932699e+07
harmonic_mean_TEPS: 2.09517954327502511e+07
harmonic_stddev_TEPS: 1.68459056751994358e+04
hwt@cxl2:~/benchmarks/graph500-2.1.4$ 
```



cpulimit使用方法

https://www.bandwagonhost.net/10685.html



这次延迟跑的不错，基本没有很大的延迟波动的情况

```shell
hwt@cxl2:~/benchmarks/graph500-2.1.4$ SCALE: 22
nvtx: 4194304
edgefactor: 16
terasize: 1.07374182399999998e-03
A: 5.69999999999999951e-01
B: 1.90000000000000002e-01
C: 1.90000000000000002e-01
D: 5.00000000000000444e-02
generation_time: 6.38459448389999977e+01
construction_time: 3.57987036399999994e+01
nbfs: 64
min_time: 4.69132908000000004e+00
firstquartile_time: 4.75088291999999957e+00
median_time: 4.78238328650000000e+00
thirdquartile_time: 4.80325355624999961e+00
max_time: 1.53281500489999996e+01
mean_time: 5.18860171192187458e+00
stddev_time: 1.89244794128057281e+00
min_nedge: 6.71081140000000000e+07
firstquartile_nedge: 6.71081140000000000e+07
median_nedge: 6.71081140000000000e+07
thirdquartile_nedge: 6.71081140000000000e+07
max_nedge: 6.71081140000000000e+07
mean_nedge: 6.71081140000000000e+07
stddev_nedge: 0.00000000000000000e+00
min_TEPS: 4.37809610327882320e+06
firstquartile_TEPS: 1.39812795581815038e+07
median_TEPS: 1.40449284379302002e+07
thirdquartile_TEPS: 1.41413976739126202e+07
max_TEPS: 1.43047125570649579e+07
harmonic_mean_TEPS: 1.29337570555483885e+07
harmonic_stddev_TEPS: 5.94330517908361857e+05
```





```shell
hwt@cxl2:~/benchmarks/graph500-2.1.4$ numactl -C 1 -m 3 ./seq-csr/seq-csr -s 22 -e 16 
SCALE: 22
nvtx: 4194304
edgefactor: 16
terasize: 1.07374182399999998e-03
A: 5.69999999999999951e-01
B: 1.90000000000000002e-01
C: 1.90000000000000002e-01
D: 5.00000000000000444e-02
generation_time: 6.38538706020000006e+01
construction_time: 3.58194355019999975e+01
nbfs: 64
min_time: 4.65364120000000003e+00
firstquartile_time: 4.73522116150000016e+00
median_time: 4.76210258750000026e+00
thirdquartile_time: 4.79770793199999979e+00
max_time: 4.85425301200000003e+00
mean_time: 4.76279031056250002e+00
stddev_time: 4.24156792682598566e-02
min_nedge: 6.71081140000000000e+07
firstquartile_nedge: 6.71081140000000000e+07
median_nedge: 6.71081140000000000e+07
thirdquartile_nedge: 6.71081140000000000e+07
max_nedge: 6.71081140000000000e+07
mean_nedge: 6.71081140000000000e+07
stddev_nedge: 0.00000000000000000e+00
min_TEPS: 1.38246016089612097e+07
firstquartile_TEPS: 1.39897933369604554e+07
median_TEPS: 1.40976578315888941e+07
thirdquartile_TEPS: 1.41821866867704019e+07
max_TEPS: 1.44205603990268949e+07
harmonic_mean_TEPS: 1.40900836745160688e+07
harmonic_stddev_TEPS: 1.58091406202259877e+04
```

![image-20241007210641991](/Users/hong/Library/Application%20Support/typora-user-images/image-20241007210641991.png)

![image-20241007210713818](/Users/hong/Library/Application%20Support/typora-user-images/image-20241007210713818.png)



![image-20241007210653336](/Users/hong/Library/Application%20Support/typora-user-images/image-20241007210653336.png)

硬件预取能够关闭吗？

https://blog.csdn.net/Longyu_wlz/article/details/124901272

![image-20241008144748194](/Users/hong/Library/Application%20Support/typora-user-images/image-20241008144748194.png)







