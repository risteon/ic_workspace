# ic_workspace
Quick ic_workspace + icmaker template.

## 30 seconds to ic_workspace
Requirements
* gitpython

```
$ git clone https://github.com/risteon/ic_workspace
$ cd ic_workspace && git submodule update --init

$ ./ic_dependencies --add icl_empty
$ mkdir build && cd build
$ cmake .. && make
$ ctest
```

