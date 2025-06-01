##  Intel MBA  debug记录



```shell
sudo -i

make && make install

modprobe msr

#需要挂载resctrl文件系统
mount -t resctrl resctrl /sys/fs/resctrl
```

https://github.com/intel/intel-cmt-cat/issues/190

When pqos library initializes, it creates libpqos file in /var/lock directory. It looks like permission issue.

Can you check libpqos is present in /var/lock directory? if not, try below command to check permissions are ok.

sudo touch /var/lock/libpqos

pqos库初始化的时候，会在/var/lock目录下创建libpqos文件，需要先把这个删除，然后再在自己的用户权限下重新touch才行（只要运行了pqos就会touch这个文件）

![image-20241006162022017](/Users/hong/Library/Application%20Support/typora-user-images/image-20241006162022017.png)

确实超过8个就不行了，应该是有一个保留的100%COS0

![image-20241006162159912](/Users/hong/Library/Application%20Support/typora-user-images/image-20241006162159912.png)

每一个COS都运行在socket1上。应用的时候如何分配呢？

