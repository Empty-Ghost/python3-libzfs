py-libzfs
======

**Python bindings for libzfs**

py-libzfs is a fairly straight-forward set of Python bindings for libzfs for ZFS on Linux and FreeBSD.


**INSTALLATION**

`./configure && make install`

After updating the bindings or OpenZFS development headers, rerun configure
and rebuild so the API checks and generated C code are refreshed:

```sh
./configure --prefix=/usr &&
make clean &&
make &&
sudo make install
```

Install the OpenZFS development headers matching the target's installed
libraries (for example, 2.4.4-1). Configure detects the installed API rather
than relying on the package version. This includes the OpenZFS 2.4 const
pointer changes, three-argument `zpool_add`, and five-argument userspace
callback. The Python userspace results retain their existing `domain`,
`rid`, and `space` fields.

Compiler-based compatibility probe tests can run without OpenZFS or a pool:

```sh
python3 -m unittest discover -s tests -v
```

These tests check legacy and 2.4-style declarations; they do not replace
building and testing the extension against the target's actual libraries.

**FEATURES:**
- Access to pools, datasets, snapshots, properties, pool disks
- Many others!

**QUICK HOWTO:**

`import libzfs`

Get a list of pools:

`pools = list(libzfs.ZFS().pools)`

Get help:

`help(libzfs)`


