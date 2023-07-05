Utility library including common classes, methods, and functions commonly used across
projects.

Currently available for python as a full namespace install or as individual submodules.

Submodules include Database and Configure.
Database offers a base class for high throughput interfacing with postgresql 
databases, a mapped class that allows for interfacing with a database table as if it were a python dictionary, and 
the optional [crypto] module extends the base class enabling automated encrypting and decrypting
of specified fields within a database.
Configure is a simple ini file parser. 