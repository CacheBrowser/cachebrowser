# CacheBrowser

CacheBrowser is currently unstable and under active development.

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

You can then use CacheBrowser by setting the HTTP proxy on your browser to `localhost:8080`

## Bootstrapping
In order to be able to browse a page using CacheBrowser, the page must first be bootstrapped.
What this means is that CacheBrowser must first find out what CDN the page is hosted on and also obtain some edge server addresses for that CDN. 

In the long run we plan on providing a remote Bootstrapping Server which CacheBrowser contacts to gain bootstrapping information. For now though, bootstrapping can be done using local bootstrapping files provided to CacheBrowser.

A local bootstrapping file is a YAML file containing a list of Host or CDN information.

For example:
```
- type: cdn
  id: akamai
  name: Akamai
  edge_servers:
    - 23.208.91.198
    - 23.218.210.7

- type: host
  name: www.nbc.com
  ssl: false
  cdn: akamai

- type: host
  name: www.bloomberg.com
  ssl: false
  cdn: akamai
```

For each **CDN** provided in the bootstrapping file the following information should be provided:

Key                        | Value 
---------------------------| ---
type                       | cdn
id                         | A unique ID to be used for the CDN
name                       | The CDN Name
edge_servers               | List of edge server addresses for the CDN

For each **Host** provided in the bootstrapping file the following information should be provided:

Key                        | Value 
---------------------------| ---
type                       | host
name                       | The hostname
cdn                        | The ID of the CDN which provides this host
ssl                        | Whether the pages supports HTTPS connections or not



CacheBrowser uses the local bootstrapping file [here](data/local_bootstrap.yaml) by default. To provide more bootstrapping files to CacheBrowser, run it with the -b option.

```
cachebrowser -b /path/to/localbootstrap.yaml
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

