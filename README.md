# CacheBrowser

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
