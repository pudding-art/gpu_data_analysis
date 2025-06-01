## 步骤二：LMbench测试延迟

`Lmbench` 是一款简易可以移植的内存测试工具，其主要功能有，带宽测评（读取缓存文件、拷贝内存、读/写内存、管道、TCP），延时测评（上下文切换、网络、文件系统的建立和删除、进程创建、信号处理、上层系统调用、内存读入反应时间）等功能。

执行单个测试用例：进入`/bin`目录下执行对应用例即可

- 这里主要关心延迟测试`lat_mem_rd`
- `lat_mem_rd`
  - 参数说明
    - `-P`：指定并行度，默认为1
    - `-t`：指定为随机访问，否则为顺序访问
    - `-N`：指定重复测试次数，默认为10次
    - `size`：访问的最大数据块，单位MB
    - `stride`：访问步长，单位Byte，默认64B
  - 示例：`./lat_mem_rd -P 2 -t -N 3 128 256`，表示并行度2，随机访问，重复测试3次，最大访问到128MB数据，步长为256（注意stride可以写多个，会依次进行测试，例如`./lat_mem_rd 128 64 256 1024`，会依次测试步长为64B、256B、1024B）

#### 执行如下指令进行测试

```shell
# loca dram
numactl -c 1 -m 1 ./lat_mem_rd -t -P 1 -N 10 1024M 64 
# remote NUMA
numactl -c 1 -m 0 ./lat_mem_rd -t -P 1 -N 10 1024M 64
# CXL memory
numactl -c 1 -m 2 ./lat_mem_rd -t -P 1 -N 10 1024M 64
```

#### 编译过程中可能出现的问题解决

![image-20240703114954312](/Users/hong/Library/Application%20Support/typora-user-images/image-20240703114954312.png)

成功，make results即可



#### 参考：

性能测试工具lmbench的使用方法以及解析运行结果

https://blog.csdn.net/qq_36393978/article/details/125989992

lmbench fatal error: rpc/rpc.h: No such file or directory

https://blog.csdn.net/qq_38963393/article/details/131715454

fix compilation error 'fatal error: rpc/rpc.h: No such file or directory' #16

https://github.com/intel/lmbench/issues/16

lmbench内存延迟测试代码分析https://developer.aliyun.com/article/591720



