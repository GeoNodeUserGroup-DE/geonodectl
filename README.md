# geonodectl

**geonodectl** is a commandline interface tool for [geonode](https://github.com/GeoNode/geonode). It uses the [geonode apiv2](https://docs.geonode.org/en/master/devel/api/V2/index.html) to interact with a geonode installation.

## How to use

geonodectl has currently the following capabilities:
```
usage: geonodectl [-h] [--not-verify-ssl] [--raw] [--page-size PAGE_SIZE]
                  {resources,resource,dataset,ds,documents,doc,document,maps,geoapps,apps,people,users,user,uploads,executionrequest}
                  ...

geonodectl is a cmd client for the geonodev4 rest-apiv2.
To use this tool you have to set the following environment variables before starting:
  
GEONODE_API_URL: https://geonode.example.com/api/v2/ -- path to the v2 endpoint of your target geonode instance
GEONODE_API_BASIC_AUTH: YWRtaW46YWRtaW4= -- you can generate this string like: echo -n user:password | base64

positional arguments:
  {resources,resource,dataset,ds,documents,doc,document,maps,geoapps,apps,people,users,user,uploads,executionrequest}
                        geonodectl commands
    resources (resource)
                        resource commands
    dataset (ds)        dataset commands
    documents (doc,document)
                        document commands
    maps                maps commands
    geoapps (apps)      geoapps commands
    people (users,user)
                        people|users commands
    uploads             uploads commands
    executionrequest    executionrequest commands

options:
  -h, --help            show this help message and exit
  --not-verify-ssl      allow to request domains with unsecure ssl certificates ...
  --raw, --json         return output as raw response json as it comes from the rest API
  --page-size PAGE_SIZE
                        return output as raw response json as it comes from the rest API

```

Currently not all features of the API are implemented. Here is a list of what you can do with geonodectl:
| geonode resource | capabilities |
|------------------|--------------|
| resource         | list, delete, download metadata |
| dataset          | list, delete, patch, describe, upload |
| documents        | list, delete, patch, describe, upload |
| maps             | list, delete, patch, describe |
| geoapps          | list, delete, patch, describe |
| people           | list, delete, patch, describe |
| uploads          | list |
| executionrequest | list |

This project is WIP, so feel free to add more functions to this project.

## Usage

first install the project with:

```
pip install  -e 'git+https://github.com/GeoNodeUserGroup-DE/geonodectl.git@main#egg=geonodectl'
```

Additionally to package install, **geonodectl** requires to set two environment variables to connect to a geonode instance like:
```
GEONODE_API_URL: https://master.demo.geonode.org/api/v2/ # make sure to supply full api url
GEONODE_API_BASIC_AUTH: dXNlcjpwYXNzd29yZA== # you can generate this string like: echo -n user:password | base64
```

Now you are ready to go. upload shape file:
```
❯ ./geonodectl ds upload -f ~/data/geolocation.shp -t example-shape
| key     | value                                       |
|---------|---------------------------------------------|
| title   | example-shape                               |
| success | True                                        |
| status  | finished                                    |
| bbox    | 13.1832819,52.4059715,13.5891838,52.5867805 |
| crs     | {'type': 'name', 'properties': 'EPSG:4326'} |
| url     | /catalogue/#/dataset/36                     |
```

show all datasets:
```
❯ ./geonodectl dataset list
|   pk | title                       | owner.username   | date                        | is_approved   | is_published   | state     | detail_url                                              |
|------|-----------------------------|------------------|-----------------------------|---------------|----------------|-----------|---------------------------------------------------------|
|   36 | example-shape               | admin            | 2023-02-06T14:52:31.991113Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/36 |
|   35 | gps_mastertable_prieros2015 | thomas           | 2023-02-06T14:16:45.375526Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/35 |
|   34 | layer                       | thomas           | 2023-02-06T10:08:12.182176Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/34 |
|   33 | a__30                       | admin            | 2023-02-03T13:18:27.715898Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/33 |
|   28 | test                        | admin            | 2023-02-03T11:30:00.609472Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/28 |
|   13 | geolocation3                | mwall            | 2023-02-02T12:15:25.477127Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/13 |
|   12 | geolocation2                | mwall            | 2023-02-02T11:53:19.231994Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/12 |
|   11 | geolocation1                | mwall            | 2023-02-02T11:51:28.975906Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/11 |
|    6 | geolocation0                | mwall            | 2023-02-02T11:03:06.859857Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/6  |
|    5 | arh                         | admin            | 2023-01-31T09:11:00Z        | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/5  |
|    4 | data_00                     | admin            | 2023-01-25T15:56:05.026049Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/4  |
|    3 | geolocation                 | admin            | 2023-01-25T15:23:44.439151Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/3  |
|    2 | data_0                      | admin            | 2023-01-25T15:01:51.042680Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/2  |
|    1 | wheaterdata 2004            | admin            | 2023-01-23T10:19:00Z        | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/1  |
```

patch dataset:
```
geonodectl ds patch 36  --set 'category={"identifier": "farming"}'
...
```

patch dataset from jsonb:
```
geonodectl ds patch 36  --json_path 'path_to/your_json_with_attributes_to_patch.json'
```

delete dataset:
```
❯ ./geonodectl ds delete 36
deleted ...
```

check if deleted:
```
./geonodectl ds list
|   pk | title                       | owner.username   | date                        | is_approved   | is_published   | state     | detail_url                                              |
|------|-----------------------------|------------------|-----------------------------|---------------|----------------|-----------|---------------------------------------------------------|
|   35 | gps_mastertable_prieros2015 | thomas           | 2023-02-06T14:16:45.375526Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/35 |
|   34 | layer                       | thomas           | 2023-02-06T10:08:12.182176Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/34 |
|   33 | a__30                       | admin            | 2023-02-03T13:18:27.715898Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/33 |
|   28 | test                        | admin            | 2023-02-03T11:30:00.609472Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/28 |
|   13 | geolocation3                | mwall            | 2023-02-02T12:15:25.477127Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/13 |
|   12 | geolocation2                | mwall            | 2023-02-02T11:53:19.231994Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/12 |
|   11 | geolocation1                | mwall            | 2023-02-02T11:51:28.975906Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/11 |
|    6 | geolocation0                | mwall            | 2023-02-02T11:03:06.859857Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/6  |
|    5 | arh                         | admin            | 2023-01-31T09:11:00Z        | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/5  |
|    4 | data_00                     | admin            | 2023-01-25T15:56:05.026049Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/4  |
|    3 | geolocation                 | admin            | 2023-01-25T15:23:44.439151Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/3  |
|    2 | data_0                      | admin            | 2023-01-25T15:01:51.042680Z | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/2  |
|    1 | wheaterdata 2004            | admin            | 2023-01-23T10:19:00Z        | True          | True           | PROCESSED | https://geonode.corki.bonares.de/catalogue/#/dataset/1  |
```


