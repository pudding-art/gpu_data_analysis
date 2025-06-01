## Stream源码分析

### 场景

由于当前使用stream工具对CXL内存平台进行测试的结果不甚理想，所以需要阅读stream源码来分析当前测试带宽的瓶颈在什么位置：

- CPU为系统瓶颈：测试随进程数增加内存带宽的变化情况；（但是现在的stream MPI 多进程的实现方式是一份数据每个进程测试一部分数据，所以这个应该不会是瓶颈，可以同时监控一下此时CPU的利用率）==4个cores的时候系统带宽最大==；
- ~~编译指令对系统性能测试的影响：主要是Array size的设置，以及一些其他编译优化的指令处理~~；（这里Array Size大于4倍之后就没有变化了）
- ~~Stream版本对性能的影响（当前使用的应该是最新的版本，以及offical version，此项影响较弱）~~

### README

<u>*Update: 2014 10 28(> v5.10)*</u>

1. MPI实现benchmark 如何处理Data Array，新版本数组分布在所有的MPI进程中，每个thread只处理其中一部分数据，旧版本中，所有进程中都要复制一份数据，每个进程处理完整数据；
2. Stream benchmark中使用posix-memalign来分配内存，而不是使用静态数组，用于分配内存并保存内存对齐的函数，可以提高内存访问的效率；
3. Error checking and timing done by all ranks and gathered by ranko for processing and output;
4. Timing uses barries to ensure correct operation even when multiple MPI ranks run on shared memory system;

*<u>Update: 2013 01 17(v5.10)</u>*

1. 更新的验证代码不会因为大数组而积累舍入误差;
2. 在编译时定义预处理变量“VERBOSE”将导致代码打印测量的平均相对绝对误差（而不仅仅打印“Solution Validates”），并打印相对误差超过误差容限的前10个数组条目;
3. **数组索引变量已经从“int”升级为“ssize_t”，以允许在64位系统上有超过20亿个元素的数组;**
4. 在源代码中对如何配置/编译/运行基准测试的**注释**进行了重大改进;
5. **控制数组大小的预处理变量已从“N”更改为“STREAM_ARRAY_SIZE”**;
6. **新的预处理变量“STREAM_TYPE”可用于将数据类型从默认的“double”更改为“float”**;
7. 某些输出方面进行了小的更改，包括以GiB为单位打印数组大小，以及更改默认输出格式以打印较少小数位数的带宽和较多小数位数的最小/最大/平均执行时间;



### 代码架构

stream.c 主要测试代码

mysecond.c 计时

stream需要根据底层运行的不同系统配置来调节测试内存大小的需求，主要取决于LLC size(S)和system timer的粒度。STREAM_ARRAY_SIZE的设置需要同时满足以下的要求：

- 至少是LLC size的4倍；`LLC size x 1024x1024xCPU路数/data type`

- 大多数Windows版本具有10毫秒的计时器粒度。在10毫秒/滴答下，20个“ticks”为200毫秒。如果芯片能够以10 GB/s的速度传输数据，在200毫秒内可传输2 GB。这意味着每个数组至少应该是1 GB，或者128M个元素。

  > 计时精度应该就是当前的主机频率对应的时钟周期。也就是一次测试应该至少有20个ticks，才能保证time计算出来的时间是准确的。
  >
  > ![image-20240318200413921](/Users/hong/Library/Application%20Support/typora-user-images/image-20240318200413921.png)

STREAM_TYPE是每个元素的类型 ；默认为double；

```c
//定义stream中定义的3个数组
static STREAM_TYPE	a[STREAM_ARRAY_SIZE+OFFSET],
			b[STREAM_ARRAY_SIZE+OFFSET],
			c[STREAM_ARRAY_SIZE+OFFSET];

//默认的bytes数组
static double	bytes[4] = {
    2 * sizeof(STREAM_TYPE) * STREAM_ARRAY_SIZE,//copy, 2个数组
    2 * sizeof(STREAM_TYPE) * STREAM_ARRAY_SIZE,//scale，2
    3 * sizeof(STREAM_TYPE) * STREAM_ARRAY_SIZE,//add，3
    3 * sizeof(STREAM_TYPE) * STREAM_ARRAY_SIZE//triad，3
    };
```

> 关于size_t和ssize_t的区别：
> size_t反映内存中对象的大小（字节为单位），ssize_t供返回字节计数或错误提示的函数使用。size_t的大小取决于体系结构，有的是unsigned int，有的是unsigned long；
>
> ```c
> //不同体系结构的内核源码
> asm-i386/posix_types.h
> 	typedef unsigned int __kernel_size_t;
> asm-ia64/posix_types.h
> 	typedef unsigned long __kernel_size_t;	
> ```
>
> size_t主要是为了增强程序的可移植性，不同的系统上size_t的定义可能你不一样。size_t一般用于表示一种计数，比如有多少东西被拷贝等，意义大致是“适用于计量内存中可容纳的数据项目个数的无符号整数类型”。eg：sizeof操作符的类型是size_t，该类型保证能容纳实现所建立的最大对象的字节大小。故其在数组下标和内存管理函数之类的地方广泛使用。
>
> ssize_t也表示可以被执行读写操作的数据块的大小，与size_t类似，但必须是signed
> https://blog.csdn.net/weibo1230123/article/details/81530367

下面分析stream.c的main函数内容：

```c
		int			quantum, checktick();
    int			BytesPerWord; // 每个word包含多少个byte？
    int			k;
    ssize_t		j; //执行读写操作的数据块的大小
    STREAM_TYPE		scalar; //放大系数
    double		t, times[4][NTIMES];

    /* --- SETUP --- determine precision and check timing --- */

    printf(HLINE);
    printf("STREAM version $Revision: 5.10 $\n");
    printf(HLINE);
    BytesPerWord = sizeof(STREAM_TYPE); //sizeo返回的变量就是size_t, 赋值给signed的size_t，sizeof就是计算当前一个类型中有几个byte，64bit/8=8byte
    printf("This system uses %d bytes per array element.\n",
	BytesPerWord); //输出结果中可以看出来这个选项

    printf(HLINE);
```

![image-20240318194300014](/Users/hong/Library/Application%20Support/typora-user-images/image-20240318194300014.png)

```c
//tuned_STREAM_Triad(scalar)和直接定义的Triad操作有什么区别？
times[3][k] = mysecond();
#ifdef TUNED
        tuned_STREAM_Triad(scalar);
#else
#pragma omp parallel for
	for (j=0; j<STREAM_ARRAY_SIZE; j++) //Triad操作
	    a[j] = b[j]+scalar*c[j];
#endif
	times[3][k] = mysecond() - times[3][k];

//tuned_STREAM_Triad(scalar)定义
void tuned_STREAM_Triad(STREAM_TYPE scalar)
{
	ssize_t j;
#pragma omp parallel for
	for (j=0; j<STREAM_ARRAY_SIZE; j++)
	    a[j] = b[j]+scalar*c[j];
}
```

> [!IMPORTANT]
>
> 加#pragma omp parallel for本质区在于并行化的方式和精细度。但是上面的普通方法也定义了，除了代码的组织结构和可读性有区别，在并行化效果上并没有本质区别。查看是否有编译上的区别。

```bash
gcc -O3 -c -S # 将代码编译成汇编语言(assembly), 然后查看生成的汇编文件
objdump -d # 查看编译后的机器代码
gcc -fverbose-asm # 输出汇编代码时包含更多注释信息

# 示例
gcc -O3 -c -S example.c # 生成汇编文件
gcc -o3 -o example example.c # 编译并链接生成可执行文件
```

- [ ] 修改编译指令，查看输出的结果中有哪些编译优化，是否会对最终的结果产生影响？加上omp_parallel_for 再使用gcc -O3是否也有区别？
- [x] 尝试将step进行改动，测试结果是否有变动，主要是考虑到如果cacheline=64byte，每次从内存读入1个cacheline，那也就是8次loads只有1次访问内存，但是如果每次都load都访存呢？也就是改成i=i+8？那就需要至少是LLC的8倍内存大小，DSTREAM_ARRAY_SIZE=1G完全可以，然后直接修改i=i+8即可；但是这样和循环展开有什么区别？（已改完代码，需要做实验）
- [ ] 

```c
//每种操作都改成如下形式
#elif STEPPING
#pragma omp parallel for
	int i;
	for (i = 0; i < 8; i++){//增加了这个，每次访问完了整个数组之后再回来，之前读入的cacheline早就不在了
	 	for (j=i; j<STREAM_ARRAY_SIZE; j=j+8) //如果这样改，中间的1-7个数就不会被赋值，这和循环展开有什么区别
	 	c[j] = a[j];
	}
#else
```

```shell
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=13 --membind=0 ./stream512M8.o | grep -E "Copy|Scale|Add|Triad"
Copy:            1320.3     6.205533     6.204488     6.207774
Scale:           1246.1     6.575983     6.574321     6.579100
Add:             1565.1     7.853853     7.851306     7.856772
Triad:           1472.0     8.348496     8.347941     8.350048
```



### 编译指令

```bash
 gcc -mtune=native -march=native -O3 -mcmodel=medium -fopenmp -DSTREAM_ARRAY_SIZE=2000000000 -DNTIMES=10  stream.c -o stream2G.o

# -O3: 指定最高编译优化，3
# -DSTREAM_ARRAY_SIZE 必须设置数组大小远大于LLC的到校，否则测试的是CPU缓存的吞吐性能，而非内存吞吐性能
#  数组大小应该足够大，以便程序输出的“timing calibration”至少为20个时钟滴答。举例来说：
#  大多数Windows版本具有10毫秒的计时器粒度。在10毫秒/滴答下，20个“ticks”为200毫秒。如果芯片能够以10 #  GB/s的速度传输数据，在200毫秒内可传输2 GB。这意味着每个数组至少应该是1 GB，或者128M个元素。
# -fopenmp: 启用OpenMP，适应多处理器环境，更能得到内存带宽实际最大值。开启后，程序默认运行线程为CPU线程数；
# -mtune=native -march=native 针对CPU指令的优化，此处由于编译机即运行机器，故使用native的优化方法，更多编译器对CPU的优化参考
# -mcmodel=medium 当单个Memory Array Size大于2GB时需要设置此参数
# -DOFFSET 数组的偏移，一般可以不定义
```

![image-20240316224141454](/Users/hong/Library/Application%20Support/typora-user-images/image-20240316224141454.png)

Swap空间已经满了，但是CPU利用率没有达到100%，难道是Swap空间对系统带宽有影响？

![image-20240316224300528](/Users/hong/Library/Application%20Support/typora-user-images/image-20240316224300528.png)

![image-20240316224824519](/Users/hong/Library/Application%20Support/typora-user-images/image-20240316224824519.png)

```bash
cpu is 0, memory is 0
Copy: 13823.9 0.592944 0.592598 0.593557 Scale: 7341.5 1.116311 1.115843 1.116574 Add: 9048.8 1.358647 1.357974 1.359128 Triad: 9086.3 1.352968 1.352366 1.353543
cpu is 0, memory is 0
Copy: 13726.9 1.166075 1.165594 1.166729 Scale: 7365.6 2.172933 2.172271 2.173435 Add: 9029.1 2.658729 2.658077 2.659256 Triad: 9090.0 2.641036 2.640277 2.641396
cpu is 0, memory is 0

cpu is 0, memory is 0

cpu is 0, memory is 0

cpu is 0, memory is 1
Copy: 10706.5 0.765451 0.765144 0.766095 
Scale: 5245.7 1.561973 1.561649 1.562558 
Add: 6533.8 1.881243 1.880677 1.882001 
Triad: 6528.1 1.882821 1.882319 1.883245
cpu is 0, memory is 1
Copy: 10723.4 1.492496 1.492061 1.493090 Scale: 5248.4 3.049302 3.048569 3.049873 Add: 6527.8 3.677577 3.676578 3.678120 Triad: 6546.3 3.667095 3.666205 3.667595
cpu is 0, memory is 1

cpu is 0, memory is 1

cpu is 0, memory is 1

cpu is 0, memory is 2
Copy: 6811.7 1.203270 1.202632 1.203589 Scale: 1767.9 4.755177 4.633822 4.854797 Add: 2321.2 5.392459 5.293823 5.467492 Triad: 2340.1 5.324578 5.250958 5.361626
cpu is 0, memory is 2

cpu is 0, memory is 2

cpu is 0, memory is 2

cpu is 0, memory is 2

cpu is 1, memory is 0
Copy: 10851.6 0.755081 0.754913 0.755338 Scale: 5360.9 1.528574 1.528104 1.529111 Add: 6707.5 1.832790 1.831980 1.833223 Triad: 6589.0 1.865499 1.864929 1.866059
cpu is 1, memory is 0
Copy: 10611.1 1.508257 1.507852 1.508686 Scale: 5336.5 2.998875 2.998220 2.999406 Add: 6679.9 3.594529 3.592889 3.595796 Triad: 6689.8 3.588210 3.587532 3.588943
cpu is 1, memory is 0

cpu is 1, memory is 0

cpu is 1, memory is 0

cpu is 1, memory is 1
Copy: 13815.7 0.593261 0.592950 0.593766 Scale: 7380.6 1.110552 1.109935 1.112121 Add: 8988.9 1.367530 1.367013 1.368090 Triad: 8973.0 1.369825 1.369439 1.370380
cpu is 1, memory is 1
Copy: 13578.0 1.178871 1.178376 1.179299 Scale: 7335.2 2.182222 2.181261 2.183148 Add: 8980.0 2.674291 2.672605 2.675137 Triad: 8926.9 2.689275 2.688516 2.689970
cpu is 1, memory is 1

cpu is 1, memory is 1

cpu is 1, memory is 1

cpu is 1, memory is 2
Copy: 7933.7 1.032750 1.032555 1.033095 Scale: 2753.3 2.976049 2.975286 2.976596 Add: 3123.7 3.935378 3.933741 3.936794 Triad: 3102.3 3.962327 3.960881 3.963225
cpu is 1, memory is 2

cpu is 1, memory is 2

cpu is 1, memory is 2

cpu is 1, memory is 2
```

以上输出结果表明，1GB以上就无法进行了。

![image-20240316225737422](/Users/hong/Library/Application%20Support/typora-user-images/image-20240316225737422.png)

```bash
cpu is 0, memory is 0
Copy: 13937.0 0.588193 0.587786 0.588798 Scale: 7451.7 1.099918 1.099341 1.100352 Add: 8996.8 1.366398 1.365819 1.366886 Triad: 8952.4 1.373118 1.372590 1.374024
cpu is 0, memory is 0
Copy: 13783.9 1.161084 1.160774 1.161723 Scale: 7493.6 2.135448 2.135152 2.135851 Add: 8681.1 2.765514 2.764620 2.765967 Triad: 8628.3 2.782144 2.781551 2.782726
cpu is 0, memory is 0

cpu is 0, memory is 0

cpu is 0, memory is 0

cpu is 0, memory is 1
Copy: 10838.8 0.756080 0.755802 0.756436 Scale: 5238.1 1.564351 1.563920 1.564659 Add: 6587.0 1.865882 1.865491 1.866578 Triad: 6624.2 1.855970 1.855003 1.856942
cpu is 0, memory is 1
Copy: 10702.5 1.495429 1.494982 1.495952 Scale: 5209.2 3.071879 3.071518 3.072188 Add: 6534.7 3.673628 3.672704 3.674366 Triad: 6502.6 3.692164 3.690822 3.692928
cpu is 0, memory is 1

cpu is 0, memory is 1

cpu is 0, memory is 1

cpu is 0, memory is 2
Copy: 6820.0 1.201554 1.201179 1.202030 Scale: 1849.6 4.494818 4.429128 4.576687 Add: 2407.0 5.170144 5.105212 5.257432 Triad: 2312.1 5.383842 5.314704 5.453402
cpu is 0, memory is 2

cpu is 0, memory is 2

cpu is 0, memory is 2

cpu is 0, memory is 2

cpu is 1, memory is 0
Copy: 10699.0 0.765952 0.765679 0.766273 Scale: 5361.8 1.528175 1.527849 1.528475 Add: 6699.0 1.834996 1.834316 1.835371 Triad: 6596.5 1.863362 1.862795 1.863737
cpu is 1, memory is 0
Copy: 10657.6 1.501848 1.501279 1.502428 Scale: 5371.8 2.979178 2.978505 2.979642 Add: 6709.2 3.577802 3.577204 3.579167 Triad: 6651.9 3.609386 3.607983 3.610455
cpu is 1, memory is 0

cpu is 1, memory is 0

cpu is 1, memory is 0

cpu is 1, memory is 1
Copy: 13706.8 0.597792 0.597658 0.597910 Scale: 7287.9 1.124479 1.124048 1.125066 Add: 8913.9 1.379238 1.378518 1.379980 Triad: 8846.7 1.389627 1.388993 1.390172
cpu is 1, memory is 1
Copy: 13612.6 1.175798 1.175378 1.176218 Scale: 7282.6 2.197625 2.197013 2.198195 Add: 8996.1 2.668133 2.667813 2.668974 Triad: 8999.3 2.667444 2.666866 2.668331
cpu is 1, memory is 1

cpu is 1, memory is 1

cpu is 1, memory is 1

cpu is 1, memory is 2
Copy: 7967.8 1.028574 1.028144 1.028948 Scale: 2730.7 3.000491 2.999983 3.001157 Add: 3186.3 3.857390 3.856488 3.858330 Triad: 2964.2 4.146516 4.145495 4.147244
cpu is 1, memory is 2

cpu is 1, memory is 2

cpu is 1, memory is 2

cpu is 1, memory is 2
```

![image-20240316235113513](/Users/hong/Library/Application%20Support/typora-user-images/image-20240316235113513.png)

即使把OMP_NUM_THREADS删掉也不行，再尝试一下将前面所有和OpenMP相关的指令都去掉:

```bash
cpu is 1, memory is 0
Copy: 13822.6 0.593204 0.592652 0.593716 Scale: 7205.3 1.137445 1.136944 1.138060 Add: 8873.0 1.385443 1.384873 1.386063 Triad: 9096.2 1.351891 1.350894 1.353465
cpu is 1, memory is 0
Copy: 13674.4 1.170464 1.170066 1.171242 Scale: 7529.9 2.125414 2.124864 2.126046 Add: 9150.9 2.623326 2.622700 2.623828 Triad: 9090.2 2.640694 2.640198 2.641109
cpu is 1, memory is 0

cpu is 1, memory is 0

cpu is 1, memory is 0

cpu is 1, memory is 1
Copy: 10745.0 0.762753 0.762399 0.763532 Scale: 5013.3 1.634769 1.634040 1.635256 Add: 6382.6 1.926147 1.925239 1.926576 Triad: 6544.8 1.878353 1.877521 1.879313
cpu is 1, memory is 1
Copy: 10763.9 1.487082 1.486449 1.487985 Scale: 5335.9 2.999229 2.998539 3.000017 Add: 6637.8 3.616593 3.615633 3.617164 Triad: 6586.7 3.644378 3.643706 3.645489
cpu is 1, memory is 1

cpu is 1, memory is 1

cpu is 1, memory is 1

cpu is 1, memory is 2
Copy: 6909.2 1.186233 1.185667 1.186616 Scale: 1808.8 4.609643 4.528952 4.674268 Add: 2395.7 5.235386 5.129254 5.313141 Triad: 2392.6 5.233230 5.135769 5.330863
cpu is 1, memory is 2

cpu is 1, memory is 2

cpu is 1, memory is 2

cpu is 1, memory is 2

cpu is 12, memory is 0
Copy: 10814.6 0.757903 0.757494 0.758253 Scale: 4740.3 1.728639 1.728144 1.729474 Add: 6191.8 1.985390 1.984570 1.985864 Triad: 6692.9 1.836663 1.835981 1.837069
cpu is 12, memory is 0
Copy: 10639.2 1.504189 1.503878 1.504703 Scale: 5134.2 3.117177 3.116327 3.118061 Add: 6414.9 3.742773 3.741282 3.746511 Triad: 6561.4 3.662834 3.657782 3.663922
cpu is 12, memory is 0

cpu is 12, memory is 0

cpu is 12, memory is 0

cpu is 12, memory is 1
Copy: 13969.5 0.586685 0.586421 0.587278 Scale: 7339.9 1.116680 1.116086 1.117641 Add: 8908.5 1.379899 1.379352 1.380525 Triad: 8853.2 1.388788 1.387966 1.390460
cpu is 12, memory is 1
Copy: 13601.4 1.176810 1.176350 1.177412 Scale: 7336.1 2.181609 2.180995 2.182134 Add: 9030.8 2.658579 2.657559 2.659337 Triad: 8869.0 2.707164 2.706067 2.707985
cpu is 12, memory is 1

cpu is 12, memory is 1

cpu is 12, memory is 1

cpu is 12, memory is 2
Copy: 7875.7 1.040603 1.040162 1.040980 Scale: 2706.5 3.027647 3.026761 3.028456 Add: 3350.6 3.668379 3.667442 3.669081 Triad: 3290.7 3.735677 3.734186 3.737181
cpu is 12, memory is 2

cpu is 12, memory is 2

cpu is 12, memory is 2

cpu is 12, memory is 2

```

再尝试不使用Openmp进行编译（结果并没有明显差异）：

```bash
cpu is 1, memory is 0
Copy: 13808.8 0.593627 0.593244 0.593880 Scale: 7489.5 1.094339 1.093802 1.095091 Add: 9196.7 1.336468 1.336126 1.336965 Triad: 9160.1 1.342380 1.341476 1.343062
cpu is 1, memory is 0
Copy: 13604.0 1.176340 1.176125 1.176926 Scale: 7433.1 2.152915 2.152526 2.153274 Add: 9075.0 2.646753 2.644634 2.648627 Triad: 8890.6 2.703677 2.699492 2.706856
cpu is 1, memory is 0

cpu is 1, memory is 0

cpu is 1, memory is 0

cpu is 1, memory is 1
Copy: 10798.2 0.759030 0.758647 0.759675 Scale: 5350.2 1.531616 1.531168 1.532442 Add: 6617.4 1.857410 1.856916 1.858329 Triad: 6529.7 1.882413 1.881864 1.883069
cpu is 1, memory is 1
Copy: 10694.2 1.496969 1.496134 1.497665 Scale: 5330.3 3.002124 3.001685 3.002826 Add: 6557.7 3.661703 3.659793 3.663240 Triad: 6549.8 3.666059 3.664255 3.668710
cpu is 1, memory is 1

cpu is 1, memory is 1

cpu is 1, memory is 1

cpu is 1, memory is 2
Copy: 6848.8 1.196495 1.196123 1.196926 Scale: 1837.7 4.588035 4.457855 4.683171 Add: 2371.2 5.320368 5.182190 5.390001 Triad: 2272.5 5.457669 5.407377 5.515552
cpu is 1, memory is 2

cpu is 1, memory is 2

cpu is 1, memory is 2

cpu is 1, memory is 2

cpu is 12, memory is 0
Copy: 10853.0 0.755171 0.754816 0.755917 Scale: 5304.4 1.544871 1.544372 1.545316 Add: 6548.3 1.877241 1.876514 1.878036 Triad: 6575.1 1.869727 1.868864 1.870627
cpu is 12, memory is 0
Copy: 10618.9 1.507530 1.506743 1.508418 Scale: 5285.4 3.027789 3.027191 3.028592 Add: 6601.5 3.637524 3.635544 3.640115 Triad: 6634.9 3.618810 3.617234 3.620897
cpu is 12, memory is 0

cpu is 12, memory is 0

cpu is 12, memory is 0

cpu is 12, memory is 1
Copy: 13848.6 0.591768 0.591541 0.591952 Scale: 7337.6 1.117231 1.116438 1.118419 Add: 9002.3 1.365883 1.364981 1.366634 Triad: 8994.3 1.366644 1.366192 1.367463
cpu is 12, memory is 1
Copy: 13799.0 1.159957 1.159500 1.160481 Scale: 7333.6 2.182394 2.181731 2.182877 Add: 9011.4 2.664036 2.663307 2.665370 Triad: 8958.3 2.681188 2.679080 2.682152
cpu is 12, memory is 1

cpu is 12, memory is 1

cpu is 12, memory is 1

cpu is 12, memory is 2
Copy: 7844.6 1.044656 1.044285 1.045142 Scale: 2741.6 2.988539 2.988000 2.989507 Add: 3272.7 3.755420 3.754658 3.756352 Triad: 3271.9 3.756529 3.755643 3.757807
cpu is 12, memory is 2

cpu is 12, memory is 2

cpu is 12, memory is 2

cpu is 12, memory is 2
```













```bash
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ 
Triad"
Copy:           13848.9     0.591946     0.591527     0.592435
Scale:           7450.7     1.100193     1.099496     1.101343
Add:             9064.3     1.356013     1.355646     1.356852
Triad:           9038.6     1.359932     1.359504     1.360527
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0,1 --membind=0 ./stream512M.o | grep -E "
Copy|Scale|Add|Triad"
Copy:           21044.5     0.389438     0.389271     0.389920
Scale:          12346.1     0.663723     0.663528     0.663994
Add:            15097.8     0.814347     0.813894     0.814890
Triad:          15061.8     0.816291     0.815838     0.816936
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0-2 --membind=0 ./stream512M.o | grep -E "
Copy|Scale|Add|Triad"
Copy:           23263.7     0.352318     0.352136     0.352596
Scale:          14750.8     0.555683     0.555359     0.556182
Add:            17902.2     0.686651     0.686397     0.687424
Triad:          17872.8     0.687994     0.687524     0.688521
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0-3 --membind=0 ./stream512M.o | grep -E "
Copy|Scale|Add|Triad"
Copy:           23925.6     0.342655     0.342395     0.343279
Scale:          16283.9     0.503524     0.503075     0.504046
Add:            19447.2     0.632275     0.631865     0.633016
Triad:          19450.2     0.632220     0.631766     0.633092
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0-4 --membind=0 ./stream512M.o | grep -E "
Copy|Scale|Add|Triad"
Copy:           23880.8     0.343275     0.343037     0.343809
Scale:          17250.3     0.475084     0.474890     0.475233
Add:            19954.0     0.616167     0.615818     0.616869
Triad:          19934.0     0.616574     0.616433     0.616771
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0-5 --membind=0 ./stream512M.o | grep -E "
Copy|Scale|Add|Triad"
Copy:           23867.4     0.343415     0.343230     0.343600
Scale:          17352.9     0.472463     0.472083     0.472757
Add:            19888.1     0.618306     0.617856     0.619231
Triad:          19917.2     0.617431     0.616954     0.617888
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0-6 --membind=0 ./stream512M.o | grep -E "Copy|Scale
|Add|Triad"
Copy:           23858.3     0.343613     0.343361     0.343874
Scale:          17497.2     0.468507     0.468190     0.468752
Add:            19906.2     0.618219     0.617295     0.621173
Triad:          19945.0     0.617064     0.616094     0.620041
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0-7 --membind=0 ./stream512M.o | grep -E "Copy|Scale
|Add|Triad"
Copy:           23921.5     0.342655     0.342453     0.342983
Scale:          17813.7     0.460106     0.459872     0.460449
Add:            19999.7     0.614682     0.614409     0.615143
Triad:          20032.8     0.613559     0.613394     0.614145
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0-8 --membind=0 ./stream512M.o | grep -E "Copy|Scale
|Add|Triad"
Copy:           23928.4     0.342461     0.342355     0.342568
Scale:          17684.3     0.463422     0.463235     0.463609
Add:            19964.2     0.615651     0.615503     0.615949
Triad:          20003.4     0.614467     0.614296     0.614675
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0-9 --membind=0 ./stream512M.o | grep -E "Copy|Scale
|Add|Triad"
Copy:           24012.6     0.341387     0.341154     0.341631
Scale:          17813.9     0.460023     0.459866     0.460188
Add:            19984.7     0.615211     0.614870     0.615486
Triad:          20020.6     0.613961     0.613769     0.614287
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0-10 --membind=0 ./stream512M.o | grep -E "Copy|Scal
e|Add|Triad"
Copy:           23957.7     0.342109     0.341936     0.342227
Scale:          17734.7     0.462138     0.461919     0.462292
Add:            20874.0     0.590116     0.588676     0.591714
Triad:          20909.7     0.589133     0.587671     0.590400
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0-11 --membind=0 ./stream512M.o | grep -E "Copy|Scal
e|Add|Triad"
Copy:           23963.0     0.342120     0.341860     0.342521
Scale:          17799.3     0.460771     0.460242     0.461527
Add:            25944.0     0.474130     0.473636     0.474593
Triad:          25998.3     0.473385     0.472647     0.474113
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12 --membind=0 ./stream512M.o | grep -E "Copy|Scale|
Add|Triad"
Copy:           10834.7     0.758256     0.756086     0.763123
Scale:           5390.6     1.524687     1.519677     1.526790
Add:             6700.0     1.839004     1.834038     1.847217
Triad:           6449.0     1.912682     1.905399     1.928441
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-13 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           15206.6     0.539410     0.538712     0.539862
Scale:           9184.8     0.895389     0.891905     0.896113
Add:            11352.1     1.085029     1.082440     1.085762
Triad:          11255.1     1.092118     1.091771     1.092308
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-14 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14969.9     0.547608     0.547232     0.549064
Scale:          10866.4     0.754233     0.753885     0.755190
Add:            13353.9     0.920578     0.920184     0.920978
Triad:          13362.3     0.919792     0.919603     0.919999
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-15 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14929.2     0.549007     0.548725     0.549364
Scale:          12116.8     0.676359     0.676085     0.676881
Add:            14740.9     0.834011     0.833597     0.834510
Triad:          14693.3     0.836794     0.836301     0.837180
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-16 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14908.1     0.549781     0.549500     0.550329
Scale:          12402.9     0.660761     0.660492     0.661119
Add:            14927.5     0.823514     0.823178     0.823850
Triad:          14965.7     0.821466     0.821076     0.822091
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-17 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14871.0     0.551224     0.550869     0.551607
Scale:          12148.8     0.674501     0.674306     0.674797
Add:            14839.2     0.828343     0.828076     0.828844
Triad:          14855.1     0.827421     0.827193     0.827705
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-18 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14873.3     0.551205     0.550786     0.551684
Scale:          12128.7     0.675713     0.675420     0.676246
Add:            14868.2     0.826683     0.826464     0.827053
Triad:          14884.2     0.825927     0.825575     0.826475
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-19 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14900.2     0.550058     0.549792     0.550433
Scale:          12236.6     0.669958     0.669467     0.670468
Add:            14928.1     0.823460     0.823143     0.824015
Triad:          14940.1     0.822780     0.822482     0.823230
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-20 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14891.7     0.550348     0.550105     0.550798
Scale:          12140.7     0.675038     0.674757     0.675628
Add:            14890.0     0.825548     0.825250     0.826010
Triad:          14921.2     0.823789     0.823525     0.824348
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-21 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14921.6     0.551216     0.549003     0.554509
Scale:          12096.6     0.683500     0.677213     0.696134
Add:            14901.0     0.832407     0.824641     0.844326
Triad:          14895.8     0.833854     0.824929     0.864093
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-22 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14965.5     0.548149     0.547392     0.549470
Scale:          12148.0     0.676689     0.674352     0.683749
Add:            14884.6     0.827173     0.825549     0.831359
Triad:          14893.5     0.828231     0.825060     0.833872
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-23 --membind=0 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           15005.0     0.546356     0.545952     0.546920
Scale:          12160.1     0.673960     0.673678     0.674526
Add:            14874.7     0.826802     0.826102     0.827405
Triad:          14897.8     0.825299     0.824819     0.826016
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12 --membind=2 ./stream512M.o | grep -E "Co
py|Scale|Add|Triad"
Copy:            7832.0     1.046283     1.045970     1.046887
Scale:           2664.5     3.075078     3.074500     3.075740
Add:             2841.6     4.325534     4.324302     4.326423
Triad:           2842.7     4.323717     4.322592     4.325177
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-13 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           13268.7     0.618318     0.617395     0.619503
Scale:           4968.3     1.651309     1.648853     1.654539
Add:             5843.6     2.105061     2.102817     2.106879
Triad:           5815.9     2.114210     2.112824     2.115401
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-14 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14862.0     0.552642     0.551204     0.554609
Scale:           6760.0     1.212538     1.211826     1.212937
Add:             7880.2     1.560424     1.559351     1.561932
Triad:           7936.8     1.548752     1.548228     1.550773
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-15 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14561.8     0.565711     0.562569     0.570454
Scale:           8109.2     1.012114     1.010207     1.014015
Add:             9354.0     1.314824     1.313668     1.317049
Triad:           9307.6     1.321060     1.320214     1.322212
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-16 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14426.5     0.572397     0.567845     0.574981
Scale:           8850.6     0.927713     0.925592     0.929706
Add:             9988.5     1.231038     1.230220     1.232646
Triad:          10044.1     1.224995     1.223410     1.227218
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-17 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           14067.7     0.585318     0.582326     0.588045
Scale:           8893.2     0.921470     0.921150     0.922413
Add:             9953.7     1.237146     1.234515     1.238789
Triad:           9960.8     1.235751     1.233632     1.237690
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-18 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           13690.5     0.602127     0.598370     0.604781
Scale:           8942.9     0.916980     0.916033     0.917598
Add:            10191.0     1.208306     1.205775     1.209739
Triad:          10195.4     1.207046     1.205244     1.209094
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-19 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           13509.4     0.615153     0.606391     0.632091
Scale:           9142.0     0.897738     0.896085     0.899086
Add:            10479.7     1.173948     1.172553     1.175644
Triad:          10503.1     1.172092     1.169937     1.173892
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-20 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           13373.4     0.617175     0.612559     0.626176
Scale:           9081.5     0.903191     0.902057     0.904293
Add:            10496.0     1.172586     1.170727     1.175367
Triad:          10489.5     1.172456     1.171459     1.173490
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-21 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           13311.6     0.619157     0.615403     0.629611
Scale:           9115.9     0.900163     0.898648     0.901333
Add:            10496.8     1.172588     1.170642     1.175083
Triad:          10508.4     1.170885     1.169348     1.172118
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-22 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           13170.4     0.626239     0.622003     0.632857
Scale:           9118.8     0.899302     0.898366     0.900529
Add:            10517.2     1.169431     1.168373     1.170895
Triad:          10538.4     1.167278     1.166022     1.168278
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-23 --membind=2 ./stream512M.o | grep -E 
"Copy|Scale|Add|Triad"
Copy:           13069.8     0.629287     0.626789     0.632767
Scale:           9164.6     0.894510     0.893875     0.895139
Add:            10535.3     1.167477     1.166360     1.168379
Triad:          10575.9     1.162992     1.161887     1.163694
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0 --membind=2 ./stream512M.o | grep -E "Cop
y|Scale|Add|Triad"

hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=0,1 --membind=2 ./stream5
12M.o | grep -E "Copy|Scale|Add|Triad"
Copy:           11015.7     0.744684     0.743666     0.745636
Scale:           3036.1     2.806890     2.698199     2.890037
Add:             3870.8     3.246647     3.174565     3.312050
Triad:           3753.2     3.344043     3.273999     3.437813
```

## Stream2结果



```shell
# 单核
hwt@cxl-2288H-V7:~/stream2$ numactl --physcpubind=13 --membind=0 ./stream2
 Smallest time delta is    9.5367431640625000E-007
     Size  Iter     FILL      COPY     DAXPY       DOT
       30     3  18593.9   97475.5   71127.6   64087.7      73.9
       48     3  27791.2  133334.4   76731.5   70670.0      69.0
       77     3  40832.1  158960.8  109068.3   97812.9      63.2
      123     3  42181.9  215578.3  111343.5  100146.1      40.9
      197     3  43040.0  263381.7  112801.8  102819.3      26.0
      315     3  33250.9  207115.5   94238.6  102166.0      12.6
      504     3  38476.4  281176.0  101318.6  102809.3       9.1
      806     3  40783.8  318403.3  106917.4  104190.5       6.0
     1290     3  42705.9  333328.1  108690.3  100737.2       3.9
     2063     3  43111.6  343039.9  111998.9  102336.5       2.5
     3302     3  43685.8  124044.7   98189.2   86295.5       1.6
     5283     3  44061.5   73741.5   83471.9   64126.2       1.0
     8454     3  44404.0   74937.6   83455.9   64201.4       0.6
    13528     3  44415.9   76208.6   83204.4   64284.3       0.4
    21647     3  44448.8   76823.4   83337.2   64301.7       0.2
    34639     3  44576.4   77502.9   83545.3   64263.5       0.2
    55428     3  44609.0   77344.6   83622.1   64197.2       0.1
    88694     3  44656.6   77559.1   83601.8   64245.0       0.1
   141925     3  44654.1   44278.6   61120.8   44677.4       0.0
   227102     3  34960.0   37079.1   40435.4   28805.1       0.0
   363400     3  26563.5   30425.6   39248.4   27837.5       0.0
   581498     3  24638.7   28887.7   39006.9   27773.1       0.0
   930489     3  24523.2   28601.2   38693.2   27628.7       0.0
  1488931     3  24250.0   28158.7   35174.8   25107.0       0.0
  2382526     3  21678.5   28023.2   24152.3   18386.3       0.0
  3812421     3  13144.9   27690.6   17189.8   16063.4       0.0
  6100481     3   8074.0   22152.9   14911.0   14336.6       0.0
  9761740     3   6880.0   19958.3   14665.5   13897.6       0.0
 15620338     3   6616.9   18329.4   14700.6   13580.5       0.0
 24995027     3   6850.2   16620.5   14756.1   13092.0       0.0
 39996021     3   7357.3   14239.2   14688.4   12164.9       0.0
 64000000     3   7466.6   14384.3   14644.1   12165.6       0.0
hwt@cxl-2288H-V7:~/stream2$ numactl --physcpubind=13 --membind=1 ./stream2
 Smallest time delta is    9.5367431640625000E-007
     Size  Iter     FILL      COPY     DAXPY       DOT
       30     3  22614.8  100302.8   73686.9   64736.9      89.9
       48     3  27265.8  133177.2   76665.7   69892.5      67.7
       77     3  29240.1  113338.5   78099.7   69143.1      45.3
      123     3  30319.3  152813.1   79454.0   70781.7      29.4
      197     3  30717.4  186965.3   80490.4   73320.5      18.6
      315     3  23940.9  146936.5   66724.3   73033.5       9.1
      504     3  27004.2  199607.9   72517.4   74176.4       6.4
      806     3  29115.5  227197.5   76455.1   74282.5       4.3
     1290     3  30094.7  237696.2   78290.9   71890.1       2.8
     2063     3  30759.3  244679.5   79860.8   73115.2       1.8
     3302     3  31173.7   89050.9   69551.9   61958.8       1.1
     5283     3  31437.4   52622.0   59533.3   45743.9       0.7
     8454     3  37969.0   74850.1   83198.3   64168.8       0.5
    13528     3  39768.5   76181.5   83290.5   64296.8       0.4
    21647     3  44332.2   76811.0   83350.1   64297.9       0.2
    34639     3  44348.0   77501.5   83526.9   64238.5       0.2
    55428     3  39073.6   77350.1   83549.4   64208.7       0.1
    88694     3  42497.7   76516.5   82603.0   63464.1       0.1
   141925     3  44622.5   48902.3   65833.0   48305.9       0.0
   227102     3  34708.4   37276.9   39844.3   28311.3       0.0
   363400     3  26540.1   30947.3   39277.3   27817.8       0.0
   581498     3  24624.6   29608.9   39090.2   27744.5       0.0
   930489     3  24522.1   29572.1   38934.5   27759.6       0.0
  1488931     3  24296.1   29493.3   37001.9   26316.8       0.0
  2382526     3  23400.0   29568.4   29033.6   21885.5       0.0
  3812421     3  17120.0   28619.5   23021.2   18795.6       0.0
  6100481     3  11173.5   23567.7   20715.3   17178.1       0.0
  9761740     3   9262.1   21814.9   20108.8   16784.2       0.0
 15620338     3   8746.5   20821.5   20035.4   16718.8       0.0
 24995027     3   8660.8   20433.3   19988.0   16653.6       0.0
 39996021     3   8642.0   20156.7   20008.4   16586.8       0.0
 64000000     3   8533.1   20334.4   19844.5   16610.9       0.0
hwt@cxl-2288H-V7:~/stream2$ numactl --physcpubind=13 --membind=2 ./stream2
 Smallest time delta is    9.5367431640625000E-007
     Size  Iter     FILL      COPY     DAXPY       DOT
       30     3  25546.1   96605.1   72378.1   63362.5     101.5
       48     3  27660.6  132010.6   76662.1   69660.2      68.7
       77     3  29157.1  113335.5   78088.3   70421.9      45.1
      123     3  30242.0  152813.1   79338.5   71056.9      29.3
      197     3  31019.1  186591.6   80482.3   72996.5      18.8
      315     3  23738.7  147547.3   66831.6   73389.2       9.0
      504     3  28159.6  200549.3   72384.6   73791.5       6.7
      806     3  29110.8  227245.6   75168.8   74127.4       4.3
     1290     3  30293.8  237748.8   77720.4   72505.4       2.8
     2063     3  30699.9  244805.0   79218.5   73125.1       1.8
     3302     3  31181.4   89384.5   69833.1   61974.0       1.1
     5283     3  31419.9   52519.7   59480.0   45764.4       0.7
     8454     3  31591.6   53442.6   59462.7   45844.9       0.4
    13528     3  31663.4   54382.2   59438.1   45912.2       0.3
    21647     3  31697.1   54837.3   59510.5   45947.9       0.2
    34639     3  31770.8   55323.0   59616.6   45872.8       0.1
    55428     3  31850.4   55233.7   59693.3   45848.3       0.1
    88694     3  31853.1   55357.8   59718.1   45859.7       0.0
   141925     3  31849.5   31243.8   43792.7   32384.5       0.0
   227102     3  26441.0   32160.1   30052.0   21553.9       0.0
   363400     3  19929.3   27966.1   29242.5   20954.5       0.0
   581498     3  24633.6   28496.9   38293.8   27762.5       0.0
   930489     3  24506.8   28362.4   36884.1   27132.6       0.0
  1488931     3  23637.3   27862.9   24212.6   17744.5       0.0
  2382526     3  18902.5   27027.5   14398.5   10890.9       0.0
  3812421     3   8566.5   24559.1   10644.7    8073.4       0.0
  6100481     3   4759.4   16300.9    9065.5    6911.6       0.0
  9761740     3   4171.4   13281.5    8441.5    6447.3       0.0
 15620338     3   3845.6   11848.3    8032.5    6158.4       0.0
 24995027     3   3730.1   10922.5    7752.2    5861.7       0.0
 39996021     3   3674.6   10590.1    7664.9    5817.3       0.0
 64000000     3   3647.2   10494.9    7574.7    5843.1       0.0
 
# 4cores
hwt@cxl-2288H-V7:~/stream2$ numactl --physcpubind=13-16 --membind=1 ./stream2
 Smallest time delta is    9.5367431640625000E-007
     Size  Iter     FILL      COPY     DAXPY       DOT
       30     3  19753.1   99757.7   69030.9   64675.4      78.5
       48     3  27639.9  133247.5   76734.2   70572.4      68.6
       77     3  29157.1  113323.6   78116.7   68984.3      45.1
      123     3  30112.2  152401.0   79429.5   70363.1      29.2
      197     3  30708.2  186965.3   80367.9   72851.6      18.6
      315     3  26479.0  147658.9   66744.4   73152.9      10.0
      504     3  27414.8  200783.6   74714.9   73738.3       6.5
      806     3  28926.5  227353.9   76303.9   73944.9       4.3
     1290     3  30046.7  237696.2   78138.9   71834.8       2.8
     2063     3  30757.5  244679.5   79889.5   73079.1       1.8
     3302     3  31177.3   89688.7   69849.0   61977.6       1.1
     5283     3  31524.2   52540.9   59577.3   45733.7       0.7
     8454     3  31525.3   53447.9   59467.1   45796.0       0.4
    13528     3  31635.9   54420.1   59440.3   45867.1       0.3
    21647     3  31457.5   54776.4   59485.2   45894.4       0.2
    34639     3  31672.4   55246.1   59611.6   45839.9       0.1
    55428     3  31823.0   55200.4   59679.5   45835.6       0.1
    88694     3  44601.9   77448.6   83574.7   64197.0       0.1
   141925     3  44606.7   48019.6   64775.7   47746.3       0.0
   227102     3  37183.7   38857.5   39794.7   28218.2       0.0
   363400     3  26855.0   31156.5   39293.6   27826.8       0.0
   581498     3  24629.1   29579.9   39116.1   27761.0       0.0
   930489     3  24512.5   29538.5   38938.3   27762.9       0.0
  1488931     3  24260.7   29479.4   36854.8   26333.3       0.0
  2382526     3  20392.8   28850.5   29669.9   22004.6       0.0
  3812421     3  15716.8   27233.2   23201.9   18855.9       0.0
  6100481     3  11104.6   23801.0   20766.1   17232.4       0.0
  9761740     3   9241.4   21825.7   20141.8   16794.7       0.0
 15620338     3   8749.8   20806.3   20028.0   16706.3       0.0
 24995027     3   8658.6   20420.2   19967.4   16650.8       0.0
 39996021     3   8629.4   20147.2   19956.0   16594.6       0.0
 64000000     3   8521.1   20318.6   19854.2   16620.1       0.0
hwt@cxl-2288H-V7:~/stream2$ numactl --physcpubind=13-16 --membind=0 ./stream2
 Smallest time delta is    9.5367431640625000E-007
     Size  Iter     FILL      COPY     DAXPY       DOT
       30     3  17726.0   98669.1   73321.3   64606.4      70.4
       48     3  28139.7  133437.9   76604.6   70084.1      69.9
       77     3  29453.9  113677.5   78068.5   69883.4      45.6
      123     3  30235.2  153222.0   79478.5   71488.6      29.3
      197     3  31011.5  187063.0   80288.7   72856.5      18.8
      315     3  24186.3  147446.0   66953.8   73022.3       9.2
      504     3  27427.7  200539.9   71802.1   73567.8       6.5
      806     3  29085.9  227197.5   75157.4   74289.0       4.3
     1290     3  30015.2  237696.2   77803.0   71718.5       2.8
     2063     3  30748.3  244735.3   78933.2   73041.8       1.8
     3302     3  31145.2   88980.8   69960.5   61984.8       1.1
     5283     3  31442.9   52600.1   59583.9   45753.7       0.7
     8454     3  30799.1   53435.9   59518.2   45781.4       0.4
    13528     3  29146.3   54370.5   59401.4   45867.1       0.3
    21647     3  31654.1   54828.9   59491.8   45894.4       0.2
    34639     3  31715.9   55288.1   59586.2   45858.5       0.1
    55428     3  31840.5   55218.8   59654.0   45837.5       0.1
    88694     3  31850.7   55300.7   59616.3   45798.0       0.0
   141925     3  31835.3   29650.2   41808.6   30991.0       0.0
   227102     3  35881.5   37626.0   40997.2   29308.6       0.0
   363400     3  26800.0   30643.3   39162.2   27811.9       0.0
   581498     3  24648.0   28945.0   38892.1   27754.2       0.0
   930489     3  24512.7   28655.7   38579.3   27690.7       0.0
  1488931     3  24241.9   28283.6   35191.3   25227.7       0.0
  2382526     3  21466.0   28848.7   23519.2   18247.2       0.0
  3812421     3  12383.3   27539.0   17075.1   16001.3       0.0
  6100481     3   8340.8   22889.6   15362.9   14526.0       0.0
  9761740     3   7033.4   20001.1   14918.1   13851.3       0.0
 15620338     3   6656.2   18335.0   14883.3   13582.0       0.0
 24995027     3   6865.2   16670.7   14836.7   13047.1       0.0
 39996021     3   7547.7   14422.4   14842.9   12248.3       0.0
 64000000     3   7490.0   14531.2   14772.6   12278.3       0.0
hwt@cxl-2288H-V7:~/stream2$ numactl --physcpubind=13-16 --membind=2 ./stream2
 Smallest time delta is    9.5367431640625000E-007
     Size  Iter     FILL      COPY     DAXPY       DOT
       30     3  25519.7   96004.8   70146.3   64647.2     101.4
       48     3  27623.2  132519.8   76581.9   71329.6      68.6
       77     3  29127.5  113779.9   77996.6   69451.7      45.1
      123     3  30117.7  152558.0   79474.6   70855.3      29.2
      197     3  30709.9  187479.4   80465.2   72691.3      18.6
      315     3  23570.4  147506.8   66530.7   87761.4       8.9
      504     3  38395.2  281084.0  101007.3  102977.0       9.1
      806     3  40741.2  318497.7  106963.5  103928.3       6.0
     1290     3  42042.9  333328.1  108719.6  100708.9       3.9
     2063     3  42951.2  342356.2  111093.1  102468.4       2.5
     3302     3  43670.7  124105.7   98321.0   86911.9       1.6
     5283     3  44034.4   73582.3   83530.3   64114.7       1.0
     8454     3  44292.2   74872.3   83342.5   64202.3       0.6
    13528     3  44339.7   76192.3   83353.0   64317.0       0.4
    21647     3  44088.3   76725.9   83382.5   64321.9       0.2
    34639     3  44394.8   77479.1   83477.1   64251.0       0.2
    55428     3  44566.4   77320.9   83617.8   64228.9       0.1
    88694     3  44594.5   71182.2   80001.7   60874.1       0.1
   141925     3  44568.7   44798.8   62051.1   45840.0       0.0
   227102     3  35982.8   39683.1   41924.3   30310.0       0.0
   363400     3  26942.6   34762.3   39580.4   28583.1       0.0
   581498     3  25174.2   33497.0   38863.7   28512.1       0.0
   930489     3  25006.7   33601.3   35107.0   26231.3       0.0
  1488931     3  23573.8   33924.5   19245.7   14580.3       0.0
  2382526     3  13130.3   30742.1   11197.3    8415.4       0.0
  3812421     3   4593.1   17572.9    8588.0    6443.4       0.0
  6100481     3   4821.2   16636.4    9159.0    7066.7       0.0
  9761740     3   4286.5   13623.0    8548.4    6573.1       0.0
 15620338     3   3990.3   12201.4    8150.2    6265.7       0.0
 24995027     3   3801.0   11147.0    7852.2    5967.3       0.0
 39996021     3   3715.8   10746.9    7752.8    5903.7       0.0
 64000000     3   3680.4   10655.6    7654.1    5926.8       0.0
```

```shell
# 4 cores stream
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$  OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-15 --membind=2 ./stream512M.o | grep -E "Copy|Scale|Add|Triad"
Copy:           15127.2     0.544591     0.541542     0.546384
Scale:           9575.1     0.857413     0.855553     0.859365
Add:            11328.3     1.086562     1.084718     1.088739
Triad:          11240.6     1.093910     1.093178     1.095049
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$  OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-15 --membind=0 ./stream512M.o | grep -E "Copy|Scale|Add|Triad"
Copy:           14861.6     0.553833     0.551219     0.563560
Scale:          11910.4     0.694481     0.687803     0.735053
Add:            14865.8     0.832946     0.826596     0.854962
Triad:          14869.5     0.836505     0.826387     0.849534
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=12-15 --membind=1 ./stream512M.o | grep -E "Copy|Scale|Add|Triad"
Copy:           24904.5     0.329465     0.328936     0.331616
Scale:          17890.1     0.458872     0.457908     0.463391
Add:            20123.8     0.616096     0.610620     0.645757
Triad:          20146.9     0.610423     0.609920     0.611356
```



## Memo

![image-20240322121036892](/Users/hong/Library/Application%20Support/typora-user-images/image-20240322121036892.png)

```bash
sudo turbostat #查看处理器的实时性能信息

#https://rootw.github.io/2018/01/%E6%97%B6%E9%97%B4%E5%AD%90%E7%B3%BB%E7%BB%9F%E6%A6%82%E8%BF%B0/
./test_single_op_latency.sh
[INFO] Test started
[TEST] op: 0 node: 0......
[RESULT] Median latency among 10000 iterations: 311.0ns (assume 2.000000GHz)
311.0
[TEST] op: 1 node: 0......
[RESULT] Median latency among 10000 iterations: 311.0ns (assume 2.000000GHz)
311.0
[TEST] op: 2 node: 0......
[RESULT] Median latency among 10000 iterations: 631.0ns (assume 2.000000GHz)
631.0
[TEST] op: 3 node: 0......
[RESULT] Median latency among 10000 iterations: 364.0ns (assume 2.000000GHz)
364.0


[TEST] op: 0 node: 1......
[RESULT] Median latency among 10000 iterations: 255.0ns (assume 2.000000GHz)
255.0
[TEST] op: 1 node: 1......
[RESULT] Median latency among 10000 iterations: 253.0ns (assume 2.000000GHz)
253.0
[TEST] op: 2 node: 1......
[RESULT] Median latency among 10000 iterations: 447.0ns (assume 2.000000GHz)
447.0
[TEST] op: 3 node: 1......
[RESULT] Median latency among 10000 iterations: 223.0ns (assume 2.000000GHz)
223.0



[TEST] op: 0 node: 2......
[RESULT] Median latency among 10000 iterations: 514.0ns (assume 2.000000GHz)
514.0
[TEST] op: 1 node: 2......
[RESULT] Median latency among 10000 iterations: 512.0ns (assume 2.000000GHz)
512.0
[TEST] op: 2 node: 2......
[RESULT] Median latency among 10000 iterations: 930.0ns (assume 2.000000GHz)
930.0
[TEST] op: 3 node: 2......
[RESULT] Median latency among 10000 iterations: 360.0ns (assume 2.000000GHz)
360.0
```



### Stream修改后的测试结果

```bash
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=13-16 --membind=1 ./stream5128.o | grep -E "Copy|Scale|Add|Triad"
Copy:           24516.0     0.334238     0.334149     0.334358
Scale:          17904.3     0.457768     0.457544     0.458225
Add:            20125.8     0.610713     0.610560     0.610867
Triad:          20128.1     0.610640     0.610490     0.610962
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=13-16 --membind=0 ./stream5128.o | grep -E "Copy|Scale|Add|Triad"
Copy:           14928.5     0.551178     0.548749     0.552615
Scale:          11919.7     0.688084     0.687264     0.689625
Add:            14880.5     0.826841     0.825777     0.828070
Triad:          14902.1     0.826125     0.824584     0.827423
hwt@cxl-2288H-V7:~/cc_test/stream/STREAM$ OMP_PLACES=cores OMP_PROC_BIND=spread numactl --physcpubind=13-16 --membind=2 ./stream5128.o | grep -E "Copy|Scale|Add|Triad"
Copy:           13985.3     0.587947     0.585758     0.590183
Scale:           9242.6     0.887741     0.886331     0.888486
Add:            10685.3     1.177906     1.149989     1.394354
Triad:          10889.0     1.171138     1.128474     1.508008
# CXL的没有跑满大概差1GB/s左右，但是DDR内存已经跑满了
```

不应该再加一个for循环了，每个for循环之间可能有比较大的延迟产生；

## Lmbench结果



```bash
hwt@cxl-2288H-V7:~/cc_test/lmbench/bin/x86_64-linux-gnu$ numactl -c 1 -m 1 ./lat_mem_rd -t -P 1 -N 10 1024M 64
"stride=64
0.00049 2.386
0.00098 2.386
0.00195 2.386
0.00293 2.386
0.00391 2.386
0.00586 2.386
0.00781 2.386
0.00977 2.386
0.01172 2.386
0.01367 2.386
0.01562 2.386
0.01758 2.386
0.01953 2.386
0.02148 2.386
0.02344 2.386
0.02539 2.386
0.02734 2.386
0.02930 2.386
0.03125 2.386
0.03516 2.386
0.03906 2.387
0.04297 2.388
0.04688 2.388
0.05078 7.635                   
0.05859 7.634
0.06250 7.635
0.07031 7.635
0.07812 7.635
0.08594 7.635
0.09375 7.635
0.10156 7.635
0.10938 7.635
0.11719 7.635
0.12500 8.199
0.14062 7.634
0.15625 7.634
0.17188 7.635
0.18750 7.635
0.20312 7.634
0.21875 8.171
0.23438 8.470
0.25000 8.105
0.28125 8.318
0.31250 9.284
0.34375 9.189
0.37500 9.284
0.40625 9.184
0.43750 9.602
0.46875 10.030
0.50000 10.031
0.56250 10.649
0.62500 10.719
0.68750 10.860
0.75000 10.784
0.81250 10.911
0.87500 10.976
0.93750 10.964
1.00000 10.988
1.12500 10.975
1.25000 13.792
1.37500 11.382
1.50000 15.084
1.62500 13.679
1.75000 16.811
1.87500 16.786
2.00000 20.752
2.25000 23.799
2.50000 27.378
2.75000 32.391
3.00000 34.964
3.25000 35.749
3.50000 38.439
3.75000 38.091
4.00000 39.361
4.50000 39.095
5.00000 41.359
5.50000 40.932
6.00000 43.484
6.50000 43.165
7.00000 45.357
7.50000 45.064
8.00000 47.715
9.00000 48.847
10.00000 51.632
11.00000 51.599
12.00000 53.108
13.00000 50.861
14.00000 53.340
15.00000 52.707
16.00000 53.615
18.00000 53.112
20.00000 54.927
22.00000 55.464
24.00000 57.665
26.00000 59.219
28.00000 62.536
30.00000 64.374
32.00000 68.575
36.00000 74.953
40.00000 80.908
44.00000 87.067
48.00000 91.508
52.00000 96.591
56.00000 105.050
60.00000 107.626
64.00000 108.140
72.00000 114.929
80.00000 122.476
88.00000 126.182
96.00000 132.336
104.00000 133.216
112.00000 138.342
120.00000 137.559
128.00000 141.670
144.00000 141.105
160.00000 145.701
176.00000 144.274
192.00000 148.197
208.00000 146.265
224.00000 149.509
240.00000 147.303
256.00000 150.165
288.00000 148.116
320.00000 150.916
352.00000 148.268
384.00000 150.974
416.00000 148.264
448.00000 150.787
480.00000 148.315
512.00000 151.265
576.00000 148.117
640.00000 150.405
704.00000 147.699
768.00000 150.277
832.00000 147.692
896.00000 150.690
960.00000 151.507
1024.00000 150.339

hwt@cxl-2288H-V7:~/cc_test/lmbench/bin/x86_64-linux-gnu$ numactl -c 1 -m 2 ./lat_mem_rd -t -P 1 -N 10 1024M 64
"stride=64
0.00049 2.386
0.00098 2.386
0.00195 2.386
0.00293 2.386
0.00391 2.386
0.00586 2.386
0.00781 2.386
0.00977 2.386
0.01172 2.385
0.01367 2.386
0.01562 2.386
0.01758 2.386
0.01953 2.386
0.02148 2.386
0.02344 2.386
0.02539 2.386
0.02734 2.386
0.02930 2.386
0.03125 2.386
0.03516 2.386
0.03906 2.468
0.04297 2.387
0.04688 2.388
0.05078 7.634
0.05469 7.634
0.05859 7.633
0.06250 7.634
0.07031 7.635
0.07812 7.635
0.08594 7.635
0.09375 7.635
0.10156 7.635
0.10938 7.635
0.11719 7.635
0.12500 7.635
0.14062 7.635
0.15625 7.635
0.17188 7.635
0.18750 8.077
0.20312 7.634
0.21875 8.522
0.23438 8.136
0.25000 8.307
0.28125 8.291
0.31250 8.583
0.34375 9.182
0.37500 8.978
0.40625 9.662
0.43750 10.232
0.46875 10.078
0.50000 9.879
0.56250 10.732
0.62500 10.704
0.68750 10.902
0.75000 10.905
0.81250 10.975
0.87500 10.976
0.93750 10.975
1.00000 10.975
1.12500 10.976
1.25000 10.974
1.37500 11.026
1.50000 11.382
1.62500 16.055
1.75000 12.778
1.87500 17.403
2.00000 17.452
2.25000 23.055
2.50000 27.421
2.75000 31.299
3.00000 34.226
3.25000 36.692
3.50000 36.410
3.75000 37.999
4.00000 37.158
4.50000 38.946
5.00000 38.447
5.50000 40.364
6.00000 40.146
6.50000 42.507
7.00000 43.256
7.50000 45.559
8.00000 45.059
9.00000 47.698
10.00000 49.054
11.00000 51.207
12.00000 50.233
13.00000 52.129
14.00000 50.801
15.00000 52.487
16.00000 51.815
18.00000 54.108
20.00000 55.240
22.00000 59.891
24.00000 62.412
26.00000 71.360
28.00000 85.496
30.00000 102.448
32.00000 118.920
36.00000 152.148
40.00000 175.365
44.00000 201.468
48.00000 219.727
52.00000 238.136
56.00000 250.061
60.00000 264.725
64.00000 273.610
72.00000 291.035
80.00000 303.586
88.00000 313.518
96.00000 325.039
104.00000 328.425
112.00000 336.955
120.00000 341.876
128.00000 345.928
144.00000 355.555
160.00000 359.168
176.00000 365.237
192.00000 368.941
208.00000 374.529
224.00000 379.736
240.00000 378.420
256.00000 384.831
288.00000 384.729
320.00000 388.200
352.00000 386.995
384.00000 391.370
416.00000 389.940
448.00000 393.366
480.00000 390.879
512.00000 392.488
576.00000 392.221
640.00000 394.746
704.00000 394.440
768.00000 396.348
832.00000 394.390
896.00000 397.136
960.00000 395.263
1024.00000 396.710

hwt@cxl-2288H-V7:~/cc_test/lmbench/bin/x86_64-linux-gnu$ numactl -c 1 -m 0 ./lat_mem_rd -t -P 1 -N 10 1024M 64
"stride=64
0.00049 2.386
0.00098 2.386
0.00195 2.386
0.00293 2.386
0.00391 2.386
0.00586 2.386
0.00781 2.386
0.00977 2.386
0.01172 2.386
0.01367 2.386
0.01562 2.386
0.01758 2.386
0.01953 2.386
0.02148 2.386
0.02344 2.386
0.02539 2.386
0.02734 2.386
0.02930 2.386
0.03125 2.386
0.03516 2.386
0.03906 2.387
0.04297 2.387
0.04688 2.388
0.05078 7.635
0.05469 7.635
0.05859 7.634
0.06250 7.634
0.07031 7.634
0.07812 7.633
0.08594 7.635
0.09375 7.635
0.10156 7.634
0.10938 7.635
0.11719 7.634
0.12500 7.635
0.14062 7.635
0.15625 7.635
0.17188 7.635
0.18750 8.452
0.20312 8.212
0.21875 7.635
0.23438 8.424
0.25000 8.054
0.28125 8.266
0.31250 9.163
0.34375 8.934
0.37500 9.767
0.40625 9.869
0.43750 9.946
0.46875 9.834
0.50000 10.081
0.56250 10.581
0.62500 10.640
0.68750 10.855
0.75000 10.936
0.81250 10.885
0.87500 10.980
0.93750 11.927
1.00000 11.697
1.12500 11.651
1.25000 14.476
1.37500 15.185
1.50000 14.065
1.62500 18.260
1.75000 18.721
1.87500 22.906
2.00000 23.175
2.25000 27.448
2.50000 28.298
2.75000 31.038
3.00000 30.357
3.25000 32.623
3.50000 31.783
3.75000 35.616
4.00000 34.085
4.50000 36.972
5.00000 36.711
5.50000 40.507
6.00000 39.380
6.50000 42.776
7.00000 41.353
7.50000 45.137
8.00000 44.070
9.00000 48.583
10.00000 48.621
11.00000 51.290
12.00000 51.142
13.00000 52.686
14.00000 51.244
15.00000 54.213
16.00000 52.814
18.00000 58.218
20.00000 60.677
22.00000 66.801
24.00000 68.695
26.00000 74.391
28.00000 75.433
30.00000 82.247
32.00000 83.986
36.00000 94.722
40.00000 100.314
44.00000 112.351
48.00000 117.998
52.00000 131.054
56.00000 134.852
60.00000 145.278
64.00000 147.561
72.00000 161.912
80.00000 165.955
88.00000 177.053
96.00000 178.835
104.00000 187.451
112.00000 186.638
120.00000 193.682
128.00000 191.169
144.00000 200.299
160.00000 197.205
176.00000 204.054
192.00000 200.572
208.00000 206.599
224.00000 202.235
240.00000 207.985
256.00000 203.371
288.00000 208.919
320.00000 204.580
352.00000 209.277
384.00000 206.463
416.00000 210.341
448.00000 206.718
480.00000 210.473
512.00000 205.881
576.00000 210.339
640.00000 205.395
704.00000 209.398
768.00000 205.009
832.00000 210.885
896.00000 204.909
960.00000 209.464
1024.00000 205.067

hwt@cxl-2288H-V7:~/cc_test/lmbench/bin/x86_64-linux-gnu$ 
```

