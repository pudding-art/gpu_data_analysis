## CXLMemSim

https://github.com/SlugLab/CXLMemSim







## gem5-CXL

https://github.com/zxhero/gem5-CXL?tab=readme-ov-file









![image-20240708103211760](/Users/hong/Library/Application%20Support/typora-user-images/image-20240708103211760.png)

出现perf_event_open error的问题，可以通过perf stat查看当前perf的状态, 如下所示为成功。

![image-20240708103718460](/Users/hong/Library/Application%20Support/typora-user-images/image-20240708103718460.png)









`ls -l /sys/devices/system/cpu/cpu0/cache/index`
index0/ index1/ index2/
index0和Index1是一级cache中的data和instruction cache

```
ls -l /sys/devices/system/cpu/cpu0/cache/index0/
```

https://www.cnblogs.com/gnivor/p/15214927.html

