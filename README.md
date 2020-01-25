# rmv-terminal

## Documentation
Official Documentation from RMV: https://opendata.rmv.de/site/start.html
+ API overview: https://www.rmv.de/hapi/
+ XML description:  https://www.rmv.de/hapi/xsd

## Access ID
In order to use the rmv open data API you need a so called 'access id'.
Just register here: https://opendata.rmv.de/site/anmeldeseite.html

You can then store the access id then in a file named `.accecss_id` (must be in the same directory as the `rmv-terminal.py` script). Or simply use the `--token` parameter.

## Example

    rmv-terminal[ master]$ ./rmv-terminal.py Galluswarte --lines "S6" --direction "Messe"
    S6 -> Friedberg (Hessen) Bahnhof: 8m
    S6 -> Friedberg (Hessen) Bahnhof: 23m
    S6 -> Karben-Groß-Karben Bahnhof: 38m
    S6 -> Friedberg (Hessen) Bahnhof: 53m

### Info
Infos are categorized into three categories from RMV.

+ 1: Most important (trains might not operate at all)
+ 2: affectint train times
+ 3: Only information

By default only category 1 info will be displayed and info will always be directed to stderr.

Example

    rmv-terminal[ master]$ ./rmv-terminal.py Hauptwache --info-min-category 2
    U8 -> Frankfurt (Main) Riedberg: 0.5m
    S6 -> Frankfurt (Main) Südbahnhof: 0.5m
    U8 -> Frankfurt (Main) Südbahnhof: 1.4m
    U6 -> Frankfurt (Main) Ostbahnhof: 2.5m
    U6 -> Frankfurt (Main) Hausen: 2.5m
    S9 -> Hanau Hauptbahnhof: 2.5m
    U2 -> Bad Homburg v.d.H.-Gonzenheim (U): 3.5m
    INFO [2]
     +++ Frankfurt: U2 - Busse statt Bahnen auf Teilstrecke am 15.02. von 08:00 Uhr bis 15:00 Uhr +++

## Help

simply append ```--help``` and you get a list of options:

    rmv-terminal[ master]$ ./rmv-terminal.py --help
    usage: rmv-terminal.py [-h] [--direction DIRECTION] [--lines LINES] [-n N]
                           [--debug] [--i3]
                           [--train_stations_csv TRAIN_STATIONS_CSV] [--token TOKEN]
                           [--threshold THRESHOLD] [--duration DURATION]
                           [--cache-duration CACHE_DURATION]
                           [--info-min-category INFO_MIN_CATEGORY] [--no-info]
                           [--more-info]
                           station
    
    positional arguments:
      station               request information for a train station
    
    optional arguments:
      -h, --help            show this help message and exit
      --direction DIRECTION
                            direction of the trains
      --lines LINES         list of lines (separated by comma and negated by !)
      -n N                  (maximum) number of trains to display
      --debug               enable debug logging
      --i3                  i3 mode
      --train_stations_csv TRAIN_STATIONS_CSV
                            path to the train stations csv file (expected to be
                            UTF-8)
      --token TOKEN         API token
      --threshold THRESHOLD
                            a threshold (in minutes) to filter the trains
      --duration DURATION   specify a duration in minutes for which to query the
                            trains
      --cache-duration CACHE_DURATION
                            minutes of cache time (before requesting new data)
      --info-min-category INFO_MIN_CATEGORY
                            filter all infos which are of a lesser category (1 =
                            HIGH, 2 = MED, 3 = LOW)
      --no-info             do not show info for trains
      --more-info           show more detailed info message
