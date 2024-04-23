# Fleet notifications


Python script that generates notifications on state changes of Fleet Protocol devices.


## Requirements
Python 3.10.12+

## Usage
To run the script execute the following from the root directory:

```bash
pip3 install -r requirements.txt
python3 -m fleet_notifications <path-to-config-file> [OPTIONS]
```
The script automatically connects to the PostgreSQL database using data from the config file. If you want to override these values, start the server with some of the following options:

|Option|Short|Description|
|------------|-----|--|
|`--username`|`-usr`|Username for the PostgreSQL database|
|`--password`|`-pwd`|Password for the PostgreSQL database|
|`--location`|`-l`  |Location of the database (e.g., `localhost`)|
|`--port`    |`-p`  |Port number (e.g., `5430`)|
|`--database-name`|`-db`|Database name|

Note that these data should comply with the requirements specified in SQLAlchemy [documentation](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls).

### Configuration
The settings can be found in the `config/config.json`, including the database information and parameters for Fleet management connection.