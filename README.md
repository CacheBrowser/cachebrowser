# CacheBrowser

The current CacheBrowser software is a research prototype implementation, and is not yet ready for end-users. If you are a researcher or developer check it out and give us feedback, otherwise please be patient while we work on an end-user version of the code. 
Thanks for you understanding and support! 

https://cachebrowser.info

## Installation
```
python setup.py install
```

## Running CacheBrowser
To run the CacheBrowser process simply enter the `cachebrowser` command
```
cachebrowser
```

## Using CacheBrowser
Once  running you use CacheBrowser by setting the HTTP proxy on your browser to `localhost:8080`

You could also run a command with CacheBrowser:
```
cachebrowser <command>
```



These are the valid commands you could give:

Command                                                                     | Description 
--------------------------------------------------------------------------- | ---
bootstrap <host>                                                            | Bootstrap <host>
get `url` `[target]`                                                        | Retrieve `url` using CacheBrowser. If `target` is specified CacheBrowser uses the given target. If not, CacheBrowser uses the bootstrapped target if the host has been bootstrapped or makes a normal request to the host if not.
list hosts                                                                  | Lists the bootstrapped hosts
list cdn                                                                    | Lists the CDNs used for the bootstrapped hosts


### Example
```
cachebrowser bootstrap www.nbc.com
cachebrowser get http://www.nbc.com

cachebrowser get https://www.istockphoto.com 69.31.76.91
```

